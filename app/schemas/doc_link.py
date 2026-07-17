import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("URL must be http or https with a non-empty host")
    return value


def _validate_non_empty(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be empty")
    return stripped


class DocLinkBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    url: str
    category: str = Field(..., min_length=1, max_length=100)

    @field_validator("title")
    @classmethod
    def _title_non_empty(cls, value: str) -> str:
        return _validate_non_empty(value, "title")

    @field_validator("category")
    @classmethod
    def _category_non_empty(cls, value: str) -> str:
        return _validate_non_empty(value, "category")

    @field_validator("url")
    @classmethod
    def _url_valid(cls, value: str) -> str:
        return _validate_url(value)


class DocLinkCreate(DocLinkBase):
    pass


class DocLinkUpdate(BaseModel):
    """Partial update - a field left unset means "not supplied," never "clear it": no field on
    ``DocLink`` is nullable in the DB, so there is no way to null one out via this schema."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    url: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("title")
    @classmethod
    def _title_non_empty(cls, value: str | None) -> str | None:
        return value if value is None else _validate_non_empty(value, "title")

    @field_validator("category")
    @classmethod
    def _category_non_empty(cls, value: str | None) -> str | None:
        return value if value is None else _validate_non_empty(value, "category")

    @field_validator("url")
    @classmethod
    def _url_valid(cls, value: str | None) -> str | None:
        return value if value is None else _validate_url(value)


class DocLinkResponse(DocLinkBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
