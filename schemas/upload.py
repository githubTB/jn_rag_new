from __future__ import annotations

from pydantic import BaseModel


class UploadedFileResponse(BaseModel):
    """API response model for one uploaded file."""

    filename: str
    relative_path: str
    cache_path: str
    cache_url: str
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


class UploadBatchResponse(BaseModel):
    """API response model for a whole frontend folder upload."""

    ok: bool
    message: str
    task_id: str
    cache_root: str
    bucket: str
    company_name: str
    company_credit_code: str | None
    chapter: str
    file_count: int
    total_bytes: int
    files: list[UploadedFileResponse]
    sqlite_db_path: str
