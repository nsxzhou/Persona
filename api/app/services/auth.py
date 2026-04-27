from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    generate_session_token,
    get_session_expiration,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.core.domain_errors import ConflictError, ForbiddenError, UnauthorizedError
from app.db.models import Session, User
from app.db.repositories.auth import AuthRepository
from app.services.plot_analysis_storage import PlotAnalysisStorageService
from app.services.style_analysis_storage import StyleAnalysisStorageService


class AuthService:
    LAST_ACCESSED_UPDATE_INTERVAL = timedelta(minutes=5)

    def __init__(self, repository: AuthRepository | None = None) -> None:
        self.repository = repository or AuthRepository()

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        """Coerce naive datetimes to UTC; convert tz-aware to UTC."""
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    async def is_initialized(self, session: AsyncSession) -> bool:
        return await self.repository.has_any_user(session)

    async def create_initial_admin(
        self, session: AsyncSession, username: str, password: str
    ) -> User:
        return await self.repository.create_user(
            session,
            username=username,
            password_hash=hash_password(password),
        )

    async def ensure_initialized(self, session: AsyncSession) -> None:
        if not await self.is_initialized(session):
            raise ForbiddenError("系统尚未初始化")

    async def ensure_not_initialized(self, session: AsyncSession) -> None:
        if await self.is_initialized(session):
            raise ConflictError("系统已初始化")

    async def authenticate(
        self, session: AsyncSession, username: str, password: str
    ) -> User:
        user = await self.repository.get_user_by_username(session, username)
        # Return the same error for "no such user" and "wrong password" to
        # prevent username enumeration.
        if user is None:
            raise UnauthorizedError("账号或密码错误")
        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("账号或密码错误")
        return user

    async def create_session(
        self, session: AsyncSession, user: User
    ) -> tuple[Session, str]:
        """Return (session_record, raw_token). The raw token is never persisted."""
        raw_token = generate_session_token()
        session_record = await self.repository.create_session(
            session,
            user_id=user.id,
            token_hash=hash_session_token(raw_token),
            expires_at=get_session_expiration(),
            last_accessed_at=datetime.now(UTC),
        )
        return session_record, raw_token

    async def resolve_user_by_token(
        self, session: AsyncSession, raw_token: str | None
    ) -> User:
        if not raw_token:
            raise UnauthorizedError("未登录")

        token_hash = hash_session_token(raw_token)
        session_record = await self.repository.get_session_by_token_hash(
            session,
            token_hash,
        )
        if session_record is None:
            raise UnauthorizedError("登录状态已失效")

        now = datetime.now(UTC)
        expires_at = self._normalize_datetime(session_record.expires_at)
        if expires_at < now:
            raise UnauthorizedError("登录状态已失效")

        # Throttle last_accessed updates to avoid write amplification on reads.
        last_accessed_at = self._normalize_datetime(session_record.last_accessed_at)
        if now - last_accessed_at >= self.LAST_ACCESSED_UPDATE_INTERVAL:
            session_record.last_accessed_at = now
            await self.repository.flush(session)

        user = session_record.user
        if user is None:
            raise UnauthorizedError("未登录")
        return user

    async def delete_session(
        self, session: AsyncSession, raw_token: str | None
    ) -> None:
        if not raw_token:
            return
        await self.repository.delete_session_by_token_hash(
            session,
            hash_session_token(raw_token),
        )

    async def delete_account(self, session: AsyncSession, *, user_id: str) -> None:
        (
            sample_storage_paths,
            artifact_job_ids,
            plot_sample_storage_paths,
            plot_artifact_job_ids,
        ) = await self.repository.list_lab_cleanup_targets(session, user_id=user_id)
        await self.repository.delete_all_account_data(session, user_id=user_id)
        storage_service = StyleAnalysisStorageService()
        plot_storage_service = PlotAnalysisStorageService()
        for storage_path in sample_storage_paths:
            try:
                await asyncio.to_thread(Path(storage_path).unlink, missing_ok=True)
            except OSError:
                # File cleanup failures should not block DB commit.
                continue
        for storage_path in plot_sample_storage_paths:
            try:
                Path(storage_path).unlink(missing_ok=True)
            except OSError:
                continue

        if artifact_job_ids:
            # Bound concurrency to avoid file-descriptor exhaustion for large accounts.
            sem = asyncio.Semaphore(20)

            async def _cleanup(job_id: str) -> None:
                async with sem:
                    await storage_service.cleanup_job_artifacts(job_id)

            async with asyncio.TaskGroup() as tg:
                for job_id in artifact_job_ids:
                    tg.create_task(_cleanup(job_id))

        if plot_artifact_job_ids:
            sem = asyncio.Semaphore(20)

            async def _cleanup_plot(job_id: str) -> None:
                async with sem:
                    await plot_storage_service.cleanup_job_artifacts(job_id)

            async with asyncio.TaskGroup() as tg:
                for job_id in plot_artifact_job_ids:
                    tg.create_task(_cleanup_plot(job_id))
