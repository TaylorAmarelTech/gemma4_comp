# Developer review loop — a multi-model advisory board for DueCare

A standing loop where **many models review the project (and each other), from many lenses**, so
DueCare gets continuous, multi-perspective critique without a single model's blind spots. It is
**propose-only**: the board surfaces suggestions; a human (or Claude Code) triages them into real
work. Nothing is auto-changed, auto-archived, or auto-merged.

## Why

One model reviewing its own work has blind spots; one lens (e.g. "is the code clean?") misses
the others ("would a YC partner fund it? would a judge score it? what's the unit economics?").
The board forces **breadth × diversity**: each persona is a different lens, run on a different
model, and the models cross-review each other.

## Architecture (`scripts/dev_review_loop.py`)

```
gather_digest()          bounded project digest (README, FOR_JUDGES, writeup, latest report, CLAUDE.md)
      │
      ▼
PERSONA PANEL            each lens on a different model, structured JSON critique
  competition_judge  →  gemma4:31b      (Gemma rubric: Impact/Video/Tech, real-not-faked)
  yc_partner         →  glm-5.2         (PMF, market, why-now, moat, founder-fit)
  ceo                →  glm-5.2         (vision, narrative, the one next bet)
  cto                →  deepseek-v3.2   (architecture, tech debt, biggest risk)
  cfo                →  kimi-k2.7-code  (cost, unit economics, runway)
  coo                →  qwen3-coder     (ops, NGO/regulator GTM, pilot blockers)
  peer_engineer      →  deepseek-v3.2   (code quality, tests, worst smell)
      │
      ▼
CROSS-REVIEW             each persona reacts to another's critique (agree / dispute / missed)
      │
      ▼
synthesize()             rank improvements by CROSS-LENS demand (how many personas raise it)
      │
      ▼
propose-only stage       reports/dev_review/latest.json  (gitignored)  →  human / Claude Code triage
```

Each persona returns `{strengths, weaknesses, top_improvements:[{title, why, effort}],
pmf_or_rubric_score, verdict}`. The synthesis ranks by how many lenses independently raise the
same improvement — cross-lens consensus is the strongest signal.

Run: `OLLAMA_API_KEY=... python scripts/dev_review_loop.py` (or `--personas yc_partner,cto`,
`--no-cross-review`). Reuses the `llm_generate` engine (reasoning-aware caller + propose-only
staging). The model call is injectable, so the board is unit-tested offline.

## The boundary (real-not-faked)

- The board **only proposes**. No file edited, no doc archived, nothing merged.
- Suggestions are drafts; a human or Claude Code decides what becomes a commit.
- This mirrors the rest of DueCare's propose-only discipline (see
  [autonomous_improvement_loop.md](autonomous_improvement_loop.md)): models draft, humans promote.

## Status

- **Built**: panel + cross-review + cross-lens synthesis + propose-only staging; 5 offline tests.
- **Live-validated**: GLM-5.2 as YC partner returned a blunt PMF 3/10 with concrete pivot
  suggestions; **Kimi 2.7** (`kimi-k2.7-code`) as CFO returned sharp unit-economics advice
  ("narrow to one paid SKU", "publish a runway model", "consolidate 17 packages to 2-3"). DeepSeek
  / Qwen / Gemma work as reviewers.

### Reasoning-model note (Kimi / GLM)

These are thinking models: the answer is in `message.content`, the chain-of-thought in
`message.reasoning`, and a **low token budget makes `content` come back empty**. Two rules:

- Use a high per-call budget (the board uses `max_tokens=3500`). At 2200 Kimi returned empty; at
  3500 it answers cleanly.
- Of the Kimi 2.7 tags on Ollama-cloud, only **`kimi-k2.7-code`** is reachable (`kimi-k2.7` 404s,
  `kimi-k2.6` returns empty). It is code-specialised but reviews fine at the right budget.

## Roadmap

1. **Adopt litellm as the model-calling layer** (scout verdict 2026-06-21, MIT, Python). It is the
   only framework with a purpose-built Moonshot/Kimi transform + a `zai/` GLM provider +
   normalized `reasoning_content`, and it wraps Ollama-cloud / OpenRouter. Swapping the raw call in
   `llm_generate.ollama_chat` for `litellm.completion(...)` makes Kimi/GLM calling robust without
   the per-tag fiddling above. Keep `grade_response_universal` and the propose-only structure.
   `inspect_ai` is the documented graduation path if the loop grows.
2. **Claude Code on the board.** Add Claude (via the Agent tool / a Workflow) as a reviewer lens
   AND as the **triager**: Claude reads `reports/dev_review/latest.json`, dedupes against open
   work, and turns the highest cross-lens items into concrete commits (still human-gated to push).
3. **Legacy-doc archival pass.** A pass that scans `docs/` + the repo for stale/superseded
   documents and proposes an archive list (propose-only) — moved only on human confirmation, into
   `_archive/`.
4. **Continuous cadence.** Schedule a weekly board run (CronCreate / the autonomous loop) so PMF +
   code + rubric critique is ongoing, and track the PMF/rubric scores over time.
5. **Close the loop.** Board suggestions feed the same triage surface as outreach/knowledge
   proposals, so "review → propose → human-promote → commit" is one consistent flywheel.
