# renonotify

Summarizes your Bluesky timeline and a set of RSS feeds over the last N hours,
uses Claude to write a digest, and posts it to Slack via an incoming webhook.
Runs on a GitHub Actions schedule, or on demand.

## Setup

### 1. Slack incoming webhook

1. Go to https://api.slack.com/apps → **Create New App** → From scratch
2. Enable **Incoming Webhooks**, then **Add New Webhook to Workspace** and pick a channel
3. Copy the webhook URL (looks like `https://hooks.slack.com/services/T.../B.../...`)

### 2. Bluesky app password

Bluesky → Settings → Privacy and Security → **App Passwords** → create one.
Don't use your real account password.

### 3. GitHub Actions secrets

Repo → Settings → Secrets and variables → Actions. Add:

| Secret | Value |
| --- | --- |
| `BLUESKY_HANDLE` | e.g. `you.bsky.social` |
| `BLUESKY_APP_PASSWORD` | the app password from step 2 |
| `ANTHROPIC_API_KEY` | from https://console.anthropic.com |
| `SLACK_WEBHOOK_URL` | from step 1 |

### 4. Configure feeds

Edit `config.yaml` — add your RSS feed URLs, tweak the digest instructions,
and adjust the default lookback window.

Instead of (or in addition to) listing feeds one by one, you can point
`rss.opml` at OPML subscription lists — local files or URLs, e.g. an export
from your feed reader. Feeds from OPML are merged with the `feeds` list and
deduplicated:

```yaml
rss:
  opml:
    - subscriptions.opml
    - https://example.com/subscriptions.opml
```

## Running

**On a schedule:** the workflow in `.github/workflows/notify.yml` runs daily at
12:00 UTC. Edit the cron line to taste.

**On demand:** Actions tab → *Feed digest* → **Run workflow** (set the hours),
or from a terminal:

```bash
gh workflow run "Feed digest" -f hours=6
```

**Locally:**

```bash
pip install -e .
export BLUESKY_HANDLE=you.bsky.social
export BLUESKY_APP_PASSWORD=...
export ANTHROPIC_API_KEY=...
renonotify --hours 12 --dry-run   # prints instead of posting
```

## Notes

- GitHub cron schedules can fire 5–15 minutes late during busy periods.
- Bluesky collection caps at `max_posts` (default 300) per run as a safety limit.
- If Bluesky auth fails, the run continues with RSS only rather than failing outright.
