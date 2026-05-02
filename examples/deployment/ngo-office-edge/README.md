# Topology B — NGO-office edge box

Run the entire Duecare stack on a Mac mini / Intel NUC / old gaming PC
in your office, accessible to caseworkers' phones and laptops over the
office Wi-Fi via mDNS at `duecare.local`. No internet, no cloud bill,
no SaaS to trust.

```
┌─────────── NGO office LAN ───────────┐
│                                      │
│   ┌─────── Mac mini / NUC ───────┐   │
│   │                              │   │
│   │   docker-compose:            │   │
│   │     - ollama (gemma4:e2b)    │   │
│   │     - duecare server          │   │
│   │     - caddy + mDNS responder  │   │
│   │                              │   │
│   │   exposed on :80, :443        │   │
│   │   advertised: duecare.local   │   │
│   └──────────────────────────────┘   │
│              ↑                       │
│              │                       │
│         caseworker phones            │
│         caseworker laptops           │
│         intern tablets               │
│                                      │
└──────────────────────────────────────┘
```

## Hardware sizing

| Hardware | Cost (new) | Verdict |
|---|---|---|
| Mac mini M2 8GB | $599 | ✓ recommended |
| Mac mini M2 16GB | $799 | ✓ better for 5+ caseworkers |
| Intel NUC 12 + 16GB RAM + 512GB | $500-700 | ✓ good Linux-native option |
| Old gaming PC + Linux | $0 (existing) | ✓ if you already have one |
| Refurbished Mac mini 2018 + 16GB | $250-350 | ✓ cheapest viable |
| Synology DS923+ + Docker | $600 + drives | acceptable, slower than Mac mini |
| Raspberry Pi 5 (8GB) | $80 | only Gemma 3 1B fits comfortably |

## Run

```bash
cp ../local-all-in-one/.env.example .env
# Edit OLLAMA_MODEL to gemma4:e4b if you want higher quality
# (and have 16+ GB RAM)

docker compose up -d
```

Wait ~5 minutes on first run while Ollama pulls Gemma 4 (~1.5 GB).

The compose file is identical to [Topology A](../local-all-in-one/)
plus an mDNS sidecar so caseworkers' phones can find the box at
`http://duecare.local` instead of needing to remember an IP.

## Worker setup (per device)

### Caseworker laptop (any browser)

Open: **http://duecare.local**

That's it. The chat UI loads. Bookmark it.

### Caseworker Android phone (Duecare Journey app)

1. Install [the latest APK](https://github.com/TaylorAmarelTech/duecare-journey-android/releases).
2. **Settings → Cloud model**
3. Format: **Ollama**
4. Endpoint URL: `http://duecare.local:11434`
5. Model name: `gemma4:e2b` (or whatever you set in `.env`)
6. Save.

The app's chat surface now routes to your office box. Journal entries
still stay encrypted on the phone.

### Caseworker iOS / non-Android phone

Open Safari to **http://duecare.local** — works as a PWA. "Add to Home
Screen" gives you an icon.

## Privacy posture

- **Worker's chat never leaves the office LAN.**
- **No internet at runtime** for chat/GREP/RAG/tool lookups (assuming
  you don't enable web search).
- **No telemetry from the box.** Stop the docker container and the
  data is on disk in the volumes.

This is the only deployment topology where you can honestly tell a
GDPR / SOC 2 / HIPAA auditor "the worker's data did not leave premises
we control."

## Backup

The `duecare-data` volume contains chat history, journal entries, and
audit logs. Back it up:

```bash
# Snapshot
docker run --rm -v duecare-data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/duecare-$(date +%F).tgz /data

# Restore
docker run --rm -v duecare-data:/data -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/duecare-2026-05-01.tgz -C /
```

A weekly cron job + an external USB drive is enough for an NGO with
< 100 caseworkers. For larger deployments, see
[Topology C](../server-and-clients/) instead.

## Troubleshooting

**Caseworker phones can't reach `duecare.local`** — Mac mini has mDNS
built in (Bonjour). On Linux, install `avahi-daemon`:

```bash
sudo apt install avahi-daemon
sudo systemctl enable --now avahi-daemon
```

Some corporate / hotel Wi-Fi networks block mDNS. Fall back to the IP
address: find it with `hostname -I` on the box and use that instead.

**Connection slow / Ollama hangs** — Gemma 4 E2B INT8 needs ~6 GB free
RAM during inference. If your box only has 8 GB total, switch to
`gemma3:1b` which needs ~2 GB and is 3× faster.

**Caseworkers want to keep using it on the road** — they need
[Topology C](../server-and-clients/) (cloud server) or
[Topology D](https://github.com/TaylorAmarelTech/duecare-journey-android)
(on-device only) for off-LAN access.

## Hardening (optional)

For an office with strict IT policy:

1. Enable HTTPS on Caddy (edit `Caddyfile`, change `:80` to your
   internal hostname; Caddy will auto-fetch a Let's Encrypt cert if
   the hostname is publicly resolvable, otherwise generate a self-
   signed one).
2. Add basic-auth in front of `/chat` and `/research` so only logged-in
   caseworkers can hit them.
3. Put the box on a separate VLAN from general office traffic.

For multi-office NGOs, pair this topology with
[Topology C](../server-and-clients/) — a hosted central server plus an
edge box per office is a common shape.
