# Duecare application launch guide

> Created 2026-04-25. Covers how to launch each surface (Enterprise,
> Individual, Knowledge) via the CLI, the FastAPI server, or both.

---

## Architecture in one diagram

```
                           +-----------------------------+
                           |  raw_python/                |
                           |  gemma4_docling_gliner_     |
                           |  graph_v1.py                |
                           |  (the 12,500-line pipeline) |
                           +--------------+--------------+
                                          | (subprocess)
                                          v
+----------------------------+   +-----------------+   +------------------+
| duecare-llm-engine         |   | pipeline output |   |  duecare-llm-    |
|  Engine.process_folder()   |-->|  enriched_*.json|<--|  evidence-db     |
|  Run / Document / Entity / |   |  entity_graph.* |   |  EvidenceStore   |
|  Edge / Finding models     |   |  reactive_*.json|   |  DuckDB / SQLite |
+----------------------------+   +-----------------+   |  / Postgres      |
                                                       +--------+---------+
                                                                |
                          +----------------------+              |
                          | duecare-llm-nl2sql   |--------------+
                          | Translator.answer()  |   templates + Gemma
                          +----------+-----------+   safety guard
                                     |
       +---------------+   +---------v---------+   +-----------------------+
       | duecare-llm-  |   | duecare-llm-      |   | duecare-llm-          |
       | research-     |-->| server (FastAPI)  |<--| cli (`duecare ...`)   |
       | tools         |   | + 4-card homepage |   +-----------------------+
       | (OpenClaw)    |   | + cloudflared/    |
       +---------------+   |   ngrok tunnel    |
                           +-------------------+
                                     |
              +----------+-----------+----------+----------+
              v          v           v          v          v
        Enterprise  Individual   Knowledge   Settings    REST API
        compliance  chatbot      / NGO                   /api/*
        (UC1)       (UC2)        (UC3)
```

## Five new packages

| Package | Purpose | Key entrypoints |
|---|---|---|
| `duecare-llm-evidence-db` | Persistent DuckDB schema for entities / edges / findings / tool-call cache | `EvidenceStore.open()` |
| `duecare-llm-engine` | Subprocess wrapper around the multimodal pipeline | `Engine().process_folder(cfg)` |
| `duecare-llm-nl2sql` | NL question → SQL with safety guard + template fallback | `Translator(store).answer(q)` |
| `duecare-llm-research-tools` | OpenClaw + pluggable research tools with PII filter | `OpenClawTool.from_env()` |
| `duecare-llm-server` | FastAPI server, 4-card homepage, cloudflared/ngrok tunnel | `duecare serve` |
| `duecare-llm-cli` | Single `duecare` CLI binding it all together | `duecare --help` |

## Quickstart (local)

```bash
# 1. Install all packages from the workspace
uv pip install -e packages/duecare-llm-evidence-db
uv pip install -e packages/duecare-llm-engine
uv pip install -e packages/duecare-llm-nl2sql
uv pip install -e packages/duecare-llm-research-tools
uv pip install -e packages/duecare-llm-server
uv pip install -e packages/duecare-llm-cli

# 2. Run the pipeline against a folder
duecare process /path/to/case-files --out ./out --max-images 25

# 3. Ingest the JSON outputs into the evidence DB
duecare ingest ./out

# 4. Ask a question
duecare query "What is the average illicit fee?"

# 5. Launch the demo server
duecare serve --port 8080
# open http://localhost:8080
```

## For the Kaggle demo recording

You want a public URL pointing to the FastAPI server so you can record
the demo from your laptop browser while the model + tools run on the
Kaggle GPU.

```python
# In a Kaggle cell, AFTER the pipeline cell has finished:
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install",
                "-e", "packages/duecare-llm-evidence-db",
                "-e", "packages/duecare-llm-engine",
                "-e", "packages/duecare-llm-nl2sql",
                "-e", "packages/duecare-llm-research-tools",
                "-e", "packages/duecare-llm-server",
                "-e", "packages/duecare-llm-cli"], check=True)

import os
os.environ["DUECARE_PIPELINE_OUT"] = "/kaggle/working/multimodal_v1_output"
os.environ["DUECARE_DB"] = "/kaggle/working/duecare.duckdb"

# Ingest the pipeline outputs first.
subprocess.run(["duecare", "ingest", "/kaggle/working/multimodal_v1_output"],
               check=True)

# Launch the server with a cloudflared quick tunnel.
# This blocks; the public URL prints as soon as cloudflared is ready.
subprocess.run(["duecare", "serve",
                "--port", "8080",
                "--tunnel", "cloudflared"], check=True)
```

The cell will print something like:
```
  ==> open this URL on your laptop:
  ==> https://random-words.trycloudflare.com
```

Visit that URL on your laptop to see the 4-card homepage.

## Demo script (3 minutes)

| Time | Surface | Action | Voiceover |
|---|---|---|---|
| 0:00–0:10 | Homepage | Pan over 4 cards | "One engine. Three audiences." |
| 0:10–0:55 | Individual | Paste coercion message → severity 9, hotline shown | "Maria's phone, no cloud, no leak" |
| 0:55–2:25 | Knowledge | Type *"How many complaints does Pacific Coast Manpower have?"* → table appears + entity graph beneath | "Same engine — investigator's view" |
| 2:25–2:50 | Enterprise | Paste suspicious job post → BLOCK badge + statute citation | "And the platforms" |
| 2:50–3:00 | Settings | Show OpenClaw configured, public URL, run history | Close on named NGOs |

## Use-case coverage

| Use case | Surface | Backend modules |
|---|---|---|
| 1. Enterprise content moderation | `/enterprise` | server.heuristics + Gemma + statute lookup |
| 2. Individual / NGO worker education | `/individual` | server.heuristics + Gemma + locale-aware hotlines |
| 3. NGO investigation suite | `/knowledge` | engine + evidence-db + nl2sql + research-tools |
| 4. Settings / control plane | `/settings` | every module's config surface |
| 5. Programmatic / agent API | `/api/*` | every module via REST |

## Configuration

All env vars (also visible in `/settings`):

| Var | Default | Purpose |
|---|---|---|
| `DUECARE_DB` | `duecare.duckdb` | Evidence-store connection string |
| `DUECARE_PIPELINE_OUT` | `./multimodal_v1_output` | Where the pipeline writes JSONs |
| `DUECARE_PIPELINE_SCRIPT` | `raw_python/gemma4_docling_gliner_graph_v1.py` | Pipeline script path |
| `OPENCLAW_API_KEY` | (unset) | OpenClaw API key |
| `OPENCLAW_BASE_URL` | `https://api.openclaw.io/v1` | OpenClaw base URL |
| `OPENCLAW_MODE` | `online` | `online` or `mock` |
| `NGROK_AUTHTOKEN` | (unset) | Required only if `--tunnel ngrok` |

Plus every existing `MM_*` and `POC_*` env var the pipeline reads.

## Custom triggers (zero-code via reactive config)

The reactive trigger pipeline (`Stage 5d`) accepts a YAML override file
(`MM_REACTIVE_CONFIG=...`) so you can tune the 5 built-in triggers
without code:

```yaml
triggers:
  fee_detected:
    enabled: true
    max_per_doc: 3
    max_total: 60
  phone_shared_cross_bundle:
    enabled: false
  passport_held_by_employer:
    max_total: 50
    multimodal: true
```

For a NEW trigger, register from Python:

```python
from gemma4_docling_gliner_graph_v1 import register_reactive_trigger, ReactiveTrigger
# or, when packaged: from duecare.engine.triggers import ...

register_reactive_trigger(ReactiveTrigger(
    name="ph_sa_corridor",
    description="Workers PH->SA -> corridor risk profile",
    matcher=my_matcher,
    prompt_builder=my_prompt_builder,
    tools=["lookup_statute", "openclaw_court_judgments"],
    max_per_doc=1, max_total=10,
))
```

## Custom research tools

Implement the `ResearchTool` protocol and register:

```python
from duecare.research_tools import register_research_tool

class CourtListenerTool:
    name = "courtlistener"
    description = "US federal court records"
    def query(self, **kwargs):
        ...

register_research_tool("courtlistener", CourtListenerTool())
```

It's then callable from the harness as
`REACTIVE_TOOL_REGISTRY["courtlistener"]` and exposed at
`/api/research/courtlistener` if you wire the route.
