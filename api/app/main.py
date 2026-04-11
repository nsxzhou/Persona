# 未来语法导入：让Python支持更新的类型注解语法，兼容旧版本Python
# 这行是Python 3.7+的特性，用于解决类型注解的前向引用问题
from __future__ import annotations

from contextlib import asynccontextmanager

# 导入FastAPI框架核心类 - FastAPI是一个现代、高性能的Python Web框架
from fastapi import FastAPI, Request

# 导入CORS中间件 - 用于处理跨域资源共享，解决前后端跨域问题
from fastapi.middleware.cors import CORSMiddleware

# 导入业务路由模块 - 这些是项目中定义的API路由
# auth: 用户认证相关接口
# projects: 项目管理相关接口
# provider_configs: 提供商配置相关接口
# setup: 系统初始化相关接口
from app.api.routes import (
    auth,
    projects,
    provider_configs,
    setup,
    style_analysis_jobs,
    style_profiles,
)

# 导入配置获取函数 - 用于读取环境变量和应用配置
from app.core.config import get_settings
from app.core.domain_errors import DomainError

# 导入数据库相关工具函数
# create_engine: 创建数据库连接引擎
# create_session_factory: 创建数据库会话工厂
from app.db.session import create_engine, create_session_factory
from app.services.style_analysis_worker import StyleAnalysisWorkerService
from fastapi.responses import JSONResponse


# 应用工厂函数：创建并配置FastAPI应用实例
# 这是工厂设计模式，便于测试和灵活配置
# 参数说明：
#   - session_factory: 可选参数，外部传入的数据库会话工厂，主要用于测试
#   - -> FastAPI: 类型注解，表示函数返回FastAPI类型的实例
def create_app(*, session_factory=None) -> FastAPI:
    # 获取应用配置 - 从环境变量或配置文件中读取配置
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker_service = StyleAnalysisWorkerService()
        await worker_service.fail_stale_running_jobs(
            app.state.session_factory,
            stale_after_seconds=settings.style_analysis_stale_timeout_seconds,
        )
        try:
            yield
        finally:
            await worker_service.aclose()
            if getattr(app.state, "owns_engine", False):
                await app.state.engine.dispose()

    # 创建FastAPI应用实例
    # title: API文档标题
    # version: API版本号
    app = FastAPI(title="Persona API", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    # 添加CORS跨域中间件
    # 中间件是FastAPI的扩展机制，用于在请求处理前后执行逻辑
    app.add_middleware(
        CORSMiddleware,
        # 允许的源列表 - 哪些域名可以访问这个API
        allow_origins=settings.cors_allowed_origins,
        # 允许携带凭证（如Cookie）
        allow_credentials=True,
        # 允许的HTTP方法 - ["*"]表示允许所有方法（GET/POST/PUT/DELETE等）
        allow_methods=["*"],
        # 允许的请求头 - ["*"]表示允许所有请求头
        allow_headers=["*"],
    )

    # 数据库会话初始化逻辑
    # 如果没有外部传入session_factory，则创建默认的数据库连接
    if session_factory is None:
        # 创建数据库引擎 - 这是SQLAlchemy的核心概念，管理数据库连接池
        engine = create_engine(settings.database_url)
        # 创建会话工厂 - 用于生成数据库会话实例
        session_factory = create_session_factory(engine)
        # 将引擎存储在app.state中 - app.state是FastAPI提供的全局状态存储
        app.state.engine = engine
        app.state.owns_engine = True
    else:
        app.state.owns_engine = False

    # 将会话工厂存储在app.state中，供整个应用使用
    app.state.session_factory = session_factory

    # 健康检查端点 - 使用FastAPI的装饰器语法定义路由
    # @app.get("/health") 表示这是一个GET请求，路径是/health
    @app.get("/health")
    # async表示这是一个异步函数 - FastAPI原生支持异步编程
    # -> dict[str, str] 是返回值类型注解，表示返回一个键和值都是字符串的字典
    async def health() -> dict[str, str]:
        # 返回健康状态 - 服务监控系统会调用这个接口检查服务是否正常
        return {"status": "ok"}

    # 注册业务路由 - 将各个模块的路由添加到主应用中
    # prefix="/api/v1" 表示所有这些路由的路径前缀都是/api/v1
    app.include_router(setup.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(provider_configs.router, prefix="/api/v1")
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(style_analysis_jobs.router, prefix="/api/v1")
    app.include_router(style_profiles.router, prefix="/api/v1")

    # 返回配置好的FastAPI应用实例
    return app


# 创建应用实例 - 这是应用的入口点
# uvicorn等ASGI服务器会加载这个app变量来运行服务
app = create_app()
