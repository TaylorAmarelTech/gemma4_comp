# DueCare Telegram bot

Migrant workers in Gulf + Southeast Asia corridors use Telegram. This
bot lets them forward a suspicious recruiter message and get back a
structured grade + local hotline in English or Tagalog. Nothing leaves
the DueCare server it talks to.

## Setup

```bash
# 1. Start a DueCare server (any of these):
docker compose up                                   # full stack
# or: uvicorn src.demo.app:app --port 8080         # demo-only

# 2. Get a bot token from @BotFather on Telegram.
export TELEGRAM_BOT_TOKEN=1234567890:ABC-DEF...

# 3. Point the bot at your DueCare endpoint
export DUECARE_ENDPOINT=http://localhost:8080        # or HF Space URL

# 4. Run
pip install -r deployment/telegram_bot/requirements.txt
python deployment/telegram_bot/bot.py
```

Open Telegram, search your bot's username, send `/start`. Forward
messages to it.

## Commands

| Command | What it does |
|---|---|
| `/start` | Welcome message (EN or TL) |
| `/help` | Usage reminder |
| `/lang en` / `/lang tl` | Switch preferred language |
| `/analyze <text>` | Explicit analysis |
| *(any text)* | Analyzed as a chat message |

## Deployment

**Simplest:** run it on any VPS / Raspberry Pi. Bot polls Telegram, so
no inbound ports.

**Zero-cost option:**
```bash
# Deploy the bot as a Hugging Face Space (CPU basic — free)
# Uses the same DUECARE_ENDPOINT as the demo Space.
```
