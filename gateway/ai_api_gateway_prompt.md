# Master Prompt: AI-Powered API Gateway with Django & FastAPI

> **Usage:** Feed this prompt to a coding-capable LLM (Claude, GPT-4, Codex, Gemini, etc.) to scaffold and build the entire project. The prompt is structured to maximize output quality by providing explicit constraints, architecture decisions, file structure, and implementation order.

---

## System Context

You are an expert Python backend engineer specializing in distributed systems, API design, and async programming. You are building a production-grade AI-Powered API Gateway — a system that sits between client applications and multiple LLM providers (OpenAI, Anthropic, local models via Ollama), providing unified authentication, multi-provider routing, token-bucket rate limiting, response caching, usage analytics, circuit breaker resilience, and SSE streaming pass-through.

The system has two services:
1. **FastAPI Gateway** — the hot path. All client requests flow through here. Fully async, stateless, horizontally scalable.
2. **Django Admin Portal** — the control plane. Manages API keys, displays usage analytics, configures rate limits, and tracks billing.

Both services share **PostgreSQL** (source of truth) and **Redis** (cache, rate limiter, circuit breaker state, Celery broker).

---

## Hard Constraints

- **Python 3.11+** — use modern syntax (match-case, type hints everywhere, `|` union types).
- **Fully async FastAPI** — no synchronous DB calls or HTTP requests in the gateway. Use `httpx.AsyncClient`, `asyncpg` via async SQLAlchemy.
- **Django 5.x** with Django REST Framework for the admin API.
- **SQLAlchemy 2.0** (async) for FastAPI's database layer. Do NOT share Django ORM models with FastAPI.
- **Redis 7+** with `redis.asyncio` for the gateway.
- **Docker Compose** for local development with all services (FastAPI, Django, PostgreSQL, Redis).
- **OpenAI-compatible API format** — the gateway's `/v1/chat/completions` endpoint must accept and return payloads in OpenAI's format so clients need zero changes.
- **Pydantic v2** for all request/response validation.
- **100% type-annotated** — every function signature, every variable where non-obvious.
- Every module must have a docstring. Every public function must have a docstring.

---

## Project Structure

Generate the following directory layout. Do not deviate from it.

```
ai-api-gateway/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── gateway/                          # FastAPI service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                       # FastAPI app factory, lifespan, middleware
│   ├── config.py                     # Pydantic Settings (env-based config)
│   ├── dependencies.py               # Dependency injection (Redis, DB session, auth)
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── service.py                # API key validation, hashing, caching
│   │   └── models.py                 # SQLAlchemy models (ApiKey, RateLimitPolicy)
│   │
│   ├── routing/
│   │   ├── __init__.py
│   │   ├── router.py                 # Provider selection logic
│   │   └── endpoints.py              # /v1/chat/completions, /v1/models, /health
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract BaseProvider interface
│   │   ├── openai.py                 # OpenAI provider implementation
│   │   ├── anthropic.py              # Anthropic provider implementation
│   │   └── ollama.py                 # Ollama (local) provider implementation
│   │
│   ├── ratelimit/
│   │   ├── __init__.py
│   │   ├── token_bucket.py           # Redis-backed token bucket with Lua scripts
│   │   └── middleware.py             # Rate limit middleware / dependency
│   │
│   ├── cache/
│   │   ├── __init__.py
│   │   └── service.py                # Request hashing, Redis cache get/set with TTL
│   │
│   ├── resilience/
│   │   ├── __init__.py
│   │   ├── circuit_breaker.py        # Per-provider circuit breaker (Redis-backed)
│   │   └── retry.py                  # Exponential backoff with jitter
│   │
│   ├── streaming/
│   │   ├── __init__.py
│   │   └── sse.py                    # SSE pass-through and token counting mid-stream
│   │
│   ├── logging_/
│   │   ├── __init__.py
│   │   ├── service.py                # Async request logger (writes to PostgreSQL)
│   │   └── models.py                 # SQLAlchemy model: RequestLog
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── requests.py               # Pydantic models for incoming requests
│   │   └── responses.py              # Pydantic models for outgoing responses
│   │
│   └── tests/
│       ├── conftest.py               # Fixtures: async client, mock Redis, mock DB
│       ├── test_auth.py
│       ├── test_ratelimit.py
│       ├── test_routing.py
│       ├── test_cache.py
│       ├── test_circuit_breaker.py
│       └── test_e2e.py               # Full request lifecycle test
│
├── admin_portal/                     # Django service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── admin_portal/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── keys/                         # API Key management app
│   │   ├── models.py                 # Django models (mirrors gateway schema)
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── admin.py
│   │
│   ├── analytics/                    # Usage analytics app
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tasks.py                  # Celery tasks for aggregation
│   │
│   └── billing/                      # Cost tracking app
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       └── urls.py
│
└── scripts/
    ├── seed_providers.py             # Seed initial provider configs
    └── generate_key.py               # CLI tool to generate an API key
```

---

## Implementation Order

Build in this exact sequence. Complete each step fully (including tests) before moving to the next.

### Step 1: Project Skeleton & Docker
- Generate `docker-compose.yml` with FastAPI (uvicorn), Django (gunicorn), PostgreSQL 16, and Redis 7 services.
- Generate `.env.example` with all required environment variables.
- Create both Dockerfiles and `requirements.txt` files.
- Verify all four containers start and communicate.

### Step 2: Database Models & Migrations
- Define SQLAlchemy async models in the gateway: `ApiKey`, `RateLimitPolicy`, `Provider`, `RequestLog`.
- Define mirrored Django models in admin_portal for the same tables.
- Both services must point to the same PostgreSQL database.
- Run Django migrations to create all tables. SQLAlchemy reads from them (no Alembic needed for v1).

### Step 3: API Key Auth
- `POST /api/keys/` (Django) — create a key, return plaintext once, store SHA-256 hash.
- Gateway dependency that extracts the `Authorization: Bearer <key>` header, hashes it, and validates against DB (with Redis cache for hot lookups, TTL 5 min).
- Return 401 for invalid/expired keys. Include `X-RateLimit-*` headers in every response.

### Step 4: Single Provider Proxy (OpenAI)
- Implement `BaseProvider` abstract class with:
  - `async def complete(self, request: ChatRequest) -> ChatResponse`
  - `async def stream(self, request: ChatRequest) -> AsyncIterator[str]`
  - `async def health_check(self) -> bool`
- Implement `OpenAIProvider` using `httpx.AsyncClient` with connection pooling and 30s timeout.
- Create `POST /v1/chat/completions` that validates the request, calls OpenAI, and returns the response.
- Write integration tests with a mock upstream.

### Step 5: Multi-Provider Routing
- Implement `AnthropicProvider` and `OllamaProvider`.
- Build the router: inspect `request.model`, map to provider. E.g., `gpt-*` → OpenAI, `claude-*` → Anthropic, everything else → Ollama.
- The mapping must be configurable via the `providers` DB table, not hardcoded.
- `GET /v1/models` returns all available models across all healthy providers.

### Step 6: Token Bucket Rate Limiting
- Implement in Redis using a Lua script for atomicity (no race conditions).
- Each key has: `capacity` (max burst), `refill_rate` (tokens/sec), `tokens_per_day` (daily cap).
- On each request: consume 1 token from the bucket. If empty, return 429 with `Retry-After` header.
- Track daily token consumption separately (reset at midnight UTC).
- Add `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers to every response.

### Step 7: Response Caching
- Hash the cache key from: `model + messages + temperature + max_tokens + top_p`.
- Only cache when `temperature == 0` (deterministic). Never cache streaming requests.
- Store in Redis with configurable TTL (default 1 hour).
- Add `X-Cache: HIT` or `X-Cache: MISS` response header.
- Cache entries must be invalidated when the provider or model is updated.

### Step 8: Circuit Breaker
- Three states per provider: CLOSED, OPEN, HALF_OPEN.
- Config: `failure_threshold=5`, `recovery_timeout=30s`, `half_open_max_requests=3`.
- Track failures in Redis with sliding window (sorted set with timestamps).
- When OPEN: immediately failover to next healthy provider. If no healthy provider, return 503.
- When HALF_OPEN: allow `half_open_max_requests` test requests. If all succeed, close. If any fail, reopen.
- Expose circuit state via `GET /health` endpoint.

### Step 9: SSE Streaming
- When client sends `"stream": true`, the gateway must:
  - Open an SSE connection to the upstream provider.
  - Forward each chunk to the client as `data: {...}\n\n`.
  - Count tokens incrementally during streaming (accumulate and log at end).
  - Handle client disconnect gracefully (cancel upstream request).
- Use `StreamingResponse` from Starlette with `media_type="text/event-stream"`.

### Step 10: Request Logging & Analytics
- Log every request asynchronously (do not block the response). Use `asyncio.create_task` or a background task.
- Log fields: `key_id, model, provider, input_tokens, output_tokens, total_tokens, latency_ms, status_code, cost_usd, cached, timestamp`.
- Calculate `cost_usd` using a cost-per-token lookup table per model.
- Django analytics views: usage over time, cost by key, cost by model, error rates, cache hit ratio, average latency.

### Step 11: Django Admin Dashboard
- API key management: create, list, revoke, update rate limits, set model scopes.
- Usage dashboard: date-range filtered charts for requests, tokens, cost, errors.
- Provider health: current circuit breaker state, uptime percentage, average latency.
- Celery periodic task: aggregate `request_logs` into `billing_records` daily.

### Step 12: Testing & Documentation
- Unit tests for every module (auth, rate limit, cache, circuit breaker, routing).
- Integration tests that spin up FastAPI + Redis + PostgreSQL via Docker.
- Load test with `locust` — target 500 RPS with < 50ms p99 gateway overhead.
- Auto-generated OpenAPI docs at `/docs` (FastAPI default).
- README with setup instructions, architecture diagram (Mermaid), and usage examples.

---

## Code Quality Standards

- Use `ruff` for linting and formatting (line length 100).
- Use `mypy --strict` for type checking.
- Every error must have a structured JSON response: `{"error": {"type": "...", "message": "...", "code": "..."}}`.
- Use Python's `logging` module with `structlog` for structured JSON output. Never use `print()`.
- All secrets loaded from environment variables via Pydantic Settings. Never hardcode.
- Write defensive code: validate all inputs, handle all edge cases, fail gracefully.

---

## Critical Implementation Details

### Token Bucket Lua Script (Redis)
```lua
-- KEYS[1] = bucket key, ARGV[1] = capacity, ARGV[2] = refill_rate, ARGV[3] = now (unix ts)
local bucket = redis.call('HMGET', KEYS[1], 'tokens', 'last_refill')
local tokens = tonumber(bucket[1]) or tonumber(ARGV[1])
local last = tonumber(bucket[2]) or tonumber(ARGV[3])
local elapsed = tonumber(ARGV[3]) - last
local refill = math.min(tonumber(ARGV[1]), tokens + elapsed * tonumber(ARGV[2]))
if refill >= 1 then
    redis.call('HMSET', KEYS[1], 'tokens', refill - 1, 'last_refill', ARGV[3])
    redis.call('EXPIRE', KEYS[1], 86400)
    return 1  -- allowed
else
    redis.call('HMSET', KEYS[1], 'tokens', refill, 'last_refill', ARGV[3])
    redis.call('EXPIRE', KEYS[1], 86400)
    return 0  -- denied
end
```

### Provider Base Class Signature
```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from schemas.requests import ChatRequest
from schemas.responses import ChatResponse

class BaseProvider(ABC):
    @abstractmethod
    async def complete(self, request: ChatRequest) -> ChatResponse: ...

    @abstractmethod
    async def stream(self, request: ChatRequest) -> AsyncIterator[str]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    @abstractmethod
    def supported_models(self) -> list[str]: ...
```

### Cache Key Generation
```python
import hashlib, json

def generate_cache_key(model: str, messages: list, **params) -> str:
    payload = json.dumps({"model": model, "messages": messages, **params}, sort_keys=True)
    return f"cache:{hashlib.sha256(payload.encode()).hexdigest()}"
```

---

## Output Instructions

1. Generate every file listed in the project structure above with complete, working code.
2. Do not use placeholder comments like `# TODO` or `pass` — implement everything fully.
3. Include inline comments only where the logic is non-obvious.
4. Generate the `docker-compose.yml` so that `docker compose up` starts the entire stack.
5. After generating all files, provide a "Quick Start" section with the exact commands to run the project from scratch.

Begin with Step 1 (Docker + skeleton) and proceed through all 12 steps sequentially. Generate complete, production-quality code for each step before moving to the next.

Remember: Always commit and push to GitHub whenever you make a change or create a file.