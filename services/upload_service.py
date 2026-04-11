from __future__ import annotations

import logging
import sqlite3
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, UploadFile

from config.settings import settings
from core.base import BaseService
from models.upload import UploadBatchResult, UploadedFileRecord
from repositories.upload_repository import UploadRepository
from services.storage import (
    MinioServiceError,
    MinioStorageService,
    build_minio_object_key,
)


class UploadService(BaseService):
    """Encapsulates upload flow so API layer only coordinates request/response."""

    def __init__(
        self,
        *,
        upload_root: Path | None = None,
        storage: MinioStorageService | None = None,
        repository: UploadRepository | None = None,
    ) -> None:
        super().__init__()
        project_root = Path(__file__).resolve().parents[1]
        self.upload_root = upload_root or (project_root / settings.upload_dir)
        self.storage = storage or MinioStorageService()
        self.repository = repository or UploadRepository()

    async def initialize(self) -> None:
        """初始化服务"""
        self.logger.info("初始化UploadService")
        # 确保上传目录存在
        self.upload_root.mkdir(parents=True, exist_ok=True)
        # 初始化仓储
        self.repository.initialize()

    async def shutdown(self) -> None:
        """关闭服务"""
        self.logger.info("关闭UploadService")
        # 关闭仓储连接
        self.repository.close()

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

        saved_files: list[UploadedFileRecord] = []
        total_bytes = 0

        for upload_file, raw_relative_path in zip(files, relative_paths):
            safe_relative_path = self._safe_relative_path(raw_relative_path)
            # 直接保存到uploads根目录，不使用task_id子目录
            destination = self.upload_root / safe_relative_path.name
            if destination.exists() and destination.is_dir():
                raise HTTPException(status_code=400, detail=f"目标路径已存在目录: {raw_relative_path}")

            # 首先保存文件到临时位置，用于计算哈希
            temp_destination = destination.with_suffix(".tmp")
            file_size = await self._save_upload_file(upload_file, temp_destination)
            
            # 计算文件的content_hash（使用MD5哈希值）
            content_hash = self._calculate_file_hash(temp_destination)
            
            # 检查文件是否已经存在（去重逻辑）
            existing_file = self.repository.get_stored_file_by_hash(content_hash)
            
            if existing_file:
                # 如果文件已经存在，直接使用现有文件，删除临时文件
                temp_destination.unlink()
                total_bytes += existing_file["size"]
                # 创建文件记录，使用现有文件的信息
                saved_files.append(
                    UploadedFileRecord(
                        filename=upload_file.filename or safe_relative_path.name,
                        relative_path=safe_relative_path.as_posix(),
                        cache_path=existing_file["cache_path"],
                        size=existing_file["size"],
                        content_type=upload_file.content_type,
                        content_hash=content_hash,
                        bucket=existing_file["bucket"],
                        object_key=existing_file["object_key"],
                        object_url=existing_file["object_url"],
                        etag=existing_file["etag"],
                        version_id=existing_file["version_id"],
                        deduplicated=True,
                        processing_required=True,
                    )
                )
            else:
                # 如果文件不存在，重命名临时文件为最终文件名，然后上传到MinIO
                temp_destination.rename(destination)
                total_bytes += file_size
                # 直接使用文件名作为object_key，不包含task_id
                object_key = build_minio_object_key(safe_relative_path.name)

                try:
                    uploaded_object = self.storage.upload_file(
                        source_path=destination,
                        object_key=object_key,
                        content_type=upload_file.content_type,
                    )
                    object_url = self.storage.presigned_get_url(object_key=object_key)
                except MinioServiceError as exc:
                    # 如果上传失败，删除文件
                    if destination.exists():
                        destination.unlink()
                    raise HTTPException(
                        status_code=502,
                        detail=f"上传到 MinIO 失败: {safe_relative_path.as_posix()} - {exc}",
                    ) from exc

                # 创建新的文件记录
                saved_files.append(
                    UploadedFileRecord(
                        filename=upload_file.filename or safe_relative_path.name,
                        relative_path=safe_relative_path.as_posix(),
                        cache_path=str(destination),
                        size=file_size,
                        content_type=upload_file.content_type,
                        content_hash=content_hash,
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
            cache_root=str(self.upload_root),
            bucket=settings.minio_bucket,
            sqlite_db_path=str(self.repository.db_path),
            file_count=len(saved_files),
            total_bytes=total_bytes,
            files=saved_files,
        )
        self.repository.save_batch(batch)

        self.logger.info(
            "[Upload] 企业=%s task_id=%s 章节=%s 文件数=%d 总大小=%dB",
            final_company_name,
            final_task_id,
            final_chapter,
            len(saved_files),
            total_bytes,
        )
        return batch

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件的MD5哈希值，用于去重"""
        import hashlib
        content_hash = ""
        try:
            with open(file_path, "rb") as f:
                hasher = hashlib.md5()
                while chunk := f.read(8192):
                    hasher.update(chunk)
                content_hash = hasher.hexdigest()
        except Exception as e:
            self.logger.error(f"计算文件哈希失败: {e}")
        return content_hash
    
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

    async def replace_file(
        self,
        *, 
        file_id: str,
        upload_file: UploadFile,
    ) -> tuple[UploadedFileRecord, str]:
        """Replace an existing file with a new one, updating metadata and storage."""
        """返回值：(替换后的文件记录, 任务ID)"""

        # 获取原文件信息
        file_info = self.repository.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        task_id = file_info["task_id"]
        old_filename = file_info["filename"]
        relative_path = file_info["relative_path"]
        old_stored_file_id = file_info["stored_file_id"]
        
        # 从上传的文件中获取文件名
        new_filename = upload_file.filename or "unknown_file"
        # 安全处理新文件名
        safe_new_filename = self._safe_relative_path(new_filename).name
        # 构建新文件路径
        destination = self.upload_root / safe_new_filename
        # 使用新文件名作为relative_path
        relative_path = safe_new_filename
        
        # 首先保存文件到临时位置，用于计算哈希
        temp_destination = destination.with_suffix(".tmp")
        file_size = await self._save_upload_file(upload_file, temp_destination)
        
        # 计算文件的content_hash（使用MD5哈希值，这是网上流行的RAG知识库去重逻辑）
        content_hash = self._calculate_file_hash(temp_destination)
        
        # 检查文件是否已经存在（去重逻辑）
        existing_file = self.repository.get_stored_file_by_hash(content_hash)
        
        if existing_file:
            # 如果文件已经存在，直接使用现有文件，删除临时文件
            temp_destination.unlink()
            # 创建新的文件记录，使用现有文件的信息
            new_file = UploadedFileRecord(
                filename=new_filename,
                relative_path=relative_path,
                cache_path=existing_file["cache_path"],
                size=existing_file["size"],
                content_type=upload_file.content_type,
                content_hash=content_hash,
                bucket=existing_file["bucket"],
                object_key=existing_file["object_key"],
                object_url=existing_file["object_url"],
                etag=existing_file["etag"],
                version_id=existing_file["version_id"],
                deduplicated=True,
                processing_required=True,
            )
        else:
            # 如果文件不存在，重命名临时文件为最终文件名，然后上传到MinIO
            temp_destination.rename(destination)
            # 直接使用新文件名作为object_key，不包含task_id
            object_key = build_minio_object_key(safe_new_filename)
            try:
                uploaded_object = self.storage.upload_file(
                    source_path=destination,
                    object_key=object_key,
                    content_type=upload_file.content_type,
                )
                object_url = self.storage.presigned_get_url(object_key=object_key)
            except MinioServiceError as exc:
                # 如果上传失败，删除文件
                if destination.exists():
                    destination.unlink()
                raise HTTPException(
                    status_code=502,
                    detail=f"上传到 MinIO 失败: {safe_new_filename} - {exc}",
                ) from exc
            
            # 创建新的文件记录
            new_file = UploadedFileRecord(
                filename=new_filename,
                relative_path=relative_path,
                cache_path=str(destination),
                size=file_size,
                content_type=upload_file.content_type,
                content_hash=content_hash,
                bucket=uploaded_object.bucket,
                object_key=uploaded_object.object_key,
                object_url=object_url,
                etag=uploaded_object.etag,
                version_id=uploaded_object.version_id,
                deduplicated=False,
                processing_required=True,
            )
        
        # 更新数据库
        try:
            # 调用repository的replace_file方法，使用正确的stored_file_id
            self.repository.replace_file(old_stored_file_id, new_file)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        
        self.logger.info(
            "[Replace] 文件=%s task_id=%s 已被覆盖",
            old_filename,
            task_id,
        )
        return new_file, task_id
