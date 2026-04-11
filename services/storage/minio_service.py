from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import timedelta

from config.settings import settings
from core.base import BaseService

try:
    from minio import Minio
    from minio.deleteobjects import DeleteObject
    from minio.error import S3Error
except ImportError:  # pragma: no cover
    Minio = None  # type: ignore[assignment]
    DeleteObject = None  # type: ignore[assignment]
    S3Error = Exception  # type: ignore[assignment]


class MinioServiceError(RuntimeError):
    """Raised when object storage is unavailable or misconfigured."""


@dataclass(frozen=True)
class UploadedObject:
    bucket: str
    object_key: str
    etag: str | None
    version_id: str | None


class MinioStorageService(BaseService):
    def __init__(self) -> None:
        super().__init__()
        if Minio is None:
            raise MinioServiceError(
                "未安装 minio 依赖，请先安装 `minio` Python SDK"
            )
        if not settings.minio_access_key or not settings.minio_secret_key:
            raise MinioServiceError("MinIO 访问凭据未配置")

        self.bucket = settings.minio_bucket
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            region=settings.minio_region,
        )

    async def initialize(self) -> None:
        """初始化服务"""
        self.logger.info("初始化MinioStorageService")
        try:
            self.ensure_bucket()
            self.logger.info(f"MinIO bucket {self.bucket} 初始化成功")
        except MinioServiceError as exc:
            self.logger.warning(f"MinIO 初始化未完成: {exc}")

    async def shutdown(self) -> None:
        """关闭服务"""
        self.logger.info("关闭MinioStorageService")
        # MinIO 客户端不需要特殊关闭操作

    def ensure_bucket(self) -> None:
        try:
            exists = self.client.bucket_exists(self.bucket)
        except S3Error as exc:  # pragma: no cover
            raise MinioServiceError(f"检查 bucket 失败: {exc}") from exc

        if exists:
            return
        if not settings.minio_auto_create_bucket:
            raise MinioServiceError(f"bucket 不存在: {self.bucket}")

        try:
            self.client.make_bucket(self.bucket, location=settings.minio_region)
        except S3Error as exc:  # pragma: no cover
            raise MinioServiceError(f"创建 bucket 失败: {exc}") from exc

    def upload_file(
        self,
        *,
        source_path: Path,
        object_key: str,
        content_type: str | None = None,
    ) -> UploadedObject:
        self.ensure_bucket()
        try:
            result = self.client.fput_object(
                bucket_name=self.bucket,
                object_name=object_key,
                file_path=str(source_path),
                content_type=content_type,
            )
        except S3Error as exc:  # pragma: no cover
            raise MinioServiceError(f"上传对象失败: {exc}") from exc

        return UploadedObject(
            bucket=self.bucket,
            object_key=object_key,
            etag=getattr(result, "etag", None),
            version_id=getattr(result, "version_id", None),
        )

    def presigned_get_url(
        self,
        *,
        object_key: str,
        expires: timedelta = timedelta(hours=settings.minio_presigned_expires_hours),
    ) -> str:
        try:
            return self.client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=object_key,
                expires=expires,
            )
        except S3Error as exc:  # pragma: no cover
            raise MinioServiceError(f"生成对象访问链接失败: {exc}") from exc

    def remove_all_objects(self) -> int:
        """Delete every object in the configured bucket and return the removed count."""
        self.ensure_bucket()
        try:
            objects = list(self.client.list_objects(self.bucket, recursive=True))
            if not objects:
                return 0

            errors = list(
                self.client.remove_objects(
                    self.bucket,
                    [DeleteObject(obj.object_name) for obj in objects],
                )
            )
        except S3Error as exc:  # pragma: no cover
            raise MinioServiceError(f"清理 MinIO 对象失败: {exc}") from exc

        if errors:
            raise MinioServiceError(f"清理 MinIO 对象失败: {errors[0]}")
        return len(objects)


def build_minio_object_key(*parts: str) -> str:
    normalized: list[str] = []
    for part in parts:
        for segment in str(part).replace("\\", "/").split("/"):
            segment = segment.strip()
            if segment:
                normalized.append(segment)
    return "/".join(normalized)
