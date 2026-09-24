"""Phase 0 acceptance: both apps start and /health reports DB + Redis connectivity."""

from httpx import AsyncClient


async def test_api_health_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "db": True, "redis": True}


async def test_redirect_health_ok(redirect_client: AsyncClient) -> None:
    response = await redirect_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "db": True, "redis": True}
