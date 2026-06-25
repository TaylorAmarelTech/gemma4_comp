# Ollama-cloud coding harness (no Claude Code)

A local agentic coding harness that drives this repo with **Ollama cloud** models
instead of Claude Code. Two models are load-bearing:

| Role | Model | Job |
|---|---|---|
| **Architect** | `glm-5.2` | Reads the repo map + your request and writes the change plan. |
| **Editor** | `kimi-k2.6` | Turns the plan into precise file diffs. |

It is built on [Aider](https://aider.chat) in `--architect` mode, pointed at the
Ollama OpenAI-compatible endpoint (`https://ollama.com/v1`). No Anthropic / Claude
dependency anywhere in the path.

## Why Aider (vs a tool-calling agent)

Open models below Claude's tier are far more reliable when constrained to a
structured **edit format** than when relying on flawless native tool-calling.
Aider's architect/editor split plays to that: GLM 5.2 reasons, Kimi K2.6 emits
diffs in a format Aider validates and applies. If a diff is malformed Aider
re-asks automatically. (A broader autonomous agent — OpenCode/Goose — is the
optional layer below.)

## One-time setup (already done on this machine)

```bash
# uv (standalone, no system Python needed):
#   PowerShell:  irm https://astral.sh/uv/install.ps1 | iex
uv tool install --python 3.12 aider-chat      # -> ~/.local/bin/aider
```

The harness reads `OLLAMA_API_KEY` from the repo's gitignored `.env`. Nothing
else to configure — model choice and behavior live in `.aider.conf.yml`.

> Note: `.env` sets `OLLAMA_HOST=http://localhost:11434` for other tooling. The
> harness ignores that and targets cloud explicitly via `OLLAMA_OPENAI_BASE`
> (default `https://ollama.com/v1`), authenticated with `OLLAMA_API_KEY`.

## Use it

Run from the repo root so Aider discovers `.aider.conf.yml` + model metadata.

```powershell
# PowerShell (primary shell)
.\scripts\harness\aider-ollama.ps1                      # interactive
.\scripts\harness\aider-ollama.ps1 packages\duecare-llm-chat\...\harness.py
.\scripts\harness\aider-ollama.ps1 --message "add a unit test for grade_response_combined" path\to\test.py
```

```bash
# Git Bash
scripts/harness/aider-ollama.sh                         # interactive
scripts/harness/aider-ollama.sh --message "fix the off-by-one in chunk_text" path/to/file.py
```

Inside the interactive session, useful Aider commands: `/add <file>`,
`/drop <file>`, `/run <cmd>` (e.g. run tests and feed output back), `/undo`
(revert the last AI commit), `/diff`, `/ask <question>` (no-edit Q&A), `/architect`.

## Swap models

Edit `.aider.conf.yml` (`model:` = architect, `editor-model:` = editor). Any ID
from the plan works, e.g. swap the editor to the coding specialist:

```yaml
model: openai/glm-5.2
editor-model: openai/qwen3-coder:480b
```

Available on the plan (verified): `glm-5.2 glm-5.1 glm-5`, `kimi-k2.6 kimi-k2.5`
(avoid `kimi-k2.7-code` — it leaks reasoning traces into `content`),
`qwen3-coder:480b qwen3-coder-next`, `devstral-2:123b`, `deepseek-v4-pro`,
`gpt-oss:120b`, `minimax-m2.7 minimax-m3`, `gemma4:31b`.

When you add a model, give it a zero-cost entry in `.aider.model.metadata.json`
(so Aider doesn't warn about unknown context/cost) and a `diff` edit-format entry
in `.aider.model.settings.yml`.

## Troubleshooting

- **`AuthenticationError` / 401** — usually `OLLAMA_API_KEY` missing from `.env`. Note
  the repo `.env` also defines a real `OPENAI_API_KEY`; the launchers isolate Aider from
  it by handing over a private temp `--env-file` (Aider loads it last, so the Ollama key
  wins). If you run `aider` directly, do the same or it will send your OpenAI key to
  Ollama and 401.
- **Edits not applying / malformed diffs** — switch that model's `edit_format`
  to `whole` in `.aider.model.settings.yml` (more tokens, more robust).
- **Truncated responses on big files** — lower the working set (`/drop` files)
  or reduce `max_input_tokens` in `.aider.model.metadata.json`.
- **Slow first reply** — cloud cold-start on 480B-class models; subsequent calls
  are faster.

## Optional: autonomous agent layer

For hands-off multi-step loops (closer to the Claude Code experience), OpenCode
(`npm i -g opencode-ai`, Node is already installed here) can target the same
Ollama cloud endpoint. Aider stays the reliable workhorse for precise edits; the
agent layer is for broader autonomous tasks. See the harness setup notes when
that layer is wired.
