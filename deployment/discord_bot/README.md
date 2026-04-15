# DueCare Discord bot

For NGO Discord servers, university research groups, and community
moderation teams. Two interaction surfaces:

1. **Slash command** `/analyze text: <message>` — shows the full
   grade + indicators + hotline embed.
2. **Context menu** right-click any message → **Apps** → "Analyze with
   DueCare" — analyzes that message, ephemeral (only you see it).

## Setup

```bash
# 1. Create an application + bot at
#    https://discord.com/developers/applications
#    Bot tab: reset token, enable MESSAGE CONTENT INTENT.
# 2. OAuth2 tab: generate invite URL with scopes
#    bot + applications.commands and permission "Send Messages".

export DISCORD_BOT_TOKEN=MT...

# 3. Point at a DueCare endpoint
export DUECARE_ENDPOINT=http://localhost:8080        # or HF Space URL

# 4. Run
pip install -r deployment/discord_bot/requirements.txt
python deployment/discord_bot/bot.py
```

Invite the bot to your server using the OAuth2 URL; slash commands
sync automatically on first connect.

## Privacy

Messages analyzed via the bot are sent only to the configured
`DUECARE_ENDPOINT`. For full on-device privacy, run the endpoint on
localhost / an internal host.
