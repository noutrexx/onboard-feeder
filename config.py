from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl


CONFIG_PATH = Path(__file__).with_name("config.json")


class AppConfig(BaseModel):
    admin_api_key: str | None = Field(default=None, min_length=16)
    cors_origins: list[str] = Field(default_factory=list)
    database_path: str = "storage/feeds.db"
    poll_interval_minutes: int = Field(default=15, ge=1)
    request_timeout_seconds: int = Field(default=12, ge=1)
    user_agent: str = "onboard-feeder/1.0"


class TwitterConfig(BaseModel):
    enabled: bool = True
    mock_mode: bool = True
    accounts: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)


class RssTarget(BaseModel):
    name: str
    url: HttpUrl


class RssNewsConfig(BaseModel):
    enabled: bool = True
    feeds: list[RssTarget] = Field(default_factory=list)


class Settings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    twitter: TwitterConfig = Field(default_factory=TwitterConfig)
    rss_news: RssNewsConfig = Field(default_factory=RssNewsConfig)


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config file: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        raw_config = json.load(config_file)

    return Settings.model_validate(raw_config)


def reload_settings() -> Settings:
    load_settings.cache_clear()
    return load_settings()
