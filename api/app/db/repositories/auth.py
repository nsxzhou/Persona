from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import (
    PlotAnalysisJob,
    PlotProfile,
    PlotSampleFile,
    Project,
    ProviderConfig,
    Session,
    StyleAnalysisJob,
    StyleProfile,
    StyleSampleFile,
    User,
)


class AuthRepository:
    async def has_any_user(self, session: AsyncSession) -> bool:
        return await session.scalar(select(User.id).limit(1)) is not None

    async def create_user(
        self,
        session: AsyncSession,
        *,
        username: str,
        password_hash: str,
    ) -> User:
        user = User(username=username, password_hash=password_hash)
        session.add(user)
        await session.flush()
        return user

    async def get_user_by_username(
        self,
        session: AsyncSession,
        username: str,
    ) -> User | None:
        return await session.scalar(select(User).where(User.username == username))

    async def create_session(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        last_accessed_at: datetime,
    ) -> Session:
        session_record = Session(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            last_accessed_at=last_accessed_at,
        )
        session.add(session_record)
        await session.flush()
        return session_record

    async def get_session_by_token_hash(
        self,
        session: AsyncSession,
        token_hash: str,
    ) -> Session | None:
        return await session.scalar(
            select(Session)
            .options(joinedload(Session.user))
            .where(Session.token_hash == token_hash)
        )

    async def get_user_by_id(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> User | None:
        return await session.get(User, user_id)

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()

    async def delete_session_by_token_hash(
        self,
        session: AsyncSession,
        token_hash: str,
    ) -> None:
        await session.execute(delete(Session).where(Session.token_hash == token_hash))

    async def list_lab_cleanup_targets(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        # 为了避免全量加载造成内存爆炸，此处仍使用 stream_scalars，但需要注意如果数据量极大，
        # 在上层调用时应该考虑分页或批处理。这里保留列表返回以适配上层接口，
        # 实际更优的做法是直接在数据库中进行级联删除，或者在此处引入 yield 分批返回。
        # 鉴于外层需要全部 ids 来传给其他服务，目前保持 list 并通过 stream_scalars 构建，
        # 但这仍可能存在内存风险。我们在外层通过 Semaphore 限制并发。
        sample_stmt = select(StyleSampleFile.storage_path)
        if user_id is not None:
            sample_stmt = sample_stmt.where(StyleSampleFile.user_id == user_id)
        sample_paths = await session.stream_scalars(
            sample_stmt.execution_options(yield_per=1000)
        )
        
        job_stmt = select(StyleAnalysisJob.id)
        if user_id is not None:
            job_stmt = job_stmt.where(StyleAnalysisJob.user_id == user_id)
        job_ids = await session.stream_scalars(
            job_stmt.execution_options(yield_per=1000)
        )
        
        plot_sample_stmt = select(PlotSampleFile.storage_path)
        if user_id is not None:
            plot_sample_stmt = plot_sample_stmt.where(PlotSampleFile.user_id == user_id)
        plot_sample_paths = await session.stream_scalars(
            plot_sample_stmt.execution_options(yield_per=1000)
        )

        plot_job_stmt = select(PlotAnalysisJob.id)
        if user_id is not None:
            plot_job_stmt = plot_job_stmt.where(PlotAnalysisJob.user_id == user_id)
        plot_job_ids = await session.stream_scalars(
            plot_job_stmt.execution_options(yield_per=1000)
        )

        return (
            [path async for path in sample_paths if path],
            [job_id async for job_id in job_ids if job_id],
            [path async for path in plot_sample_paths if path],
            [job_id async for job_id in plot_job_ids if job_id],
        )

    async def delete_all_account_data(self, session: AsyncSession, *, user_id: str) -> None:
        await session.execute(delete(Project).where(Project.user_id == user_id))
        await session.execute(delete(PlotProfile).where(PlotProfile.user_id == user_id))
        await session.execute(delete(PlotAnalysisJob).where(PlotAnalysisJob.user_id == user_id))
        await session.execute(delete(PlotSampleFile).where(PlotSampleFile.user_id == user_id))
        await session.execute(delete(StyleProfile).where(StyleProfile.user_id == user_id))
        await session.execute(delete(StyleAnalysisJob).where(StyleAnalysisJob.user_id == user_id))
        await session.execute(delete(StyleSampleFile).where(StyleSampleFile.user_id == user_id))
        await session.execute(delete(ProviderConfig).where(ProviderConfig.user_id == user_id))
        await session.execute(delete(Session).where(Session.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
