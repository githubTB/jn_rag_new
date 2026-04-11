from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


class ApplicationConfig:
    """应用配置类，封装应用的基本配置"""

    def __init__(
        self,
        title: str = "RAG 知识库",
        version: str = "0.2.0",
        debug: bool = False,
        base_dir: Optional[Path] = None,
    ):
        self.title = title
        self.version = version
        self.debug = debug
        self.base_dir = base_dir or Path(__file__).resolve().parents[1]
        self.static_dir = self.base_dir / "static"
        self.routers: list = []
        self.middlewares: list = []
        self.lifespan_handlers: list = []
        self.logger = logging.getLogger(__name__)

    def add_router(self, router: Any) -> "ApplicationConfig":
        """添加路由"""
        self.routers.append(router)
        return self

    def add_middleware(self, middleware: Callable) -> "ApplicationConfig":
        """添加中间件"""
        self.middlewares.append(middleware)
        return self

    def add_lifespan_handler(self, handler: Callable) -> "ApplicationConfig":
        """添加生命周期处理器"""
        self.lifespan_handlers.append(handler)
        return self


class ApplicationFactory:
    """应用工厂类，用于创建和配置FastAPI应用"""

    def __init__(self, config: Optional[ApplicationConfig] = None):
        self.config = config or ApplicationConfig()
        self.logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """应用生命周期管理"""
        self.logger.info("应用启动中...")
        
        # 执行启动前处理
        for handler in self.config.lifespan_handlers:
            if hasattr(handler, "on_startup"):
                await handler.on_startup(app)
        
        yield
        
        # 执行关闭前处理
        self.logger.info("应用关闭中...")
        for handler in self.config.lifespan_handlers:
            if hasattr(handler, "on_shutdown"):
                await handler.on_shutdown(app)

    def create_app(self) -> FastAPI:
        """创建FastAPI应用实例"""
        app = FastAPI(
            title=self.config.title,
            version=self.config.version,
            lifespan=self._lifespan,
            debug=self.config.debug,
        )

        # 配置中间件
        self._setup_middlewares(app)

        # 配置路由
        self._setup_routers(app)

        # 确保必要的目录存在
        self._ensure_directories()

        self.logger.info(f"应用 {self.config.title} v{self.config.version} 创建成功")
        return app

    def _setup_middlewares(self, app: FastAPI):
        """配置中间件"""
        # 默认添加CORS中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 添加自定义中间件
        for middleware in self.config.middlewares:
            app.add_middleware(middleware)

    def _setup_routers(self, app: FastAPI):
        """配置路由"""
        for router in self.config.routers:
            app.include_router(router)

    def _ensure_directories(self):
        """确保必要的目录存在"""
        self.config.static_dir.mkdir(parents=True, exist_ok=True)


class LifespanHandler:
    """生命周期处理器基类"""

    async def on_startup(self, app: FastAPI):
        """应用启动时调用"""
        pass

    async def on_shutdown(self, app: FastAPI):
        """应用关闭时调用"""
        pass
