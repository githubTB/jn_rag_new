"""
app.py - RAG API service entrypoint.

Run:
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from api.routes.ingest import router as ingest_router
from api.routes.search import router as search_router
from config.settings import settings
from repositories.upload_repository import UploadRepository
from services.maintenance_service import MaintenanceService
from services.storage import MinioServiceError, MinioStorageService

log_level_name = settings.log_level.upper()
log_level = getattr(logging, log_level_name, logging.INFO)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)5s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / settings.upload_dir


@asynccontextmanager
async def lifespan(_: FastAPI):
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    UploadRepository().initialize()

    logger.info("服务启动")
    logger.info("  log_level      : %s", log_level_name)
    logger.info("  upload_dir     : %s", UPLOAD_DIR)
    logger.info("  db_path        : %s", settings.db_path)
    logger.info(
        "  milvus         : %s:%s collection=%s",
        settings.milvus_host,
        settings.milvus_port,
        settings.milvus_collection,
    )
    logger.info(
        "  embedding      : %s @ %s",
        settings.embedding_model,
        settings.embedding_device,
    )
    logger.info("  vl_backend     : %s", settings.vl_backend or "local-cpu")
    logger.info("  pdf_force_ocr  : %s", settings.pdf_force_ocr)
    logger.info(
        "  minio          : %s bucket=%s secure=%s",
        settings.minio_endpoint,
        settings.minio_bucket,
        settings.minio_secure,
    )
    try:
        MinioStorageService().ensure_bucket()
    except MinioServiceError as exc:
        logger.warning("MinIO 初始化未完成: %s", exc)
    yield
    logger.info("服务关闭")


app = FastAPI(
    title="RAG 知识库",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(search_router)


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": app.title,
            "version": app.version,
            "upload_dir": str(UPLOAD_DIR),
            "db_path": settings.db_path,
            "milvus": {
                "host": settings.milvus_host,
                "port": settings.milvus_port,
                "collection": settings.milvus_collection,
            },
            "embedding": {
                "provider": settings.embedding_provider,
                "model": settings.embedding_model,
                "device": settings.embedding_device,
            },
            "ocr": {
                "backend": settings.vl_backend or "local-cpu",
                "model": settings.vl_model,
                "force_pdf_ocr": settings.pdf_force_ocr,
            },
            "object_storage": {
                "endpoint": settings.minio_endpoint,
                "bucket": settings.minio_bucket,
                "secure": settings.minio_secure,
            },
        }
    )


@app.get("/")
async def index():
    html = STATIC_DIR / "index.html"
    if html.exists():
        return FileResponse(str(html))
    return JSONResponse(
        {
            "message": "RAG API is running",
            "health": "/api/health",
            "upload_folder": "/api/upload/folder",
            "search": "/api/search",
        }
    )


@app.get("/api/files/{task_id}/{file_path:path}")
async def get_uploaded_file(task_id: str, file_path: str):
    safe_task_id = task_id.strip()
    relative = Path(unquote(file_path))
    if not safe_task_id or relative.is_absolute() or ".." in relative.parts:
        raise HTTPException(status_code=400, detail="非法文件路径")

    target = UPLOAD_DIR / safe_task_id / relative
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(str(target))


@app.delete("/api/collection/drop")
async def drop_collection():
    """Clear upload cache, SQLite metadata, MinIO objects, and Milvus collection."""
    result = MaintenanceService().drop_collection_data()
    return JSONResponse(
        {
            "ok": all(item.get("ok", False) for item in result.values()),
            "message": "uploads、SQLite、MinIO、Milvus 清理已执行",
            "details": result,
        }
    )
