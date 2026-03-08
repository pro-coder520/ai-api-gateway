"""API endpoints: /v1/chat/completions, /v1/models, /health."""

import time

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from schemas.requests import ChatRequest
from schemas.responses import ChatResponse, ErrorResponse, ErrorDetail

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Return gateway health status."""
    return {
        "status": "healthy",
        "service": "ai-api-gateway",
        "timestamp": str(int(time.time())),
    }


@router.get("/v1/models", tags=["Models"])
async def list_models() -> dict[str, object]:
    """Return a list of available models across all providers.

    Placeholder — fully populated in Step 5 with multi-provider routing.
    """
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4", "object": "model", "owned_by": "openai"},
            {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
            {
                "id": "claude-3-opus-20240229",
                "object": "model",
                "owned_by": "anthropic",
            },
            {
                "id": "claude-3-sonnet-20240229",
                "object": "model",
                "owned_by": "anthropic",
            },
        ],
    }


@router.post("/v1/chat/completions", tags=["Chat"])
async def chat_completions(
    request: Request,
    chat_request: ChatRequest,
) -> JSONResponse:
    """Process a chat completion request.

    Placeholder — provider proxy, caching, rate limiting, etc. are added
    in subsequent steps.
    """
    await logger.ainfo(
        "chat_completion_request",
        model=chat_request.model,
        stream=chat_request.stream,
        message_count=len(chat_request.messages),
    )

    # Placeholder response until provider proxy is wired in Step 4
    return JSONResponse(
        status_code=501,
        content=ErrorResponse(
            error=ErrorDetail(
                type="not_implemented",
                message="Provider proxy not yet configured. Complete Step 4 to enable.",
                code="not_implemented",
            )
        ).model_dump(),
    )
