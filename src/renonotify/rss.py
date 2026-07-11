"""Collect recent entries from a list of RSS/Atom feeds."""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

log = logging.getLogger(__name__)


def feeds_from_opml(sources: str | list[str] | None) -> list[str]:
    """Extract feed URLs from OPML subscription lists.

    `sources` is a single OPML location or a list of them; each may be a
    local file path or an http(s) URL. Unreadable sources are logged and
    skipped rather than failing the run.
    """
    if not sources:
        return []
    if isinstance(sources, str):
        sources = [sources]

    urls: list[str] = []
    for source in sources:
        try:
            if source.startswith(("http://", "https://")):
                resp = requests.get(source, timeout=30)
                resp.raise_for_status()
                text = resp.text
            else:
                text = Path(source).read_text()
            root = ET.fromstring(text)
        except Exception:
            log.exception("Failed to load OPML, skipping: %s", source)
            continue

        # iter() walks nested outlines, so folder hierarchies work too
        found = [
            o.attrib["xmlUrl"]
            for o in root.iter("outline")
            if o.attrib.get("xmlUrl")
        ]
        if found:
            log.info("Loaded %d feeds from OPML: %s", len(found), source)
        else:
            log.warning("No feeds found in OPML: %s", source)
        urls += found
    return urls


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
