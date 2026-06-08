from __future__ import annotations

import hashlib
import hmac
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from config import AlertIntegrationConfig
from models import FeedItem, SourceType
from services.alert_client import _to_bot_payload, push_items_to_alert


def make_item(**overrides: object) -> FeedItem:
    values: dict[str, object] = {
        "id": 1,
        "title": "Adana test alert",
        "description": "A short alert description.",
        "source_url": "https://example.com/news/1",
        "source_type": SourceType.rss_news,
        "created_at": datetime.now(timezone.utc),
        "inserted_at": datetime.now(timezone.utc),
        "source_name": "Example News",
        "has_location": True,
        "location_city": "Adana",
        "location_lat": 37.0,
        "location_lng": 35.3213,
        "location_confidence": 0.0,
    }
    values.update(overrides)
    return FeedItem.model_validate(values)


class AlertPayloadTests(unittest.TestCase):
    def test_payload_matches_onboard_alert_schema(self) -> None:
        payload = _to_bot_payload(
            make_item(
                title="x" * 240,
                description="ok",
                has_location=False,
                location_city=None,
                location_lat=None,
                location_lng=None,
            ),
            min_confidence=0.55,
        )

        self.assertEqual(len(payload["title"]), 220)
        self.assertGreaterEqual(len(payload["description"]), 5)
        self.assertEqual(payload["confidence"], 0.0)
        self.assertNotIn("lat", payload)
        self.assertNotIn("lng", payload)
        self.assertNotIn("locationText", payload)

    def test_invalid_coordinates_are_left_for_alert_geocoding(self) -> None:
        payload = _to_bot_payload(
            make_item(location_lat=91, location_lng=181, location_city="Adana"),
            min_confidence=0.55,
        )

        self.assertNotIn("lat", payload)
        self.assertNotIn("lng", payload)
        self.assertEqual(payload["locationText"], "Adana")

    @patch("services.alert_client.requests.post")
    def test_hmac_signs_the_exact_json_body_sent_to_alert(self, post: Mock) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        post.return_value = response
        integration = AlertIntegrationConfig(
            enabled=True,
            bot_ingest_api_key="bot-api-key-value",
            bot_ingest_hmac_secret="a-long-enough-shared-hmac-secret",
        )

        result = push_items_to_alert([make_item()], integration)

        self.assertEqual(result.pushed, 1)
        request = post.call_args
        body = request.kwargs["data"].decode("utf-8")
        headers = request.kwargs["headers"]
        expected_signature = hmac.new(
            integration.bot_ingest_hmac_secret.encode("utf-8"),
            f"{headers['x-timestamp']}.{body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        self.assertEqual(headers["x-signature"], expected_signature)
        self.assertEqual(request.kwargs["timeout"], 10)
        self.assertEqual(json.loads(body)["lat"], 37)
        self.assertNotIn('"lat":37.0', body)


if __name__ == "__main__":
    unittest.main()
