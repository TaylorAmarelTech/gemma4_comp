# Duecare WhatsApp Business Cloud API bot

Production WhatsApp integration via Meta's official Cloud API. For
NGOs that want a verified business WhatsApp number for migrant-
worker outreach.

## Why Cloud API vs Twilio Sandbox

| | Cloud API (this) | Twilio Sandbox |
|---|---|---|
| Number | NGO's own verified business number | Twilio shared `+1 415 523 8886` |
| Branding | NGO name + green checkmark | Twilio sandbox |
| Setup | ~30 min (Meta App + verification) | ~5 min |
| Cost | $0.005-0.10/msg (per country/category) | Twilio per-segment fees |
| Production-ready | yes | no (sandbox only) |
| When | NGO pilot graduating to real deploy | Earliest prototype |

## Setup

### 1. Meta App + WhatsApp product

1. https://developers.facebook.com/apps → Create App → "Business"
2. Add the WhatsApp product
3. Note the **Phone Number ID** (in the WhatsApp → Getting Started panel)
4. Either use Meta's test number (free, 5 numbers cap) OR register
   your real NGO number (requires Meta business verification)

### 2. Long-lived access token

The token Meta gives you in the Getting Started panel expires in
24 hours. For production you need a System User token:

1. business.facebook.com → Business Settings → Users → System Users
2. Add a System User → assign to the WhatsApp Business Account
3. Generate token with `whatsapp_business_messaging` +
   `whatsapp_business_management` permissions, set "Never" expiry

### 3. Webhook subscription

In Meta App → WhatsApp → Configuration → Webhook:

- Callback URL: `https://your-host/webhook`
- Verify token: pick any string, save it
- Subscribe to: `messages`

### 4. Run the bot

```bash
pip install -r requirements.txt

export WA_PHONE_NUMBER_ID="123456789012345"
export WA_ACCESS_TOKEN="EAAxxxxx..."          # the long-lived System User token
export VERIFY_TOKEN="random-string-from-step-3"
export DUECARE_API="https://your-duecare-deploy.example.com"

python bot.py                                 # listens on 0.0.0.0:5000
```

For dev with ngrok:

```bash
ngrok http 5000
# Then put https://<ngrok-id>.ngrok.io/webhook in the Meta webhook config
```

For production: deploy on Render / Fly / Cloud Run / etc., put the
public HTTPS URL in the webhook config.

### 5. Try it

WhatsApp the connected number (or its test variant) — bot replies.

## Commands

| Command | What |
|---|---|
| `/start` or `/help` | Welcome + command list |
| `/corridor PH-HK` | Set worker's corridor |
| `/reset` | Clear conversation |

## Production checklist

- [ ] Verified business number (not just the test number)
- [ ] System User access token (NOT 24h temporary)
- [ ] HTTPS endpoint
- [ ] HMAC verify webhook payloads against the App Secret
- [ ] Persist `_user_state` to a real DB
- [ ] Per-WA-ID rate limiting
- [ ] Privacy: log structured events but NOT message text
- [ ] Message templates approved by Meta if you want to message
      users outside the 24-hour window (proactive outreach)

## 24-hour messaging window (important)

Per Meta policy, you can only freely send freeform text within
24 hours of the user's last message. Outside that window:
- For reactive customer support during the worker's active session,
  you're fine
- For proactive outreach (e.g., "your refund claim was approved"),
  use Meta-approved Message Templates

The bot example above is purely reactive — only responds to
incoming messages. Safe by default.

## Cost estimate

- Test number: free, 5 numbers cap, 250 service conversations/24hrs
- Verified number: $0.005-0.10 per conversation depending on country
  + category (utility / authentication / marketing / service)
- For a 100-OFW-user pilot at MfMW HK: ~$5-30/month

## License

MIT.
