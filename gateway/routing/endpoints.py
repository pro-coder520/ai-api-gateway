"""API endpoints: /v1/chat/completions, /v1/models, /health.

Implements the full request pipeline:
1. Authenticate via API key (bcrypt).
2. Enforce rate limits (token bucket + daily cap).
3. Check response cache (for deterministic requests).
4. Route to the correct provider (DB-backed or prefix fallback).
5. Check circuit breaker state (with failover).
6. Forward the request (streaming or non-streaming).
7. Cache the response if applicable.
8. Log the request asynchronously.
9. Return the response with rate limit, cache, and circuit headers.
"""

import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse

from cache.service import CacheService, generate_cache_key
from config import settings
from dependencies import CurrentApiKey, DbSession, Redis, get_db_session, get_redis, get_session_factory
from logging_.service import log_request
from providers.anthropic import AnthropicProvider
from providers.base import BaseProvider
from providers.ollama import OllamaProvider
from providers.openai import OpenAIProvider
from ratelimit.middleware import check_daily_limit, check_rate_limit
from resilience.circuit_breaker import CircuitBreaker, CircuitState
from routing.router import resolve_provider_slug_from_db
from schemas.requests import ChatRequest
from schemas.responses import ChatResponse, ErrorDetail, ErrorResponse
from streaming.sse import SSEHandler

logger = structlog.get_logger(__name__)

router = APIRouter()

# ── Provider singletons ──────────────────────────────────────────────────────

_providers: dict[str, BaseProvider] = {}


def _get_provider(slug: str) -> BaseProvider:
    """Return the provider instance for a given slug, creating it on first use."""
    if slug not in _providers:
        match slug:
            case "openai":
                _providers[slug] = OpenAIProvider()
            case "anthropic":
                _providers[slug] = AnthropicProvider()
            case "ollama":
                _providers[slug] = OllamaProvider()
            case _:
                raise ValueError(f"Unknown provider slug: {slug}")
    return _providers[slug]


async def close_providers() -> None:
    """Close all provider httpx clients. Called during shutdown."""
    for provider in _providers.values():
        await provider.close()
    _providers.clear()


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/health", tags=["System"])
async def health_check(redis_client=Depends(get_redis)) -> dict[str, Any]:
    """Return gateway health status including provider circuit breaker states."""
    provider_states: dict[str, str] = {}
    for slug in ("openai", "anthropic", "ollama"):
        cb = CircuitBreaker(redis_client, slug)
        state = await cb.get_state()
        provider_states[slug] = state.value

    return {
        "status": "healthy",
        "service": "ai-api-gateway",
        "timestamp": str(int(time.time())),
        "providers": provider_states,
    }


@router.get("/v1/models", tags=["Models"])
async def list_models(session: DbSession) -> dict[str, Any]:
    """Return a list of available models across all healthy providers."""
    from auth.models import Provider
    from sqlalchemy import select

    all_models: list[dict[str, str]] = []

    # Fetch from DB if possible
    try:
        stmt = select(Provider).where(Provider.is_active == True)  # noqa: E712
        result = await session.execute(stmt)
        db_providers = result.scalars().all()

        for db_provider in db_providers:
            try:
                provider = _get_provider(db_provider.slug)
                for model_name in provider.supported_models():
                    all_models.append(
                        {
                            "id": model_name,
                            "object": "model",
                            "owned_by": db_provider.slug,
                        }
                    )
            except Exception:
                continue
    except Exception:
        # Fallback: list static models from providers
        for slug in ("openai", "anthropic", "ollama"):
            try:
                provider = _get_provider(slug)
                for model_name in provider.supported_models():
                    all_models.append(
                        {
                            "id": model_name,
                            "object": "model",
                            "owned_by": slug,
                        }
                    )
            except Exception:
                continue

    return {"object": "list", "data": all_models}


@router.post("/v1/chat/completions", tags=["Chat"])
async def chat_completions(
    request: Request,
    chat_request: ChatRequest,
    api_key: CurrentApiKey,
    session: DbSession,
    redis_client: Redis,
) -> JSONResponse | StreamingResponse:
    """Process a chat completion request through the full pipeline."""
    start_time = time.time()

    await logger.ainfo(
        "chat_completion_request",
        model=chat_request.model,
        stream=chat_request.stream,
        message_count=len(chat_request.messages),
        key_id=api_key.get("id"),
    )

    # ── Rate limit check ──────────────────────────────────────────────
    rate_limit_headers = await check_rate_limit(api_key, redis_client)

    # ── Pre-flight daily token limit check ────────────────────────────
    await check_daily_limit(api_key, redis_client, tokens_used=0)

    # ── Check model scopes ────────────────────────────────────────────
    if api_key.get("scopes"):
        allowed_prefixes = [s.strip() for s in api_key["scopes"].split(",")]
        if not any(chat_request.model.startswith(p) for p in allowed_prefixes):
            response = JSONResponse(
                status_code=403,
                content=ErrorResponse(
                    error=ErrorDetail(
                        type="permission_error",
                        message=f"Model '{chat_request.model}' is not allowed for this API key",
                        code="model_not_allowed",
                    )
                ).model_dump(),
            )
            for k, v in rate_limit_headers.items():
                response.headers[k] = v
            return response

    # ── Cache check (only for deterministic, non-streaming) ───────────
    cache_service = CacheService(redis_client)
    cache_hit = False
    cache_key: str | None = None

    if CacheService.should_cache(chat_request.temperature, chat_request.stream):
        cache_key = generate_cache_key(
            chat_request.model,
            [m.model_dump() for m in chat_request.messages],
            temperature=chat_request.temperature,
            max_tokens=chat_request.max_tokens,
            top_p=chat_request.top_p,
        )
        cached_response = await cache_service.get(cache_key)
        if cached_response is not None:
            cache_hit = True
            latency_ms = (time.time() - start_time) * 1000
            log_request(
                session_factory=get_session_factory(),
                key_id=api_key.get("id"),
                model=chat_request.model,
                provider="cache",
                input_tokens=cached_response.get("usage", {}).get("prompt_tokens", 0),
                output_tokens=cached_response.get("usage", {}).get(
                    "completion_tokens", 0
                ),
                latency_ms=latency_ms,
                status_code=200,
                cached=True,
            )
            response = JSONResponse(content=cached_response)
            response.headers["X-Cache"] = "HIT"
            for k, v in rate_limit_headers.items():
                response.headers[k] = v
            return response

    # ── Route to provider (DB-backed) ─────────────────────────────────
    slug = await resolve_provider_slug_from_db(chat_request.model, session)

    # ── Circuit breaker check ─────────────────────────────────────────
    cb = CircuitBreaker(redis_client, slug)
    if not await cb.is_request_allowed():
        # Only failover to providers that support the requested model
        fallback_slugs = [s for s in ("openai", "anthropic", "ollama") if s != slug]
        fallback_found = False
        for fb_slug in fallback_slugs:
            try:
                fb_provider = _get_provider(fb_slug)
                if chat_request.model not in fb_provider.supported_models():
                    continue
            except ValueError:
                continue
            fb_cb = CircuitBreaker(redis_client, fb_slug)
            if await fb_cb.is_request_allowed():
                await logger.awarn(
                    "circuit_breaker_failover", from_provider=slug, to_provider=fb_slug
                )
                slug = fb_slug
                cb = fb_cb
                fallback_found = True
                break
        if not fallback_found:
            response = JSONResponse(
                status_code=503,
                content=ErrorResponse(
                    error=ErrorDetail(
                        type="service_unavailable",
                        message="All providers are currently unavailable. Please try again later.",
                        code="all_providers_down",
                    )
                ).model_dump(),
            )
            for k, v in rate_limit_headers.items():
                response.headers[k] = v
            return response

    provider = _get_provider(slug)

    # ── Streaming path ────────────────────────────────────────────────
    if chat_request.stream:
        try:
            stream_iter = provider.stream(chat_request)
            sse_handler = SSEHandler()

            async def _on_stream_complete(total_tokens: int) -> None:
                """Called after the stream finishes successfully."""
                await cb.record_success()
                latency_ms = (time.time() - start_time) * 1000
                # Track daily token usage for streaming responses
                if total_tokens > 0:
                    try:
                        await check_daily_limit(api_key, redis_client, total_tokens)
                    except Exception:
                        pass  # Don't fail the stream; limit enforced on next request
                log_request(
                    session_factory=get_session_factory(),
                    key_id=api_key.get("id"),
                    model=chat_request.model,
                    provider=slug,
                    input_tokens=0,
                    output_tokens=total_tokens,
                    latency_ms=latency_ms,
                    status_code=200,
                    cached=False,
                )

            async def _on_stream_error(exc: Exception) -> None:
                """Called when the stream encounters an error."""
                await cb.record_failure()

            streaming_response = await sse_handler.stream_response(
                stream_iter,
                chat_request.model,
                on_complete=_on_stream_complete,
                on_error=_on_stream_error,
            )
            for k, v in rate_limit_headers.items():
                streaming_response.headers[k] = v
            streaming_response.headers["X-Cache"] = "MISS"
            return streaming_response
        except Exception as exc:
            await cb.record_failure()
            await logger.aerror(
                "stream_error", model=chat_request.model, error=str(exc)
            )
            response = JSONResponse(
                status_code=502,
                content=ErrorResponse(
                    error=ErrorDetail(
                        type="upstream_error",
                        message="An error occurred while streaming from the upstream provider. Please try again later.",
                        code="stream_failed",
                    )
                ).model_dump(),
            )
            for k, v in rate_limit_headers.items():
                response.headers[k] = v
            return response

    # ── Non-streaming path ────────────────────────────────────────────
    try:
        response_data: ChatResponse = await provider.complete(chat_request)
        await cb.record_success()
    except Exception as exc:
        await cb.record_failure()
        latency_ms = (time.time() - start_time) * 1000
        await logger.aerror(
            "provider_error",
            model=chat_request.model,
            provider=slug,
            error=str(exc),
            latency_ms=latency_ms,
        )
        response = JSONResponse(
            status_code=502,
            content=ErrorResponse(
                error=ErrorDetail(
                    type="upstream_error",
                    message="An error occurred while processing your request with the upstream provider. Please try again later.",
                    code="provider_failed",
                )
            ).model_dump(),
        )
        for k, v in rate_limit_headers.items():
            response.headers[k] = v
        return response

    latency_ms = (time.time() - start_time) * 1000
    response_dict = response_data.model_dump()

    # ── Cache set ─────────────────────────────────────────────────────
    if cache_key is not None:
        await cache_service.set(cache_key, response_dict)

    # ── Daily token tracking (record usage; limit enforced pre-flight) ─
    total_tokens = response_data.usage.total_tokens
    if total_tokens > 0:
        try:
            await check_daily_limit(api_key, redis_client, total_tokens)
        except Exception:
            pass  # Tokens already consumed; limit enforced on next request

    # ── Async logging ─────────────────────────────────────────────────
    log_request(
        session_factory=get_session_factory(),
        key_id=api_key.get("id"),
        model=chat_request.model,
        provider=slug,
        input_tokens=response_data.usage.prompt_tokens,
        output_tokens=response_data.usage.completion_tokens,
        latency_ms=latency_ms,
        status_code=200,
        cached=False,
    )

    # ── Build response ────────────────────────────────────────────────
    json_response = JSONResponse(content=response_dict)
    json_response.headers["X-Cache"] = "MISS"
    for k, v in rate_limit_headers.items():
        json_response.headers[k] = v

    await logger.ainfo(
        "chat_completion_response",
        model=chat_request.model,
        provider=slug,
        latency_ms=round(latency_ms, 2),
        tokens=response_data.usage.total_tokens,
        cached=False,
    )

    return json_response
