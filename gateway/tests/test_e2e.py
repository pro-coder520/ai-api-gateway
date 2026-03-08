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

    @pytest.mark.asyncio
    async def test_list_models(self, async_client: AsyncClient) -> None:
        """GET /v1/models returns a list of models."""
        response = await async_client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) > 0

    @pytest.mark.asyncio
    async def test_chat_completions_placeholder(
        self, async_client: AsyncClient
    ) -> None:
        """POST /v1/chat/completions returns 501 until providers are wired."""
        response = await async_client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        # Returns 501 in the skeleton (provider proxy wired in Step 4)
        assert response.status_code == 501
