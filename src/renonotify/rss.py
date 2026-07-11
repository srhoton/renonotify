"""Collect recent entries from a list of RSS/Atom feeds."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import feedparser

log = logging.getLogger(__name__)


def _entry_time(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
    return None


def collect_entries(feed_urls: list[str], cutoff: datetime) -> list[dict]:
    """Return feed entries newer than `cutoff` as simple dicts."""
    items: list[dict] = []

    for url in feed_urls:
        try:
            feed = feedparser.parse(url)
        except Exception:
            log.exception("Failed to parse feed: %s", url)
            continue

        if feed.bozo and not feed.entries:
            log.warning("Feed unreadable, skipping: %s", url)
            continue

        feed_title = feed.feed.get("title", url)
        for entry in feed.entries:
            ts = _entry_time(entry)
            if ts is None or ts < cutoff:
                continue
            summary = entry.get("summary", "") or ""
            # Strip to a reasonable length; the LLM doesn't need full articles
            if len(summary) > 1000:
                summary = summary[:1000] + "…"
            items.append(
                {
                    "source": "rss",
                    "feed": feed_title,
                    "title": entry.get("title", "(untitled)"),
                    "summary": summary,
                    "url": entry.get("link", ""),
                    "created_at": ts.isoformat(),
                }
            )

    log.info("Collected %d RSS entries since %s", len(items), cutoff.isoformat())
    return items
