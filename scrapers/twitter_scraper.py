from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha1

from config import TwitterConfig
from models import FeedItemCreate, SourceType


def scrape_twitter_targets(config: TwitterConfig) -> list[FeedItemCreate]:
    """Return tweet-like feed items from configured targets.

    This intentionally uses mock mode by default. In production this module can be
    replaced with a Tweepy, official X API, Nitter mirror, or paid data-provider
    implementation without changing the public API contract.
    """

    if not config.enabled:
        return []

    if not config.mock_mode:
        # The project skeleton keeps non-mock scraping explicit so credentials and
        # API policies are handled deliberately later.
        return []

    now = datetime.now(timezone.utc)
    items: list[FeedItemCreate] = []

    for account in config.accounts:
        tweet_id = _stable_numeric_id(f"account:{account}")
        items.append(
            FeedItemCreate(
                title=f"X hesabı takibi: @{account}",
                description=(
                    f"@{account} hesabından gelen örnek uyarı. Gerçek X API "
                    "entegrasyonu bağlandığında bu alan tweet metniyle doldurulur."
                ),
                source_url=f"https://twitter.com/{account}/status/{tweet_id}",
                source_type=SourceType.twitter,
                created_at=now,
                source_name=f"@{account}",
                external_id=tweet_id,
            )
        )

    for hashtag in config.hashtags:
        clean_hashtag = hashtag.lstrip("#")
        tweet_id = _stable_numeric_id(f"hashtag:{clean_hashtag}")
        items.append(
            FeedItemCreate(
                title=f"Hashtag takibi: #{clean_hashtag}",
                description=(
                    f"#{clean_hashtag} etiketi için mock haber sinyali üretildi. "
                    "Bu kayıt ana harita servisinde kaynak linkiyle doğrulanabilir."
                ),
                source_url=f"https://twitter.com/hashtag/{clean_hashtag}",
                source_type=SourceType.twitter,
                created_at=now,
                source_name=f"#{clean_hashtag}",
                external_id=tweet_id,
            )
        )

    return items


def _stable_numeric_id(value: str) -> str:
    digest = sha1(value.encode("utf-8")).hexdigest()
    return str(int(digest[:15], 16))
