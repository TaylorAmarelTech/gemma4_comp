# Duecare adversarial audit (2026-04-25)

> Created at full power. Brutally honest. Severity-tagged so you can
> pick what's worth fixing in 24 days vs. what to defer or document
> as known limitations.
>
> **Severity tags:** P0 = blocks a credible submission / security
> hole, P1 = visibly weakens the rubric story, P2 = engineering hygiene.

---

## 0. What this document is

You asked for a full spectrum audit of the system as it stands after
the last several commits. I went through everything I built (the new
6 packages + the 12,500-line pipeline + the reactive triggers + the
HTML UIs + the CLI + the OpenClaw integration) looking for:

- Things that are silently broken
- Things that are only fake
- Things that are unsafe
- Things that are missing
- Things that won't survive a judge clicking around for 5 minutes

I am NOT pulling punches. Some of what's below is on me (I assumed
APIs exist that don't), some is on the architecture (the pipeline
file is too big), some is just gaps you should know about.

---

## 1. Things I got wrong or oversold

### 1.1 OpenClaw is a fictional API endpoint  ·  P0
I wrote `OpenClawTool` against `https://api.openclaw.io/v1` and four
endpoint shapes I invented: `/search`, `/court_judgments`,
`/news_check`, `/law_lookup`. **That URL almost certainly doesn't
exist as I described it.** The mock mode is the only thing that
genuinely works today.

**Fix.** Either:
- Make `OpenClawTool` a generic adapter and ship 1-2 known-real
  research providers as the actual default backends:
  - **Tavily Search API** (commercial, simple JSON; we already need
    something Gemma can call)
  - **Brave Search API** (commercial, free tier 2000 req/mo)
  - **Serper.dev** (commercial, simple)
  - **CourtListener** (free, US-only, real legal records)
  - **GDELT** (free, global news event database)
- Keep `OpenClawTool` as a thin "bring-your-own URL" wrapper that
  just POSTs to a configured URL with the args dict, in case OpenClaw
  IS a thing the user has access to.
- Document the mock mode as the offline path.

### 1.2 The "queryable evidence DB" is single-user  ·  P1
DuckDB is in-process. Every CLI/server invocation opens its own
connection. The server doesn't pool, so two concurrent requests
serialise on the file lock. Demo-fine, but the "agent can query the
DB" story falls apart with >1 simultaneous agent.

**Fix.** Either accept this as a single-tenant constraint and
document it, or run DuckDB in MotherDuck-style server mode, or ship
the Postgres backend as the production path.

### 1.3 The cloudflared / ngrok integration is happy-path only  ·  P1
- Auto-install writes the binary to `/usr/local/bin/cloudflared` — only
  works on Kaggle (which runs as root) or with sudo elsewhere
- The subprocess is never explicitly killed; `Ctrl+C` on `duecare
  serve` leaks the cloudflared process
- The URL-detection regex assumes specific domains; if Cloudflare
  changes the URL shape, we miss it

**Fix.** Add `atexit` cleanup + a `--no-auto-install` flag + a
configurable URL pattern.

### 1.4 No Gemma backend is actually wired into the server  ·  P0
`ServerState.set_gemma_call()` exists but nothing calls it.
`heuristics.quick_moderate` and `worker_check` always fall back to
the keyword heuristic. **The "Gemma 4 powered enterprise moderation"
demo is currently a regex demo.** Same for NL2SQL — the Translator
defaults to template-only, never uses Gemma.

**Fix.** Add a `--gemma-backend` flag to `duecare serve` that loads
either:
- A subprocess proxy to Gemma (slow, model lives in a separate
  process)
- An in-process load via `transformers` (fast, eats VRAM)
- A Kaggle / HF Inference Endpoint URL (cloud, but contradicts
  "privacy is non-negotiable")

The cleanest demo path is to load Gemma 4 in the same process the
server runs in (Kaggle session has the GPU + the model is already
cached).

---

## 2. Pipeline (`gemma4_docling_gliner_graph_v1.py`) issues

### 2.1 The file is 12,500 lines  ·  P1
- Any bug requires editing the monolith
- Can't easily import functions for testing
- The `if __name__ == "__main__" or True:` ALWAYS runs main() at
  import — that's why the engine has to subprocess
- The hardcoded curated Drive blob (333 lines of base64) bloats the
  diff every time we touch the file

**Fix (proper).** Refactor into modules and a thin orchestration
script. **Fix (pragmatic).** Don't touch it; treat the file as the
"backend processor binary" and let the engine wrap it.

### 2.2 Hardcoded Google Drive API key in source  ·  P0 if shared, P2 if private
You acknowledged this and asked for it. Risk: any time the file
leaks (committed to a public repo, screenshared, copy-pasted to a
support thread), the key is harvested.

**Fix.** Add a sanitiser script: `scripts/_strip_credentials.py` that
produces a "publishable" copy with the key replaced by
`os.environ["GOOGLE_DRIVE_API_KEY"]` and rotates the live key. Run
it before any public artifact ships.

### 2.3 Stage ordering brittleness  ·  P2
Stages 5b → 5c → 5d → 6 → 6b each depend on the prior one's outputs
in the rows list. If 5b silently produces empty `gemma_graph` for
all rows (e.g. budget exhausted before any docs ran), 5c selects no
pairs, 5d's matchers find nothing, 6 builds a graph from regex
fallback only. There's no clear "this stage produced no output, so
you're getting degraded results" warning.

**Fix.** Add a per-stage health check that asserts a minimum output
volume; warn loudly when degraded.

### 2.4 Reactive triggers are English-only  ·  P1
All 5 built-in trigger matchers use English keywords ("recruited",
"deployed", "passport held by"). Documents in Tagalog / Arabic /
Hindi / Indonesian won't fire any trigger even though those are the
LANGUAGES the corpus actually contains.

**Fix.** Multilingual keyword tables, or run translation first via
Gemma, or shift the matchers from keyword-based to entity-pattern-
based (which works regardless of language).

### 2.5 The `backend` NameError lives in main(), but VRAM cleanup is now manual  ·  P2
After the fix that returns `(rows, backend)` from `run()`, callers
(main + any future external caller) MUST call `backend.unload()`
themselves. The next time someone copies main() as a template, they
will forget. Should be a context manager.

### 2.6 Drive walker has no rate limiting  ·  P2
`_gdrive_via_api_key` issues bulk requests with no exponential
backoff. Drive will 429 you eventually.

### 2.7 `_eg_pair_load_image` does no PII redaction  ·  P1
Loads raw images from disk straight into Gemma's processor. If a
document contains a victim's face, name, passport scan — it goes
into the prompt unredacted. The pipeline persists `image_path` to
`enriched_results.json` and the Evidence DB; anyone reading either
file can re-open the underlying image.

**Fix.** Two options:
- Redact at parse time (face blur via OpenCV cascade, text blur over
  detected PII regions)
- Or document that the DB and pipeline outputs ARE confidential and
  the caller is responsible for storage controls

---

## 3. Evidence database issues

### 3.1 Schema portability is partial  ·  P1
SQL functions used in templates that ARE NOT cross-DB:
- `GROUP_CONCAT(...)` — works in DuckDB + SQLite, **not in Postgres
  (uses `STRING_AGG(...)`)**
- `strftime(...)` — works in DuckDB + SQLite, **not in Postgres
  (uses `to_char(...)`)**
- `'%' || :param || '%'` concatenation — works everywhere

The Postgres backend will fail on `avg_fee_by_corridor`,
`complaints_by_agency`, and `fee_change_over_time` until those are
rewritten with backend-aware SQL.

**Fix.** Per-template per-backend SQL or a tiny SQL-AST translator.

### 3.2 No vector index  ·  P1
The README implies semantic search ("find similar cases") but no
actual vector column exists. Need either:
- DuckDB's `vss` extension (`INSTALL vss; LOAD vss;`)
- `sqlite-vss` for the SQLite backend
- `pgvector` for Postgres

Plus an embedder (sentence-transformers) and a backfill script.

### 3.3 No migrations system  ·  P2
`SCHEMA_VERSION` is declared. Nothing reads it. If you add a column,
existing user DBs will silently lack it and queries will fail.

**Fix.** Migration directory + migration runner that diffs `schema_meta`.

### 3.4 `tool_call_cache.ttl_seconds` is unenforced  ·  P2
Column exists, never checked. Cache grows forever.

### 3.5 `_safe_float(0)` returns None  ·  P2
`return float(v) if v is not None else None` — but `float(0)` is OK,
the bug is in `_safe_float(0.0)` paths where `or 0` patterns lose
information.

### 3.6 `_upsert` uses error-message string matching for PK detection  ·  P2
Fragile. DuckDB / SQLite / Postgres each phrase the constraint
violation differently. A future DB version could change the message
and break upserts silently.

---

## 4. NL2SQL / Translator issues

### 4.1 Template matcher is keyword-fragile  ·  P1
"What is the typical agency markup?" misses `avg_fee_by_corridor`
because "typical" + "markup" don't match the trigger words. Real
users phrase questions in unpredictable ways.

**Fix.** Embed all template descriptions, embed the question, pick
the highest-cosine template. Falls back to Gemma if no template is
above a threshold.

### 4.2 `validate_readonly` has false positives  ·  P2
`SELECT * FROM entities WHERE etype = 'INSERT'` would be rejected
because the keyword scan sees the word `INSERT` even though it's
inside a string literal. Same for `'CREATE'`, `'DROP'`, etc.

**Fix.** Strip string literals before tokenizing.

### 4.3 No row limit enforcement  ·  P1
Trusts Gemma to add LIMIT. If Gemma forgets, a query against a
large evidence DB returns millions of rows and OOMs the server.

**Fix.** Wrap every executed query in a `LIMIT 1000` outer SELECT.

### 4.4 No semantic search fallback  ·  P1
"Find me documents about exploitation in Saudi Arabia" can't fall
back to vector similarity. With no template match and no Gemma
backend wired in, it just returns "(no Gemma backend supplied)".

### 4.5 No query history table  ·  P2
Every NL2SQL invocation should write to a `query_log` table for
replay, debugging, and "what did the demo audience actually ask"
analytics.

---

## 5. Server / FastAPI issues

### 5.1 No authentication, no rate limiting  ·  P0
Every endpoint is open. Anyone with the cloudflared URL can:
- POST `/api/process` (spawns a subprocess that runs the pipeline —
  resource bomb)
- POST `/api/query` (executes any SELECT against the DB)
- POST `/api/research/openclaw` (issues network calls on your behalf)

**Fix.** Three-line middleware: read `DUECARE_API_TOKEN` env var, if
set require `Authorization: Bearer <token>` on every `/api/*` route
except `/api/status` (and `/api/healthz`). Generate a token on first
launch and print it in big letters.

### 5.2 `/api/process` runs synchronously  ·  P0
Pipeline takes 5–60 minutes. The HTTP request times out after the
proxy's idle timeout (cloudflared: 100s default). Caller never sees
the result.

**Fix.** Background tasks: `BackgroundTasks` from FastAPI plus a
job table in the DB; `/api/process` returns 202 + `job_id`,
`/api/jobs/{id}` polls.

### 5.3 No CORS config  ·  P2
Browsers may block API calls from cross-origin pages. The static
HTML pages happen to be same-origin so it works for the demo, but
any embedded use case (a partner NGO embedding the worker chat
widget) fails.

### 5.4 Static HTML inline JavaScript / no CSP  ·  P2
Every page has inline `<script>`. No Content-Security-Policy header.
If a future endpoint reflects user input into HTML, XSS landing.

### 5.5 The entity-graph iframe is a placeholder  ·  P1
`/knowledge` shows an iframe with `srcdoc="<p>...placeholder</p>"`
instead of actually serving the pipeline's `entity_graph.html`. The
file exists at `MM_OUT_DIR/entity_graph.html` but the server doesn't
mount that directory. For the demo this is the most visible feature
that doesn't work.

**Fix.** Mount the pipeline output dir as `/static/pipeline/` and
point the iframe at `/static/pipeline/entity_graph.html`.

### 5.6 Settings page leaks system state without auth  ·  P1
`openclaw_configured: yes/no` is reachable without auth. Combine
with absence of rate limiting and an attacker can probe what's set.

### 5.7 No `/healthz` separate from `/api/status`  ·  P2
Load balancers and uptime monitors want a fast 200 with no DB call.

### 5.8 `heuristics.py` is keyword-only  ·  P0 for the demo
The Enterprise + Individual surfaces fall back to keyword matching
when no Gemma backend is wired in. The `_SUSPICIOUS_KEYWORDS` list
is 13 hard-coded English phrases. **A judge testing the Individual
chatbot in any non-English locale gets a useless verdict.**

**Fix.** Either:
- Wire Gemma into the server by default
- OR translate heuristic keywords into the supported locales (~30
  min of work)
- OR clearly label the surface as "demo / heuristic; Gemma backend
  required for production"

### 5.9 `/api/process` doesn't auto-ingest  ·  P1
You run `duecare process`, then SEPARATELY have to `duecare ingest`.
Should be one command that triggers both.

---

## 6. Research tools / OpenClaw issues

### 6.1 The PII filter is incomplete  ·  P1
- Single-name people ("Maria") slip through unless honorific present
- Hyphenated last names ("Maria-Cruz")
- O'Brien-style names with apostrophes
- Date-of-birth strings like "1991-05-12"
- National-ID formats from non-PH/SA jurisdictions
- "Indirect identifiers" (bundle name + age + corridor + employer
  could uniquely identify someone in a small case file)

**Fix.** Add a Microsoft Presidio-style NER pre-pass for high-recall
PII detection, plus a post-filter `k`-anonymity check (e.g. don't
release any combination of fields that would identify <k=5 people).

### 6.2 No audit log of rejected queries  ·  P1
Demo loses: "Look — we BLOCKED 47 PII attempts on this corpus, all
locally" is a phenomenal video beat that's currently impossible
because we don't count.

### 6.3 Mock mode is too obvious  ·  P2
`[mock] Agency licence suspended pending investigation` is clearly
fake. A judge inspecting the responses will notice.

**Fix.** Mock mode should pull from a small canned-data file with
realistic-looking entries.

---

## 7. CLI issues

### 7.1 No `duecare init`  ·  P1
A fresh user has no idea what to do first. `init` should:
- Create the DB
- Create a `.duecarerc` config file in cwd
- Print the next 3 commands

### 7.2 No `duecare doctor`  ·  P1
Diagnose every component:
- Pipeline script reachable? ✓
- DB writable? ✓
- Gemma model accessible (HF token + local cache)? ✗
- Cloudflared installed? ✗
- OpenClaw API key set? ✗

### 7.3 `duecare research` has no caching integration  ·  P2
Should write results to `tool_call_cache` so repeated lookups don't
hit the network. Right now it always calls.

### 7.4 No machine-readable output mode globally  ·  P2
Per-command `--json-out` exists on `query` only. Should be a global
flag.

---

## 8. Engine issues

### 8.1 Subprocess approach loses streaming output unless `stream_output=True`  ·  P2
Server callers want streaming so the UI can show progress.

### 8.2 No timeout on the subprocess  ·  P1
If the pipeline hangs (model load deadlock, infinite Gemma loop), the
engine waits forever.

### 8.3 No resumability  ·  P1
Crash mid-pipeline = restart from Stage 1. For a 9-hour Drive walk
that's brutal. The pipeline itself has budget tracking but no
resume-from-checkpoint.

### 8.4 `_detect_project_root()` walks up from cwd  ·  P2
Fragile when called from inside a notebook with weird cwd.

### 8.5 `EngineConfig` has a fixed env-var set  ·  P2
Any new pipeline env var requires editing the config dataclass. Need
an `extra_env: dict[str, str]` escape hatch.

---

## 9. The training / fine-tuning question (your explicit ask)

**You DO have the ability to retrain.** CLAUDE.md confirms:
- Notebook 530 is `Phase 3 Unsloth Fine-Tune`
- Notebook 525 is `Uncensored 5-Grade Generator` (synthetic data)
- The project's Special Tech track entry depends on Unsloth fine-tuning
- You have a Kaggle T4 + Gemma 4 E4B model already loaded

What's MISSING is the bridge between "we have pipeline outputs" and
"we have Unsloth-ready training data." Specifically:

### 9.1 No synthetic label generator
You're right that you have very little ground-truth data. The way
to get more is the standard semi-supervised playbook:

- **Cluster-based weak labelling.** Embed every doc's text +
  Gemma's facts; cluster (HDBSCAN or k-means with silhouette
  score). For each cluster, take the majority Gemma-predicted
  category as the label for ALL members. Filter clusters whose
  majority share is below 80%.
- **Multi-pass agreement.** When Stage 3 (multimodal classify) and
  Stage 5b (per-doc graph extraction) BOTH say the same thing
  about an entity ("recruitment_agency = Pacific Coast Manpower"),
  treat it as confident.
- **Cross-doc consistency.** If 4 of 5 documents containing entity
  X classify it as "employer", label entity X as "employer" with
  4/5 confidence.
- **Tool-call validation.** When `fee_detected` triggered AND the
  `lookup_statute` call confirmed a violation, that's a strong
  positive label for "illegal_recruitment_fee" on that doc + entity
  pair.

### 9.2 No active learning queue
- Items below confidence threshold go into a review queue
- A CLI / web UI presents one item at a time to a human
- Human label promotes the item to high-confidence
- Reviewed items become training data immediately

### 9.3 No training-dataset assembler
- Convert (input, label, confidence) triples into Unsloth chat-
  format JSONL
- Train/val/test splits stratified by label
- Balance: oversample low-frequency labels, cap high-frequency ones

### 9.4 No "kick off retrain" UX
- "Coming Soon" framing is fine
- But the SCAFFOLD should exist so it's literally one button when
  you DO have GPU budget
- Track training runs in the same DB (`training_runs` table)

**See section 12 below for the package skeleton I'm shipping in this
turn that covers all four pieces.**

---

## 10. Demo / video readiness

### 10.1 Empty DB on first launch  ·  P0 for demo
A judge runs `duecare serve`, opens `/knowledge`, types a question
→ "no rows". That's the worst possible first impression.

**Fix.** `duecare demo init` command that:
- Runs the pipeline against the synthetic mini-corpus (or a checked-in
  sample folder)
- Ingests it into the DB
- Now `/knowledge` has data

### 10.2 No video script for the new packages  ·  P1
The existing `docs/video_script.md` predates the new architecture.
Needs an update.

### 10.3 No screenshot / mockup gallery  ·  P2
For the writeup; otherwise judges have to launch to see the UI.

### 10.4 `entity_graph.html` iframe is a placeholder  ·  P0 for demo
Already noted in §5.5. Most visible broken thing.

---

## 11. Security / privacy gaps

### 11.1 Pipeline outputs persist raw entity values  ·  P0 if shared, P1 always
The Evidence DB stores Gemma-extracted person names, phone numbers,
addresses, passports verbatim. If the DB file ends up in a backup,
git commit, or screenshare — full plaintext PII leak.

**Fix.** Two-tier:
- Hash-and-store: persist `sha256(value)` + a non-reversible bucket
  name; original text only lives in the per-row response JSON which
  CAN be selectively redacted
- Or: encrypt the DB file at rest (DuckDB doesn't support this
  natively; SQLite does via SQLCipher; Postgres can use TDE)
- Or: clearly label the DB file as "confidential, treat as raw case
  data" and add it to `.gitignore`

### 11.2 No audit log  ·  P1
Who queried what, when, from which IP. If this ever runs in an NGO
context with multiple investigators, the audit log is a soft
requirement.

### 11.3 No data retention policy  ·  P2
`tool_call_cache` and audit-log tables grow unboundedly.

### 11.4 The cloudflared tunnel exposes the FULL API  ·  P0 if URL leaks
If the URL gets shared / posted / cached — every endpoint is open.
Auth (§5.1) addresses this.

---

## 12. The training package (built in this turn — see `packages/duecare-llm-training`)

Five modules:

1. **`labels.py`** — synthetic label generator. Three strategies
   (cluster-vote, multi-pass-agreement, cross-doc-consistency).
   Reads from EvidenceStore, writes labels with confidence.
2. **`review_queue.py`** — active learning queue. CLI `duecare
   review next` shows one low-confidence item, asks for human label.
3. **`dataset.py`** — assembler. Reads labels, produces Unsloth
   chat-format JSONL with stratified splits.
4. **`trainer.py`** — Unsloth wrapper. `--dry-run` works without
   GPU; the actual kick-off is gated behind a "Coming Soon" flag
   that requires `MM_TRAINING_ENABLED=1` + a GPU check.
5. **`runs.py`** — training-runs DB table + status accessor.

CLI surface:
```
duecare train labels --strategy cluster-vote --min-confidence 0.8
duecare train review next
duecare train dataset --output dataset.jsonl
duecare train kickoff --dry-run                     # always works
duecare train kickoff                               # gated, "Coming Soon"
duecare train status
```

Server adds `/training` page with the same operations as cards.

---

## 13. Prioritized improvement plan (24-day budget)

### Week 1 — fix the demo
- [ ] **§5.5** Mount pipeline output dir + serve `entity_graph.html`
  in iframe
- [ ] **§10.1** `duecare demo init` for sample data
- [ ] **§5.1** Auth token middleware (1-line env var, 3-line check)
- [ ] **§5.2** Background tasks for `/api/process` + `/api/jobs/{id}`
- [ ] **§1.1** Replace fictional OpenClaw with Tavily / Brave Search
  + keep OpenClaw as a generic adapter
- [ ] **§1.4** Wire Gemma backend into the server (single load,
  shared by Translator + heuristics)

### Week 2 — fix the core gaps
- [ ] **§4.1, §4.3** NL2SQL: vector-embedded template matcher +
  forced LIMIT wrapper
- [ ] **§3.1** Postgres-compatible SQL in templates
- [ ] **§9** Training package (this turn) + review CLI
- [ ] **§7.1, §7.2** `duecare init` and `duecare doctor`
- [ ] **§2.4** Multilingual reactive triggers (Tagalog + Arabic +
  Hindi keyword tables, or shift to entity-pattern triggers)

### Week 3 — polish for the video
- [ ] **§10.2** New video script reflecting the 3-act / 4-card story
- [ ] **§6.2** PII rejection counter + a "we blocked N attempts"
  widget for the Settings page
- [ ] **§3.2** Vector search on top of DuckDB `vss` extension
- [ ] Wire OpenClaw / Tavily into a reactive trigger
  (`agency_negative_news_check`) so it fires automatically

### Week 4 — record + submit
- [ ] Demo recording with the cloudflared URL
- [ ] Writeup pass (already drafted; update for the new architecture)
- [ ] Final dependency audit — rerun `pip install -e packages/...`
  in a fresh env and document what breaks

### Explicitly cut (don't do)
- Postgres production deploy (single-tenant DuckDB is fine for a
  hackathon demo)
- Docker / k8s
- Tests beyond a couple of smoke tests for the new packages
- Migrations system (manually drop+recreate is fine)
- Tracing / metrics
- CSP / CORS hardening

---

## 14. The brutal honest one-line summary

The system has the SHAPE of a complete product: pipeline → DB → NL
query → 3 surfaces → CLI → public-URL demo → research tools →
training scaffold. About **70% of the substance behind that shape
is real**, **20% is heuristic placeholder** (the moderation/worker
heuristics, OpenClaw URL, NL2SQL template matcher), and **10% is
known broken** (entity graph iframe, no auth, sync /api/process,
incomplete PII filter).

The fastest path to a demo a judge would believe is:
1. Fix the iframe (§5.5)
2. Fix demo data preloading (§10.1)
3. Wire Gemma into the server (§1.4)
4. Add auth (§5.1)
5. Replace OpenClaw with a real search provider (§1.1)
6. Update the video script (§10.2)

Six items. Maybe 3 days of focused work. After that, what's left is
making the surfaces look good enough on camera.
