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
        body = _serialize_payload(payload)
        headers = _headers(body, integration)

        try:
            response = requests.post(
                endpoint,
                data=body.encode("utf-8"),
                headers=headers,
                timeout=integration.request_timeout_seconds,
            )
            response.raise_for_status()
            pushed += 1
        except requests.RequestException as error:
            detail = str(error)
            if error.response is not None and error.response.text:
                detail = f"{detail}: {error.response.text[:300]}"
            errors.append(f"{item.source_url}: {detail}")

    attempted = len(items)
    return PushResult(attempted=attempted, pushed=pushed, failed=attempted - pushed, errors=errors[:10])


def _to_bot_payload(item: FeedItem, min_confidence: float) -> dict[str, object]:
    confidence = (
        item.location_confidence
        if item.location_confidence is not None
        else min_confidence
    )
    source = "twitter_bot" if item.source_type.value == "twitter" else "rss_feed"
    title = item.title.strip()[:220]
    if len(title) < 3:
        title = f"{title} alert".strip()[:220]
    description = (item.description.strip() or title)[:300]
    if len(description) < 5:
        description = f"{description} feed"[:300]

    payload: dict[str, object] = {
        "title": title,
        "description": description,
        "severity": "green",
        "source": source,
        "sourceUrl": str(item.source_url),
        "confidence": max(0.0, min(float(confidence), 1.0)),
        "metadata": {
            "feeder_id": item.id,
            "feeder_source_type": item.source_type.value,
            "feeder_source_name": item.source_name,
            "location_tag": item.location_tag,
        },
    }

    if (
        item.has_location
        and item.location_lat is not None
        and item.location_lng is not None
        and -90 <= item.location_lat <= 90
        and -180 <= item.location_lng <= 180
    ):
        payload.update({"lat": item.location_lat, "lng": item.location_lng})

    location_text = (item.location_city or item.location_text or "").strip()[:180]
    if len(location_text) >= 2:
        payload["locationText"] = location_text

    return payload


def _serialize_payload(payload: dict[str, object]) -> str:
    normalized = _normalize_integral_floats(payload)
    return json.dumps(
        normalized,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _normalize_integral_floats(value: object) -> object:
    """Match JSON.stringify for integral numbers used in HMAC-protected payloads."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: _normalize_integral_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_integral_floats(item) for item in value]
    return value


def _headers(body: str, integration: AlertIntegrationConfig) -> dict[str, str]:
    headers = {
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "x-api-key": integration.bot_ingest_api_key or "",
    }

    if integration.bot_ingest_hmac_secret:
        timestamp = str(int(time.time() * 1000))
        signature = hmac.new(
            integration.bot_ingest_hmac_secret.encode("utf-8"),
            f"{timestamp}.{body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers.update({"x-timestamp": timestamp, "x-signature": signature})

    return headers
