from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class UploadedFileRecord:
    """Represents one task-bound file after deduplication and object storage lookup."""

    filename: str
    relative_path: str
    cache_path: str
    size: int
    content_type: str | None
    content_hash: str
    bucket: str
    object_key: str
    object_url: str
    etag: str | None
    version_id: str | None
    deduplicated: bool
    processing_required: bool


@dataclass(frozen=True)
class UploadBatchResult:
    """Represents the whole upload batch that should be persisted to SQLite."""

    task_id: str
    company_name: str
    company_credit_code: str | None
    chapter: str
    cache_root: str
    bucket: str
    sqlite_db_path: str
    file_count: int
    total_bytes: int
    files: list[UploadedFileRecord] = field(default_factory=list)
