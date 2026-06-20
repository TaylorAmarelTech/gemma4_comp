# Contributing to DueCare

> DueCare is built to be **adopted**, not just demo'd. Extensions are the
> whole point. If you're here because you need an on-device LLM safety
> evaluator for your own high-stakes domain, this file is for you.

For a full extensibility walkthrough with skeleton code for each plugin
kind, see [`docs/EXTENDING.md`](./docs/EXTENDING.md).

For peer reviewers + hackathon judges verifying the submission, see
[`docs/FOR_PEER_REVIEW.md`](./docs/FOR_PEER_REVIEW.md).

For documentation and GitHub-metadata edits, use
[`docs/DOCUMENTATION_GUIDE.md`](./docs/DOCUMENTATION_GUIDE.md). It records the
canonical six-lane order, active Kaggle surfaces, package count, and test-claim
policy.

## Stakeholders — edit a curator JSON without reading Python

The grader's "magic strings" — per-language signal lists, statute
allowlists, dimension multipliers, evaluator questions, etc. — live in
**12 versioned JSON files** with provenance metadata. Domain experts
(NGO partners, jurists, language experts, regulators) can submit
single-file PRs. See:

- **[`docs/contributing_curator_blocks.md`](./docs/contributing_curator_blocks.md)** — single-page guide with file-by-file conventions, required provenance fields, and a step-by-step PR workflow
- **[`docs/maintenance/`](./docs/maintenance/)** — per-component edit guides (personas, GREP rules, RAG corpus, tool functions, online search, [data sources & registries](./docs/maintenance/entity_sources.md))
- **`scripts/validate_curator_blocks.py`** — schema + cross-reference validator. Run before PR: `python scripts/validate_curator_blocks.py`

CI runs the validator on every PR (see `.github/workflows/ci.yml`).
Malformed curator blocks are blocked at merge.

## Quick paths

### "I want to add a new safety domain"

Zero code required. Create `configs/duecare/domains/your_domain/`
with six YAML/JSONL files (card, taxonomy, rubric, pii_spec,
seed_prompts, evidence). 30 minutes for a minimal pack. Full recipe in
[`docs/EXTENDING.md#add-a-new-safety-domain`](./docs/EXTENDING.md#add-a-new-safety-domain).

### "I want to add a new data source or registry (open knowledge & entity verification)"

Mostly zero code. DueCare's **propose-only** entity-verification layer checks the
recruiters, employers, and owners behind a case against official public records. A
**server-rendered table, JSON API, or downloadable CSV/XLSX/PDF** is onboarded as a
single YAML block in `configs/duecare/research_monitor/registry_specs.yaml` — no
per-source Python — and is then addressable via
`python scripts/acquisition_cascade.py --registry <id>`. Full recipe (the three
contribution levels, the spec shape, the propose-only boundary, FollowTheMoney /
open-knowledge interop, and the verification commands) in
[`docs/maintenance/entity_sources.md`](./docs/maintenance/entity_sources.md).

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

### "I want to add a new Kaggle kernel"

The active Kaggle submission path is intentionally narrow:
`01-duecare-exploration-workbench`, `02-live-demo`, and
`A-00-omni-experiment-workbench`. New kernels should be added only when they
serve a clear review or reproducibility need; archived A-01 through A-24
notebook-era surfaces are reference material, not the current path.

**1. Folder layout.** Place under `kaggle/<slot>-<short-purpose>/`
with these files:

```
kaggle/A-21-my-new-thing/
├── kernel.py                ← source-of-truth (pasted into Kaggle)
├── kernel-metadata.json     ← Kaggle CLI metadata
├── README.md                ← documentation (see below)
└── wheels/                  ← optional; per-kernel pip wheels
```

**2. Bundle output (if your kernel emits JSON).** Use the shared
helper instead of hand-rolling:

```python
from duecare.appendix_primitives import (
    BundleEnvelope, PerRow, make_run_id, write_v1_bundle,
)

run_id = make_run_id("a21", "my_purpose", GEMMA_VARIANT)
env = BundleEnvelope(
    kernel_id="a-21-my-new-thing",
    run_id=run_id,
    config={"model_variant": GEMMA_VARIANT},
    metadata={"started_at": iso_utc_now()},
    summary={"n_results": len(rows)},
    results=[PerRow(...) for r in rows],
)
paths = write_v1_bundle(env, Path("/kaggle/working"))
# paths = {results_json, run_jsonl, metadata_json, bundle_zip, manifest}
```

The full v1.0 envelope shape is in
[`docs/knowledge_module_schema.md`](docs/knowledge_module_schema.md).

**3. README sections (required).** Every kernel README must carry:

- `<!-- duecare:lane-label -->` HTML comment + a `> **Serves lanes:** ...`
  line (the public-surface audit's `kaggle_lane_labels` check
  enforces this).
- `<!-- duecare:judge-quick-path -->` HTML comment + a "Judge quick
  path" table with at minimum these rows:
  `| **Lede** | ... |`
  `| **What it does** | ... |`
  `| **Demo path** | ... |`
  `| **Audience** | ... |`
  `| **Inputs** | ... |`           *(session 2026-05-12 standard)*
  `| **Gemma 4 features** | ... |` *(session 2026-05-12 standard)*
  `| **Outputs** | ... |`
  `| **Cross-links** | ... |`

  See `kaggle/01-duecare-exploration-workbench/README.md`,
  `kaggle/02-live-demo/README.md`, or
  `kaggle/A-00-omni-experiment-workbench/README.md` for active examples.

- `## What it does / ## Pipeline / ## Inputs / ## Outputs /
  ## Where this slot lives` -- canonical Markdown headers for the
  longer-form documentation. Pattern in
  `kaggle/A-19-multilingual-demo/README.md`.

**4. Audit + validation.** Before opening a PR:

```bash
.venv/Scripts/python.exe scripts/validate_public_surface.py
# Expects the public-surface audit to finish with 0 findings.
```

Any new `kernel.py` is automatically swept by the
`bundle_envelope_v1` check for schema-version drift, missing
`summary`, and legacy results-array names. To opt out of a flag
that's a non-envelope use of a flagged key, add an
`audit-allow:drift` inline marker on the source line with a
one-sentence justification:

```python
"aggregate": _phase_summary  # audit-allow:drift -- phase-result key, not v1.0 envelope
```

**5. Index registration.** Add a row to
[`kaggle/_INDEX.md`](kaggle/_INDEX.md) so the active roster stays current.

**6. Optional: register the kernel in
[`docs/gemma4_feature_showcase.md`](docs/gemma4_feature_showcase.md)**
if it exercises a specific Gemma 4 capability (function calling,
multimodal, multilingual, on-device, long-context, etc.) so the
30-pt Technical Depth mapping stays current.

**7. Telemetry.** Wire `dc_log` from `duecare.chat._dc_log` at
kernel start so the kernel emits structured events. Pattern:

```python
try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-21-my-new-thing")
    dc_log("kernel.start", "my new kernel loading")
except Exception:
    def dc_log(*a, **kw):  # type: ignore[no-redef]
        return None
```

For the slot-numbering convention and the experiment-ladder
relationships (which kernel produces inputs for which downstream
kernel), see
[`docs/current_kaggle_notebook_state.md`](docs/current_kaggle_notebook_state.md).

## Development setup

```bash
# Clone
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp

# Install in editable mode for the workspace packages
pip install -e packages/duecare-llm

# Optional: heavier extras for actually running models
pip install -e "packages/duecare-llm-models[transformers,unsloth,llama-cpp]"

# Run the package test suite, or collect first if you only need a fast check
python -m pytest packages --collect-only -q
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
# Full package suite
python -m pytest packages -v

# Fast package collection check
python -m pytest packages --collect-only -q

# Single package
python -m pytest packages/duecare-llm-core -v

# Single module
python -m pytest packages/duecare-llm-core/src/duecare/core/enums -v
```

CI runs on every PR via `.github/workflows/`. Python 3.11 and 3.12 are
both tested.

For public-facing docs, also run:

```bash
python scripts/validate_public_surface.py
```

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
