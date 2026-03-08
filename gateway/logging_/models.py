"""SQLAlchemy model for the request log table."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from auth.models import Base


class RequestLog(Base):
    """Stores every request flowing through the gateway for analytics.

    Written asynchronously so logging never blocks the response path.
    """

    __tablename__ = "analytics_requestlog"

    id: int = None  # type: ignore[assignment]
    __table_args__ = {"extend_existing": True}

    from sqlalchemy.orm import Mapped, mapped_column

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    model: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
