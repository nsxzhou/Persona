from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ProviderConfig, StyleAnalysisJob, StyleProfile


class ProviderConfigRepository:
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

    async def has_style_lab_references(
        self,
        session: AsyncSession,
        provider_id: str,
        *,
        user_id: str | None = None,
    ) -> bool:
        style_job_stmt = select(StyleAnalysisJob.id).where(
            StyleAnalysisJob.provider_id == provider_id
        )
        if user_id is not None:
            style_job_stmt = style_job_stmt.where(StyleAnalysisJob.user_id == user_id)
        style_job_ref = await session.scalar(style_job_stmt.limit(1))
        if style_job_ref is not None:
            return True

        style_profile_stmt = select(StyleProfile.id).where(
            StyleProfile.provider_id == provider_id
        )
        if user_id is not None:
            style_profile_stmt = style_profile_stmt.where(StyleProfile.user_id == user_id)
        style_profile_ref = await session.scalar(style_profile_stmt.limit(1))
        return style_profile_ref is not None

    async def delete(self, session: AsyncSession, provider: ProviderConfig) -> None:
        await session.delete(provider)
