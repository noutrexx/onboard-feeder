from __future__ import annotations

from config import Settings
from models import FeedItemCreate
from scrapers.news_scraper import scrape_rss_targets
from scrapers.twitter_scraper import scrape_twitter_targets
from services.location_extractor import enrich_items_location
from services.alert_client import push_items_to_alert
from storage.repository import FeedRepository


class FeedCollector:
    def __init__(self, settings: Settings, repository: FeedRepository) -> None:
        self.settings = settings
        self.repository = repository

    def collect_once(self) -> dict[str, int]:
        items = self.collect_items()
        inserted = self.repository.upsert_many(items)
        result = {"collected": len(items), "inserted": inserted}
        if self.settings.alert_integration.push_after_collect:
            recent = self.repository.list_recent(limit=len(items))
            push = push_items_to_alert(recent, self.settings.alert_integration)
            result.update({"pushed": push.pushed, "push_failed": push.failed})
        return result

    def collect_items(self) -> list[FeedItemCreate]:
        items: list[FeedItemCreate] = []
        items.extend(scrape_twitter_targets(self.settings.twitter))
        for account in self.settings.twitter.accounts:
            self.repository.record_source_status(
                source_key=f"x:account:{account}",
                source_type="twitter",
                source_name=f"@{account}",
                status="ok" if self.settings.twitter.mock_mode else "disabled",
                error="mock mode" if self.settings.twitter.mock_mode else "twitter scraper disabled",
            )
        for hashtag in self.settings.twitter.hashtags:
            self.repository.record_source_status(
                source_key=f"x:hashtag:{hashtag.lstrip('#')}",
                source_type="twitter",
                source_name=f"#{hashtag.lstrip('#')}",
                status="ok" if self.settings.twitter.mock_mode else "disabled",
                error="mock mode" if self.settings.twitter.mock_mode else "twitter scraper disabled",
            )
        items.extend(
            scrape_rss_targets(
                self.settings.rss_news,
                timeout_seconds=self.settings.app.request_timeout_seconds,
                user_agent=self.settings.app.user_agent,
                status_callback=self.repository.record_source_status,
            )
        )
        return enrich_items_location(items)
