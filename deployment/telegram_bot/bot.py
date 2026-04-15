"""DueCare Telegram bot — analyze forwarded messages for trafficking risk.

Setup:
    1. Talk to @BotFather, /newbot, get your TELEGRAM_BOT_TOKEN.
    2. export TELEGRAM_BOT_TOKEN=...
    3. export DUECARE_ENDPOINT=http://localhost:8080  # or HF Spaces URL
    4. python bot.py

Commands:
    /start           — onboarding message in EN/TL
    /help            — usage
    /lang <en|tl>    — set preferred language
    /analyze <text>  — explicit analysis of text
    <any text>       — forwards message content to DueCare for analysis

Privacy: messages are sent to the configured DueCare endpoint only. Run
the endpoint on localhost (no internet required) for full privacy.
"""

from __future__ import annotations

import logging
import os

import httpx
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("duecare-telegram")

DUECARE_ENDPOINT = os.environ.get("DUECARE_ENDPOINT", "http://localhost:8080")
DEFAULT_LANGUAGE = "en"

GREETING_EN = (
    "Hello. I am DueCare.\n\n"
    "Forward me any suspicious recruiter message, job advert, contract "
    "clause, or chat conversation. I will tell you whether it looks "
    "exploitative, which ILO conventions it may violate, and whom you "
    "can call for help.\n\n"
    "Privacy is non-negotiable. Nothing you send leaves the server you "
    "are talking to."
)
GREETING_TL = (
    "Hello po. Ako si DueCare.\n\n"
    "I-forward mo sa akin ang anumang kahina-hinalang recruiter message, "
    "job advert, contract, o usapan. Sasabihin ko sa iyo kung mukhang "
    "exploitative ito, aling ILO conventions ang baka nilalabag, at "
    "kanino ka pwedeng humingi ng tulong.\n\n"
    "Hindi ibibigay ang iyong mensahe sa third party."
)


def _lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.user_data.get("lang", DEFAULT_LANGUAGE)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(ctx)
    msg = GREETING_TL if lang == "tl" else GREETING_EN
    await update.message.reply_text(msg)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Commands:\n"
        "/start — welcome\n"
        "/lang en|tl — preferred language\n"
        "/analyze <text> — analyze text\n"
        "\nOr just forward any message and I will analyze it."
    )


async def cmd_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    choice = (ctx.args[0].lower() if ctx.args else "").strip()
    if choice not in ("en", "tl"):
        await update.message.reply_text("Usage: /lang en  OR  /lang tl")
        return
    ctx.user_data["lang"] = choice
    await update.message.reply_text(
        "Language set to English." if choice == "en" else "Naitakda sa Tagalog."
    )


async def _analyze_text(text: str, lang: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{DUECARE_ENDPOINT}/api/v1/analyze",
            json={"text": text, "context": "chat", "language": lang},
        )
        r.raise_for_status()
        return r.json()


def _format_result(data: dict, lang: str) -> str:
    grade = data.get("grade", "neutral")
    action = data.get("action", "review").upper()
    score = int((data.get("score") or 0) * 100)
    emoji = {"worst": "🚨", "bad": "⚠️", "neutral": "🟡", "good": "🟢", "best": "✅"}.get(grade, "🟡")

    lines = [
        f"{emoji} *{grade.upper()}* — action: *{action}* ({score}%)",
        "",
    ]

    if data.get("warning_text"):
        lines.extend([data["warning_text"], ""])

    indicators = data.get("indicators") or []
    if indicators:
        lines.append("*Indicators detected:*")
        for i in indicators[:6]:
            lines.append(f"• {i.replace('_', ' ')}")
        lines.append("")

    legal = data.get("legal_refs") or []
    if legal:
        lines.append("*Applicable laws:*")
        for r in legal[:4]:
            lines.append(f"• {r}")
        lines.append("")

    resources = data.get("resources") or []
    if resources:
        lines.append("*Help:*")
        for r in resources[:4]:
            name = r.get("name", "")
            num = r.get("number") or ""
            url = r.get("url") or ""
            bits = [f"• *{name}*"]
            if num:
                bits.append(f"📞 `{num}`")
            if url:
                bits.append(url)
            lines.append(" — ".join(bits))

    footer = (
        "_Privacy is non-negotiable. Your message was analyzed on-device._"
        if lang == "en"
        else
        "_Hindi ibinabahagi ang mensahe mo sa third party._"
    )
    lines.extend(["", footer])
    return "\n".join(lines)


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message.text
    if not msg:
        return
    lang = _lang(ctx)
    log.info("analyze: lang=%s chars=%d", lang, len(msg))
    try:
        result = await _analyze_text(msg, lang)
    except Exception as e:
        await update.message.reply_text(
            f"Sorry — could not reach DueCare server at {DUECARE_ENDPOINT}.\n"
            f"Error: {type(e).__name__}"
        )
        return
    await update.message.reply_text(
        _format_result(result, lang), parse_mode=ParseMode.MARKDOWN
    )


async def cmd_analyze(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(ctx.args or []).strip()
    if not text:
        await update.message.reply_text("Usage: /analyze <text>")
        return
    fake_update = Update(
        update_id=update.update_id,
        message=update.message.reply_text_with_text if False else update.message,
    )
    update.message.text = text  # reuse on_text flow
    await on_text(update, ctx)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("set TELEGRAM_BOT_TOKEN environment variable")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("DueCare Telegram bot starting — endpoint: %s", DUECARE_ENDPOINT)
    app.run_polling()


if __name__ == "__main__":
    main()
