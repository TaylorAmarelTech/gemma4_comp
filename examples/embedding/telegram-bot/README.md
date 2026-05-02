# Duecare Telegram bot

Wraps the Duecare REST API as a Telegram bot. OFWs use Telegram
heavily across the PH→HK and ID→HK corridors — this is the highest-
leverage messaging integration.

## Setup

### 1. Create a bot

DM `@BotFather` on Telegram: `/newbot`, follow prompts, save the
token he gives you.

### 2. Deploy a Duecare REST API

Pick any path from
[`docs/cloud_deployment.md`](../../../docs/cloud_deployment.md).
Cheapest: Render Starter ($7/mo) or Fly.io shared-cpu ($5/mo).

### 3. Run the bot

```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN="123456:ABC-DEF..."
export DUECARE_API="https://your-duecare-deploy.example.com"
python bot.py
```

Or via Docker:

```bash
docker run --rm -it \
    -e TELEGRAM_TOKEN=... \
    -e DUECARE_API=... \
    -v $(pwd):/app -w /app \
    python:3.12-slim bash -c "pip install -r requirements.txt && python bot.py"
```

### 4. Try it

Find your bot by username on Telegram, send `/start`. Then ask a
question — the bot calls Duecare and replies.

## Commands

| Command | What |
|---|---|
| `/start` | Welcome message |
| `/corridor PH-HK` | Set corridor for better advice |
| `/reset` | Clear conversation history |
| `/help` | List commands |
| (any text) | Sent to Duecare as a chat message |

## Production notes

- **Persistence:** the example uses in-memory state (`_chat_state`
  dict). For production, persist to SQLite / Postgres + restore on
  restart.
- **Rate limiting:** add per-user limits via `python-telegram-bot`'s
  built-in throttling middleware.
- **Privacy:** the bot logs structured events but NOT message
  contents. Make sure `DUECARE_API` runs in a region appropriate to
  the worker's data-residency expectations.
- **Long responses:** Telegram caps messages at 4096 chars. The bot
  splits on paragraph boundaries; long Gemma responses become
  multiple Telegram messages.
- **Hosting:** the bot itself uses ~50 MB RAM, fits anywhere — Fly
  free tier, Railway, even a Raspberry Pi at home. The Duecare API
  is the heavy bit.

## License

MIT.
