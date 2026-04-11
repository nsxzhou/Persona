from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Project, ProviderConfig, Session, User


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
        return await session.scalar(select(Session).where(Session.token_hash == token_hash))

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

    async def delete_all_account_data(self, session: AsyncSession) -> None:
        await session.execute(delete(Project))
        await session.execute(delete(ProviderConfig))
        await session.execute(delete(Session))
        await session.execute(delete(User))
