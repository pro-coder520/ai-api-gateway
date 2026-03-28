"""SQLAlchemy async models for API keys and rate limit policies."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


class ApiKey(Base):
    """Represents an API key used by clients to authenticate with the gateway."""

    __tablename__ = "keys_apikey"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prefix: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    hashed_key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)

    rate_limit_policy: Mapped["RateLimitPolicy | None"] = relationship(
        "RateLimitPolicy", back_populates="api_key", uselist=False
    )

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name='{self.name}', prefix='{self.prefix}')>"


class RateLimitPolicy(Base):
    """Rate limit policy attached to an API key."""

    __tablename__ = "keys_ratelimitpolicy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("keys_apikey.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    refill_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    daily_token_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1_000_000
    )

    api_key: Mapped["ApiKey"] = relationship(
        "ApiKey", back_populates="rate_limit_policy"
    )

    def __repr__(self) -> str:
        return (
            f"<RateLimitPolicy(api_key_id={self.api_key_id}, capacity={self.capacity})>"
        )


class Provider(Base):
    """Represents an LLM provider configuration."""

    __tablename__ = "keys_provider"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    api_base: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key_env_var: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    model_prefix: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Provider(name='{self.name}', slug='{self.slug}')>"
