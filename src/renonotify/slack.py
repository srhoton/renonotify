"""Deliver the digest to Slack via an incoming webhook."""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

# Slack section blocks cap at 3000 chars of text; stay under it
_CHUNK = 2900


def _chunks(text: str) -> list[str]:
    if len(text) <= _CHUNK:
        return [text]
    parts: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        while len(line) > _CHUNK:  # hard-split a single oversized line
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:_CHUNK])
            line = line[_CHUNK:]
        if len(current) + len(line) > _CHUNK:
            parts.append(current)
            current = ""
        current += line
    if current:
        parts.append(current)
    # Slack rejects section blocks with empty/whitespace-only text
    return [p for p in parts if p.strip()]


def post_digest(webhook_url: str, header: str, digest: str) -> None:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header, "emoji": True},
        }
    ]
    for part in _chunks(digest):
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": part}}
        )

    resp = requests.post(webhook_url, json={"blocks": blocks}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Slack webhook failed: {resp.status_code} {resp.text[:200]}"
        )
    log.info("Posted digest to Slack (%d blocks)", len(blocks))
