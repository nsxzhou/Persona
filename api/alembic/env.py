from __future__ import annotations

# 日志配置工具：读取 alembic.ini 中的 logging 配置，给迁移过程提供一致的日志输出
from logging.config import fileConfig

# Alembic 的上下文对象：迁移执行时的核心入口（读配置、判断离线/在线、运行迁移脚本）
from alembic import context
# SQLAlchemy 的引擎/连接池组件：
# - engine_from_config: 用配置创建同步引擎（常见于 Alembic 默认模板）
# - pool: 提供不同的连接池策略（这里会用到 NullPool）
from sqlalchemy import engine_from_config, pool

# Base: SQLAlchemy Declarative Base，所有 ORM 模型都会挂在它的 metadata 上
# metadata 是 Alembic “对照当前模型结构”生成/校验迁移的依据
from app.db.base import Base
# 重要：显式导入模型模块，确保所有模型类都被加载并注册到 Base.metadata
# 否则 Base.metadata 可能不完整，导致 autogenerate 或迁移目标表缺失
from app.db import models  # noqa: F401

# Alembic 配置对象：主要来自 api/alembic.ini（也可被命令行参数覆盖）
config = context.config

# 如果存在配置文件（通常就是 alembic.ini），就按其中的 logging 段落初始化日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 迁移目标元数据：Alembic 会用它来了解“业务期望的表结构是什么”
# 在 autogenerate 模式下，会用它和数据库当前结构做差异对比
target_metadata = Base.metadata


# 离线迁移：不连接数据库，只生成 SQL（例如：alembic upgrade head --sql）
def run_migrations_offline() -> None:
    # 离线模式下使用 alembic.ini 的 sqlalchemy.url 作为数据库地址
    # 这通常用于“生成 SQL 给 DBA 审核/手动执行”，而不是直接执行变更
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        # target_metadata 决定了迁移/生成 SQL 时要对照的模型结构
        target_metadata=target_metadata,
        # literal_binds=True 会把绑定参数直接渲染到 SQL 字符串中，方便直接拿去执行
        literal_binds=True,
        # dialect_opts 用来指定不同数据库方言的参数风格
        dialect_opts={"paramstyle": "named"},
    )

    # begin_transaction 会创建一个“逻辑事务上下文”
    # 在离线模式下它不会真的开库事务，但能让 Alembic 以一致的方式输出 SQL
    with context.begin_transaction():
        # 执行 versions/ 下的迁移脚本（upgrade/downgrade）
        context.run_migrations()


# 真正执行迁移的同步函数：Alembic 的核心 API 是同步的
# 对于异步引擎，我们会用 connection.run_sync 把它包起来执行
def do_run_migrations(connection) -> None:
    # 把外部传进来的 connection 注入到 Alembic context
    # target_metadata 用于 autogenerate/校验（即使这里主要是执行已有脚本）
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


# 在线迁移（异步版本）：连接数据库并真正执行 DDL
async def run_async_migrations() -> None:
    # 读取 alembic.ini 的原始配置：用于识别“是否有人在运行时覆盖了 sqlalchemy.url”
    from configparser import ConfigParser
    # SQLAlchemy 异步引擎：用于 async with connectable.connect() 建立异步连接
    from sqlalchemy.ext.asyncio import create_async_engine

    # 连接字符串选择策略（兼容测试与本地开发）：
    # - 默认：使用 settings.database_url（便于用 .env 控制迁移目标库）
    # - 但如果调用方显式覆盖了 alembic_config.set_main_option("sqlalchemy.url", ...)，
    #   则优先使用覆盖后的 URL（例如测试里给每个用例创建临时 sqlite 文件）
    configured_url = config.get_main_option("sqlalchemy.url")
    file_url: str | None = None
    if config.config_file_name is not None:
        parser = ConfigParser()
        parser.read(config.config_file_name)
        file_url = parser.get("alembic", "sqlalchemy.url", fallback=None)

    if configured_url and (file_url is None or configured_url != file_url):
        url = configured_url
    else:
        # 只有在未显式覆盖 sqlalchemy.url 时，才回退到应用配置里的数据库地址。
        # 这样测试或脚本传入临时库地址时，不会被无关的应用级配置校验阻塞。
        from app.core.config import get_settings

        settings = get_settings()
        url = settings.database_url

    # 异步迁移需要“异步驱动”的 URL（例如 sqlite+aiosqlite / postgresql+asyncpg）
    # 为了兼容常见的同步 URL 写法，这里做一次轻量的自动补全/转换
    if url.startswith("sqlite:///") and "+aiosqlite" not in url:
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if (url.startswith("postgresql://") or url.startswith("postgres://")) and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
            "postgres://", "postgresql+asyncpg://", 1
        )
    
    # NullPool：迁移是短生命周期任务，不需要连接复用；用 NullPool 可以避免连接池带来的复杂性
    connectable = create_async_engine(url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        # connection.run_sync: 在异步连接上运行同步的 Alembic 迁移逻辑
        await connection.run_sync(do_run_migrations)


# 在线迁移的同步包装：Alembic 调用入口通常是同步函数
def run_migrations_online() -> None:
    import asyncio
    asyncio.run(run_async_migrations())


# 根据 Alembic 的运行模式选择入口：
# - offline: 生成 SQL（不连库）
# - online: 真连库执行迁移
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
