from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ProviderConfig, User


class ProviderConfigRepository:
    async def get_first_user_id(self, session: AsyncSession) -> str | None:
        stmt = select(User.id).limit(1)
        return await session.scalar(stmt)

    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
    ) -> list[ProviderConfig]:
        stmt = select(ProviderConfig).order_by(ProviderConfig.created_at.asc())
        if user_id is not None:
            stmt = stmt.where(ProviderConfig.user_id == user_id)
        result = await session.stream_scalars(stmt)
        return [config async for config in result]

    async def create(
        self,
        session: AsyncSession,
        *,
        label: str,
        base_url: str,
        api_key_encrypted: str,
        api_key_hint_last4: str,
        default_model: str,
        is_enabled: bool,
        user_id: str,
    ) -> ProviderConfig:
        provider = ProviderConfig(
            label=label,
            base_url=base_url,
            api_key_encrypted=api_key_encrypted,
            api_key_hint_last4=api_key_hint_last4,
            default_model=default_model,
            is_enabled=is_enabled,
            user_id=user_id,
        )
        session.add(provider)
        await session.flush()
        return provider

    async def get_by_id(
        self,
        session: AsyncSession,
        provider_id: str,
        *,
        user_id: str | None = None,
    ) -> ProviderConfig | None:
        stmt = select(ProviderConfig).where(ProviderConfig.id == provider_id)
        if user_id is not None:
            stmt = stmt.where(ProviderConfig.user_id == user_id)
        return await session.scalar(stmt)

    async def get_with_projects(
        self,
        session: AsyncSession,
        provider_id: str,
        *,
        user_id: str | None = None,
    ) -> ProviderConfig | None:
        stmt = (
            select(ProviderConfig)
            .options(selectinload(ProviderConfig.projects))
            .where(ProviderConfig.id == provider_id)
        )
        if user_id is not None:
            stmt = stmt.where(ProviderConfig.user_id == user_id)
        return await session.scalar(stmt)

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()

    async def delete(self, session: AsyncSession, provider: ProviderConfig) -> None:
        await session.delete(provider)
