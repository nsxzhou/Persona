from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import encrypt_secret
from app.db.models import Project, ProviderConfig
from app.schemas.provider_configs import ProviderConfigCreate, ProviderConfigUpdate


class ProviderConfigService:
    async def list(self, session: AsyncSession) -> list[ProviderConfig]:
        result = await session.stream_scalars(select(ProviderConfig).order_by(ProviderConfig.created_at.asc()))
        return [c async for c in result]

    async def create(self, session: AsyncSession, payload: ProviderConfigCreate) -> ProviderConfig:
        provider = ProviderConfig(
            label=payload.label,
            base_url=payload.base_url,
            api_key_encrypted=encrypt_secret(payload.api_key),
            api_key_hint_last4=payload.api_key[-4:],
            default_model=payload.default_model,
            is_enabled=payload.is_enabled,
        )
        session.add(provider)
        await session.flush()
        return provider

    async def get_or_404(self, session: AsyncSession, provider_id: str) -> ProviderConfig:
        provider = await session.get(ProviderConfig, provider_id)
        if provider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider 不存在")
        return provider

    async def update(self, session: AsyncSession, provider_id: str, payload: ProviderConfigUpdate) -> ProviderConfig:
        provider = await self.get_or_404(session, provider_id)
        data = payload.model_dump(exclude_unset=True)
        if "label" in data:
            provider.label = data["label"]
        if "base_url" in data:
            provider.base_url = data["base_url"]
        if "default_model" in data:
            provider.default_model = data["default_model"]
        if "is_enabled" in data:
            provider.is_enabled = data["is_enabled"]
        if data.get("api_key"):
            provider.api_key_encrypted = encrypt_secret(data["api_key"])
            provider.api_key_hint_last4 = data["api_key"][-4:]
        await session.flush()
        return provider

    async def update_test_result(
        self,
        session: AsyncSession,
        provider: ProviderConfig,
        *,
        status_value: str,
        error_message: str | None,
    ) -> ProviderConfig:
        provider.last_test_status = status_value
        provider.last_test_error = error_message
        provider.last_tested_at = datetime.now(UTC)
        await session.flush()
        return provider

    async def delete(self, session: AsyncSession, provider_id: str) -> None:
        provider = await session.scalar(
            select(ProviderConfig)
            .options(selectinload(ProviderConfig.projects))
            .where(ProviderConfig.id == provider_id)
        )
        if provider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider 不存在")

        has_active_project = any(project.archived_at is None for project in provider.projects)
        if has_active_project:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该 Provider 正被项目引用，无法删除")

        await session.delete(provider)

    async def ensure_enabled(self, session: AsyncSession, provider_id: str) -> ProviderConfig:
        provider = await session.get(ProviderConfig, provider_id)
        if provider is None or not provider.is_enabled:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="默认 Provider 不存在或未启用")
        return provider
