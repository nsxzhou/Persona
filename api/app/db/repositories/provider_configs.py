from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ProviderConfig, StyleAnalysisJob, StyleProfile


class ProviderConfigRepository:
    async def list(self, session: AsyncSession) -> list[ProviderConfig]:
        result = await session.stream_scalars(
            select(ProviderConfig).order_by(ProviderConfig.created_at.asc())
        )
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
    ) -> ProviderConfig:
        provider = ProviderConfig(
            label=label,
            base_url=base_url,
            api_key_encrypted=api_key_encrypted,
            api_key_hint_last4=api_key_hint_last4,
            default_model=default_model,
            is_enabled=is_enabled,
        )
        session.add(provider)
        await session.flush()
        return provider

    async def get_by_id(
        self,
        session: AsyncSession,
        provider_id: str,
    ) -> ProviderConfig | None:
        return await session.get(ProviderConfig, provider_id)

    async def get_with_projects(
        self,
        session: AsyncSession,
        provider_id: str,
    ) -> ProviderConfig | None:
        return await session.scalar(
            select(ProviderConfig)
            .options(selectinload(ProviderConfig.projects))
            .where(ProviderConfig.id == provider_id)
        )

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()

    async def has_style_lab_references(
        self,
        session: AsyncSession,
        provider_id: str,
    ) -> bool:
        style_job_ref = await session.scalar(
            select(StyleAnalysisJob.id)
            .where(StyleAnalysisJob.provider_id == provider_id)
            .limit(1)
        )
        if style_job_ref is not None:
            return True

        style_profile_ref = await session.scalar(
            select(StyleProfile.id)
            .where(StyleProfile.provider_id == provider_id)
            .limit(1)
        )
        return style_profile_ref is not None

    async def delete(self, session: AsyncSession, provider: ProviderConfig) -> None:
        await session.delete(provider)
