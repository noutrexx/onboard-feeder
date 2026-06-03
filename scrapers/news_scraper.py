from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests
from bs4 import BeautifulSoup

from config import RssNewsConfig
from models import FeedItemCreate, SourceType


def scrape_rss_targets(
    config: RssNewsConfig,
    timeout_seconds: int,
    user_agent: str,
    status_callback=None,
) -> list[FeedItemCreate]:
    if not config.enabled:
        return []

    items: list[FeedItemCreate] = []

    for target in config.feeds:
        try:
            response = requests.get(
                str(target.url),
                headers={"User-Agent": user_agent},
                timeout=timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            if status_callback:
                status_callback(
                    source_key=str(target.url),
                    source_type="rss_news",
                    source_name=target.name,
                    status="error",
                    error=str(error)[:500],
                )
            continue

        parsed_feed = feedparser.parse(response.content)
        if status_callback:
            status_callback(
                source_key=str(target.url),
                source_type="rss_news",
                source_name=target.name,
                status="ok",
                error=None,
            )

        for entry in parsed_feed.entries:
            source_url = entry.get("link")
            title = _clean_html(entry.get("title", "")).strip()
            description = _clean_html(
                entry.get("summary") or entry.get("description") or title
            ).strip()

            if not source_url or not title:
                continue

            items.append(
                FeedItemCreate(
                    title=title[:240],
                    description=(description or title)[:500],
                    source_url=source_url,
                    source_type=SourceType.rss_news,
                    created_at=_parse_entry_datetime(entry),
                    source_name=target.name,
                    external_id=entry.get("id") or source_url,
                )
            )

    return items


def _clean_html(value: str) -> str:
    if "<" not in (value or ""):
        return " ".join((value or "").split())

    soup = BeautifulSoup(value or "", "html.parser")
    return " ".join(soup.get_text(" ").split())


def _parse_entry_datetime(entry: dict) -> datetime:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue

        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue

    return datetime.now(timezone.utc)
