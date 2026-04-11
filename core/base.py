from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


class BaseService(ABC):
    """服务基类"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def initialize(self) -> None:
        """初始化服务"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """关闭服务"""
        pass


class BaseRepository(ABC):
    """仓储基类"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def initialize(self) -> None:
        """初始化仓储"""
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭仓储连接"""
        pass


class BaseExtractor(ABC):
    """提取器基类"""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def extract(self) -> list[Any]:
        """提取内容"""
        pass

    @abstractmethod
    def extract_text(self, separator: str = "\n\n") -> str:
        """提取文本内容"""
        pass


class SingletonMeta(type):
    """单例元类"""

    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class ThreadSafeSingletonMeta(type):
    """线程安全的单例元类"""

    import threading

    _lock: threading.Lock = threading.Lock()
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


class Factory(Generic[T]):
    """工厂基类"""

    def __init__(self):
        self._creators: dict[str, type[T]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def register(self, key: str, creator: type[T]) -> "Factory[T]":
        """注册创建器"""
        self._creators[key] = creator
        self.logger.debug(f"Registered creator: {key}")
        return self

    def create(self, key: str, *args, **kwargs) -> Optional[T]:
        """创建实例"""
        creator = self._creators.get(key)
        if creator is None:
            self.logger.warning(f"Creator not found: {key}")
            return None
        return creator(*args, **kwargs)

    def list_creators(self) -> list[str]:
        """列出所有注册的创建器"""
        return list(self._creators.keys())
