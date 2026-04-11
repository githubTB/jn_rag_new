from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar("T")


class ServiceRegistry:
    """服务注册器，用于管理服务实例"""

    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._logger = logging.getLogger(__name__)

    def register(self, service_type: Type[T], instance: T) -> "ServiceRegistry":
        """直接注册服务实例"""
        self._services[service_type] = instance
        self._logger.debug(f"Registered service: {service_type.__name__}")
        return self

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        singleton: bool = False,
    ) -> "ServiceRegistry":
        """注册服务工厂函数"""
        self._factories[service_type] = (factory, singleton)
        self._logger.debug(f"Registered factory: {service_type.__name__} (singleton={singleton})")
        return self

    def get(self, service_type: Type[T]) -> Optional[T]:
        """获取服务实例"""
        # 优先检查直接注册的实例
        if service_type in self._services:
            return self._services[service_type]

        # 检查单例缓存
        if service_type in self._singletons:
            return self._singletons[service_type]

        # 检查工厂函数
        if service_type in self._factories:
            factory, singleton = self._factories[service_type]
            instance = factory()
            
            if singleton:
                self._singletons[service_type] = instance
                self._logger.debug(f"Created singleton: {service_type.__name__}")
            else:
                self._logger.debug(f"Created instance: {service_type.__name__}")
            
            return instance

        self._logger.warning(f"Service not found: {service_type.__name__}")
        return None

    def has(self, service_type: Type) -> bool:
        """检查服务是否已注册"""
        return (
            service_type in self._services
            or service_type in self._singletons
            or service_type in self._factories
        )

    def clear(self):
        """清空所有注册的服务"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._logger.debug("Cleared all services")


class Container:
    """依赖注入容器"""

    _instance: Optional["Container"] = None
    _registry: ServiceRegistry

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry = ServiceRegistry()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "Container":
        """获取容器单例"""
        return cls()

    @property
    def registry(self) -> ServiceRegistry:
        """获取服务注册器"""
        return self._registry

    def register(self, service_type: Type[T], instance: T) -> "Container":
        """注册服务实例"""
        self._registry.register(service_type, instance)
        return self

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        singleton: bool = False,
    ) -> "Container":
        """注册服务工厂"""
        self._registry.register_factory(service_type, factory, singleton)
        return self

    def get(self, service_type: Type[T]) -> Optional[T]:
        """获取服务实例"""
        return self._registry.get(service_type)

    def has(self, service_type: Type) -> bool:
        """检查服务是否存在"""
        return self._registry.has(service_type)


def get_container() -> Container:
    """获取依赖注入容器实例"""
    return Container.get_instance()


def inject(service_type: Type[T]) -> T:
    """依赖注入装饰器/函数"""
    container = get_container()
    instance = container.get(service_type)
    if instance is None:
        raise ValueError(f"Service not registered: {service_type.__name__}")
    return instance
