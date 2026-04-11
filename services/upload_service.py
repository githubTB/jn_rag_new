from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, UploadFile

from config.settings import settings
from models.upload import UploadBatchResult, UploadedFileRecord
from repositories.upload_repository import UploadRepository
from services.storage import (
    MinioServiceError,
    MinioStorageService,
    build_minio_object_key,
)

logger = logging.getLogger(__name__)


class UploadService:
    """Encapsulates upload flow so API layer only coordinates request/response."""

    def __init__(
        self,
        *,
        upload_root: Path | None = None,
        storage: MinioStorageService | None = None,
        repository: UploadRepository | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[1]
        self.upload_root = upload_root or (project_root / settings.upload_dir)
        self.storage = storage or MinioStorageService()
        self.repository = repository or UploadRepository()

    async def upload_folder(
        self,
        *,
        files: list[UploadFile],
        relative_paths: list[str],
        task_id: str,
        company_name: str,
        company_credit_code: str | None,
        chapter: str,
    ) -> UploadBatchResult:
        """Save files to local cache, upload to MinIO, then persist metadata to SQLite."""
        if not files:
            raise HTTPException(status_code=400, detail="files 不能为空")
        if len(files) != len(relative_paths):
            raise HTTPException(status_code=400, detail="files 和 relative_paths 数量不一致")

        final_task_id = self._safe_segment(task_id, "task_id")
        final_company_name = company_name.strip()
        if not final_company_name:
            raise HTTPException(status_code=400, detail="company_name 不能为空")
        final_chapter = chapter.strip()
        if not final_chapter:
            raise HTTPException(status_code=400, detail="chapter 不能为空")

        task_root = self.upload_root / final_task_id
        task_root.mkdir(parents=True, exist_ok=True)

        saved_files: list[UploadedFileRecord] = []
        total_bytes = 0

        for upload_file, raw_relative_path in zip(files, relative_paths):
            safe_relative_path = self._safe_relative_path(raw_relative_path)
            destination = task_root / safe_relative_path
            if destination.exists() and destination.is_dir():
                raise HTTPException(status_code=400, detail=f"目标路径已存在目录: {raw_relative_path}")

            file_size = await self._save_upload_file(upload_file, destination)
            total_bytes += file_size
            object_key = build_minio_object_key(final_task_id, safe_relative_path.as_posix())

            try:
                uploaded_object = self.storage.upload_file(
                    source_path=destination,
                    object_key=object_key,
                    content_type=upload_file.content_type,
                )
                object_url = self.storage.presigned_get_url(object_key=object_key)
            except MinioServiceError as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"上传到 MinIO 失败: {safe_relative_path.as_posix()} - {exc}",
                ) from exc

            saved_files.append(
                UploadedFileRecord(
                    filename=upload_file.filename or safe_relative_path.name,
                    relative_path=safe_relative_path.as_posix(),
                    cache_path=str(destination),
                    size=file_size,
                    content_type=upload_file.content_type,
                    content_hash="",
                    bucket=uploaded_object.bucket,
                    object_key=uploaded_object.object_key,
                    object_url=object_url,
                    etag=uploaded_object.etag,
                    version_id=uploaded_object.version_id,
                    deduplicated=False,
                    processing_required=True,
                )
            )

        batch = UploadBatchResult(
            task_id=final_task_id,
            company_name=final_company_name,
            company_credit_code=(company_credit_code or "").strip() or None,
            chapter=final_chapter,
            cache_root=str(task_root),
            bucket=settings.minio_bucket,
            sqlite_db_path=str(self.repository.db_path),
            file_count=len(saved_files),
            total_bytes=total_bytes,
            files=saved_files,
        )
        self.repository.save_batch(batch)

        logger.info(
            "[Upload] 企业=%s task_id=%s 章节=%s 文件数=%d 总大小=%dB",
            final_company_name,
            final_task_id,
            final_chapter,
            len(saved_files),
            total_bytes,
        )
        return batch

    def _safe_relative_path(self, raw_path: str) -> Path:
        """Reject unsafe traversal paths from frontend relative file paths."""
        candidate = PurePosixPath((raw_path or "").strip())
        if not candidate.parts:
            raise HTTPException(status_code=400, detail="relative_paths 中包含空路径")
        if candidate.is_absolute() or ".." in candidate.parts:
            raise HTTPException(status_code=400, detail=f"非法相对路径: {raw_path}")
        return Path(*candidate.parts)

    def _safe_segment(self, value: str, field_name: str) -> str:
        """Keep task identifiers safe for local paths and object keys."""
        cleaned = (value or "").strip()
        if not cleaned:
            raise HTTPException(status_code=400, detail=f"{field_name} 不能为空")
        if any(ch in cleaned for ch in ("/", "\\", "\x00")):
            raise HTTPException(status_code=400, detail=f"{field_name} 包含非法字符")
        return cleaned

    async def _save_upload_file(self, upload_file: UploadFile, destination: Path) -> int:
        """Persist uploaded content to local cache before object storage upload."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with destination.open("wb") as target:
            while True:
                chunk = await upload_file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                target.write(chunk)
        await upload_file.close()
        return size
