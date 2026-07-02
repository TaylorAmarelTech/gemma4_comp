# Project Bible

This root pointer exists so Claude Code, Codex, Fable 5-style agents, and other
repo-root pickup tools can find the current long-loop handoff quickly.

Canonical pickup file:

- [`docs/codex/PROJECT_BIBLE.md`](docs/codex/PROJECT_BIBLE.md)

Read order for continuation sessions:

1. [`AGENTS.md`](AGENTS.md)
2. [`CLAUDE.md`](CLAUDE.md)
3. [`.claude/rules/05_project_bible_pickup.md`](.claude/rules/05_project_bible_pickup.md)
4. [`docs/codex/PROJECT_BIBLE.md`](docs/codex/PROJECT_BIBLE.md)

This pointer is not permission to start the autonomous judging engine, remove
`reports/autonomous_engine.stop`, call Ollama, or promote candidate dimensions.
Those actions still require Taylor's explicit current instruction plus the
normal preflight and review gates.
