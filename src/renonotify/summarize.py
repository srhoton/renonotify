"""Summarize collected items with the Claude API."""

from __future__ import annotations

import json
import logging

import anthropic

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a personal feed digest assistant. You receive a JSON
list of Bluesky posts and RSS entries collected over a time window, and you
produce a concise digest formatted with Slack mrkdwn.

Slack mrkdwn rules (these differ from standard Markdown):
- Bold is *single asterisks*, italic is _underscores_
- Links are <https://example.com|link text>
- Use short sections with a bold header line, then a few bullet lines ("• ")
- No tables, no headings with #

Keep the whole digest comfortably under 2800 characters."""


def summarize(
    items: list[dict],
    hours: float,
    instructions: str,
    model: str,
    max_tokens: int,
    api_key: str,
) -> str:
    if not items:
        return f"Nothing new in the last {hours:g} hours. :zzz:"

    client = anthropic.Anthropic(api_key=api_key)

    user_content = (
        f"Time window: last {hours:g} hours. "
        f"{len(items)} items collected.\n"
        f"Additional instructions: {instructions}\n\n"
        f"Items:\n{json.dumps(items, ensure_ascii=False)}"
    )

    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    log.info("Summary generated (%d chars)", len(text))
    return text.strip()
