# NGO office deployment — case intake, document analysis, research

> **Persona.** You direct an NGO with 1-20 caseworkers helping
> migrant workers, trafficking survivors, or asylum seekers. You
> need a private, on-premises tool that helps caseworkers do case
> intake, analyse contract photos / receipts / IDs, look up
> jurisdiction-specific law, and produce a referral packet — without
> sending any worker data to a cloud service you don't control.
>
> **What you need.** A Mac mini or NUC in your office, plugged in,
> reachable on the office Wi-Fi, with `duecare.local` as the URL
> caseworkers bookmark. No subscription. No telemetry. Backups
> nightly to a USB drive.
>
> **What this doc gives you.** Day-1 setup script, day-2 caseworker
> quickstart, day-30 expansion checklist, and the operational
> patterns that have worked at peer NGOs.

## Day 1 — Initial setup (90 minutes)

### What you'll need

| Item | Notes |
|---|---|
| **Mac mini** (M2, 16 GB or 32 GB) **or** Intel NUC + Linux | $250-800 one-time. M2 is easiest. |
| Office Wi-Fi with a static IP for the box | Bind a DHCP reservation in the router |
| External USB-C SSD (≥ 256 GB) | For nightly backups |
| One free hour of an IT-comfortable colleague | OR follow the script below — no terminal experience required |

### Step 1 — Install Docker Desktop (10 min)

Mac mini: download Docker Desktop from https://docs.docker.com/desktop/install/mac-install/ — drag to Applications, open, accept the privacy prompt.

Linux NUC: `curl -fsSL https://get.docker.com | sh` followed by
`sudo usermod -aG docker $USER` and a re-login.

Open a terminal and confirm: `docker version` should print client
+ server versions.

### Step 2 — Clone and bring up the stack (15 min)

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp.git
cd gemma4_comp

# One-command bring-up. Pulls Gemma 4 E2B (~1.5 GB), starts the
# stack, smoke-tests it, prints the URLs.
make demo
```

First run takes ~5 minutes (Docker image build + Gemma 4 download).
Subsequent boots are seconds.

### Step 3 — Make it reachable as `duecare.local` on the office LAN (10 min)

The compose file already includes mDNS (Bonjour on macOS, Avahi on
Linux) so `http://duecare.local` resolves on the same Wi-Fi.

Mac mini: enable Network Sharing in System Settings → General →
Sharing → Remote Login. The Bonjour daemon publishes the hostname
automatically. Test from a colleague's laptop on the same Wi-Fi:
`ping duecare.local`.

Linux NUC: install Avahi (`sudo apt install avahi-daemon`) and start
it (`sudo systemctl enable --now avahi-daemon`).

If your office Wi-Fi blocks mDNS (some corporate networks do), fall
back to the box's static IP. Find it with `ifconfig | grep inet` and
have caseworkers bookmark `http://<that-ip>:8080` instead.

### Step 4 — Configure caseworker accounts (15 min)

For an office with ≤ 5 caseworkers, the simplest pattern is
**Cloudflare Tunnel + Cloudflare Access**:

```bash
# On the Mac mini:
brew install cloudflared
cloudflared tunnel login    # opens browser; pick your CF account
cloudflared tunnel create duecare-office
cloudflared tunnel route dns duecare-office duecare.your-org.org
cloudflared tunnel run duecare-office
```

In Cloudflare dashboard → Zero Trust → Access → Applications → Add:
- App type: Self-hosted
- Hostname: `duecare.your-org.org`
- Policy: Allow emails ending in `@your-org.org`

Now `https://duecare.your-org.org` is reachable from anywhere with
SSO — but only for verified colleagues. Free for ≤ 50 users.

For ≥ 5 caseworkers OR if you don't want CF in the loop, use the
self-hosted oauth2-proxy overlay:

```bash
# Edit .env: pick an OIDC provider (Google Workspace / Microsoft /
# Authentik / Keycloak), set the OAUTH2_* fields, then:
make demo-with-auth
```

See `docs/considerations/multi_tenancy.md` for provider cheat sheets.

### Step 5 — Schedule nightly backups (10 min)

```bash
# Mount the USB drive at /Volumes/Backup (Mac) or /mnt/backup (Linux).
# Add a cron job:
crontab -e
# Add this line:
0 3 * * * cd /path/to/gemma4_comp && bash scripts/backup.sh --dest /Volumes/Backup --skip-models >> /var/log/duecare-backup.log 2>&1

# Test the backup runs:
bash scripts/backup.sh --dest /Volumes/Backup --skip-models
ls -lh /Volumes/Backup/
```

`--skip-models` keeps backups under 100 MB (vs ~2 GB with model
weights). Restore the model on a new box just by re-running
`make demo`.

### Step 6 — Verify it works (10 min)

Run the doctor:

```bash
make doctor
# Expected: all checks pass except possibly OAuth (if you skipped step 4)
```

Open the chat in your browser, type:

> "Is a 50,000 PHP training fee legal for a Filipino domestic
> worker going to Hong Kong?"

You should get a response citing **POEA Memorandum Circular 14-2017
§3** (the zero-fee corridor rule) within ~10 seconds. If you do —
the harness is working. If not, see "When something breaks" below.

### Step 7 — Onboard the first caseworker (20 min)

Hand them the [Caseworker Quickstart](#caseworker-quickstart) below
and walk through:
- How to log in (their email + the SSO flow)
- The chat surface
- The Reports tab
- The intake wizard
- "What never to type" privacy training

Have them run through one mock intake — a real situation from
recent casework with names changed. Catch confusion early.

## Caseworker quickstart

> **Audience.** A caseworker on day 1. Not technical. This is the
> page you print and tape next to their monitor.

### Logging in

1. Open the browser bookmark for `duecare.local` (or your CF Access
   URL).
2. If prompted for SSO, sign in with your work email.
3. The chat surface loads.

### What you can ask

The chatbot is trained on:
- ILO forced-labour law (Conventions C029, C181, C189, C095)
- The UN Palermo Protocol
- POEA / BMET / BP2MI / DoFE recruitment regulations
- HK / Saudi / Singapore / UAE / Qatar / Malaysia labour codes
- Migration-corridor placement-fee caps for 6 corridors
- Trafficking pattern recognition (37 GREP rules)

It is NOT a lawyer. Use it to:

- **Quickly look up** the law for a fee or contract clause
- **Generate** a draft NGO referral packet
- **Spot patterns** you might have missed (e.g., the recruiter's
  language matches a known fraud playbook)
- **Cite** statute + ILO indicator in your case notes

### What never to type

- Real names of workers (use composite labels: "Worker A", "the
  client from intake 2026-05-02")
- Passport numbers, IDs, account numbers
- Exact addresses (use "a household in Causeway Bay" instead)
- Phone numbers / email addresses

The harness's audit log keeps **only hashes** of what you type, not
the plaintext. But typing PII is still bad practice — caseworker
notes can be subpoenaed; the chat box should not be the only filter.

### The intake wizard

For new cases, click **Add entry** → **Quick guided intake** in the
journal. Walks through 10 questions (recruiter name, fees, contract,
documents, destination, communication freedom, threats). Produces
auto-tagged journal entries that show up in the Reports tab.

### The Reports tab

Click **Reports**. You'll see:

- **Case overview** — entries, fee lines, risk flags, critical risks
- **ILO indicator coverage** — which of the 11 ILO forced-labour
  indicators have fired in this case
- **Detailed risk findings** — each fired GREP rule with statute
  citation + recommended next step
- **Fee table** — every fee tracked, flagged legal/illegal vs the
  corridor cap
- **Generate intake document** — produces a markdown report you can
  share with a partner NGO, lawyer, or regulator. One tap; share via
  email / Signal / WhatsApp / print to PDF.

### When the chatbot is wrong

It will be wrong sometimes. Always:
- Check the cited statute (POEA MC 14-2017 should be findable on
  https://dmw.gov.ph)
- Check the ILO citation against
  https://www.ilo.org/dyn/normlex
- Check the NGO contact phone number is current
- For anything actionable, get a lawyer in the loop

The harness reduces lookup time by 90%. It does not replace
professional judgment.

## Day 2-7 — Operational rhythm

### Morning routine (5 min)

```bash
# Confirm the box is healthy
make doctor

# Check overnight backup ran
ls -lt /Volumes/Backup/duecare-*.tgz | head -1
```

### Weekly (15 min)

- Pull Duecare updates: `git pull && make demo` (rebuilds from
  source; no data loss)
- Skim `docker compose logs --tail=200` for errors
- Verify the USB backup drive isn't full

### Monthly (30 min)

- Test the restore path on a different box: copy a backup to a
  spare laptop, run `bash scripts/restore.sh <backup>`, confirm the
  journal restores correctly
- Review caseworker activity per the Reports tab — anomalies?
  Unanswered tickets?
- Update the Gemma model if a new variant is published:
  `DUECARE_OLLAMA_MODEL=gemma4:newer docker compose up -d`

## Day 30 — Expansion checklist

Once the workflow has stabilized, consider:

| Add-on | Cost | Benefit |
|---|---|---|
| Observability stack (`make demo-with-monitoring`) | $0 + RAM | Per-caseworker usage dashboards, error spikes alert before users notice |
| Android v0.9 APK installed on caseworker phones | $0 | Workers can do field intake offline, sync to office on Wi-Fi |
| 2nd Mac mini as hot standby | $250-800 | Survives a hardware failure with < 1h RTO |
| Tavily / Brave / Serper API key for web research | $0-25/mo | The agentic-research toggle (A4 notebook) becomes useful |
| Per-caseworker OIDC group → tenant routing | $0 | Per-caseworker rate limit + audit log shard |
| Custom domain pack for your jurisdiction | $0 + 1 day work | Add corridor / regulator / NGO contacts the bundled corpus doesn't have |

## When something breaks

Run `make doctor`. The output will point at the failed check.
Common cases:

| Symptom | Likely cause | Fix |
|---|---|---|
| Doctor says "ollama-model: no Gemma model pulled" | First-launch model pull failed (network / disk full) | `docker compose exec ollama ollama pull gemma4:e2b` |
| Doctor says "chat-roundtrip: no response" | Model is loading (cold start) | Wait 30s, retry |
| `duecare.local` doesn't resolve from caseworker phones | mDNS blocked on the office network | Bookmark the box's IP instead, or use Cloudflare Tunnel |
| Chat starts giving canned responses | Ollama container died | `docker compose restart ollama` then check `docker compose logs ollama` |
| "Disk full" warnings | Audit log + journal grew | `bash scripts/backup.sh && docker compose exec duecare-chat duecare audit prune --older-than=90d` |
| Power outage corrupted the journal | SQLCipher journal can be repaired | Restore from last night's backup: `bash scripts/restore.sh /Volumes/Backup/duecare-LATEST.tgz` |
| Caseworker says chat is wrong | Always possible — Gemma 4 is helpful, not infallible | Cross-check the cited statute; if a real bug, file an issue with the prompt + response (PII redacted) |

For deeper triage: `docs/considerations/runbook.md` has incident
playbooks per Prometheus alert.

## What you're committing to

By running this in your office:

- **Privacy**: every chat / journal / report stays on the box. Your
  caseworkers can honestly tell a client "this never leaves the
  office."
- **Cost**: $0 / month after the one-time hardware. (Optional:
  Cloudflare Tunnel free, $5/mo for a domain.)
- **Maintenance**: ~30 min/week of an IT-comfortable colleague.
- **Update cadence**: pull weekly to get rule + corpus updates.
- **Backup discipline**: nightly USB-drive snapshots; monthly
  restore test.

## What you're NOT committing to

- Building software. The repo + image are maintained upstream.
- Hosting customer data with a third party. The Mac mini is the
  full surface.
- A lawyer's role. The harness assists casework; a lawyer remains
  in the loop for actionable advice.
- A SOC 2 audit. The deployment can support a SOC-2-style claim
  (see `docs/considerations/COMPLIANCE.md`) but achieving the
  certification is your audit firm's job.

## See also

- [`examples/deployment/ngo-office-edge/`](../../examples/deployment/ngo-office-edge/)
  — the underlying compose file + NGO-specific helpers
- [`docs/deployment_topologies.md`](../deployment_topologies.md) —
  if your needs grow beyond an office (multi-site / cloud / hybrid)
- [`docs/considerations/multi_tenancy.md`](../considerations/multi_tenancy.md) —
  per-caseworker isolation when you expand
- [`docs/considerations/runbook.md`](../considerations/runbook.md) —
  on-call playbooks
- [`docs/gemma4_model_guide.md`](../gemma4_model_guide.md) — picking
  the right Gemma 4 variant for your hardware
