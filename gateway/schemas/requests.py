"""Pydantic v2 models for incoming requests (OpenAI-compatible format)."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: str = Field(
        ..., description="Role of the message author: system, user, or assistant"
    )
    content: str = Field(..., description="Content of the message")
    name: str | None = Field(default=None, description="Optional name of the author")


class ChatRequest(BaseModel):
    """OpenAI-compatible chat completion request payload."""

    model: str = Field(
        ..., description="Model identifier, e.g. 'gpt-4', 'claude-3-opus'"
    )
    messages: list[ChatMessage] = Field(
        ..., min_length=1, description="List of messages in the conversation"
    )
    temperature: float | None = Field(
        default=1.0, ge=0.0, le=2.0, description="Sampling temperature"
    )
    top_p: float | None = Field(
        default=1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter"
    )
    max_tokens: int | None = Field(
        default=None, gt=0, description="Maximum tokens to generate"
    )
    stream: bool = Field(
        default=False, description="Whether to stream the response via SSE"
    )
    n: int = Field(
        default=1, ge=1, le=10, description="Number of completions to generate"
    )
    stop: str | list[str] | None = Field(default=None, description="Stop sequences")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    user: str | None = Field(
        default=None, description="End-user identifier for abuse detection"
    )
