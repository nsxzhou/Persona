from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.live_llm


@pytest.mark.asyncio
async def test_provider_connection_test_updates_status(
    initialized_live_client: AsyncClient,
    initialized_live_provider: dict[str, object],
) -> None:
    provider_id = str(initialized_live_provider["id"])
    response = await initialized_live_client.post(f"/api/v1/provider-configs/{provider_id}/test")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["message"] == "连接成功"

    refreshed = (await initialized_live_client.get("/api/v1/provider-configs")).json()[0]
    assert refreshed["last_test_status"] == "success"
