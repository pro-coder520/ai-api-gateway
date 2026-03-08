"""FastAPI application factory, lifespan management, and middleware configuration."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from dependencies import init_db_engine, shutdown_db_engine, init_redis, shutdown_redis
from routing.endpoints import router as api_router

logger = structlog.get_logger(__name__)


def configure_logging() -> None:
    """Configure structlog for structured JSON logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.get_level_from_name(settings.gateway_log_level),
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown of shared resources (DB pool, Redis)."""
    configure_logging()
    log = structlog.get_logger("lifespan")
    await log.ainfo("Starting up AI API Gateway")

    await init_db_engine()
    await init_redis()

    yield

    await log.ainfo("Shutting down AI API Gateway")
    await shutdown_redis()
    await shutdown_db_engine()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="AI API Gateway",
        description="Unified gateway for multiple LLM providers with auth, rate limiting, caching, and analytics.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router)

    return application


app = create_app()
