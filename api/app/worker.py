from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.services.style_analysis_worker import StyleAnalysisWorkerService

async def run_worker() -> None:
    settings = get_settings()
    if not settings.style_analysis_worker_enabled:
        return
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    service = StyleAnalysisWorkerService()

    try:
        await service.run_worker(
            session_factory,
            poll_interval_seconds=settings.style_analysis_poll_interval_seconds,
            max_poll_interval_seconds=max(
                settings.style_analysis_poll_interval_seconds,
                settings.style_analysis_poll_interval_seconds * 4,
            ),
        )
    finally:
        await service.aclose()
        await engine.dispose()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
