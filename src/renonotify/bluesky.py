"""Collect posts from the authenticated user's Bluesky timeline."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from atproto import Client

log = logging.getLogger(__name__)


def _parse_ts(ts: str) -> datetime:
    # Bluesky timestamps are ISO 8601, e.g. "2026-07-11T14:03:22.123Z"
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:  # keep comparisons against the aware cutoff safe
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def collect_posts(
    handle: str,
    app_password: str,
    cutoff: datetime,
    max_posts: int = 300,
) -> list[dict]:
    """Return timeline posts newer than `cutoff` as simple dicts.

    Paginates backwards through the timeline until posts are older than
    the cutoff or max_posts is reached.
    """
    client = Client()
    client.login(handle, app_password)

    items: list[dict] = []
    cursor: str | None = None

    while len(items) < max_posts:
        resp = client.get_timeline(cursor=cursor, limit=100)
        if not resp.feed:
            break

        page_exhausted = False
        for feed_item in resp.feed:
            post = feed_item.post
            created = _parse_ts(post.record.created_at)
            if created < cutoff:
                # Timeline is roughly reverse-chronological; reposts can be
                # slightly out of order, so don't bail on the first old post —
                # but if the whole page trend is old, stop.
                continue

            author = post.author.handle
            text = getattr(post.record, "text", "") or ""
            uri_parts = post.uri.split("/")
            url = f"https://bsky.app/profile/{author}/post/{uri_parts[-1]}"

            entry = {
                "source": "bluesky",
                "author": author,
                "display_name": post.author.display_name or author,
                "text": text,
                "created_at": created.isoformat(),
                "url": url,
                "likes": post.like_count or 0,
                "reposts": post.repost_count or 0,
            }
            if getattr(feed_item, "reason", None):
                entry["repost"] = True
            items.append(entry)
            if len(items) >= max_posts:
                break

        # Stop paginating once the last post on the page is past the cutoff
        last_created = _parse_ts(resp.feed[-1].post.record.created_at)
        if last_created < cutoff:
            page_exhausted = True

        cursor = resp.cursor
        if page_exhausted or not cursor:
            break

    log.info("Collected %d Bluesky posts since %s", len(items), cutoff.isoformat())
    return items
