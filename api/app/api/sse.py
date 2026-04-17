from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


def sse_response(
    content_generator: AsyncGenerator[str, None],
    *,
    error_log_message: str = "SSE streaming error",
) -> StreamingResponse:
    async def _sse():
        try:
            async for chunk in content_generator:
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as exc:
            logger.exception(error_log_message)
            yield f"event: error\ndata: {json.dumps(str(exc))}\n\n"

    return StreamingResponse(_sse(), media_type="text/event-stream")
