"""Shared public HTTP response schemas."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorBody(APIModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(APIModel):
    error: ErrorBody


T = TypeVar("T")


class ItemList(APIModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
