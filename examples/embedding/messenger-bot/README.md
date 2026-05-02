# Duecare Facebook Messenger bot

For NGOs that already have a Facebook Page (MfMW HK, Polaris BeFree,
IJM PH, BP2MI Indonesia, etc.). Lets workers DM the Page with
questions and get Duecare-grounded responses.

## Why Messenger

- **Existing audience.** NGO Pages already have followers — no
  install friction, no new app to learn.
- **Familiar UX.** Workers already DM Pages for help. Duecare-as-the-
  responder is invisible.
- **Verified Page.** The blue checkmark (when present) is the trust
  signal workers recognize, not a third-party app.
- **Reach.** Across PH/ID corridors, Facebook reach exceeds even
  WhatsApp.

## Setup (one-time, ~30 min)

### 1. Facebook Page

Use your existing NGO Page or create one at facebook.com/pages/create.

### 2. Meta App + Messenger product

1. Go to https://developers.facebook.com/apps → Create App
2. Type: "Other" → "Business"
3. Add the Messenger product
4. Connect your Page → generate a Page Access Token (NOT a User
   Access Token). Save it.

### 3. Webhook subscription

In Meta App → Messenger → Webhooks:

- Callback URL: `https://your-host/webhook` (must be HTTPS)
- Verify token: pick any random string, save it
- Subscribe to: `messages`, `messaging_postbacks`

### 4. Run the bot

```bash
pip install -r requirements.txt

export PAGE_ACCESS_TOKEN="EAAxxxxx..."     # from step 2
export VERIFY_TOKEN="random-string-from-step-3"
export DUECARE_API="https://your-duecare-deploy.example.com"

python bot.py                              # listens on 0.0.0.0:5000
```

For dev with ngrok:

```bash
ngrok http 5000
# Then put https://<ngrok-id>.ngrok.io/webhook in Meta App
```

For production: deploy on Render / Fly / Cloud Run / etc., point
the Meta webhook at the public HTTPS URL.

### 5. Try it

DM the connected Page. The bot replies via Send API.

## Commands

| Command | What |
|---|---|
| `/start` or `/help` | Welcome + command list |
| `/corridor PH-HK` | Set the worker's corridor |
| `/reset` | Clear conversation |

## Production checklist

- [ ] HTTPS endpoint (Meta requires it). Render / Fly / Cloud Run
      handle this automatically.
- [ ] App reviewed + Pages_messaging permission approved by Meta
      (otherwise only test users see the bot).
- [ ] Privacy policy URL set on the Meta App (required for App
      Review).
- [ ] Persist `_user_state` to a real DB (sqlite/postgres) — current
      example is in-memory.
- [ ] Rate limiting per PSID (worker abuse / runaway costs).
- [ ] Logging strips message contents — only structured event
      metadata (PSID, command, timestamp).
- [ ] HMAC verification of incoming webhook payloads against the
      Meta App Secret (current example trusts the verify token only).

## Limitations

- **24-hour messaging window.** Per Meta policy, you can only
  freely send messages within 24 hours of a user's last message.
  Outside that window requires a Message Tag (one of: confirmed
  event update, post-purchase update, account update, human agent).
  Worker conversations naturally fit "human agent" if a real NGO
  staffer is in the loop.
- **2000-char message cap.** The bot splits longer responses on
  paragraph boundaries.
- **Spam filtering.** Meta will throttle / block Pages that get
  reported. Make sure the welcome message clearly identifies the
  bot + the NGO.

## License

MIT.
