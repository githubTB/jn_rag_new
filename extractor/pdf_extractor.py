"""
extractor/pdf_extractor.py — PDF 提取器。

自动区分两种 PDF：
  文本 PDF（Word 导出、数字原生）→ pypdfium2 直接提取文字层，速度快
  扫描件 PDF（图片扫描进去）    → 转图片 → OCR（PaddleOCR-VL）

判断逻辑：
  每页提取文字，有效字符数 < TEXT_THRESHOLD 视为扫描页
  整个 PDF 超过 SCAN_RATIO 比例的页都是扫描页 → 走 OCR 路径
"""

from __future__ import annotations

import logging
import json
import multiprocessing as mp
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pypdfium2

from config.settings import settings
from .base import BaseExtractor
from models.document import Document

logger = logging.getLogger(__name__)

# 每页有效字符数低于此值视为扫描页（空格/换行不算）
TEXT_THRESHOLD = 30
# 超过此比例的页是扫描页，整个 PDF 走 OCR
SCAN_RATIO = 0.5
PDF_EXTRACT_SUBPROCESS_TIMEOUT = 1800
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_RESULT_PREFIX = "__PDF_EXTRACT_RESULT__="
PDF_OCR_RENDER_DPI = 220
PDF_OCR_MIN_TIMEOUT = 240
PDF_OCR_MAX_PIXELS = 3200
GARBLED_PAGE_RATIO = 0.3
GARBLED_TOKEN_RATIO = 0.2
GARBLED_MIN_TOKENS = 8
GARBLED_RELAXED_TOKEN_RATIO = 0.08
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{3,}")
_VALID_LATIN_WORD_RE = re.compile(r"^[A-Za-z]+(?:['.-][A-Za-z]+)*$")
_CONSONANT_RUN_RE = re.compile(r"[bcdfghjklmnpqrstvwxyz]{4,}", re.IGNORECASE)
_VOWEL_RUN_RE = re.compile(r"[aeiou]{3,}", re.IGNORECASE)
_PDF_BLOCK_SPLIT_RE = re.compile(r"\n\s*\n+")


def _serialize_docs(docs: list[Document]) -> list[dict]:
    return [
        {
            "page_content": doc.page_content,
            "metadata": dict(doc.metadata or {}),
        }
        for doc in docs
    ]


def _deserialize_docs(payload: list[dict]) -> list[Document]:
    return [
        Document(
            page_content=item.get("page_content", ""),
            metadata=dict(item.get("metadata") or {}),
        )
        for item in payload
    ]


def _page_looks_garbled(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True

    latin_tokens = _LATIN_WORD_RE.findall(stripped)
    if not latin_tokens:
        return False

    suspicious = 0
    for token in latin_tokens:
        if not _VALID_LATIN_WORD_RE.match(token):
            suspicious += 1
            continue
        lower = token.lower()
        vowel_count = sum(1 for ch in lower if ch in "aeiou")
        case_transition_count = sum(
            1 for i in range(1, len(token))
            if token[i - 1].isalpha() and token[i].isalpha() and token[i - 1].islower() != token[i].islower()
        )
        if len(token) >= 6 and vowel_count == 0:
            suspicious += 1
        elif len(set(lower)) <= 2 and len(token) >= 5:
            suspicious += 1
        elif len(token) >= 7 and _CONSONANT_RUN_RE.search(lower):
            suspicious += 1
        elif len(token) >= 6 and _VOWEL_RUN_RE.search(lower):
            suspicious += 1
        elif (
            "q" in lower
            and "qu" not in lower
            and "qing" not in lower
            and not token.isupper()
            and len(token) >= 6
        ):
            suspicious += 1
        elif case_transition_count >= 2:
            suspicious += 1

    ratio = suspicious / len(latin_tokens)
    return ratio >= GARBLED_TOKEN_RATIO or (
        suspicious >= GARBLED_MIN_TOKENS and ratio >= GARBLED_RELAXED_TOKEN_RATIO
    )


def _should_force_ocr_by_text_quality(pages_text: list[str]) -> tuple[bool, dict]:
    total_pages = len(pages_text)
    if total_pages == 0:
        return False, {"total_pages": 0, "garbled_pages": 0, "garbled_ratio": 0.0}

    garbled_pages = sum(1 for text in pages_text if _page_looks_garbled(text))
    ratio = garbled_pages / total_pages
    return ratio >= GARBLED_PAGE_RATIO, {
        "total_pages": total_pages,
        "garbled_pages": garbled_pages,
        "garbled_ratio": ratio,
    }

class PdfExtractor(BaseExtractor):

    def __init__(
        self,
        file_path: str,
        extract_images: bool = False,
        doc_type: str = "document",
        # OCR 参数（扫描件时透传给 VL）
        vl_backend: str | None = None,
        vl_base_url: str | None = None,
        device: str | None = None,
        isolate_subprocess: bool = True,
        force_ocr: bool = False,
        **_ignored,
    ):
        self._file_path = file_path
        self._extract_images = extract_images
        self._doc_type = doc_type
        self._isolate_subprocess = isolate_subprocess
        self._force_ocr = force_ocr
        self._vl_kwargs = {k: v for k, v in {
            "vl_backend":    vl_backend,
            "vl_base_url":   vl_base_url,
            "device":        device,
        }.items() if v is not None}

    def extract(self) -> list[Document]:
        if self._should_isolate():
            return self._extract_isolated()
        return self._extract_direct()

    def _should_isolate(self) -> bool:
        if not self._isolate_subprocess:
            return False
        return mp.current_process().name != "MainProcess"

    def _extract_isolated(self) -> list[Document]:
        payload = {
            "file_path": self._file_path,
            "extract_images": self._extract_images,
            "doc_type": self._doc_type,
            "vl_kwargs": self._vl_kwargs,
        }
        child_code = """
import json
import sys
from extractor.pdf_extractor import PdfExtractor, _serialize_docs

payload = json.loads(sys.argv[1])
try:
    extractor = PdfExtractor(
        payload["file_path"],
        extract_images=payload["extract_images"],
        doc_type=payload["doc_type"],
        isolate_subprocess=False,
        **payload["vl_kwargs"],
    )
    result = {"ok": True, "docs": _serialize_docs(extractor._extract_direct())}
except Exception as exc:
    result = {"ok": False, "error": str(exc)}

sys.stdout.write("__PDF_EXTRACT_RESULT__=" + json.dumps(result, ensure_ascii=False) + "\\n")
"""
        try:
            proc = subprocess.run(
                [sys.executable, "-c", child_code, json.dumps(payload, ensure_ascii=False)],
                cwd=str(_PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=PDF_EXTRACT_SUBPROCESS_TIMEOUT,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"PDF 解析超时({PDF_EXTRACT_SUBPROCESS_TIMEOUT}s): {Path(self._file_path).name}"
            ) from exc

        if proc.returncode != 0:
            raise RuntimeError(
                f"PDF 解析子进程异常退出(exitcode={proc.returncode}): "
                f"{Path(self._file_path).name}; stderr={proc.stderr.strip()[:500]}"
            )

        if not proc.stdout.strip():
            raise RuntimeError(f"PDF 解析未返回结果: {Path(self._file_path).name}")

        result_line = None
        for line in reversed(proc.stdout.splitlines()):
            if line.startswith(_RESULT_PREFIX):
                result_line = line[len(_RESULT_PREFIX):]
                break
        if result_line is None:
            raise RuntimeError(
                f"PDF 解析结果缺失: {Path(self._file_path).name}; "
                f"stdout={proc.stdout.strip()[:500]} stderr={proc.stderr.strip()[:500]}"
            )

        result = json.loads(result_line)
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "PDF 解析失败")
        return _deserialize_docs(result.get("docs") or [])

    def _extract_direct(self) -> list[Document]:
        if settings.pdf_force_ocr or self._force_ocr:
            logger.info("[PDF] 已启用 PDF_FORCE_OCR，直接走 OCR: %s", Path(self._file_path).name)
            return self._ocr_fallback()

        pdf = pypdfium2.PdfDocument(self._file_path, autoclose=True)
        try:
            pages_text = self._extract_all_text(pdf)
        finally:
            pdf.close()

        total = len(pages_text)
        scan_pages = sum(1 for t in pages_text if len(t.strip()) < TEXT_THRESHOLD)
        scan_ratio = scan_pages / total if total else 0

        logger.info("[PDF] %s  总页数=%d  扫描页=%d  扫描比例=%.0f%%",
                    Path(self._file_path).name, total, scan_pages, scan_ratio * 100)

        if scan_ratio >= SCAN_RATIO:
            logger.info("[PDF] 判定为扫描件，转图片走 OCR")
            return self._ocr_fallback()

        force_ocr, quality_stats = _should_force_ocr_by_text_quality(pages_text)
        logger.info(
            "[PDF] 文字层质量检测: 总页数=%d  疑似乱码页=%d  比例=%.0f%%",
            quality_stats["total_pages"],
            quality_stats["garbled_pages"],
            quality_stats["garbled_ratio"] * 100,
        )
        if force_ocr:
            logger.info("[PDF] 文字层质量较差，自动切换 OCR")
            return self._ocr_fallback()

        # 文本 PDF：按页内段落/条目拆成结构块，避免整页混在一起。
        docs = []
        global_reading_order = 0
        for page_num, text in enumerate(pages_text):
            blocks = self._split_text_page_into_blocks(text)
            for block_index, block_text in enumerate(blocks):
                docs.append(Document(
                    page_content=block_text,
                    metadata={
                        "source": self._file_path,
                        "page": page_num,
                        "label": "text",
                        "source_parser": "pdf_native",
                        "block_index": block_index,
                        "page_block_total": len(blocks),
                        "reading_order": global_reading_order,
                    },
                ))
                global_reading_order += 1
        logger.info("[PDF] 文本 PDF，提取 %d 个文本块", len(docs))
        return docs

    def _extract_all_text(self, pdf: pypdfium2.PdfDocument) -> list[str]:
        texts = []
        for page in pdf:
            tp = page.get_textpage()
            texts.append(tp.get_text_range())
            tp.close()
            page.close()
        return texts

    def _ocr_fallback(self) -> list[Document]:
        """将 PDF 每页渲染为图片，逐页走 PaddleOCR-VL。"""
        try:
            import pypdfium2 as pdfium
        except ImportError:
            raise ImportError("pypdfium2 未安装")

        docs: list[Document] = []
        pdf = pdfium.PdfDocument(self._file_path, autoclose=True)

        try:
            for page_num, page in enumerate(pdf):
                # 扫描件优先保留细字清晰度，避免工程图/检测报告的小字被压糊。
                bitmap = page.render(scale=PDF_OCR_RENDER_DPI / 72)
                pil_img = bitmap.to_pil()
                page.close()

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    tmp_path = f.name
                try:
                    pil_img.save(tmp_path, "PNG")
                    page_docs = self._ocr_image(tmp_path, page_num)
                    docs.extend(page_docs)
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

        finally:
            pdf.close()

        logger.info("[PDF] 扫描件 OCR 完成，共 %d 页 %d 块", len(set(d.metadata.get('page') for d in docs)), len(docs))
        return docs

    def _split_text_page_into_blocks(self, text: str) -> list[str]:
        normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            return []

        chunks = [part.strip() for part in _PDF_BLOCK_SPLIT_RE.split(normalized) if part.strip()]
        if not chunks:
            return [normalized]

        blocks: list[str] = []
        for chunk in chunks:
            lines = [line.strip() for line in chunk.splitlines() if line.strip()]
            if not lines:
                continue
            if len(lines) == 1:
                blocks.append(lines[0])
                continue

            buffer = lines[0]
            for line in lines[1:]:
                if len(line) <= 28 and any(token in line for token in ("编号", "日期", "有效期", "信用代码", "标准", "范围")):
                    blocks.append(buffer.strip())
                    buffer = line
                    continue
                if len(buffer) + len(line) <= 800:
                    buffer = f"{buffer}\n{line}".strip()
                else:
                    blocks.append(buffer.strip())
                    buffer = line
            if buffer.strip():
                blocks.append(buffer.strip())

        return blocks or [normalized]

    def _ocr_image(self, img_path: str, page_num: int) -> list[Document]:
        from extractor.ocr_router import route_ocr
        from config.settings import settings

        vl_kwargs = {}
        if settings.vl_backend:
            vl_kwargs["vl_backend"] = settings.vl_backend
        if settings.vl_base_url:
            vl_kwargs["vl_base_url"] = settings.vl_base_url
        if settings.vl_model:
            vl_kwargs["vl_model"] = settings.vl_model
        if settings.vl_device:
            vl_kwargs["device"] = settings.vl_device
        if settings.vl_timeout:
            vl_kwargs["timeout"] = max(settings.vl_timeout, PDF_OCR_MIN_TIMEOUT)
        vl_kwargs["max_pixels"] = max(settings.vl_max_px, PDF_OCR_MAX_PIXELS)

        try:
            page_docs = route_ocr(img_path, doc_type=self._doc_type, **vl_kwargs)
        except Exception as exc:
            logger.error("[PDF] 第 %d 页 OCR 失败: %s", page_num, exc)
            return []

        for doc in page_docs:
            doc.metadata["source"] = self._file_path
            doc.metadata["page"] = page_num
            doc.metadata.setdefault("source_parser", "pdf_ocr_or_layout")

        return page_docs
