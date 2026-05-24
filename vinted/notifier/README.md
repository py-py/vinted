# Vinted notifier

Polls Vinted catalog/search URLs and pushes **new** items to Telegram.

Every run: for each active subscription it parses the catalog page, finds items
with `id > last_seen_id`, sends them to the subscription's Telegram chat (oldest
first), then advances `last_seen_id`. The **first** run for a subscription only
records the current high-water mark and sends nothing (so you don't get the whole
page at once).

## Configuration

Set in `.env` (see `.env.example`):

| Variable | Purpose |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID`   | Default chat for `subscribe` (per-subscription otherwise) |
| `NOTIFIER_STORE`     | `firestore` (default) or `json` (local file) |
| `GOOGLE_CLOUD_PROJECT` | GCP project (firestore backend) — `vinted-492007` |
| `FIRESTORE_DATABASE` | Firestore database id — `vinted-dev` |

Firestore access uses gcloud Application Default Credentials:

```bash
gcloud auth application-default login
```

## Commands

Add a subscription (chat id defaults to `TELEGRAM_CHAT_ID`):

```bash
uv run python -m vinted.notifier.subscribe "https://www.vinted.pl/catalog?search_text=&catalog[]=2652&order=newest_first"

# explicit chat id
uv run python -m vinted.notifier.subscribe "<url>" --chat 478132676
```

Run one polling pass (this is the Cloud Run Job command):

```bash
uv run python -m vinted.notifier
```

Use the local JSON store instead of Firestore (writes `notifier_state.json`):

```bash
NOTIFIER_STORE=json uv run python -m vinted.notifier
```

## Firestore data

Collection `subscriptions`, one doc per subscription. The document id is
`md5(url)` — deterministic, so re-subscribing the same URL is a no-op
(no duplicates, existing `last_seen_id` is kept).

| Field | Type | Notes |
| --- | --- | --- |
| `telegram_chat_id` | int | where to send |
| `url` | string | full catalog/search URL to poll |
| `last_seen_id` | int \| null | highest item id already sent; null = first run |
| `active` | bool | inactive subs are skipped |
| `created_at` | string | ISO timestamp |

## Scheduling (Cloud Run Job + Cloud Scheduler)

Planned: build into a Cloud Run Job running `python -m vinted.notifier`, with the
bot token in Secret Manager, triggered by Cloud Scheduler on `*/5 * * * *`.
