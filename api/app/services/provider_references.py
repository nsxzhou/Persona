from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PlotAnalysisJob, PlotProfile, StyleAnalysisJob, StyleProfile


class ProviderReferenceService:
    async def has_analysis_references(
        self,
        session: AsyncSession,
        provider_id: str,
        *,
        user_id: str | None = None,
    ) -> bool:
        checks = (
            (StyleAnalysisJob.id, StyleAnalysisJob.provider_id, StyleAnalysisJob.user_id),
            (StyleProfile.id, StyleProfile.provider_id, StyleProfile.user_id),
            (PlotAnalysisJob.id, PlotAnalysisJob.provider_id, PlotAnalysisJob.user_id),
            (PlotProfile.id, PlotProfile.provider_id, PlotProfile.user_id),
        )
        for id_column, provider_column, user_column in checks:
            stmt = select(id_column).where(provider_column == provider_id).limit(1)
            if user_id is not None:
                stmt = stmt.where(user_column == user_id)
            if await session.scalar(stmt) is not None:
                return True
        return False
