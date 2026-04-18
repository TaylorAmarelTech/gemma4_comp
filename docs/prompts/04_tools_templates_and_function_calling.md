# Prompt 04. Tools, templates, and function calling (band 600 to 690)

> Paste everything below the horizontal rule into Copilot. Copilot has
> filesystem access to `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.
> This prompt covers native function-calling evaluation, tool
> generation and maintenance, template libraries, template generation
> and maintenance, and adversarial tool and template abuse. Read
> `docs/prompts/_shared_discipline.md` first.

---

## Scope

Cover band 600 to 690 only.

| Band | Section | What this prompt owns |
|---|---|---|
| 600 to 690 | Tools and templates | Native function calling in Gemma 4 (Coordinator agent uses it), tool call evaluation, tool generation, tool maintenance, prompt template evaluation, template generation, template maintenance, adversarial tool and template abuse. Multimodal variants where applicable. |

Tool-enabled evaluation of a full corpus (how well does Gemma 4 use
tools across 10K prompts) stays in this band if the notebook fits
the Principle C size caps. If it does not fit, split and route one
half to band 400.

## Why this band matters

Native function calling is explicitly named in the hackathon rules
as one of Gemma 4's load-bearing unique features. The Coordinator
agent uses it to orchestrate the swarm. Tool call quality is a
first-class rubric input, not an aside. See
`.claude/rules/00_overarching_goals.md` and the
load-bearing-features requirement.

## Coverage targets (must each be satisfied inside band 600 to 690)

1. **Tool call eval, Gemma 4 alone.** Define a small tool schema
   (for example, `lookup_ilo_convention`, `lookup_corridor`,
   `report_to_ngo`). Run Gemma 4 and score: invocation correctness,
   argument fidelity, required-field coverage, argument-type
   discipline, refusal-vs-call calibration. Cite existing
   function-calling surface `src/demo/function_calling.py`.
2. **Tool call eval vs other models.** Same tools, same prompts,
   across adapters in `packages/duecare-llm-models/`. Flag adapters
   that do not support native function calling; fall back to
   JSON-mode or textual tool emulation with a clear label.
3. **Tool call adversarial.** Jailbreaks via tool call abuse:
   synthesized fake tools, argument injection, tool-name aliasing,
   refusal bypass through tool framing. Responsible-disclosure
   metadata attached per
   `.claude/rules/10_safety_gate.md`.
4. **Tool generation.** Generate new tools from domain needs using
   Gemma 4 itself as the tool designer. Evaluate generated tools
   against a schema (valid JSON schema, unique name, required args
   present, side-effect class labeled). Store accepted tools under
   `configs/duecare/tools/` (propose this path; verify if it
   exists, otherwise mark gap).
5. **Tool maintenance.** Detect schema drift in tools over time
   (for example, third-party API adds a new required arg). Produce
   a suggested migration diff. Regression-test generated tools
   against a fixture corpus.
6. **Template library evaluation.** A template is a reusable
   prompt scaffold with slots. Evaluate Gemma 4 and other models on
   a shared template library for stability (same input, same
   output after N reruns), adversarial resilience (templates that
   resist injection), and fidelity (template produces the intended
   structured output).
7. **Template generation.** Generate new templates from domain
   need. Evaluate with the same battery as 6.
8. **Template maintenance.** Detect template decay (for example,
   the underlying model updates and the template no longer
   produces structured output). Propose migration.
9. **Multimodal tool and template evaluation.** Voice and image
   siblings where appropriate. Inline vs split per notebook;
   defend in one sentence.
10. **Section summary at 690.** Reads cached outputs, produces the
    headline chart (tool-call success rate by model, template
    stability by template, adversarial success rate) and the
    paragraph for the writeup.

## Source of truth for kernel state

`docs/current_kaggle_notebook_state.md` is authoritative. Use the
Kaggle id from that file when referring to a kernel. Legacy
directory-to-code-file aliases for kernels placed in band 600 to
690 must be resolved by the renumber pass (for example,
`duecare_08_fc_multimodal` contains
`08_function_calling_multimodal.ipynb`,
`duecare_09_llm_judge` contains `09_llm_judge_grading.ipynb`,
`duecare_10_conversations` contains
`10_conversation_testing.ipynb`,
`duecare_13_rubric_eval` contains `13_rubric_evaluation.ipynb`).
Do not touch `forge_llm_core_demo.ipynb`; that orphan is owned by
prompt 01.

## Current kernels relevant to this band

- `duecare_08_fc_multimodal` is the current seed for tool-call
  evaluation. It also carries multimodal coverage. Decide band
  610 or 615 placement and whether to split.
- `duecare_12_prompt_factory` contributes to template generation
  patterns; may partially move from band 300 into this band for
  the template sub-track, or stay in band 300 with a clear
  cross-link. Decide.
- `duecare_03_agent_swarm_deep_dive` uses function calling via the
  Coordinator but sits in band 200 or 400; cite and link, do not
  move.
- `src/demo/function_calling.py` is the library surface. Notebooks
  import from it; no notebook in this band defines its own tool
  schema inline.

For every current kernel decision, cite `path:line`.

## Deliverable, produce `docs/review/600-690_tools_templates.md`

Sections 0 through 5 in order. Cite `path:line` for every factual
claim. Maximum 2,500 words.

### Section 0. Band scope and grounding (at most 200 words)

State the band's purpose in plain English. Explain the distinction
between a tool (a callable with a schema, executed by the runtime)
and a template (a reusable prompt scaffold with slots). Confirm
the packages vs notebooks boundary: tool schemas live in
`configs/duecare/tools/` (or a new directory, flagged if absent),
tool execution lives in `duecare.tasks.tool_use`, function calling
adapter glue lives in `duecare.models.*` adapters and
`src/demo/function_calling.py`. Notebooks orchestrate, never
re-implement.

### Section 1. Per-notebook audit of kernels placed in band 600 to 690

For each kernel, fill the Principle B header checklist plus:

- Tool schema used (path to YAML or JSON or code).
- Which adapters support native function calling vs fallback.
- Grading dimensions for tool calls: invocation, argument fidelity,
  required fields, type discipline, refusal calibration.
- For templates: stability metric, injection resistance metric,
  structured-output fidelity metric.
- For adversarial: threat model, disclosure metadata.

Compact table, one row per kernel.

### Section 2. Target section map for band 600 to 690

- Scope in one sentence.
- Rubric dimensions advanced (note the explicit Tech rubric tie to
  load-bearing Gemma 4 features).
- Summary notebook narrative goal.
- Insertion slots currently free.
- Sub-bands proposal, for example: "610 to 630 tool call eval
  (self, vs others, adversarial), 640 to 650 tool generation and
  maintenance, 660 to 670 template eval, generation, maintenance,
  680 multimodal siblings, 690 summary".

### Section 3. Full notebook table for the band

Columns as in shared discipline. Every coverage target 1 through
10 must appear as a row. Every current kernel placed in the band
must be mapped, moved, or marked delete with reason.

Append:

- `git mv` block.
- `kernel-metadata.json` id edits.
- Build-script names for every gap row.
- If `configs/duecare/tools/` does not exist, include a creation
  ticket plus the minimal YAML schema (fields: `name`,
  `description`, `parameters` as JSON schema, `side_effect_class`
  one of `read`, `write`, `external`).

### Section 4. Tool and template catalog

A table listing every tool and template the band will evaluate.
Columns: name, kind (tool or template), schema path, required
fields, side-effect class (for tools), modality coverage, which
notebook evaluates it, which notebook generates or maintains it.
A minimal catalog of five tools and five templates is acceptable
at this stage; larger catalogs defer to post-submission.

### Section 5. Ticket list for this band

Flat, one per line, at most 120 characters, ordered P0 to P2.

```
[P0][S][Tech][Sep-of-Concerns] Extract duecare_08 inline tool schemas to configs/duecare/tools/
[P0][M][Tech][Feature] Build duecare_610_tool_call_eval_gemma4 using duecare.tasks.tool_use
[P0][M][Video][Feature] Build duecare_620_tool_call_eval_vs_others with fallback labels
[P0][L][Impact][Adversarial] Build duecare_630_tool_call_adversarial with disclosure metadata
[P0][M][Tech][Best-Practices] Add schema-drift detection for generated tools
[P0][M][Video][Summary] Build duecare_690_summary with tool-success chart
...
```

Include tickets for:

- Every notebook that currently defines tool schemas inline.
- Every adapter missing a function-calling capability flag in
  `duecare.core.enums.Capability`.
- The `configs/duecare/tools/` directory creation if absent.
- The template library directory creation if absent (propose
  `configs/duecare/templates/`).
- Every missing responsible-disclosure block on adversarial
  notebooks.
- The 690 summary notebook.

## Constraints specific to this prompt

- Do not design general adversarial notebooks here; only tool and
  template abuse. General adversarial goes to band 500.
- Do not design data-pipeline or demo notebooks here.
- Every tool schema is stored under `configs/duecare/tools/` or a
  successor path. No inline tool schemas in notebook cells.
- Every template is stored under `configs/duecare/templates/` or
  a successor path.
- Every notebook that tests native function calling explicitly
  names it a load-bearing Gemma 4 feature in the header and links
  to `.claude/rules/00_overarching_goals.md`.
- Every generated tool and generated template carries provenance
  back to the notebook and git SHA that produced it.

## Read before writing, in order, stop when grounded

1. `docs/current_kaggle_notebook_state.md`.
2. `docs/prompts/_shared_discipline.md`.
3. `.claude/rules/00_overarching_goals.md` (load-bearing features).
3. `src/demo/function_calling.py`.
4. `src/demo/multimodal.py`.
5. `packages/duecare-llm-tasks/src/duecare/tasks/tool_use/` (full
   folder).
6. `packages/duecare-llm-models/src/duecare/models/` for
   function-calling capability flags per adapter.
7. `packages/duecare-llm-core/src/duecare/core/enums/` for the
   Capability enum.
8. `packages/duecare-llm-agents/src/duecare/agents/coordinator/`.
9. `kaggle/kernels/duecare_08_fc_multimodal/08_function_calling_multimodal.ipynb`.
10. `kaggle/kernels/duecare_12_prompt_factory/12_prompt_factory.ipynb`.
11. `kaggle/kernels/duecare_03_agent_swarm_deep_dive/`.
12. `configs/duecare/` (entire) to see whether `tools/` and
    `templates/` directories already exist.

## Output

Single file at `docs/review/600-690_tools_templates.md`. Sections
0 through 5 in order.
