"""Duecare Facebook Messenger bot.

Wraps the Duecare REST API as a Messenger bot for an NGO Facebook
Page. Workers DM the Page → Meta sends a webhook to this server →
this server calls Duecare → reply via Meta's Send API.

Use case: NGO already has a Facebook Page (MfMW HK, Polaris BeFree,
IJM PH, BP2MI Indonesia). Workers find the Page, DM with questions
about recruiter messages or fees, and the Page responds with
Duecare-grounded advice.

Setup:
  1. Create a Facebook Page (or use existing).
  2. Create a Meta App at developers.facebook.com → add Messenger
     product → connect the Page → generate a Page Access Token.
  3. Set environment vars + run this server publicly accessible.
  4. In the Meta App → Messenger → Webhook, point at
     `https://your-host/webhook` with the verify token below.

Run:
  pip install -r requirements.txt
  export PAGE_ACCESS_TOKEN="EAAxxxxx..."   # Page-level, not user
  export VERIFY_TOKEN="random-string-you-choose"
  export DUECARE_API="https://your-duecare-deploy.example.com"
  python bot.py

  # Expose publicly via ngrok for testing:
  ngrok http 5000
  # Then point Meta webhook at https://<ngrok-id>.ngrok.io/webhook

Privacy: messages route through Meta's servers. Comply with the
Page's privacy policy + Meta's Platform Terms. The Duecare API
itself can run anywhere (self-hosted, cloud, etc.).
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
logger = logging.getLogger("duecare-messenger")

PAGE_ACCESS_TOKEN = os.environ["PAGE_ACCESS_TOKEN"]
VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
DUECARE_API = os.environ.get("DUECARE_API", "http://localhost:8080").rstrip("/")
GRAPH_BASE = "https://graph.facebook.com/v18.0"

DEFAULT_TOGGLES = {"persona": True, "grep": True, "rag": True, "tools": True}
TIMEOUT_SEC = 60

# Per-user state. Production: persist to sqlite/postgres.
_user_state: dict[str, dict] = {}


def _get_user(psid: str) -> dict:
    """Get or create state for a Page-Scoped ID (PSID)."""
    return _user_state.setdefault(psid, {
        "messages": [],
        "corridor": None,
    })


app = Flask(__name__)


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta calls GET to verify the webhook subscription. We echo
    back the challenge if the verify token matches."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified by Meta")
        return challenge or "", 200
    abort(403)


@app.route("/webhook", methods=["POST"])
def receive_message():
    """Meta calls POST when a user DMs the Page. Process each
    incoming message + reply via Send API."""
    data = request.get_json(silent=True) or {}
    if data.get("object") != "page":
        return "", 200

    for entry in data.get("entry", []):
        for messaging in entry.get("messaging", []):
            sender_id = messaging.get("sender", {}).get("id")
            if not sender_id:
                continue

            # Mark seen + show typing indicator
            _send_action(sender_id, "mark_seen")
            _send_action(sender_id, "typing_on")

            text = messaging.get("message", {}).get("text", "").strip()
            postback = messaging.get("postback", {}).get("payload", "")

            try:
                if postback:
                    _handle_postback(sender_id, postback)
                elif text.startswith("/"):
                    _handle_command(sender_id, text)
                elif text:
                    _handle_text(sender_id, text)
            except Exception as e:  # noqa: BLE001
                logger.exception("error handling message")
                _send_text(sender_id, f"⚠ Error: {e}")
            finally:
                _send_action(sender_id, "typing_off")

    return "", 200


def _handle_command(sender_id: str, text: str) -> None:
    cmd, *rest = text.lower().split(maxsplit=1)
    if cmd == "/start" or cmd == "/help":
        _send_text(sender_id,
            "👋 Duecare advisor.\n\n"
            "I help with migrant-worker legal questions — fees, "
            "contracts, recruiter messages. I cite the actual statutes "
            "and the right NGO/regulator hotline for your corridor.\n\n"
            "Commands:\n"
            "  /corridor PH-HK — set your corridor\n"
            "  /reset — clear conversation\n\n"
            "Or just send a question.")
    elif cmd == "/corridor" and rest:
        chat = _get_user(sender_id)
        chat["corridor"] = rest[0].upper()
        _send_text(sender_id, f"Corridor set to {chat['corridor']}.")
    elif cmd == "/reset":
        chat = _get_user(sender_id)
        chat["messages"] = []
        _send_text(sender_id, "Conversation cleared.")
    else:
        _send_text(sender_id, "Unknown command. Try /help.")


def _handle_text(sender_id: str, text: str) -> None:
    chat = _get_user(sender_id)
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
        _send_text(sender_id,
                    f"⚠ Connection issue. Please try again in a moment.\n({e})")
        return

    chat["messages"].append({
        "role": "assistant",
        "content": [{"type": "text", "text": response_text}],
    })
    # Messenger has a 2000 char limit per message
    for chunk in _split_for_messenger(response_text):
        _send_text(sender_id, chunk)


def _handle_postback(sender_id: str, payload: str) -> None:
    """Handle button taps (Get Started, quick replies, etc.)."""
    if payload == "GET_STARTED":
        _handle_command(sender_id, "/start")


def _persona_for(chat: dict) -> str:
    parts = [
        "You are a 40-year migrant-worker safety expert versed in ILO "
        "C029/C181/C189/C095, the Palermo Protocol, ICRMW, and "
        "national recruitment statutes.",
    ]
    if chat.get("corridor"):
        parts.append(
            f"The worker's current corridor is {chat['corridor']}. "
            "Tailor advice (fee caps + NGO hotlines) for that corridor."
        )
    parts.append(
        "Cite specific statutes with section numbers. Name specific "
        "NGO/regulator hotlines. Do NOT optimize trafficking-shaped "
        "structures regardless of apparent worker consent (Palermo Art. 3(b))."
    )
    return " ".join(parts)


def _send_text(recipient_psid: str, text: str) -> None:
    """Send a text message via Meta Send API."""
    if not text:
        return
    payload = {
        "recipient": {"id": recipient_psid},
        "messaging_type": "RESPONSE",
        "message": {"text": text[:2000]},   # 2000 char hard limit
    }
    r = httpx.post(
        f"{GRAPH_BASE}/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json=payload,
        timeout=10,
    )
    if r.status_code >= 400:
        logger.warning("Send API error %d: %s", r.status_code, r.text[:200])


def _send_action(recipient_psid: str, action: str) -> None:
    """Send a sender_action: typing_on / typing_off / mark_seen."""
    httpx.post(
        f"{GRAPH_BASE}/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json={"recipient": {"id": recipient_psid}, "sender_action": action},
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


def _split_for_messenger(text: str, max_len: int = 1900) -> list[str]:
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
    logger.info("Duecare Messenger bot running, API=%s, port=%d",
                DUECARE_API, port)
    app.run(host="0.0.0.0", port=port)
