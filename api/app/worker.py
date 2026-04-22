from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.services.plot_analysis_worker import PlotAnalysisWorkerService
from app.services.style_analysis_worker import StyleAnalysisWorkerService

async def run_worker() -> None:
    settings = get_settings()
    if not settings.style_analysis_worker_enabled:
        return
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    style_service = StyleAnalysisWorkerService()
    plot_service = PlotAnalysisWorkerService()

    try:
        await asyncio.gather(
            style_service.run_worker(
                session_factory,
                poll_interval_seconds=settings.style_analysis_poll_interval_seconds,
                max_poll_interval_seconds=max(
                    settings.style_analysis_poll_interval_seconds,
                    settings.style_analysis_poll_interval_seconds * 4,
                ),
            ),
            plot_service.run_worker(
                session_factory,
                poll_interval_seconds=settings.style_analysis_poll_interval_seconds,
                max_poll_interval_seconds=max(
                    settings.style_analysis_poll_interval_seconds,
                    settings.style_analysis_poll_interval_seconds * 4,
                ),
            ),
        )
    finally:
        await style_service.aclose()
        await plot_service.aclose()
        await engine.dispose()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
