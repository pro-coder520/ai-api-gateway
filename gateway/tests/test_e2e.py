"""End-to-end test for the full request lifecycle."""

import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestEndToEnd:
    """Full lifecycle tests exercising the API from HTTP entry to response."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client: AsyncClient) -> None:
        """GET /health returns 200 with healthy status."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "providers" in data

    @pytest.mark.asyncio
    async def test_list_models(self, async_client: AsyncClient) -> None:
        """GET /v1/models returns a list of models."""
        response = await async_client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) > 0

    @pytest.mark.asyncio
    async def test_chat_completions_missing_auth(
        self, async_client: AsyncClient
    ) -> None:
        """POST /v1/chat/completions without auth returns 401."""
        response = await async_client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"]["code"] == "missing_auth"

    @pytest.mark.asyncio
    async def test_chat_completions_invalid_auth_scheme(
        self, async_client: AsyncClient
    ) -> None:
        """POST /v1/chat/completions with wrong auth scheme returns 401."""
        response = await async_client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello"}],
            },
            headers={"Authorization": "Basic invalid-key"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"]["code"] == "invalid_auth"
