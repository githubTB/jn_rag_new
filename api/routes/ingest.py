from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from models.upload import UploadBatchResult, UploadedFileRecord
from repositories.upload_repository import UploadRepository
from schemas.upload import UploadBatchResponse, UploadedFileResponse
from services.upload_service import UploadService

router = APIRouter(prefix="/api", tags=["ingest"])


def _cache_file_url(task_id: str, relative_path: str) -> str:
    encoded_relative_path = "/".join(quote(part) for part in relative_path.split("/"))
    return f"/api/files/{quote(task_id)}/{encoded_relative_path}"


def _serialize_file(request: Request, task_id: str, file: UploadedFileRecord) -> UploadedFileResponse:
    """Build API response payload for one uploaded file."""
    cache_url = _cache_file_url(task_id, file.relative_path)
    return UploadedFileResponse(
        filename=file.filename,
        relative_path=file.relative_path,
        cache_path=file.cache_path,
        cache_url=str(request.base_url).rstrip("/") + cache_url,
        size=file.size,
        content_type=file.content_type,
        content_hash=file.content_hash,
        bucket=file.bucket,
        object_key=file.object_key,
        object_url=file.object_url,
        etag=file.etag,
        version_id=file.version_id,
        deduplicated=file.deduplicated,
        processing_required=file.processing_required,
    )


def _serialize_batch(request: Request, batch: UploadBatchResult) -> UploadBatchResponse:
    """Keep route response formatting separate from the core upload flow."""
    return UploadBatchResponse(
        ok=True,
        message="上传完成，MinIO 为主存储，本地文件作为缓存，元数据已写入 SQLite",
        task_id=batch.task_id,
        cache_root=batch.cache_root,
        bucket=batch.bucket,
        company_name=batch.company_name,
        company_credit_code=batch.company_credit_code,
        chapter=batch.chapter,
        file_count=batch.file_count,
        total_bytes=batch.total_bytes,
        files=[_serialize_file(request, batch.task_id, file) for file in batch.files],
        sqlite_db_path=batch.sqlite_db_path,
    )


@router.post("/upload/folder", response_model=UploadBatchResponse)
async def upload_folder(
    request: Request,
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(...),
    task_id: str = Form(...),
    company_name: str = Form(...),
    company_credit_code: str | None = Form(None),
    chapter: str = Form(...),
):
    """Receive frontend folder upload and delegate all business logic to the service layer."""
    batch = await UploadService().upload_folder(
        files=files,
        relative_paths=relative_paths,
        task_id=task_id,
        company_name=company_name,
        company_credit_code=company_credit_code,
        chapter=chapter,
    )
    return _serialize_batch(request, batch)


@router.get("/upload/{task_id}", response_model=UploadBatchResponse)
async def get_upload_batch(task_id: str, request: Request):
    """Query one upload batch from SQLite for frontend playback or debugging."""
    batch = UploadRepository().get_batch(task_id.strip())
    if batch is None:
        raise HTTPException(status_code=404, detail="上传批次不存在")
    return _serialize_batch(request, batch)
