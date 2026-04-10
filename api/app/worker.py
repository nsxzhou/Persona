from __future__ import annotations

import asyncio
import time

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

    last_stale_check = 0.0
    stale_check_interval = max(5.0, float(settings.style_analysis_stale_timeout_seconds) / 3.0)

    try:
        while True:
            now = time.monotonic()
            if now - last_stale_check >= stale_check_interval:
                await service.fail_stale_running_jobs(
                    session_factory,
                    stale_after_seconds=settings.style_analysis_stale_timeout_seconds,
                )
                last_stale_check = now

            processed = await service.process_next_pending(session_factory)
            if not processed:
                await asyncio.sleep(settings.style_analysis_poll_interval_seconds)
    finally:
        await service.aclose()
        await engine.dispose()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
