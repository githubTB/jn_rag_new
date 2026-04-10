from __future__ import annotations

import shutil
from pathlib import Path

from config.settings import settings
from repositories.upload_repository import UploadRepository
from services.storage import MinioServiceError, MinioStorageService


class MaintenanceService:
    """Handles destructive maintenance operations behind admin-style APIs."""

    def __init__(
        self,
        *,
        upload_root: Path | None = None,
        repository: UploadRepository | None = None,
        storage: MinioStorageService | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[1]
        self.upload_root = upload_root or (project_root / settings.upload_dir)
        self.repository = repository or UploadRepository()
        self.storage = storage

    def drop_collection_data(self) -> dict[str, object]:
        """Clear local cache, SQLite upload metadata, MinIO objects, and Milvus collection."""
        result = {
            "uploads": self._clear_upload_cache(),
            "sqlite": self._reset_sqlite(),
            "minio": self._clear_minio(),
            "milvus": self._clear_milvus(),
        }
        return result

    def _clear_upload_cache(self) -> dict[str, object]:
        removed_entries = 0
        self.upload_root.mkdir(parents=True, exist_ok=True)
        for entry in list(self.upload_root.iterdir()):
            removed_entries += 1
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        return {
            "ok": True,
            "path": str(self.upload_root),
            "removed_entries": removed_entries,
        }

    def _reset_sqlite(self) -> dict[str, object]:
        self.repository.reset()
        return {
            "ok": True,
            "db_path": str(self.repository.db_path),
        }

    def _clear_minio(self) -> dict[str, object]:
        try:
            storage = self.storage or MinioStorageService()
            removed_count = storage.remove_all_objects()
            return {
                "ok": True,
                "bucket": storage.bucket,
                "removed_objects": removed_count,
            }
        except MinioServiceError as exc:
            return {
                "ok": False,
                "bucket": settings.minio_bucket,
                "error": str(exc),
            }

    def _clear_milvus(self) -> dict[str, object]:
        try:
            from pymilvus import connections, utility
        except ImportError:
            return {
                "ok": False,
                "collection": settings.milvus_collection,
                "error": "未安装 pymilvus，无法清理 Milvus",
            }

        try:
            connections.connect(
                alias="default",
                host=settings.milvus_host,
                port=settings.milvus_port,
            )
            if utility.has_collection(settings.milvus_collection):
                utility.drop_collection(settings.milvus_collection)
                dropped = True
            else:
                dropped = False
            connections.disconnect("default")
            return {
                "ok": True,
                "collection": settings.milvus_collection,
                "dropped": dropped,
            }
        except Exception as exc:  # pragma: no cover
            return {
                "ok": False,
                "collection": settings.milvus_collection,
                "error": str(exc),
            }
