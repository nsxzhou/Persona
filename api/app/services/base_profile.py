from __future__ import annotations

from typing import Generic, TypeVar, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import ConflictError, NotFoundError

T = TypeVar("T")

class BaseProfileService(Generic[T]):
    def __init__(self, repository: Any, profile_name: str) -> None:
        self.repository = repository
        self.profile_name = profile_name

    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[T]:
        limit = min(max(limit, 1), 100)
        return await self.repository.list(session, user_id=user_id, offset=offset, limit=limit)

    async def get_or_404(
        self,
        session: AsyncSession,
        profile_id: str,
        *,
        user_id: str | None = None,
    ) -> T:
        profile = await self.repository.get_by_id(session, profile_id, user_id=user_id)
        if profile is None:
            raise NotFoundError(f"{self.profile_name}不存在")
        return profile

    async def _check_delete_constraints(self, session: AsyncSession, profile: T) -> None:
        pass

    async def delete(
        self,
        session: AsyncSession,
        profile_id: str,
        *,
        user_id: str | None = None,
    ) -> None:
        profile = await self.repository.get_with_projects(
            session,
            profile_id,
            user_id=user_id,
        )
        if profile is None:
            raise NotFoundError(f"{self.profile_name}不存在")
        await self._check_delete_constraints(session, profile)
        await self.repository.delete(session, profile)
