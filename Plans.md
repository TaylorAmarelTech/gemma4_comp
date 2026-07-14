# Continuation Plans

This file is a compatibility bridge for older Claude Code handoffs that say to
read `Plans.md`. It is not the canonical planning source.

For current long-running work, read:

1. [`AGENTS.md`](AGENTS.md)
2. [`CLAUDE.md`](CLAUDE.md)
3. [`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)
4. [`docs/codex/PROJECT_BIBLE.md`](docs/codex/PROJECT_BIBLE.md)

Current safe improvement loops:

- Keep handoff docs and validators synchronized with the actual engine state (including paused engine state)
  and validation evidence.
- Strengthen privacy-safe aggregate validators between generated research
  artifacts and active model, rubric, or leaderboard behavior.
- Keep global-protections and developing-country worker-protection work
  offline, propose-only, and blocked from public scoring until source and
  curator gates pass.
- Keep v2 rubric and h2 harness evidence isolated from the active v1/h1
  leaderboard.

This file is not permission to remove `reports/autonomous_engine.stop`, start
the autonomous judging engine, call Ollama, or promote candidate dimensions.
Those actions still require Taylor's explicit current instruction plus the
normal preflight and review gates.
