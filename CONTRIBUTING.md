# Contributing to DueCare

> DueCare is built to be **adopted**, not just demo'd. Extensions are the
> whole point. If you're here because you need an on-device LLM safety
> evaluator for your own high-stakes domain, this file is for you.

For a full extensibility walkthrough with skeleton code for each plugin
kind, see [`docs/EXTENDING.md`](./docs/EXTENDING.md).

For judges verifying the submission, see
[`docs/FOR_JUDGES.md`](./docs/FOR_JUDGES.md).

## Quick paths

### "I want to add a new safety domain"

Zero code required. Create `configs/duecare/domains/your_domain/`
with six YAML/JSONL files (card, taxonomy, rubric, pii_spec,
seed_prompts, evidence). 30 minutes for a minimal pack. Full recipe in
[`docs/EXTENDING.md#add-a-new-safety-domain`](./docs/EXTENDING.md#add-a-new-safety-domain).

### "I want to plug in a new model"

Implement one Protocol (`Model`), register it, add one YAML row. 20
minutes for an HTTP-API provider, 2 hours for a local-inference
adapter. Reference: the 8 existing adapters in
`packages/duecare-llm-models/`.

### "I want to add a new capability test"

Implement the `Task` Protocol in its own subfolder of
`packages/duecare-llm-tasks/src/duecare/tasks/`. Reference the 9
existing tasks — they're all under 200 LOC.

### "I want to add a new agent"

Agents live in `packages/duecare-llm-agents/src/duecare/agents/`.
Implement the `Agent` Protocol, register it, optionally expose as a
tool to the Gemma 4 Coordinator. The existing 12 agents are the
templates.

## Development setup

```bash
# Clone
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp

# Install in editable mode (all 8 packages at once via the meta)
pip install -e packages/duecare-llm

# Optional: heavier extras for actually running models
pip install -e "packages/duecare-llm-models[transformers,unsloth,llama-cpp]"

# Run the test suite (should see 194 passed)
python -m pytest packages -v

# Run the demo
python -m uvicorn src.demo.app:app --port 8080
```

## Project conventions

- **Python 3.11+** (3.12 is the primary target)
- **Pydantic v2** for all data models — never dataclasses when a
  Pydantic model would be right
- **`typing.Protocol`** for cross-layer interfaces — no forced
  inheritance hierarchies
- **Type hints on every public function** — `ruff` + `mypy` enforce
- **`from __future__ import annotations`** at the top of every module
- **`pathlib.Path`** for every file path, never bare strings
- **Folder-per-module** — every module is a folder, not a file

See [`.claude/rules/20_code_style.md`](./.claude/rules/20_code_style.md)
for the full style guide.

## Testing

Every module has a `tests/` folder. Minimum bar: at least one real
test per module that exercises the public surface.

```bash
# Full suite (194 tests across 8 packages)
python -m pytest packages -v

# Single package
python -m pytest packages/duecare-llm-core -v

# Single module
python -m pytest packages/duecare-llm-core/src/duecare/core/enums -v
```

CI runs on every PR via `.github/workflows/`. Python 3.11 and 3.12 are
both tested.

## The safety gate

Every contribution must preserve three invariants:

1. **No raw PII in git, logs, or published artifacts.** The Anonymizer
   agent is a hard gate. See
   [`.claude/rules/10_safety_gate.md`](./.claude/rules/10_safety_gate.md).
2. **On-device operation remains a first-class mode.** Cloud calls are
   opt-in and must be documented.
3. **"Real, not faked for demo."** Every claim in the writeup must be
   reproducible from `(git_sha, dataset_version)`. Stubs are allowed
   during development but must be clearly labeled and not count toward
   headline metrics.

## Reporting issues

- **Safety issue** (a model response that could harm someone):
  open a GitHub issue labeled `safety` immediately. Do not post the
  problematic prompt/response publicly; link a gist or email first.
- **Bug**: reproducible test case + expected vs actual behavior.
- **Feature request**: concrete use case + what existing plugin point
  should be extended (or why a new one is needed).

## Code of conduct

This project deals with human trafficking — people who have been
harmed, people at risk, people fighting to protect them. Treat every
interaction with the gravity the subject deserves. Be kind to
contributors new to the codebase. Be rigorous about safety claims.
Be patient with reviewers who cannot approve a change until it is
verifiably correct.

## License

MIT. Contributions are accepted under the same license.
