from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from models import FeedItem, FeedItemCreate, SourceType


class FeedRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=15000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feed_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    source_url TEXT NOT NULL UNIQUE,
                    source_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    inserted_at TEXT NOT NULL,
                    source_name TEXT,
                    external_id TEXT,
                    has_location INTEGER NOT NULL DEFAULT 0,
                    location_tag TEXT,
                    location_city TEXT,
                    location_text TEXT,
                    location_lat REAL,
                    location_lng REAL,
                    location_confidence REAL
                )
                """
            )
            self._ensure_location_columns(connection)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_feed_items_created_at ON feed_items(created_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_feed_items_source_type ON feed_items(source_type)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_feed_items_has_location ON feed_items(has_location)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS source_status (
                    source_key TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    last_status TEXT NOT NULL,
                    last_error TEXT,
                    last_checked_at TEXT NOT NULL,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0
                )
                """
            )

    def upsert_many(self, items: Iterable[FeedItemCreate]) -> int:
        inserted = 0
        with self.connect() as connection:
            for item in items:
                cursor = connection.execute(
                    """
                    INSERT INTO feed_items (
                        title,
                        description,
                        source_url,
                        source_type,
                        created_at,
                        inserted_at,
                        source_name,
                        external_id,
                        has_location,
                        location_tag,
                        location_city,
                        location_text,
                        location_lat,
                        location_lng,
                        location_confidence
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_url) DO UPDATE SET
                        title = excluded.title,
                        description = excluded.description,
                        source_type = excluded.source_type,
                        created_at = excluded.created_at,
                        source_name = excluded.source_name,
                        external_id = excluded.external_id,
                        has_location = excluded.has_location,
                        location_tag = excluded.location_tag,
                        location_city = excluded.location_city,
                        location_text = excluded.location_text,
                        location_lat = excluded.location_lat,
                        location_lng = excluded.location_lng,
                        location_confidence = excluded.location_confidence
                    """,
                    (
                        item.title,
                        item.description,
                        str(item.source_url),
                        item.source_type.value,
                        item.created_at.isoformat(),
                        datetime.now(timezone.utc).isoformat(),
                        item.source_name,
                        item.external_id,
                        1 if item.has_location else 0,
                        item.location_tag,
                        item.location_city,
                        item.location_text,
                        item.location_lat,
                        item.location_lng,
                        item.location_confidence,
                    ),
                )
                inserted += cursor.rowcount
        return inserted

    def list_recent(self, limit: int = 50, offset: int = 0, location_only: bool = False) -> list[FeedItem]:
        where_clause = "WHERE has_location = 1" if location_only else ""
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM feed_items
                {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

        return [self._row_to_model(row) for row in rows]

    def count(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM feed_items").fetchone()
        return int(row["total"])

    def count_located(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM feed_items WHERE has_location = 1"
            ).fetchone()
        return int(row["total"])

    def record_source_status(
        self,
        *,
        source_key: str,
        source_type: str,
        source_name: str,
        status: str,
        error: str | None = None,
    ) -> None:
        checked_at = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            current = connection.execute(
                "SELECT consecutive_failures FROM source_status WHERE source_key = ?",
                (source_key,),
            ).fetchone()
            failures = int(current["consecutive_failures"]) if current else 0
            next_failures = 0 if status == "ok" else failures + 1
            connection.execute(
                """
                INSERT INTO source_status (
                    source_key,
                    source_type,
                    source_name,
                    last_status,
                    last_error,
                    last_checked_at,
                    consecutive_failures
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_key) DO UPDATE SET
                    source_type = excluded.source_type,
                    source_name = excluded.source_name,
                    last_status = excluded.last_status,
                    last_error = excluded.last_error,
                    last_checked_at = excluded.last_checked_at,
                    consecutive_failures = excluded.consecutive_failures
                """,
                (
                    source_key,
                    source_type,
                    source_name,
                    status,
                    error,
                    checked_at,
                    next_failures,
                ),
            )

    def list_source_status(self) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM source_status
                ORDER BY last_checked_at DESC
                """
            ).fetchall()

        return [dict(row) for row in rows]

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> FeedItem:
        return FeedItem(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            source_url=row["source_url"],
            source_type=SourceType(row["source_type"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            inserted_at=datetime.fromisoformat(row["inserted_at"]),
            source_name=row["source_name"],
            external_id=row["external_id"],
            has_location=bool(row["has_location"]),
            location_tag=row["location_tag"],
            location_city=row["location_city"],
            location_text=row["location_text"],
            location_lat=row["location_lat"],
            location_lng=row["location_lng"],
            location_confidence=row["location_confidence"],
        )

    @staticmethod
    def _ensure_location_columns(connection: sqlite3.Connection) -> None:
        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(feed_items)").fetchall()
        }
        migrations = {
            "has_location": "ALTER TABLE feed_items ADD COLUMN has_location INTEGER NOT NULL DEFAULT 0",
            "location_tag": "ALTER TABLE feed_items ADD COLUMN location_tag TEXT",
            "location_city": "ALTER TABLE feed_items ADD COLUMN location_city TEXT",
            "location_text": "ALTER TABLE feed_items ADD COLUMN location_text TEXT",
            "location_lat": "ALTER TABLE feed_items ADD COLUMN location_lat REAL",
            "location_lng": "ALTER TABLE feed_items ADD COLUMN location_lng REAL",
            "location_confidence": "ALTER TABLE feed_items ADD COLUMN location_confidence REAL",
        }

        for column_name, statement in migrations.items():
            if column_name not in existing_columns:
                connection.execute(statement)
