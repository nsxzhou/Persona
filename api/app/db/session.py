# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入异步迭代器类型注解
from collections.abc import AsyncIterator

# 导入FastAPI请求对象
from fastapi import Request

# 导入SQLAlchemy异步相关组件
# AsyncEngine: 异步数据库引擎
# AsyncSession: 异步数据库会话
# async_sessionmaker: 异步会话工厂
# create_async_engine: 创建异步引擎的函数
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


# 创建异步数据库引擎
# 这是SQLAlchemy连接数据库的入口点，管理数据库连接池
# 每个应用通常只创建一个引擎实例
#
# future=True: 启用SQLAlchemy 2.0的兼容模式，这是新项目的标准配置
def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, future=True)


# 创建异步会话工厂
# 会话工厂用于生成数据库会话实例，类似于连接池的管理器
#
# expire_on_commit=False: 非常重要的配置！
# 这个参数关闭了提交后对象过期的默认行为
# 如果不设置为False，commit之后你就不能再读取对象的属性了
# 这是FastAPI项目的标准配置
def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


# FastAPI依赖注入函数：获取数据库会话
# 这是FastAPI中最核心的数据库依赖，几乎所有接口都会用到
#
# 工作原理：
# 1. FastAPI在处理请求时会自动调用这个函数
# 2. 函数从app.state中获取提前创建好的会话工厂
# 3. 使用async with创建一个会话，这个会话会在请求结束时自动关闭
# 4. 使用yield将会话注入到路由处理函数中
#
# 这是FastAPI + SQLAlchemy异步的标准写法
async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    # 从应用状态中获取会话工厂（这个工厂在create_app时已经创建好了）
    session_factory: async_sessionmaker[AsyncSession] = (
        request.app.state.session_factory
    )
    # async with上下文管理器：自动管理会话的生命周期
    # 请求结束时会自动回滚未提交的事务并关闭会话
    async with session_factory() as session:
        # yield表示这是一个生成器依赖
        # FastAPI会把yield出来的session传给路由函数
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
