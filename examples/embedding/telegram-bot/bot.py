"""Duecare Telegram bot — wraps the Duecare REST API for Telegram.

OFWs use Telegram heavily across the PH→HK and ID→HK corridors. This
bot lets a worker chat with the safety harness via DM:

  - Worker DMs the bot a question (or forwards a recruiter message).
  - Bot calls Duecare /api/chat/send with all harness layers ON.
  - Bot replies with Gemma's response, formatted for Telegram.

Usage:
    pip install -r requirements.txt
    export TELEGRAM_TOKEN=bot_token_from_@BotFather
    export DUECARE_API=https://your-duecare-deploy.example.com
    python bot.py

Per-chat customization: each chat (user or group) gets its own
persona + corridor selection via /persona and /corridor commands.
Stored in-memory; production deploys would persist to a small
SQLite db.

Privacy: the bot does NOT log message contents. The bot only sees
text the worker sends; Duecare itself runs anywhere you've deployed
the REST API.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

import httpx
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("duecare-tg")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
DUECARE_API = os.environ.get("DUECARE_API", "http://localhost:8080").rstrip("/")
DEFAULT_TOGGLES = {"persona": True, "grep": True, "rag": True, "tools": True}
TIMEOUT_SEC = 120

# Per-chat state. Production: persist to sqlite/postgres.
_chat_state: dict[int, dict] = {}


def _get_chat(chat_id: int) -> dict:
    return _chat_state.setdefault(chat_id, {
        "messages": [],
        "corridor": None,
        "stage": None,
        "persona_text": None,
    })


WELCOME = """\
👋 *Duecare advisor*

I help migrant workers with legal advice grounded in the actual
statutes and the right NGO/regulator hotlines for your corridor.

I won't tell you what to do — you decide. I will tell you what the
law says, and document anything you ask me to.

*Quick start:*
  • Just send me a question or paste a recruiter message
  • /corridor PH-HK — set your corridor (better advice)
  • /reset — clear the conversation

I'm built on Gemma 4 + the Duecare safety harness. All advice is
informational, not legal counsel.
"""


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown(WELCOME)


async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat = _get_chat(update.effective_chat.id)
    chat["messages"] = []
    await update.message.reply_text("Conversation cleared.")


async def cmd_corridor(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat = _get_chat(update.effective_chat.id)
    if not ctx.args:
        await update.message.reply_text(
            "Usage: /corridor PH-HK\n\n"
            "Common: PH-HK, PH-SA, ID-HK, ID-SA, NP-QA, NP-MY, BD-SA, BD-QA"
        )
        return
    chat["corridor"] = ctx.args[0].upper()
    await update.message.reply_text(f"Corridor set to {chat['corridor']}.")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/start - welcome\n"
        "/corridor PH-HK - set your corridor for better advice\n"
        "/reset - clear conversation\n"
        "/help - this message\n\n"
        "Or just send a question / paste a recruiter message."
    )


def _system_prompt(chat: dict) -> str:
    parts = [
        "You are a 40-year migrant-worker safety expert versed in ILO "
        "C029/C181/C189/C095, the Palermo Protocol, ICRMW, and "
        "national recruitment statutes.",
    ]
    if chat.get("corridor"):
        parts.append(
            f"The worker's current corridor is {chat['corridor']}. "
            "Tailor advice (especially fee caps + NGO hotlines) "
            "specifically for that corridor."
        )
    parts.append(
        "Cite specific statutes with section numbers + ILO Convention "
        "numbers. If the worker may have a complaint to file, name "
        "the specific NGO/regulator + their hotline. Do NOT optimize "
        "any structure that contains trafficking indicators, "
        "regardless of the worker's apparent consent (Palermo Art. 3(b))."
    )
    return " ".join(parts)


async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat = _get_chat(update.effective_chat.id)
    text = (update.message.text or "").strip()
    if not text:
        return

    # Show typing indicator
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Append user message to history (Duecare expects message list)
    chat["messages"].append({
        "role": "user",
        "content": [{"type": "text", "text": text}],
    })

    payload = {
        "messages": chat["messages"],
        "generation": {"max_new_tokens": 1024},
        "toggles": dict(DEFAULT_TOGGLES, persona_text=_system_prompt(chat)),
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
            r = await client.post(f"{DUECARE_API}/api/chat/send", json=payload)
            r.raise_for_status()
            # Parse SSE — same shape as the chat playground client
            response_text = await _parse_sse(r)
    except httpx.HTTPError as e:
        logger.warning("Duecare API call failed: %s", e)
        await update.message.reply_text(
            f"⚠ Connection error to Duecare API at {DUECARE_API}\n{e}"
        )
        return
    except Exception as e:  # noqa: BLE001
        logger.exception("Unexpected error")
        await update.message.reply_text(f"⚠ Unexpected error: {e}")
        return

    chat["messages"].append({
        "role": "assistant",
        "content": [{"type": "text", "text": response_text}],
    })

    # Telegram has a 4096 char limit per message; split if needed.
    for chunk in _split_for_telegram(response_text):
        await update.message.reply_text(chunk)


async def _parse_sse(r: httpx.Response) -> str:
    """The Duecare /api/chat/send endpoint returns SSE: keepalive
    `:` comments while generating, then one final `data: {...}` event
    with the full response. Extract the final response text."""
    buffer = ""
    async for chunk in r.aiter_text():
        buffer += chunk
    # Find the last data: event
    data_idx = buffer.rfind("data:")
    if data_idx == -1:
        raise RuntimeError("SSE stream contained no data event")
    data_payload = buffer[data_idx + 5:].split("\n\n", 1)[0].strip()
    parsed = json.loads(data_payload)
    if "error" in parsed:
        raise RuntimeError(parsed["error"])
    return parsed.get("response", "(empty response)")


def _split_for_telegram(text: str, max_len: int = 3500) -> list[str]:
    """Split a long response on paragraph boundaries to fit Telegram's
    4096-char per-message limit."""
    if len(text) <= max_len:
        return [text]
    out: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) + 2 > max_len:
            if current:
                out.append(current.rstrip())
            current = paragraph
        else:
            current = (current + "\n\n" + paragraph).strip() if current else paragraph
    if current:
        out.append(current.rstrip())
    return out


def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("corridor", cmd_corridor))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Duecare Telegram bot running, API=%s", DUECARE_API)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
