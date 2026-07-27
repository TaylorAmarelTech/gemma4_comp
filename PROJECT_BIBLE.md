# Project Bible

This root pointer exists so Claude Code, Codex, Fable 5-style agents, and other
repo-root pickup tools can find the current long-loop handoff quickly.
Older hidden Claude handoffs may mention `Plans.md`; that file is a
compatibility bridge back to this pickup path, not a separate planning source.

Canonical pickup file:

- [`docs/codex/PROJECT_BIBLE.md`](docs/codex/PROJECT_BIBLE.md)

Canonical publication stopping point, release boundary, and prioritized
model/data backlog:

- [`docs/PUBLICATION_READINESS.md`](docs/PUBLICATION_READINESS.md)
- [`docs/DEFERRED_WORK.md`](docs/DEFERRED_WORK.md)

Current human-maintainer pickup and dated closeout plan:

- [`docs/MAINTAINER_HANDOFF.md`](docs/MAINTAINER_HANDOFF.md)
- [`docs/PROJECT_TRANSITION_PLAN.md`](docs/PROJECT_TRANSITION_PLAN.md)

Read order for continuation sessions:

1. [`AGENTS.md`](AGENTS.md)
2. [`CLAUDE.md`](CLAUDE.md)
3. [`.claude/rules/05_project_bible_pickup.md`](.claude/rules/05_project_bible_pickup.md)
4. [`docs/MAINTAINER_HANDOFF.md`](docs/MAINTAINER_HANDOFF.md)
5. [`docs/PROJECT_TRANSITION_PLAN.md`](docs/PROJECT_TRANSITION_PLAN.md)
6. [`docs/PUBLICATION_READINESS.md`](docs/PUBLICATION_READINESS.md)
7. [`docs/DEFERRED_WORK.md`](docs/DEFERRED_WORK.md)
8. [`docs/codex/PROJECT_BIBLE.md`](docs/codex/PROJECT_BIBLE.md)

This pointer is not permission to start the autonomous judging engine, remove
`reports/autonomous_engine.stop`, call Ollama, or promote candidate dimensions.
Those actions still require Taylor's explicit current instruction plus the
normal preflight and review gates.
