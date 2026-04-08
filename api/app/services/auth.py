from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    generate_session_token,
    get_session_expiration,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.db.models import Session, User


class AuthService:
    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    async def is_initialized(self, session: AsyncSession) -> bool:
        result = await session.scalar(select(User.id).limit(1))
        return result is not None

    async def create_initial_admin(self, session: AsyncSession, username: str, password: str) -> User:
        user = User(username=username, password_hash=hash_password(password))
        session.add(user)
        await session.flush()
        return user

    async def authenticate(self, session: AsyncSession, username: str, password: str) -> User:
        user = await session.scalar(select(User).where(User.username == username))
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
        return user

    async def create_session(self, session: AsyncSession, user: User) -> tuple[Session, str]:
        raw_token = generate_session_token()
        session_record = Session(
            user_id=user.id,
            token_hash=hash_session_token(raw_token),
            expires_at=get_session_expiration(),
            last_accessed_at=datetime.now(UTC),
        )
        session.add(session_record)
        await session.flush()
        return session_record, raw_token

    async def resolve_user_by_token(self, session: AsyncSession, raw_token: str | None) -> User:
        if not raw_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

        token_hash = hash_session_token(raw_token)
        session_record = await session.scalar(select(Session).where(Session.token_hash == token_hash))
        if session_record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效")

        if self._normalize_datetime(session_record.expires_at) < datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效")

        session_record.last_accessed_at = datetime.now(UTC)
        await session.flush()

        user = await session.get(User, session_record.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
        return user

    async def delete_session(self, session: AsyncSession, raw_token: str | None) -> None:
        if not raw_token:
            return
        await session.execute(delete(Session).where(Session.token_hash == hash_session_token(raw_token)))
