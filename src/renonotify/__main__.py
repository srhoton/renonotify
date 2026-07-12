"""renonotify CLI: collect → summarize → deliver."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from . import bluesky, rss, slack, summarize

log = logging.getLogger("renonotify")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="renonotify",
        description="Summarize Bluesky + RSS feeds and post the digest to Slack.",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=None,
        help="Lookback window in hours (default: from config)",
    )
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the digest instead of posting to Slack",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        cfg = yaml.safe_load(args.config.read_text()) or {}
    except FileNotFoundError:
        log.error("Config file not found: %s", args.config)
        return 1
    hours = args.hours if args.hours is not None else cfg.get("default_hours", 12)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    items: list[dict] = []

    bsky_cfg = cfg.get("bluesky", {})
    if bsky_cfg.get("enabled", True):
        handle = os.environ.get("BLUESKY_HANDLE") or bsky_cfg.get("handle") or ""
        app_password = os.environ.get("BLUESKY_APP_PASSWORD", "")
        if handle and app_password:
            try:
                items += bluesky.collect_posts(
                    handle,
                    app_password,
                    cutoff,
                    max_posts=bsky_cfg.get("max_posts", 300),
                )
            except Exception:
                log.exception("Bluesky collection failed; continuing without it")
        else:
            log.warning("Bluesky enabled but handle/app password missing; skipping")

    rss_cfg = cfg.get("rss", {})
    if rss_cfg.get("enabled", True):
        feeds = list(rss_cfg.get("feeds") or [])
        feeds += rss.feeds_from_opml(rss_cfg.get("opml"))
        feeds = list(dict.fromkeys(feeds))  # dedupe, keep order
        items += rss.collect_entries(feeds, cutoff)

    sum_cfg = cfg.get("summary", {})
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.error("ANTHROPIC_API_KEY is not set")
        return 1

    digest = summarize.summarize(
        items,
        hours=hours,
        instructions=sum_cfg.get("instructions", ""),
        model=sum_cfg.get("model", "claude-haiku-4-5"),
        max_tokens=sum_cfg.get("max_tokens", 1500),
        api_key=api_key,
    )

    header = f"Feed digest — last {hours:g}h ({len(items)} items)"

    if args.dry_run:
        print(f"=== {header} ===\n{digest}")
        return 0

    webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook:
        log.error("SLACK_WEBHOOK_URL is not set")
        return 1

    slack.post_digest(webhook, header, digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
