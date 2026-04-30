from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProviderConfig, User
from app.schemas.setup import SetupRequest
from app.services.auth import AuthService
from app.services.provider_configs import ProviderConfigService


@dataclass(frozen=True)
class SetupResult:
    user: User
    provider: ProviderConfig
    raw_token: str


class SetupService:
    def __init__(
        self,
        auth_service: AuthService | None = None,
        provider_service: ProviderConfigService | None = None,
    ) -> None:
        self.auth_service = auth_service or AuthService()
        self.provider_service = provider_service or ProviderConfigService()

    async def run_initial_setup(
        self,
        session: AsyncSession,
        payload: SetupRequest,
    ) -> SetupResult:
        await self.auth_service.ensure_not_initialized(session)
        user = await self.auth_service.create_initial_admin(
            session,
            payload.username,
            payload.password,
        )
        provider = await self.provider_service.create(
            session,
            payload.provider,
            user_id=user.id,
        )
        _, raw_token = await self.auth_service.create_session(session, user)
        return SetupResult(user=user, provider=provider, raw_token=raw_token)
