from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.services.novel_workflow_worker import NovelWorkflowWorkerService
from app.services.plot_analysis_worker import PlotAnalysisWorkerService
from app.services.style_analysis_worker import StyleAnalysisWorkerService

logger = logging.getLogger(__name__)


async def _run_worker_lane(
    *,
    lane_name: str,
    service_factory: Callable[[], Any],
    session_factory: Any,
    poll_interval_seconds: float,
    max_poll_interval_seconds: float,
    restart_backoff_seconds: float = 1.0,
) -> None:
    while True:
        service = service_factory()
        try:
            await service.run_worker(
                session_factory,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_interval_seconds=max_poll_interval_seconds,
            )
            return
        except asyncio.CancelledError:
            current_task = asyncio.current_task()
            if current_task is not None and current_task.cancelling():
                raise
            return
        except Exception:
            logger.exception("Worker lane crashed; restarting", extra={"lane": lane_name})
        finally:
            await service.aclose()
        await asyncio.sleep(restart_backoff_seconds)

async def run_worker() -> None:
    settings = get_settings()
    if not settings.style_analysis_worker_enabled:
        return
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    max_poll_interval_seconds = max(
        settings.style_analysis_poll_interval_seconds,
        settings.style_analysis_poll_interval_seconds * 4,
    )
    lane_tasks = [
        asyncio.create_task(
            _run_worker_lane(
                lane_name="style",
                service_factory=StyleAnalysisWorkerService,
                session_factory=session_factory,
                poll_interval_seconds=settings.style_analysis_poll_interval_seconds,
                max_poll_interval_seconds=max_poll_interval_seconds,
            )
        ),
        asyncio.create_task(
            _run_worker_lane(
                lane_name="plot",
                service_factory=PlotAnalysisWorkerService,
                session_factory=session_factory,
                poll_interval_seconds=settings.style_analysis_poll_interval_seconds,
                max_poll_interval_seconds=max_poll_interval_seconds,
            )
        ),
        asyncio.create_task(
            _run_worker_lane(
                lane_name="novel-workflow",
                service_factory=NovelWorkflowWorkerService,
                session_factory=session_factory,
                poll_interval_seconds=settings.style_analysis_poll_interval_seconds,
                max_poll_interval_seconds=max_poll_interval_seconds,
            )
        ),
    ]

    try:
        await asyncio.gather(*lane_tasks)
    finally:
        for task in lane_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*lane_tasks, return_exceptions=True)
        await engine.dispose()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
