from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import (
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

    async def list_style_lab_cleanup_targets(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
    ) -> tuple[list[str], list[str]]:
        sample_stmt = select(StyleSampleFile.storage_path)
        if user_id is not None:
            sample_stmt = sample_stmt.where(StyleSampleFile.user_id == user_id)
        sample_paths = await session.stream_scalars(sample_stmt)
        job_stmt = select(StyleAnalysisJob.id)
        if user_id is not None:
            job_stmt = job_stmt.where(StyleAnalysisJob.user_id == user_id)
        job_ids = await session.stream_scalars(job_stmt)
        return (
            [path async for path in sample_paths if path],
            [job_id async for job_id in job_ids if job_id],
        )

    async def delete_all_account_data(self, session: AsyncSession, *, user_id: str) -> None:
        await session.execute(delete(Project).where(Project.user_id == user_id))
        await session.execute(delete(StyleProfile).where(StyleProfile.user_id == user_id))
        await session.execute(delete(StyleAnalysisJob).where(StyleAnalysisJob.user_id == user_id))
        await session.execute(delete(StyleSampleFile).where(StyleSampleFile.user_id == user_id))
        await session.execute(delete(ProviderConfig).where(ProviderConfig.user_id == user_id))
        await session.execute(delete(Session).where(Session.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
