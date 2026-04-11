"""
app.py - 面向对象优化后的RAG API服务入口点

使用ApplicationFactory和依赖注入容器，提供更好的代码组织和可维护性
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from api.routes.ingest import router as ingest_router
from api.routes.search import router as search_router
from config.settings import settings
from core.application import ApplicationConfig, ApplicationFactory, LifespanHandler
from core.di import get_container
from repositories.upload_repository import UploadRepository
from services.maintenance_service import MaintenanceService
from services.storage import MinioServiceError, MinioStorageService
from services.upload_service import UploadService


class RAGLifespanHandler(LifespanHandler):
    """RAG应用生命周期处理器"""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.base_dir = Path(__file__).resolve().parent
        self.upload_dir = self.base_dir / settings.upload_dir

    async def on_startup(self, app: FastAPI):
        """应用启动时执行"""
        self._setup_directories()
        self._initialize_repositories()
        self._setup_storage()
        self._log_startup_info()
        await self._register_services()

    async def on_shutdown(self, app: FastAPI):
        """应用关闭时执行"""
        self.logger.info("正在清理资源...")
        # 关闭服务
        container = get_container()
        if container.has(UploadService):
            upload_service = container.get(UploadService)
            if upload_service:
                await upload_service.shutdown()
        if container.has(UploadRepository):
            upload_repo = container.get(UploadRepository)
            if upload_repo:
                upload_repo.close()
        if container.has(MinioStorageService):
            minio_service = container.get(MinioStorageService)
            if minio_service:
                await minio_service.shutdown()
        if container.has(MaintenanceService):
            maintenance_service = container.get(MaintenanceService)
            if maintenance_service:
                await maintenance_service.shutdown()

    def _setup_directories(self):
        """设置必要的目录"""
        (self.base_dir / "static").mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def _initialize_repositories(self):
        """初始化仓储"""
        UploadRepository().initialize()

    def _setup_storage(self):
        """设置存储"""
        try:
            MinioStorageService().ensure_bucket()
        except MinioServiceError as exc:
            self.logger.warning("MinIO 初始化未完成: %s", exc)

    def _log_startup_info(self):
        """记录启动信息"""
        self.logger.info("服务启动")
        self.logger.info("  log_level      : %s", settings.log_level.upper())
        self.logger.info("  upload_dir     : %s", self.upload_dir)
        self.logger.info("  db_path        : %s", settings.db_path)
        self.logger.info(
            "  milvus         : %s:%s collection=%s",
            settings.milvus_host,
            settings.milvus_port,
            settings.milvus_collection,
        )
        self.logger.info(
            "  embedding      : %s @ %s",
            settings.embedding_model,
            settings.embedding_device,
        )
        self.logger.info("  vl_backend     : %s", settings.vl_backend or "local-cpu")
        self.logger.info("  pdf_force_ocr  : %s", settings.pdf_force_ocr)
        self.logger.info(
            "  minio          : %s bucket=%s secure=%s",
            settings.minio_endpoint,
            settings.minio_bucket,
            settings.minio_secure,
        )

    async def _register_services(self):
        """注册服务到容器"""
        container = get_container()
        
        # 注册MinioStorageService
        try:
            minio_service = MinioStorageService()
            await minio_service.initialize()
            container.register(MinioStorageService, minio_service)
        except MinioServiceError as exc:
            self.logger.warning(f"MinIO 服务初始化失败: {exc}")
        
        # 注册UploadService
        upload_service = UploadService()
        await upload_service.initialize()
        container.register(UploadService, upload_service)
        
        # 注册UploadRepository
        upload_repo = UploadRepository()
        upload_repo.initialize()
        container.register(UploadRepository, upload_repo)
        
        # 注册MaintenanceService
        maintenance_service = MaintenanceService()
        await maintenance_service.initialize()
        container.register(MaintenanceService, maintenance_service)

    async def on_startup(self, app: FastAPI):
        """应用启动时执行"""
        self._setup_directories()
        self._initialize_repositories()
        self._setup_storage()
        self._log_startup_info()
        await self._register_services()


def create_rag_app() -> FastAPI:
    """创建RAG应用"""
    config = ApplicationConfig(
        title="RAG 知识库",
        version="0.2.0",
        debug=settings.log_level.upper() == "DEBUG",
    )

    config.add_router(ingest_router)
    config.add_router(search_router)
    config.add_lifespan_handler(RAGLifespanHandler())

    factory = ApplicationFactory(config)
    app = factory.create_app()
    setup_routes(app)
    return app


def setup_routes(app: FastAPI):
    """设置应用路由"""
    base_dir = Path(__file__).resolve().parent
    static_dir = base_dir / "static"
    upload_dir = base_dir / settings.upload_dir

    @app.get("/api/health")
    async def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": app.title,
                "version": app.version,
                "upload_dir": str(upload_dir),
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
        html = static_dir / "index.html"
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

        target = upload_dir / safe_task_id / relative
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail="文件不存在")
        return FileResponse(str(target))

    @app.delete("/api/collection/drop")
    async def drop_collection():
        result = MaintenanceService().drop_collection_data()
        return JSONResponse(
            {
                "ok": all(item.get("ok", False) for item in result.values()),
                "message": "uploads、SQLite、MinIO、Milvus 清理已执行",
                "details": result,
            }
        )


def setup_logging():
    """设置日志"""
    log_level_name = settings.log_level.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)5s] %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )


setup_logging()
app = create_rag_app()
