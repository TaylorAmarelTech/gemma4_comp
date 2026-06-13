# Scheduled scraping — run forever, propose-only

The recruitment pipeline runs on a schedule via the existing **research
monitor** (`duecare.research_tools.monitor`): a propose-only freshness checker
that fetches every page in the public official-source registry, content-hashes
it (normalized so trivial chrome diffs don't false-flag), diffs against the
prior run, and emits a **curator review queue** of what changed. It never
mutates the knowledge layer and stores no PII.

This is the "scheduled runs, starting now, forever" layer. The scraping itself
is deterministic Python — no LLM in the loop — so it runs cheaply on a plain
cron with no model cost.

## The forever scheduler — GitHub Actions cron

`.github/workflows/scheduled-scrape.yml` runs daily (06:17 UTC) **forever** on
GitHub's scheduler, plus a `workflow_dispatch` trigger to **run now** from the
Actions tab. Each run:

1. installs the monitor + advanced-fetch extras (`curl_cffi`,
   `charset_normalizer`);
2. restores the prior content-hash **state** from the Actions cache (so a run
   flags only what changed since last time — the "continue forever" diff);
3. runs `python -m duecare.research_tools.monitor check --sources ... --state
   ... --out ...`;
4. uploads the proposals + run log as an artifact and writes a job summary —
   the review queue.

No local machine stays on; GitHub keeps it running. If the state cache is
evicted, the next run simply re-baselines (every source reported `new` once) —
harmless.

## Advanced web scraping (WAF-resistant)

Government / NGO sites behind Cloudflare or Akamai drop a stdlib-urllib request
by its TLS/JA3 fingerprint — a User-Agent string alone does not help. The
monitor's `default_fetch` prefers **`curl_cffi`** with a real Chrome TLS
fingerprint (`impersonate="chrome"`), which defeats those WAF 403s, and falls
back to stdlib urllib when curl_cffi is not installed. `charset_normalizer`
detects the charset to avoid mojibake. Both are optional extras; the monitor
runs without them.

For JavaScript-rendered registries (the DMW inquiry is a Nuxt SPA), the page
HTML still exposes the backing JSON API; point `scripts/scrape_agency_sources.py
--source dmw_api` at that endpoint (env-keyed). A headless-browser escalation
(Playwright) is a documented option for sites with no reachable API — see
`docs/research/` tooling surveys.

## The review-and-promote loop

```
  scheduled run ─► proposals (needs_review=True) ─► curator reviews the queue
        ▲                                                    │
        └──────────── promote vetted updates ◄──────────────┘
   (agency_registry.py --ingest for licence lists; GREP/RAG promotion for
    statute/guidance changes — all manual, all propose-only)
```

Nothing is auto-applied. A changed agency-licensing page (`ph_dmw_licensed_agencies`,
`hk_eaa_licensed`, `sg_mom_ea_directory`) or a new advisory
(`ph_dmw_advisories`) becomes a review item; the curator decides what to fold
into the verification registry or knowledge packs.

## Self-hosted scheduling (alternatives to GitHub Actions)

Same command, any scheduler:

```bash
CMD="python -m duecare.research_tools.monitor check \
  --sources configs/duecare/research_monitor/sources.yaml \
  --state .monitor-state/state.json \
  --out reports/research_monitor/proposals.json"
```

- **cron** (Linux/macOS): `17 6 * * *  cd /path/to/gemma4_comp && <CMD>`
- **systemd timer**: a `OnCalendar=*-*-* 06:17:00` timer running the unit.
- **Windows Task Scheduler**: a daily task running the same command.

Keep `.monitor-state/state.json` between runs so each run diffs against the
last.

## Sources

`configs/duecare/research_monitor/sources.yaml` — 22 public official pages
(ILO, US TIP, UNODC, IOM, FATF, regulators, hotlines, oversight bodies) plus
the recruitment-agency licensing registries (PH DMW licensed-agency inquiry +
advisories, HK EAA, SG MOM EA directory). Add sources by jurisdiction/corridor
over time; PUBLIC pages only.

## Responsible-use boundary

- Propose-only: the monitor writes proposals + a hash state, never production
  packs.
- Public official pages only; no PII stored (proposal summaries are
  PII-scrubbed).
- Polite: the monitor fetches each source once per run with a browser-grade UA
  and retries; it is not a crawler and does not spider links.
- Tests: `tests/test_scheduled_scrape_sources.py` (registry validity + offline
  run + change-detection) and `packages/duecare-llm-research-tools/tests/test_monitor.py`.
