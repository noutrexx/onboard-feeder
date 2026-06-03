from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    twitter = "twitter"
    rss_news = "rss_news"


class FeedItemCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=1, max_length=500)
    source_url: HttpUrl
    source_type: SourceType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_name: str | None = Field(default=None, max_length=120)
    external_id: str | None = Field(default=None, max_length=260)
    has_location: bool = False
    location_tag: str | None = Field(default=None, max_length=80)
    location_city: str | None = Field(default=None, max_length=80)
    location_text: str | None = Field(default=None, max_length=160)
    location_lat: float | None = None
    location_lng: float | None = None
    location_confidence: float | None = Field(default=None, ge=0, le=1)


class FeedItem(FeedItemCreate):
    id: int
    inserted_at: datetime


class HealthResponse(BaseModel):
    ok: bool
    service: str
    stored_items: int
    located_items: int
