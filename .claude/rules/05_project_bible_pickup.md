# Project bible pickup pointer

> Auto-loaded by Claude Code at the project memory level.

When Claude Code, Codex, Fable 5-style agents, or similar tools start or resume
work, read root `AGENTS.md`, `docs/CLAUDE_CODE_HANDOFF.md`, and root `PROJECT_BIBLE.md`
before broad edits. Use `docs/codex/PROJECT_BIBLE.md` only
when deeper benchmark, dataset, or autonomous-engine history is needed.
If an older hidden handoff says to read `Plans.md`, treat that file only as a
compatibility bridge back to the project bible and the pause-safe loop
priorities.

Saved `.claude/state/` files and ignored reports are historical evidence only.
Re-establish live Git, process, scheduler, provider, deployment, and validator
truth before claiming completion.

Do not treat any handoff as permission to start the autonomous benchmark
engine, remove `reports/autonomous_engine.stop`, call Ollama, change Render or
DNS, publish artifacts, or promote candidate dimensions.
Those actions still require Taylor's explicit current instruction and the normal
preflight/review gates.

The active board loop remains `active_loop_scope.rubric_version` `v1` and
`active_loop_scope.harness_version` `h1`. The `--rubric-version v2` rubric and
`--harness-version h2` refusal-collapse fix are opt-in research surfaces only;
do not mix v2/h2 rows into the active leaderboard or autonomous loop without a
fresh explicit instruction and the normal gates.

The benign-control intent split is also opt-in research evidence:
`--benign-control configs/duecare/benchmarks/benign_control_prompts.json`
feeds a separate over-refusal block for legitimate worker questions. It is
never merged into the active v1/h1 under-refusal lift headline, public
leaderboard, or autonomous loop.
