"""Pydantic v2 models for outgoing responses (OpenAI-compatible format)."""

import time
import uuid

from pydantic import BaseModel, Field


class Usage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChoiceMessage(BaseModel):
    """A message returned by a chat completion."""

    role: str = "assistant"
    content: str = ""


class Choice(BaseModel):
    """A single completion choice."""

    index: int = 0
    message: ChoiceMessage
    finish_reason: str | None = "stop"


class ChatResponse(BaseModel):
    """OpenAI-compatible chat completion response payload."""

    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[Choice]
    usage: Usage = Field(default_factory=Usage)


class StreamDelta(BaseModel):
    """Delta content in a streaming chunk."""

    role: str | None = None
    content: str | None = None


class StreamChoice(BaseModel):
    """A single choice in a streaming chunk."""

    index: int = 0
    delta: StreamDelta
    finish_reason: str | None = None


class StreamChunk(BaseModel):
    """OpenAI-compatible streaming chunk."""

    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[StreamChoice]


class ErrorDetail(BaseModel):
    """Structured error detail."""

    type: str
    message: str
    code: str


class ErrorResponse(BaseModel):
    """Structured JSON error response."""

    error: ErrorDetail
