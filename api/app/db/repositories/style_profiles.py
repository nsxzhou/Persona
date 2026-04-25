from __future__ import annotations

from dataclasses import dataclass

# 导入SQLAlchemy核心组件
# select: 用于构造SQL SELECT查询
from sqlalchemy import select

# AsyncSession: SQLAlchemy 2.0 异步数据库会话，这是现代异步ORM的标准用法
from sqlalchemy.ext.asyncio import AsyncSession

# 导入ORM加载和延迟加载工具
# defer: 延迟加载指定字段 - 这是重要的性能优化手段
#        对于大体积的JSON字段，在列表查询时不加载，只在详情查询时加载
# joinedload: 立即加载关联对象（使用JOIN方式），适合一对一/多对一关系
# selectinload: 立即加载关联对象（使用IN查询方式），适合一对多关系，避免笛卡尔积问题
from sqlalchemy.orm import defer, joinedload, selectinload

# 导入数据库模型
from app.db.models import StyleAnalysisJob, StyleProfile


@dataclass(frozen=True)
class StyleProfileCreateData:
    source_job_id: str
    provider_id: str
    model_name: str
    source_filename: str
    style_name: str
    analysis_report_payload: str
    prompt_pack_payload: str
    user_id: str


# 风格配置文件仓库类
# 封装所有与StyleProfile表相关的数据库操作
# 遵循仓库模式设计原则：
# 1. 所有数据库访问逻辑集中在这里，业务层不需要知道SQL细节
# 2. 提供统一的接口，便于单元测试时Mock
# 3. 数据库查询优化和最佳实践在这里统一实现
class StyleProfileRepository:
    # 注意：所有方法的第一个参数都是session，而不是在类初始化时传入
    # 这是FastAPI依赖注入系统的最佳实践：每个请求有独立的会话
    async def list(
        self,
        session: AsyncSession,
        *,
        # * 是Python的关键字参数分隔符，强制后面的参数必须用关键字传递
        # 这是API设计的最佳实践，提高可读性，避免参数顺序错误
        user_id: str | None = None,
        offset: int,
        limit: int,
    ) -> list[StyleProfile]:
        # 构造查询语句
        stmt = (
            select(StyleProfile)
            .options(
                # 这里是关键的性能优化：
                # 这三个JSON字段每个可能有几十KB甚至上百KB
                # 在列表页我们只需要显示名称、创建时间等基本信息
                # 所以使用defer延迟加载这些大字段，大幅减少网络传输和内存占用
                defer(StyleProfile.analysis_report_payload),
                defer(StyleProfile.style_summary_payload),
                defer(StyleProfile.prompt_pack_payload),
            )
            # 按创建时间倒序，最新的在前
            .order_by(StyleProfile.created_at.desc())
            # 标准分页参数
            .offset(offset)
            .limit(limit)
        )
        # 如果传入了user_id，添加用户过滤条件
        # 这实现了行级权限控制：用户只能看到自己的风格配置
        if user_id is not None:
            stmt = stmt.where(StyleProfile.user_id == user_id)
        # 使用stream_scalars而不是scalars
        # 对于大数据量查询，流式返回可以减少内存占用
        result = await session.stream_scalars(stmt)
        # 使用异步生成器推导式转换为列表
        return [profile async for profile in result]

    async def get_by_id(
        self,
        session: AsyncSession,
        profile_id: str,
        *,
        user_id: str | None = None,
    ) -> StyleProfile | None:
        # 基础查询：根据主键查询
        stmt = select(StyleProfile).where(StyleProfile.id == profile_id)
        # 可选的用户权限验证
        # 注意：这里不是在应用层过滤，而是在SQL层面添加WHERE条件
        # 即使profile_id正确，如果不属于该用户，也会返回None
        if user_id is not None:
            stmt = stmt.where(StyleProfile.user_id == user_id)
        # scalar返回第一个结果，没有则返回None
        return await session.scalar(stmt)

    async def get_with_projects(
        self,
        session: AsyncSession,
        profile_id: str,
        *,
        user_id: str | None = None,
    ) -> StyleProfile | None:
        # 获取风格配置并预加载关联的项目列表
        stmt = (
            select(StyleProfile)
            # 这里使用selectinload而不是joinedload
            # 因为StyleProfile和Project是一对多关系
            # joinedload会产生笛卡尔积，而selectinload使用IN查询，性能更好
            .options(selectinload(StyleProfile.projects))
            .where(StyleProfile.id == profile_id)
        )
        if user_id is not None:
            stmt = stmt.where(StyleProfile.user_id == user_id)
        return await session.scalar(stmt)

    async def get_by_source_job_id(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> StyleProfile | None:
        # 根据来源分析任务ID查询对应的风格配置
        # 因为source_job_id有唯一索引，所以最多返回一个结果
        stmt = select(StyleProfile).where(StyleProfile.source_job_id == job_id)
        if user_id is not None:
            stmt = stmt.where(StyleProfile.user_id == user_id)
        return await session.scalar(stmt)

    async def get_job_for_profile_creation(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> StyleAnalysisJob | None:
        # 获取用于创建风格配置的分析任务
        # 这个方法专门设计用于创建风格配置前的校验和数据提取
        # 所以一次性预加载所有需要的关联数据，避免N+1查询
        stmt = (
            select(StyleAnalysisJob)
            .options(
                # 预加载样本文件信息
                joinedload(StyleAnalysisJob.sample_file),
                # 预加载提供商配置信息
                joinedload(StyleAnalysisJob.provider),
                # 预加载可能已经存在的风格配置，用于防重复创建校验
                joinedload(StyleAnalysisJob.style_profile),
            )
            .where(StyleAnalysisJob.id == job_id)
        )
        if user_id is not None:
            stmt = stmt.where(StyleAnalysisJob.user_id == user_id)
        return await session.scalar(stmt)

    async def create(
        self,
        session: AsyncSession,
        *,
        data: StyleProfileCreateData,
    ) -> StyleProfile:
        # 创建新的风格配置
        # 注意：这里没有接收id参数，ID由数据库模型自动生成UUID
        profile = StyleProfile(
            source_job_id=data.source_job_id,
            provider_id=data.provider_id,
            model_name=data.model_name,
            source_filename=data.source_filename,
            style_name=data.style_name,
            analysis_report_payload=data.analysis_report_payload,
            style_summary_payload="",
            prompt_pack_payload=data.prompt_pack_payload,
            user_id=data.user_id,
        )
        # 将对象添加到会话
        session.add(profile)
        # flush而不是commit
        # 这是仓库模式的最佳实践：
        # 仓库只负责数据操作，事务提交由上层业务逻辑控制
        await session.flush()
        # flush后profile对象已经有了数据库生成的id和时间戳
        return profile

    async def flush(self, session: AsyncSession) -> None:
        # 通用的flush方法，供业务层在批量操作后调用
        await session.flush()

    async def delete(self, session: AsyncSession, profile: StyleProfile) -> None:
        # 删除风格配置
        # 注意：接收的是对象而不是ID
        # 这是ORM的最佳实践：如果对象已经在会话中，不需要再次查询
        await session.delete(profile)
