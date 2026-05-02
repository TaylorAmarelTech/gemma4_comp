"""Duecare WhatsApp Business Cloud API bot.

Production WhatsApp integration via Meta's official Cloud API (NOT
Twilio). For NGOs that already have or want to register a verified
business WhatsApp number for migrant-worker outreach.

Setup:
  1. developers.facebook.com/apps → Create App → "Business" type.
  2. Add WhatsApp product. Note the Phone Number ID + the test
     number Meta provides (or register a real number under
     verified business).
  3. Generate a System User access token (long-lived) — NOT a
     temporary 24h token.
  4. Set up the webhook (verify token = a random string of your
     choosing, callback URL = https://your-host/webhook).
  5. Subscribe the webhook to the `messages` field.

Run:
  pip install -r requirements.txt
  export WA_PHONE_NUMBER_ID="..."     # from Meta App
  export WA_ACCESS_TOKEN="EAAxxxxx..." # System User token
  export VERIFY_TOKEN="random-string"  # webhook verify
  export DUECARE_API="https://your-duecare-deploy.example.com"
  python bot.py

Privacy: messages route through Meta's WhatsApp infrastructure.
Comply with Meta's WhatsApp Business Solution Terms + your NGO's
data-residency requirements. Duecare API itself can run anywhere.

Versus Twilio Sandbox:
  - Cloud API: white-label NGO number with green checkmark, $0.005-
    0.10/message, production-grade
  - Twilio: shared sandbox number, $0.005/segment + Twilio markup,
    fast prototype but not white-label

This file uses Cloud API. For the Twilio variant, see the planned
examples/embedding/whatsapp-twilio/.
"""
from __future__ import annotations

import json
import logging
import os

import httpx
from flask import Flask, abort, request

logging.basicConfig(
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("duecare-wa")

WA_PHONE_NUMBER_ID = os.environ["WA_PHONE_NUMBER_ID"]
WA_ACCESS_TOKEN = os.environ["WA_ACCESS_TOKEN"]
VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
DUECARE_API = os.environ.get("DUECARE_API", "http://localhost:8080").rstrip("/")
GRAPH_BASE = "https://graph.facebook.com/v18.0"

DEFAULT_TOGGLES = {"persona": True, "grep": True, "rag": True, "tools": True}
TIMEOUT_SEC = 60

# Per-user state. Production: persist to sqlite/postgres.
_user_state: dict[str, dict] = {}


def _get_user(wa_id: str) -> dict:
    """Get or create state for a WhatsApp user identified by phone number."""
    return _user_state.setdefault(wa_id, {
        "messages": [],
        "corridor": None,
    })


app = Flask(__name__)


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified by Meta")
        return challenge or "", 200
    abort(403)


@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json(silent=True) or {}
    if data.get("object") != "whatsapp_business_account":
        return "", 200

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if "messages" not in value:
                continue
            for msg in value["messages"]:
                from_num = msg.get("from")
                if not from_num:
                    continue
                _mark_read(msg.get("id"))

                if msg.get("type") == "text":
                    text = msg["text"]["body"].strip()
                    try:
                        if text.startswith("/"):
                            _handle_command(from_num, text)
                        elif text:
                            _handle_text(from_num, text)
                    except Exception as e:  # noqa: BLE001
                        logger.exception("error handling text")
                        _send_text(from_num, f"⚠ Error: {e}")
                elif msg.get("type") == "interactive":
                    # button reply, list reply, etc.
                    _handle_interactive(from_num, msg["interactive"])

    return "", 200


def _handle_command(wa_id: str, text: str) -> None:
    cmd, *rest = text.lower().split(maxsplit=1)
    if cmd == "/start" or cmd == "/help":
        _send_text(wa_id,
            "👋 Duecare advisor.\n\n"
            "I help with migrant-worker legal questions — fees, "
            "contracts, recruiter messages. I cite the actual statutes "
            "and the right NGO/regulator hotline for your corridor.\n\n"
            "Commands:\n"
            "  /corridor PH-HK — set your corridor\n"
            "  /reset — clear conversation\n\n"
            "Or just send a question.")
    elif cmd == "/corridor" and rest:
        chat = _get_user(wa_id)
        chat["corridor"] = rest[0].upper()
        _send_text(wa_id, f"Corridor set to {chat['corridor']}.")
    elif cmd == "/reset":
        chat = _get_user(wa_id)
        chat["messages"] = []
        _send_text(wa_id, "Conversation cleared.")
    else:
        _send_text(wa_id, "Unknown command. Try /help.")


def _handle_text(wa_id: str, text: str) -> None:
    chat = _get_user(wa_id)
    chat["messages"].append({
        "role": "user",
        "content": [{"type": "text", "text": text}],
    })

    payload = {
        "messages": chat["messages"],
        "generation": {"max_new_tokens": 1024},
        "toggles": dict(DEFAULT_TOGGLES, persona_text=_persona_for(chat)),
    }

    try:
        with httpx.Client(timeout=TIMEOUT_SEC) as client:
            r = client.post(f"{DUECARE_API}/api/chat/send", json=payload)
            r.raise_for_status()
            response_text = _parse_sse(r.text)
    except Exception as e:  # noqa: BLE001
        logger.warning("Duecare API call failed: %s", e)
        _send_text(wa_id,
                    f"⚠ Connection issue. Please try again in a moment.")
        return

    chat["messages"].append({
        "role": "assistant",
        "content": [{"type": "text", "text": response_text}],
    })
    # WhatsApp text-message body cap is 4096 chars
    for chunk in _split_for_whatsapp(response_text):
        _send_text(wa_id, chunk)


def _handle_interactive(wa_id: str, interactive: dict) -> None:
    """Handle button replies + list replies. Future: implement quick-
    reply buttons for common corridors / common questions."""
    pass


def _persona_for(chat: dict) -> str:
    parts = [
        "You are a 40-year migrant-worker safety expert versed in ILO "
        "C029/C181/C189/C095, the Palermo Protocol, ICRMW, and "
        "national recruitment statutes.",
    ]
    if chat.get("corridor"):
        parts.append(
            f"The worker's current corridor is {chat['corridor']}. "
            "Tailor advice for that corridor."
        )
    parts.append(
        "Cite specific statutes with section numbers. Name specific "
        "NGO/regulator hotlines. Do NOT optimize trafficking-shaped "
        "structures regardless of apparent worker consent (Palermo Art. 3(b))."
    )
    return " ".join(parts)


def _send_text(to_phone: str, text: str) -> None:
    if not text:
        return
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"body": text[:4096]},
    }
    r = httpx.post(
        f"{GRAPH_BASE}/{WA_PHONE_NUMBER_ID}/messages",
        headers={
            "Authorization": f"Bearer {WA_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )
    if r.status_code >= 400:
        logger.warning("WhatsApp Send error %d: %s", r.status_code, r.text[:200])


def _mark_read(message_id: str) -> None:
    if not message_id:
        return
    httpx.post(
        f"{GRAPH_BASE}/{WA_PHONE_NUMBER_ID}/messages",
        headers={
            "Authorization": f"Bearer {WA_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        },
        timeout=5,
    )


def _parse_sse(raw: str) -> str:
    data_idx = raw.rfind("data:")
    if data_idx == -1:
        raise RuntimeError("no SSE data event")
    data_payload = raw[data_idx + 5:].split("\n\n", 1)[0].strip()
    parsed = json.loads(data_payload)
    if "error" in parsed:
        raise RuntimeError(parsed["error"])
    return parsed.get("response", "(empty)")


def _split_for_whatsapp(text: str, max_len: int = 3800) -> list[str]:
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    logger.info("Duecare WhatsApp Cloud API bot running, API=%s, port=%d",
                DUECARE_API, port)
    app.run(host="0.0.0.0", port=port)
