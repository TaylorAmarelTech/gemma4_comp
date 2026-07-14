# Project bible pickup pointer

> Auto-loaded by Claude Code at the project memory level.

When Claude Code, Codex, Fable 5-style agents, or similar tools start or resume
long-running improvement work, read the root `PROJECT_BIBLE.md`, then
`docs/codex/PROJECT_BIBLE.md`, after `CLAUDE.md` and before broad repo edits.
It records the current autonomous-engine pause state, candidate-dimension
review-gate safety boundary, global-protections offline-planning state, recent
hardening work, and validation commands.
If an older hidden handoff says to read `Plans.md`, treat that file only as a
compatibility bridge back to the project bible and the pause-safe loop
priorities.

Do not treat the project bible as permission to start the autonomous benchmark
engine, remove `reports/autonomous_engine.stop`, call Ollama, or promote candidate dimensions.
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
