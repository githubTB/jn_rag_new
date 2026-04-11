# 面向对象优化指南

## 概述

本项目进行了全面的面向对象重构，以提高代码的可维护性、可扩展性和可测试性。

## 新增文件

### 1. `core/application.py` - 应用工厂类

**主要类**:
- `ApplicationConfig`: 封装应用配置，支持链式调用添加路由、中间件和生命周期处理器
- `ApplicationFactory`: 工厂类，负责创建和配置FastAPI应用实例
- `LifespanHandler`: 生命周期处理器基类

**使用示例**:
```python
from core.application import ApplicationConfig, ApplicationFactory, LifespanHandler

config = ApplicationConfig(title="我的应用", version="1.0.0")
config.add_router(my_router)
config.add_lifespan_handler(MyLifespanHandler())

factory = ApplicationFactory(config)
app = factory.create_app()
```

### 2. `core/di.py` - 依赖注入容器

**主要类**:
- `ServiceRegistry`: 服务注册器，管理服务实例和工厂
- `Container`: 依赖注入容器，使用单例模式
- 辅助函数: `get_container()`, `inject()`

**使用示例**:
```python
from core.di import get_container

container = get_container()
container.register_factory(MyService, lambda: MyService(), singleton=True)

service = container.get(MyService)
```

### 3. `core/base.py` - 基类和接口

**主要基类**:
- `BaseService`: 服务基类，定义initialize和shutdown方法
- `BaseRepository`: 仓储基类，定义initialize和close方法
- `BaseExtractor`: 提取器基类，定义extract和extract_text方法
- `SingletonMeta`: 单例元类
- `ThreadSafeSingletonMeta`: 线程安全的单例元类
- `Factory[T]`: 工厂基类

### 4. `app_v2.py` - 优化后的应用入口

使用新的应用工厂和依赖注入容器重构的应用入口。

## 设计模式应用

### 1. 工厂模式
- `ApplicationFactory`: 创建FastAPI应用
- `Factory[T]`: 通用工厂基类

### 2. 单例模式
- `SingletonMeta`: 非线程安全的单例元类
- `ThreadSafeSingletonMeta`: 线程安全的单例元类
- `Container`: 依赖注入容器使用单例

### 3. 依赖注入模式
- `Container`: 管理服务实例的生命周期
- 支持单例和非单例服务

### 4. 模板方法模式
- `LifespanHandler`: 定义生命周期处理的模板方法

### 5. 策略模式
- `BaseExtractor`: 不同文件类型的提取策略

## 迁移指南

### 从app.py迁移到app_v2.py

1. **保留原app.py**: 原文件仍然可以正常使用
2. **使用新架构**: 新功能可以使用app_v2.py的架构
3. **逐步迁移**: 可以逐步将代码迁移到新架构

### 使用依赖注入

```python
# 旧方式
service = UploadService()

# 新方式
from core.di import get_container
container = get_container()
service = container.get(UploadService)
```

### 创建自定义生命周期处理器

```python
from core.application import LifespanHandler

class MyLifespanHandler(LifespanHandler):
    async def on_startup(self, app):
        self.logger.info("应用启动")
        # 初始化逻辑
    
    async def on_shutdown(self, app):
        self.logger.info("应用关闭")
        # 清理逻辑
```

## 优势

1. **更好的代码组织**: 职责分离清晰
2. **易于测试**: 依赖注入使得单元测试更容易
3. **可扩展性**: 通过基类和接口轻松扩展功能
4. **可维护性**: 代码结构清晰，易于理解和修改
5. **灵活性**: 可以灵活配置应用行为

## 下一步

1. 逐步将现有的服务类迁移到使用基类
2. 完善依赖注入的使用
3. 添加更多的单元测试
4. 考虑添加配置管理的进一步优化
