# Topology A — local CLI (no Docker)

Single Python script. Bundles Gemma 4 (via Ollama) + GREP + RAG +
tools + internet search. For developers and sysadmins who want an
all-in-one local chat without Docker overhead.

## Prerequisites

```bash
# 1. Ollama (https://ollama.com/download)
# Mac: brew install ollama
# Linux/WSL: curl -fsSL https://ollama.com/install.sh | sh
# Windows: download installer

# 2. Pull a Gemma 4 model
ollama pull gemma4:e2b         # ~1.5 GB INT8, recommended
# or:
# ollama pull gemma4:e4b       # ~3.5 GB, higher quality
# ollama pull gemma3:1b        # ~600 MB, fastest

# 3. Install the harness packages
pip install duecare-llm-chat duecare-llm-research-tools
```

## Run

```bash
# Interactive REPL
python duecare_cli.py

# One-shot
python duecare_cli.py --once "Is a 50,000 PHP training fee legal for a domestic worker going to Hong Kong?"

# Show the GREP/RAG/tool pipeline before the answer
python duecare_cli.py --pipeline "My recruiter is keeping my passport for safekeeping"

# Internet search only
python duecare_cli.py --search "POEA Memorandum Circular training fee 2025"

# Tag the corridor so the harness adds corridor-specific tool lookups
python duecare_cli.py --corridor PH-HK
```

In the REPL, `/search <query>`, `/pipeline <question>`, and `/quit`
are slash-commands.

## Internet search (optional)

The CLI uses whichever provider it finds an API key for. Pick one:

```bash
export TAVILY_API_KEY=tvly-...           # https://app.tavily.com/sign-in
# or
export BRAVE_SEARCH_API_KEY=BSA...       # https://api.search.brave.com/app/keys
# or
export SERPER_API_KEY=...                # https://serper.dev
```

Without any of those, search falls back to DuckDuckGo HTML scraping
(works without a key, but is rate-limited and may break).

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Where Ollama is reachable |
| `OLLAMA_MODEL` | `gemma4:e2b` | Which model to load |
| `DUECARE_DATA_DIR` | `~/.duecare/` | Chat history + journal |

## What it does

For every question, the script:

1. **Runs the GREP layer** — 37 trafficking-pattern regexes from
   `duecare-llm-chat`. Surfaces ILO-indicator citations.
2. **Retrieves RAG docs** — top-3 from the 26-doc legal corpus via BM25.
3. **Runs the tool layer** — corridor fee cap, NGO directory, ILO
   indicator description (if `--corridor` is set).
4. **Composes a journey-aware prompt** — persona + GREP hits + RAG
   snippets + tool results + the question.
5. **Streams Gemma 4's response** — token-by-token from Ollama.

The `/pipeline` slash command shows steps 1-4 before step 5 streams.

## When to graduate to Docker / cloud

| If you... | Use instead... |
|---|---|
| Want a web UI, not a terminal | [Topology A — Docker Compose](../local-all-in-one/) |
| Want multiple users on a LAN | [Topology B — NGO-office edge](../ngo-office-edge/) |
| Want a hosted backend for your phone app | [Topology C — server + clients](../server-and-clients/) |
| Want to run on the worker's phone | [Topology D — Android](https://github.com/TaylorAmarelTech/duecare-journey-android) |
