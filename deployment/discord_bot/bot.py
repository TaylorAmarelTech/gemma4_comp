"""DueCare Discord bot — slash-command analyzer for anti-trafficking NGOs.

Two surfaces:
1. Slash command `/analyze text: <message>` — public response.
2. Right-click a message → Apps → "Analyze with DueCare" — ephemeral response.

Setup:
    1. Create a Discord application at https://discord.com/developers/applications
    2. Bot > Reset Token > copy. Grant intents: MESSAGE_CONTENT, GUILDS.
    3. OAuth2 URL Generator: bot + applications.commands; scope invite.
    4. export DISCORD_BOT_TOKEN=...
    5. export DUECARE_ENDPOINT=http://localhost:8080
    6. python bot.py
"""

from __future__ import annotations

import logging
import os
from typing import Any

import discord
import httpx
from discord import app_commands

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("duecare-discord")

DUECARE_ENDPOINT = os.environ.get("DUECARE_ENDPOINT", "http://localhost:8080")


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


async def _analyze_text(text: str, jurisdiction: str = "", language: str = "en") -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(
            f"{DUECARE_ENDPOINT}/api/v1/analyze",
            json={"text": text, "context": "chat", "jurisdiction": jurisdiction, "language": language},
        )
        r.raise_for_status()
        return r.json()


def _build_embed(data: dict[str, Any]) -> discord.Embed:
    grade = (data.get("grade") or "neutral").lower()
    action = (data.get("action") or "review").upper()
    score = int((data.get("score") or 0) * 100)

    color = {
        "worst": discord.Color.red(),
        "bad": discord.Color.orange(),
        "neutral": discord.Color.yellow(),
        "good": discord.Color.green(),
        "best": discord.Color.teal(),
    }.get(grade, discord.Color.light_grey())

    embed = discord.Embed(
        title=f"DueCare: {grade.upper()} — {action} ({score}%)",
        description=data.get("warning_text") or "",
        color=color,
    )

    indicators = data.get("indicators") or []
    if indicators:
        embed.add_field(
            name="Indicators detected",
            value="\n".join(f"• {i.replace('_', ' ')}" for i in indicators[:6]) or "—",
            inline=False,
        )

    legal = data.get("legal_refs") or []
    if legal:
        embed.add_field(
            name="Applicable laws",
            value="\n".join(f"• {r}" for r in legal[:4]),
            inline=False,
        )

    resources = data.get("resources") or []
    if resources:
        lines = []
        for r in resources[:5]:
            bits = [f"**{r.get('name', '')}**"]
            if r.get("number"):
                bits.append(f"`{r['number']}`")
            if r.get("url"):
                bits.append(r["url"])
            lines.append(" — ".join(bits))
        embed.add_field(name="Help", value="\n".join(lines), inline=False)

    embed.set_footer(text="Privacy is non-negotiable. Analyzed on-device.")
    return embed


@tree.command(name="analyze", description="Analyze text for trafficking / exploitation indicators.")
@app_commands.describe(
    text="The suspicious recruiter message, chat, or contract clause",
    jurisdiction="Migration corridor (e.g. PH_HK, BD_MY, NP_MY)",
    language="Response language: en or tl",
)
async def slash_analyze(
    interaction: discord.Interaction,
    text: str,
    jurisdiction: str = "",
    language: str = "en",
) -> None:
    await interaction.response.defer(thinking=True, ephemeral=False)
    try:
        data = await _analyze_text(text, jurisdiction=jurisdiction, language=language)
    except Exception as e:
        await interaction.followup.send(
            f"Could not reach DueCare at `{DUECARE_ENDPOINT}` — {type(e).__name__}",
            ephemeral=True,
        )
        return
    await interaction.followup.send(embed=_build_embed(data))


@tree.context_menu(name="Analyze with DueCare")
async def ctx_analyze(interaction: discord.Interaction, message: discord.Message) -> None:
    if not message.content:
        await interaction.response.send_message(
            "This message has no text to analyze.", ephemeral=True
        )
        return
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        data = await _analyze_text(message.content)
    except Exception as e:
        await interaction.followup.send(
            f"Could not reach DueCare — {type(e).__name__}", ephemeral=True
        )
        return
    await interaction.followup.send(embed=_build_embed(data), ephemeral=True)


@client.event
async def on_ready() -> None:
    await tree.sync()
    log.info("DueCare Discord bot ready as %s (endpoint: %s)", client.user, DUECARE_ENDPOINT)


def main() -> None:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("set DISCORD_BOT_TOKEN environment variable")
    client.run(token)


if __name__ == "__main__":
    main()
