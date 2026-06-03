from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass

import requests

from config import AlertIntegrationConfig
from models import FeedItem


@dataclass
class PushResult:
    attempted: int
    pushed: int
    failed: int
    errors: list[str]


def push_items_to_alert(
    items: list[FeedItem],
    integration: AlertIntegrationConfig,
) -> PushResult:
    if not integration.enabled:
        return PushResult(attempted=0, pushed=0, failed=0, errors=["integration_disabled"])

    if not integration.bot_ingest_api_key:
        return PushResult(attempted=0, pushed=0, failed=0, errors=["missing_bot_ingest_api_key"])

    endpoint = f"{integration.api_url.rstrip('/')}/api/webhooks/bot-ingest"
    pushed = 0
    errors: list[str] = []

    for item in items:
        payload = _to_bot_payload(item, integration.min_confidence)
        headers = _headers(payload, integration)

        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            pushed += 1
        except requests.RequestException as error:
            errors.append(f"{item.source_url}: {error}")

    attempted = len(items)
    return PushResult(attempted=attempted, pushed=pushed, failed=attempted - pushed, errors=errors[:10])


def _to_bot_payload(item: FeedItem, min_confidence: float) -> dict[str, object]:
    confidence = item.location_confidence or min_confidence
    source = "twitter_bot" if item.source_type.value == "twitter" else "rss_feed"

    return {
        "title": item.title,
        "description": item.description[:300],
        "lat": item.location_lat if item.has_location else None,
        "lng": item.location_lng if item.has_location else None,
        "locationText": item.location_city or item.location_text,
        "severity": "green",
        "source": source,
        "sourceUrl": str(item.source_url),
        "confidence": max(min_confidence, min(float(confidence), 1.0)),
        "metadata": {
            "feeder_id": item.id,
            "feeder_source_type": item.source_type.value,
            "feeder_source_name": item.source_name,
            "location_tag": item.location_tag,
        },
    }


def _headers(payload: dict[str, object], integration: AlertIntegrationConfig) -> dict[str, str]:
    headers = {"x-api-key": integration.bot_ingest_api_key or ""}

    if integration.bot_ingest_hmac_secret:
        timestamp = str(int(time.time() * 1000))
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        signature = hmac.new(
            integration.bot_ingest_hmac_secret.encode("utf-8"),
            f"{timestamp}.{body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers.update({"x-timestamp": timestamp, "x-signature": signature})

    return headers
