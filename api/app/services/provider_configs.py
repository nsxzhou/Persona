from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
)
from app.core.security import encrypt_secret
from app.core.redaction import redact_sensitive_text
from app.db.models import ProviderConfig, User
from app.db.repositories.provider_configs import ProviderConfigRepository
from app.schemas.provider_configs import ProviderConfigCreate, ProviderConfigUpdate
from app.services.llm_provider import LLMProviderService


PROVIDER_CONNECTION_TEST_ERROR_MESSAGE = "Provider 连通性测试失败，请检查配置后重试"


class ProviderConfigService:
    def __init__(
        self,
        repository: ProviderConfigRepository | None = None,
        llm_provider_service: LLMProviderService | None = None,
    ) -> None:
        self.repository = repository or ProviderConfigRepository()
        self.llm_provider_service = llm_provider_service or LLMProviderService()

    async def _resolve_user_id(
        self,
        session: AsyncSession,
        user_id: str | None,
    ) -> str:
        if user_id is not None:
            return user_id
        resolved = await session.scalar(select(User.id).limit(1))
        if resolved is None:
            raise UnprocessableEntityError("缺少用户上下文，无法创建 Provider")
        return resolved

    async def list(
        self, session: AsyncSession, *, user_id: str | None = None
    ) -> list[ProviderConfig]:
        return await self.repository.list(session, user_id=user_id)

    async def create(
        self,
        session: AsyncSession,
        payload: ProviderConfigCreate,
        *,
        user_id: str | None = None,
    ) -> ProviderConfig:
        resolved_user_id = await self._resolve_user_id(session, user_id)
        return await self.repository.create(
            session,
            label=payload.label,
            base_url=payload.base_url,
            api_key_encrypted=encrypt_secret(payload.api_key),
            api_key_hint_last4=payload.api_key[-4:],
            default_model=payload.default_model,
            is_enabled=payload.is_enabled,
            user_id=resolved_user_id,
        )

    async def get_or_404(
        self,
        session: AsyncSession,
        provider_id: str,
        *,
        user_id: str | None = None,
    ) -> ProviderConfig:
        provider = await self.repository.get_by_id(session, provider_id, user_id=user_id)
        if provider is None:
            raise NotFoundError("Provider 不存在")
        return provider

    async def update(
        self,
        session: AsyncSession,
        provider_id: str,
        payload: ProviderConfigUpdate,
        *,
        user_id: str | None = None,
    ) -> ProviderConfig:
        provider = await self.get_or_404(session, provider_id, user_id=user_id)
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
        await self.repository.flush(session)
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
        await self.repository.flush(session)
        return provider

    async def test_connection_and_update(
        self,
        session: AsyncSession,
        provider_id: str,
        *,
        user_id: str | None = None,
    ) -> dict[str, str]:
        provider = await self.get_or_404(session, provider_id, user_id=user_id)
        result = await self.llm_provider_service.test_connection(provider)
        if result["status"] == "success":
            await self.update_test_result(
                session,
                provider,
                status_value="success",
                error_message=None,
            )
            return result

        raw_summary = str(result.get("error_summary") or result.get("message") or "")
        error_summary = redact_sensitive_text(raw_summary).strip()
        if error_summary:
            error_summary = error_summary[:199] + "…" if len(error_summary) > 200 else error_summary
        else:
            error_summary = "UnknownError"

        await self.update_test_result(
            session,
            provider,
            status_value="error",
            error_message=error_summary,
        )
        return {
            "status": "error",
            "message": f"{PROVIDER_CONNECTION_TEST_ERROR_MESSAGE}（原因：{error_summary}）"
        }

    async def delete(
        self, session: AsyncSession, provider_id: str, *, user_id: str | None = None
    ) -> None:
        provider = await self.repository.get_with_projects(session, provider_id, user_id=user_id)
        if provider is None:
            raise NotFoundError("Provider 不存在")

        has_active_project = any(project.archived_at is None for project in provider.projects)
        if has_active_project:
            raise ConflictError("该 Provider 正被项目引用，无法删除")

        has_refs = await self.repository.has_style_lab_references(session, provider_id, user_id=user_id)
        if has_refs:
            raise ConflictError("该 Provider 正被 Style Lab 引用，无法删除")

        await self.repository.delete(session, provider)

    async def ensure_enabled(
        self,
        session: AsyncSession,
        provider_id: str,
        *,
        user_id: str | None = None,
    ) -> ProviderConfig:
        provider = await self.repository.get_by_id(session, provider_id, user_id=user_id)
        if provider is None or not provider.is_enabled:
            raise UnprocessableEntityError("默认 Provider 不存在或未启用")
        return provider
