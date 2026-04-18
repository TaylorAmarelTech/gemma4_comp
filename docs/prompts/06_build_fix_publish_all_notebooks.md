# Prompt 06. Build, fix, and publish ALL notebooks to Kaggle

> This is the execution prompt. Previous prompts (01 through 05) were
> review and design prompts. This prompt takes their outputs and turns
> them into working code, fixed notebooks, and successful Kaggle
> publishes. Paste everything below the horizontal rule into Copilot
> with Max mode enabled. Copilot has filesystem access to
> `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.
>
> Read `docs/prompts/_shared_discipline.md` first for voice, engineering
> discipline, and curriculum principles.

---

## Who you are

You are an execution engineer. You do not review, plan, or discuss.
You read the review outputs in `docs/review/`, then build, fix, rename,
and publish notebooks until every notebook passes validation and is
live on Kaggle. If the review outputs do not exist yet, fall back to
the authoritative inventory and curriculum principles and execute
anyway.

Voice: terse, no filler, no em dashes, no emojis. When you make a
change, state the file, the change, and why in one sentence. Then move
to the next change.

## Ground truth files (read these first, in this order)

1. `docs/current_kaggle_notebook_state.md` (authoritative kernel
   inventory: 28 tracked, 16 legacy aliases, 1 orphan).
2. `docs/prompts/_shared_discipline.md` (principles A through J,
   engineering discipline, anti-slop rules).
3. `docs/review/100-290_exploration_and_basic_eval.md` if it exists.
4. `docs/review/300-390_data_pipeline.md` if it exists.
5. `docs/review/400-590_advanced_eval_and_adversarial.md` if it exists.
6. `docs/review/600-690_tools_templates.md` if it exists.
7. `docs/review/800-990_demo_and_architecture.md` if it exists.
8. `scripts/build_notebook_00.py` (811 lines, the canonical build
   script pattern: `md()` and `code()` cell helpers, `NB_METADATA`
   dict, `CELLS` list, write to `notebooks/` and
   `kaggle/kernels/<slug>/`).
9. `scripts/publish_kaggle.py` (the publish orchestrator:
   `push-notebooks` discovers all `kaggle/kernels/*/kernel-metadata.json`
   and pushes via `kaggle kernels push`).
10. `Makefile` targets: `kaggle-push`, `kaggle-status`, `kaggle-dry-run`,
    `notebooks`, `build`.

## What you must do (in order)

Execute these phases sequentially. Do not skip ahead. After each
phase, run the stated validation command. If validation fails, fix
the failure before moving to the next phase.

### Phase 1. Fix every legacy alias

The 16 legacy directory-to-code-file aliases in
`docs/current_kaggle_notebook_state.md` mean the directory slug and
the notebook filename inside it diverge. For each of the 16:

a. Rename the directory to match the code file's base name, prefixed
   with `duecare_`. For example, `duecare_06_adversarial/` containing
   `06_adversarial_resistance.ipynb` becomes
   `duecare_06_adversarial_resistance/06_adversarial_resistance.ipynb`.

b. Update the `kernel-metadata.json` inside the renamed directory:
   - `id` field: update the slug portion after `taylorsamarel/` to
     match the new directory name.
   - `code_file` field: confirm it still points to the correct
     `.ipynb` filename.
   - `title` field: update to match the new human-readable name.

c. Update the `notebooks/` local mirror: ensure the filename matches.

d. Update any `scripts/build_notebook_*.py` that writes to the old
   directory path.

Do NOT change the Kaggle kernel id prefix (`taylorsamarel/`). The
slug portion after the slash is the only part that changes.

Validation: `python scripts/publish_kaggle.py --dry-run push-notebooks`
must discover all 28 kernels with no errors.

### Phase 2. Renumber into the curriculum scheme

Apply the three-digit zero-padded curriculum IDs from the review
outputs (or from the curriculum spine in
`docs/copilot_review_prompt.md` if review outputs do not exist).
For every notebook:

a. Rename the directory under `kaggle/kernels/` to
   `duecare_NNN_<snake_case_purpose>/`.

b. Rename the `.ipynb` file inside to
   `NNN_<snake_case_purpose>.ipynb`.

c. Update `kernel-metadata.json`:
   - `id`: `taylorsamarel/duecare-NNN-<kebab-case-purpose>` (Kaggle
     ids use hyphens, not underscores).
   - `code_file`: `NNN_<snake_case_purpose>.ipynb`.
   - `title`: `NNN: <Human Readable Title>`.

d. Update the `notebooks/` local mirror filename.

e. Rename the matching `scripts/build_notebook_*.py` to
   `scripts/build_notebook_NNN_<slug>.py`.

f. Inside each renamed build script, update the output path
   constants that reference the old directory and filename.

Numbering rules:
- Section boundaries on round hundreds (000, 100, 200, 300, 400,
  500, 600, 700, 800, 900).
- Step of 10 between siblings.
- Summary notebooks at the highest tens slot in each section
  (090, 190, 290, 390, 490, 590, 690, 790, 890, 990).
- `duecare_index` becomes `duecare_000_index`.
- `duecare_phase2_comparison` and `duecare_phase3_finetune` merge
  into the numeric sequence (not parallel naming).
- `forge_llm_core_demo.ipynb` is either deleted, promoted into
  the curriculum with a new ID, or marked local-only, per the
  decision in `docs/review/100-290_exploration_and_basic_eval.md`
  or prompt 01's decision gate.

Validation: `python scripts/publish_kaggle.py --dry-run push-notebooks`
must discover all renamed kernels with no errors.

### Phase 3. Insert the Principle B header block into every notebook

Every notebook must start with a markdown cell containing:

```markdown
# NNN: <Title>

| Field | Value |
|---|---|
| Question | <one sentence> |
| Inputs | <paths and Kaggle slugs> |
| Outputs | <paths and schemas> |
| Decision impact | <downstream notebook IDs for each plausible answer> |
| Dependencies | <upstream notebook IDs> |
| Kind | <build / eval / summary / demo / meta> |
| Modality | <text / voice / image / multimodal> |
| Runtime | <expected wall time on free Kaggle kernel> |
| Provenance | `(git_sha, dataset_version, run_id)` |
```

For notebooks built by a `scripts/build_notebook_NNN_*.py`, edit
the build script's first `md()` cell. For notebooks that are raw
`.ipynb` files without a build script, edit the `.ipynb` JSON
directly (update the first cell's `source` array).

Do not invent answers for fields you cannot verify. Write
"[TO BE FILLED]" for any field that requires running the notebook
to determine (for example, Runtime). Do not leave Question or Kind
as "[TO BE FILLED]"; those are determinable from the notebook's
existing content.

Validation: Run a quick script or grep to confirm every notebook's
first cell contains the string "| Question |" and "| Kind |".

### Phase 4. Fix broken imports and pin versions

Scan every notebook (build script source or raw `.ipynb` JSON) for:

a. `pip install` cells. Every install must pin a version:
   `pip install duecare-llm-core==0.1.0`, not
   `pip install duecare-llm-core`. If the current version is 0.1.0
   (check `packages/duecare-llm-core/pyproject.toml`), pin to that.

b. `from duecare.* import` lines. Verify each imported symbol
   actually exists in the corresponding package's `__init__.py` or
   module. For any import that references a symbol that does not
   exist, either:
   - Add the missing symbol to the package (if it should exist), or
   - Remove the import from the notebook (if it was speculative).

c. Kaggle dataset references. Every notebook that loads from a
   Kaggle dataset must reference the dataset by its full slug
   (for example, `taylorsamarel/duecare-trafficking-prompts`), not
   a relative path.

d. Kaggle model references. Every notebook that loads Gemma 4 via
   `kagglehub` must reference the model by its official slug.

Validation: `make build` (builds all 8 wheels) followed by
`make test` (runs pytest across all packages). Both must pass.

### Phase 5. Build missing notebooks

For every gap identified in the review outputs (or in the curriculum
spine where no current kernel maps), create a build script at
`scripts/build_notebook_NNN_<slug>.py` following the pattern in
`scripts/build_notebook_00.py`:

- Define `md(s)` and `code(s)` helpers.
- Define `NB_METADATA` with appropriate Kaggle accelerator (none
  for free-tier, `nvidiaTeslaT4` for GPU notebooks).
- Define `CELLS` as a list.
- Write to both `notebooks/NNN_<slug>.ipynb` and
  `kaggle/kernels/duecare_NNN_<slug>/NNN_<slug>.ipynb`.
- Create the `kernel-metadata.json` alongside the notebook.

Priority order for gap-builds:

1. Section summary notebooks (090, 190, 290, 390, 490, 590, 690,
   790, 890, 990) because they are judge-facing rollup points.
2. The glossary notebook (005 or wherever the review placed it)
   because it is the orientation entry point for judges.
3. Any notebook that a downstream notebook depends on (check the
   "Dependencies" field).
4. Everything else, ordered by rubric weight: Impact notebooks
   first, then Video, then Tech.

Each new notebook must satisfy Principle C: at most 40 cells, at
most 300 lines of notebook-resident Python, at most 60 lines per
code cell. Longer logic goes into `duecare-*` packages.

Validation: Run the new build script. Confirm the `.ipynb` is valid
JSON and opens without errors. Confirm
`python scripts/publish_kaggle.py --dry-run push-notebooks`
discovers the new kernel.

### Phase 6. Rebuild all existing notebooks from build scripts

14 build scripts currently exist under `scripts/build_notebook_*.py`.
After the renaming in Phases 1 and 2, their output paths are stale.
For every build script:

a. Run it: `python scripts/build_notebook_NNN_<slug>.py`.
b. Confirm the output `.ipynb` appears at both
   `notebooks/NNN_<slug>.ipynb` and
   `kaggle/kernels/duecare_NNN_<slug>/NNN_<slug>.ipynb`.
c. Confirm the `kernel-metadata.json` in the kernel directory has
   the correct `id`, `code_file`, and `title`.

If a build script fails, fix the script (not the notebook JSON
directly). The build script is the source of truth; the `.ipynb` is
a generated artifact.

Validation: All 14+ build scripts run without errors.

### Phase 7. Dry-run publish all notebooks

Run:

```bash
python scripts/publish_kaggle.py --dry-run push-notebooks
```

This must:

- Discover every kernel directory under `kaggle/kernels/`.
- Validate every `kernel-metadata.json`.
- Report the kernel count. It must match the total tracked count
  (28 existing plus however many gap-builds Phase 5 produced).
- Exit 0.

If it exits non-zero, read the error, fix the cause, and rerun.
Do not move to Phase 8 until this passes.

### Phase 8. Live publish all notebooks

Run:

```bash
python scripts/publish_kaggle.py push-notebooks
```

This pushes every kernel to Kaggle via `kaggle kernels push`. After
it completes, run:

```bash
python scripts/publish_kaggle.py status-notebooks
```

Report the status of every kernel. For any kernel that fails or is
queued, state the kernel slug and the error. Do not retry more than
twice per kernel. If a kernel fails after two retries, log it and
move on.

After publish, update `docs/current_kaggle_notebook_state.md` with
the new inventory (new kernel ids, new filenames, resolved aliases,
new kernels from gap-builds).

### Phase 9. Update all downstream docs

After all notebooks are renamed, rebuilt, and published:

a. Regenerate `docs/notebook_guide.md` from the new inventory.
   The notebook guide must be a generated artifact, not hand-edited.
   If a generation script does not exist, create one at
   `scripts/generate_notebook_guide.py` that reads all
   `kernel-metadata.json` files, sorts by numeric ID, and produces
   the guide with section headers, notebook table (columns: ID,
   title, kind, modality, question, Kaggle link, status), and
   reading-order notes.

b. Update `docs/kaggle_integration.md` or merge it into
   `notebook_guide.md` (per the review output's recommendation).

c. Update `README.md` notebook links to use new slugs.

d. Update `docs/copilot_review_prompt.md` kernel count and
   inventory block.

e. Update `docs/current_kaggle_notebook_state.md` with the final
   post-publish state.

Validation: All updated docs reference only slugs that exist under
`kaggle/kernels/`. No dead links.

## Size caps (hard rejects)

Per Principle C:

- No more than 40 cells per notebook.
- No more than 300 lines of total notebook-resident Python.
- No more than 60 lines per single code cell.
- No notebook defines a helper function that already exists in
  `duecare.*` packages. Extract it.

If any notebook exceeds a cap, split it into a sibling at an
adjacent slot (for example, 215 if 210 and 220 are taken).

## Anti-slop rules (inherited, restated for emphasis)

- No filler words: leveraging, seamlessly, robust, cutting-edge,
  state-of-the-art, comprehensive, empower, delve, in today's
  landscape, it is worth noting that, navigate the complexities,
  unlock, harness, journey, synergy.
- No em dashes. No emojis.
- No placeholder code: no `raise NotImplementedError()`, no `pass`
  bodies, no `TODO implement this` in shipped notebook cells. If
  a cell cannot be completed, delete the cell and add a gap ticket
  to the output.
- No hallucinated imports. Every `from duecare.* import X` must
  resolve. If X does not exist, do not invent it.

## What NOT to do

- Do not rewrite package code (`packages/duecare-llm-*`). If you
  find a missing export, add it to the package's `__init__.py`,
  but do not restructure packages.
- Do not change the evaluation logic inside notebooks. This prompt
  fixes infrastructure (paths, imports, metadata, headers), not
  science.
- Do not run GPU-dependent notebooks on a CPU machine. Build and
  validate only; Kaggle runs the GPU kernels.
- Do not delete any kernel that is currently live on Kaggle without
  explicit confirmation from Taylor.
- Do not change Kaggle dataset slugs or model slugs. Only kernel
  slugs change.
- Do not force-push or overwrite a kernel version that has
  meaningful output. Use `kaggle kernels push` which creates a new
  version, not a destructive overwrite.
- Do not poll Kaggle status more than three times. Check once after
  publish, once after five minutes, then move on.

## Output

After completing all nine phases, produce a single summary file at
`docs/review/notebook_publish_report.md` with:

1. A table of every notebook: new slug, new Kaggle id, old slug,
   status (published / failed / gap-built / skipped), and one-line
   note.
2. A list of every build script created or modified, with old and
   new paths.
3. A list of every doc file updated.
4. A list of any remaining failures or gaps that require Taylor's
   manual intervention (for example, GPU notebooks that need a
   Kaggle runtime to verify, or kernels that failed after two
   retries).
5. The final kernel count: total tracked, total published, total
   gap-built, total failed.

## Constraints

- Every phase has a validation gate. Do not skip it.
- `docs/current_kaggle_notebook_state.md` is the source of truth
  before you start. It is also the artifact you update when you
  finish.
- Build scripts are the source of truth for notebook content. Raw
  `.ipynb` JSON is a generated artifact. Edit the build script,
  not the JSON, whenever a build script exists.
- Kaggle ids use hyphens. Directory slugs use underscores. Filenames
  use underscores. Do not confuse them.
- The `kernel-metadata.json` `id` field must match the pattern
  `taylorsamarel/<kebab-case-slug>`.
- Plain English, no em dashes, no emojis.
- If any phase takes more than 30 minutes of wall time, stop, report
  progress, and ask Taylor whether to continue.

## Read before executing (in order)

1. `docs/current_kaggle_notebook_state.md`.
2. `docs/prompts/_shared_discipline.md`.
3. `docs/review/*.md` (all review outputs, if they exist).
4. `docs/copilot_review_prompt.md` (the curriculum spine, if review
   outputs do not exist).
5. `scripts/build_notebook_00.py` (the canonical build pattern).
6. `scripts/publish_kaggle.py` (the publish orchestrator).
7. `Makefile` (the `kaggle-push`, `kaggle-dry-run`, `notebooks`,
   `build`, `test` targets).
8. Every `kaggle/kernels/*/kernel-metadata.json` (28 files).
9. Every `packages/duecare-llm-*/pyproject.toml` (version numbers
   for pinning).
