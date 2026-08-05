# Goal command 15 - GPT-5.6 SOL Kaggle hackathon showcase and visual notebooks

> Created 2026-07-15. Paste the block below into GPT-5.6 SOL, GPT-style
> coding agents, Claude Code, Codex, or another agentic coding model when the
> goal is to polish the DueCare Kaggle hackathon dataset and notebook
> experience into a professional, reviewer-friendly, learning-oriented
> showcase without weakening privacy, reproducibility, or claim boundaries.

This command continues Goal 14. It assumes the training-data flywheel has
already produced public, manifest-bound Kaggle datasets and companion notebooks. The
purpose here is not just to upload files: it is to make the Kaggle surface read
like a serious hackathon submission, a transparent learning artifact, and a
professional applied-AI demonstration.

Use it when the immediate objective is:

- make Kaggle datasets easy to understand at first glance;
- make notebooks visibly load, verify, test, explore, and visualize the data;
- improve dataset usability, metadata, previews, and reviewer navigation;
- frame the work honestly as a Kaggle / Gemma hackathon learning experience;
- keep public releases useful without publishing private or unsafe material by
  accident.

Related source documents:

- [Goal 14 training-data flywheel](14_training_dataset_kaggle_flywheel_gpt56.md)
- [Training data and fine-tuning](../../training_and_finetuning.md)
- [Goal command series](README.md)
- [Kaggle surface index](../../../kaggle/_INDEX.md)

## Copy-paste master prompt

````text
You are working in:

<repo-root>

You are a senior coding agent continuing the DueCare / Gemma 4 Kaggle
hackathon showcase. Work end to end. Do not stop at explanation. Inspect the
live repository and live Kaggle state, improve what is weak, validate, and
report exact evidence.

PRIMARY INTENT

This is a Kaggle hackathon project and learning experience. Treat the public
and private Kaggle surfaces as a professional portfolio-quality demonstration:

- clear enough for a Kaggle reviewer to understand quickly;
- rigorous enough for a technical reviewer to reproduce;
- honest enough that it never overclaims training, fine-tuning, model lift, or
  legal authority;
- educational enough that another learner can see how the dataset, notebooks,
  manifests, safety gates, and evaluation methodology fit together.

The goal is a polished Kaggle learning-and-research showcase, not a deceptive
production launch.

CURRENT STATE TO VERIFY FIRST

As of 2026-07-15, the project is expected to have two public Kaggle datasets:

1. taylorsamarel/duecare-measured-response-training-corpus
   - Public Kaggle dataset, version 4.
   - Release manifest SHA-256:
     56fa69c19990c524002e4f91b833faef58648a66d87729a8f4c61dd56722b74b
   - Collection manifest SHA-256:
     906d50d72f663f29243ab76a13fb980e7d15c51563ac9ea4cef7c72c265b2ce5
   - Expected contents:
     - 791 supervised fine-tuning rows
     - 791 Direct Preference Optimization / preference pairs
     - 1,582 reward-label rows
     - 184,650 response-inventory rows
     - 6,884 quarantine rows
   - safe_to_train=true
   - safe_to_publish=true
   - Benchmark-contaminated for independent model-improvement claims.

2. taylorsamarel/duecare-multiperspective-finetuning-corpus
   - Public Kaggle dataset, version 4.
   - Release manifest SHA-256:
     ea644df422d9e8c43003805f49a227d441e3a952d6deb3ea3e6fb3b6b579211d
   - Collection manifest SHA-256:
     7ecf56fafcc3128fb16bebe938073ffd6ce533a006a52ed15198bc90a021c1c9
   - Expected contents:
     - 25,600 supervised fine-tuning train rows
     - 25,600 preference train rows
     - 2,048 validation rows
     - 2,048 test rows
   - safe_to_train=true
   - safe_to_publish=true

There should be nine public Kaggle notebooks:

1. taylorsamarel/duecare-response-corpus-integrity
2. taylorsamarel/duecare-response-training-plan
3. taylorsamarel/duecare-response-dataset-visual-explorer
4. taylorsamarel/duecare-large-corpus-integrity-and-exploration
5. taylorsamarel/duecare-gemma-4-large-corpus-plan-and-smoke
6. taylorsamarel/duecare-large-corpus-visual-explorer
7. taylorsamarel/duecare-training-data-loading-quickstart
8. taylorsamarel/duecare-response-quality-baseline
9. taylorsamarel/duecare-training-data-quality-dashboard

The two visual explorer notebooks should visibly load and display the datasets:

- duecare-response-dataset-visual-explorer should produce lane tables,
  accepted-row quality samples, score/lift plots, reward-label balance,
  quarantine reasons, text-length charts, and summary JSON.
- duecare-large-corpus-visual-explorer should produce lane tables,
  perspective coverage, journey-stage coverage, evidence-state coverage,
  temporal-lens coverage, view-mode coverage, jurisdiction-pattern coverage,
  prompt-family coverage, response-style coverage, controlled-failure coverage,
  text-length charts, and summary JSON.

Do not trust this state blindly. Verify it live.

READ FIRST

Read these files if present:

1. AGENTS.md
2. README.md
3. docs/training_and_finetuning.md
4. docs/codex/PROJECT_BIBLE.md
5. docs/codex/goal_commands/14_training_dataset_kaggle_flywheel_gpt56.md
6. docs/codex/goal_commands/15_kaggle_hackathon_showcase_gpt56.md
7. kaggle/_INDEX.md
8. kaggle/shared-datasets/training-data/README.md
9. scripts/build_response_kaggle_collection.py
10. scripts/build_large_kaggle_training_collection.py
11. scripts/build_kaggle_visual_exploration_notebooks.py
12. reports/kaggle_publish/visual_notebooks_manifest.json
13. reports/kaggle_publish/response_training_collection_v6/collection-manifest.json
14. reports/kaggle_publish/large_training_collection_v4/collection-manifest.json
15. reports/kaggle_publish/showcase_notebooks_v1/showcase-notebooks-manifest.json

VERIFY LIVE KAGGLE STATE

Run equivalent checks:

```powershell
uvx kaggle datasets status taylorsamarel/duecare-measured-response-training-corpus
uvx kaggle datasets status taylorsamarel/duecare-multiperspective-finetuning-corpus

uvx kaggle kernels status taylorsamarel/duecare-response-corpus-integrity
uvx kaggle kernels status taylorsamarel/duecare-response-training-plan
uvx kaggle kernels status taylorsamarel/duecare-response-dataset-visual-explorer
uvx kaggle kernels status taylorsamarel/duecare-large-corpus-integrity-and-exploration
uvx kaggle kernels status taylorsamarel/duecare-gemma-4-large-corpus-plan-and-smoke
uvx kaggle kernels status taylorsamarel/duecare-large-corpus-visual-explorer
uvx kaggle kernels status taylorsamarel/duecare-training-data-loading-quickstart
uvx kaggle kernels status taylorsamarel/duecare-response-quality-baseline
uvx kaggle kernels status taylorsamarel/duecare-training-data-quality-dashboard
```

Download output artifacts for the visual notebooks and confirm remote Kaggle
execution produced actual charts and summaries:

```powershell
uvx kaggle kernels output taylorsamarel/duecare-response-dataset-visual-explorer `
  -p reports/kaggle_publish/kaggle_kernel_outputs/response_visual_explorer -o

uvx kaggle kernels output taylorsamarel/duecare-large-corpus-visual-explorer `
  -p reports/kaggle_publish/kaggle_kernel_outputs/large_visual_explorer -o
```

Expected response explorer artifacts include:

- response-visual-summary.json
- response-visual-report.md
- response-audit-population.csv
- response-category-summary.csv
- response-component-summary.csv
- response-dimension-lift.csv
- response-lane-summary.csv
- response-quality-summary.csv
- response-quarantine-summary.csv
- response-reward-label-summary.csv
- response-teacher-model-summary.csv
- response-text-length-summary.csv
- response_rows_by_lane.png
- response_split_balance.png
- response_score_distribution.png
- response_dimension_lift.png
- response_component_scores.png
- response_prompt_category_coverage.png
- response_teacher_models.png
- response_reward_label_balance.png
- response_quarantine_reasons.png
- response_audit_population.png
- response_text_lengths.png

Expected large explorer artifacts include:

- large-visual-summary.json
- large-visual-report.md
- large-axis-summary.csv
- large-lane-summary.csv
- large-size-summary.csv
- large-text-length-summary.csv
- large_perspective_journey_heatmap.csv
- large_evidence_temporal_heatmap.csv
- large_view_jurisdiction_heatmap.csv
- large_rows_by_lane.png
- large_storage_profile.png
- large_perspective_coverage.png
- large_journey_stage_coverage.png
- large_evidence_state_coverage.png
- large_temporal_lens_coverage.png
- large_view_mode_coverage.png
- large_jurisdiction_pattern_coverage.png
- large_prompt_family_coverage.png
- large_response_style_coverage.png
- large_controlled_failure_coverage.png
- large_perspective_journey_heatmap.png
- large_evidence_temporal_heatmap.png
- large_view_jurisdiction_heatmap.png
- large_text_lengths.png

SHOWCASE IMPROVEMENT TARGETS

Improve the Kaggle experience until it looks like a professional hackathon
submission and a useful learning artifact.

Prioritize:

1. Dataset landing-page clarity
   - Improve README/DATA_CARD/SOURCES/LIMITATIONS/SCHEMA files.
   - Add "start here" links to the best notebooks.
   - Explain what each dataset is, what it is not, and why it exists.
   - State that this is a Kaggle / Gemma hackathon learning project.
   - Explain the methodology at a professional level without overclaiming.

2. Kaggle usability score
   - Add small preview CSV/JSON files if they improve Kaggle usability.
   - Keep previews safe, small, and representative.
   - Do not include unsafe raw text, private logs, PII, or hidden reasoning.
   - Make file types obvious to Kaggle where possible.

3. Notebook visual quality
   - Ensure notebooks display DataFrames, charts, summaries, and short
     interpretation notes.
   - Avoid notebooks that only print JSON logs.
   - Add section headers that tell a reviewer what they are seeing.
   - Save chart PNGs and summary JSON into Kaggle output.
   - Keep CPU-safe defaults.

4. Professional learning narrative
   - Make the notebooks teach the workflow:
     inventory -> manifest verification -> schema inspection -> sample rows ->
     quality gates -> visualization -> training plan -> evaluation plan.
   - Explain why private candidate datasets remain private.
   - Explain how synthetic visible decision scaffolds differ from hidden
     chain-of-thought.
   - Explain why measured-response data is useful for training experiments but
     contaminated for independent evaluation claims.

5. Publication readiness without unsafe publication
   - Prepare a public-safe preview if appropriate.
   - Do not public-publish the private advanced datasets unless the user gives
     explicit approval and privacy/license gates pass.
   - Clearly separate:
     candidate private,
     public preview,
     trained adapter,
     evaluated adapter,
     production-ready system.

6. Website and docs
   - Update docs only from validated artifact evidence.
   - Update public-facing copy to say "Kaggle hackathon learning artifact" or
     equivalent where helpful.
   - Avoid vague marketing claims. Use dated, manifest-bound claims.

SAFETY RULES

Never publish:

- raw PII
- real worker contact details
- private case files
- private logs
- credentials
- Kaggle tokens
- hidden chain-of-thought
- provider-private reasoning
- unversioned legal/resource claims
- unsafe operational exploitation guidance

Use public-safe language:

- visible rationale
- visible decision scaffold
- reviewed reasoning summary
- rubric rationale
- action trace
- evidence map
- uncertainty note
- learning notebook
- hackathon research artifact
- private candidate dataset
- public-safe preview

Do not claim:

- hidden chain-of-thought extraction
- production adapter release
- GPU training
- model improvement
- legal advice
- public release readiness

unless exact artifact evidence exists.

NOTEBOOK QUALITY BAR

A good Kaggle notebook for this project should:

- attach to the correct dataset via `dataset_sources`;
- verify the release manifest hash before loading rows;
- show a compact dataset identity table;
- show lane/split/shard row counts;
- show a small safe sample or metadata sample;
- show at least 3 useful charts for a small dataset and at least 8 useful
  charts for the large multiperspective dataset;
- write a JSON summary artifact;
- write chart PNG artifacts;
- say explicitly whether GPU training ran;
- say explicitly whether an adapter was produced;
- say explicitly whether model lift was demonstrated;
- avoid hidden chain-of-thought language;
- keep training disabled by default unless explicitly approved.

DATASET QUALITY BAR

A good Kaggle dataset package for this project should contain:

- dataset-metadata.json
- README.md or DATA_CARD.md
- SCHEMA.md
- SOURCES.md
- LIMITATIONS.md
- CITATION.cff
- LICENSE
- release-manifest.json
- candidate-manifest.json
- shard-index.json
- train/validation/test JSONL shards where applicable
- safe preview files where applicable
- checksums for all release artifacts
- clear publication state
- clear safe_to_train and safe_to_publish flags
- clear notebook links

If any of these are missing or weak, improve them.

VALIDATION COMMANDS

Run the relevant focused checks after changes:

```powershell
uvx ruff check scripts/build_kaggle_visual_exploration_notebooks.py
python -m py_compile scripts/build_kaggle_visual_exploration_notebooks.py

python scripts/validate_public_surface.py
python -m pytest packages --collect-only -q
python scripts/validate_main_kaggle_kernels.py
py -3.12 scripts/validate_kaggle_page_sources.py
git diff --check
```

If dependencies are missing, use an isolated command such as:

```powershell
uv run --no-project --python 3.12 --with pytest --with fastapi --with python-multipart --with pydantic --with typing-extensions --with httpx --with jinja2 python scripts/validate_public_surface.py
```

For local notebook execution, use:

```powershell
uv run --no-project --python 3.12 --with nbformat --with nbclient --with ipykernel --with pandas --with matplotlib --with ipython python scripts/build_kaggle_visual_exploration_notebooks.py --execute-local
```

GIT / RENDER BOUNDARY

The worktree may contain unrelated dirty files and generated reports. Do not
use `git add -A`.

If asked to publish to GitHub/Render:

1. Inspect `git status --short`.
2. Stage only intentional code/docs/test files.
3. Do not commit generated `reports/` unless explicitly requested.
4. Confirm branch and remote.
5. Render deploys from `master` via `render.yaml` after GitHub checks pass.
6. Do not claim Render is live unless deployment is verified.

ACCEPTANCE CRITERIA

This slice is successful when:

1. The two public Kaggle datasets are verified live.
2. All nine Kaggle notebooks are verified live.
3. The visual explorer notebooks have remote Kaggle output artifacts.
4. Dataset cards/readmes make the hackathon learning purpose clear.
5. The Kaggle presentation is professional and navigable.
6. Public claims remain bounded and manifest-linked.
7. Validation commands pass or failures are precisely documented.
8. No unsafe/private material is public-published.

FINAL REPORT FORMAT

When you stop, report:

- changed files;
- generated local artifact paths;
- Kaggle dataset IDs and statuses;
- Kaggle notebook IDs and statuses;
- remote notebook output artifacts confirmed;
- row counts by dataset and lane;
- manifest hashes;
- usability/discoverability improvements made;
- hackathon/professional learning framing added;
- validation commands and exact results;
- whether GPU training ran;
- whether any adapter was produced;
- whether any public publication happened;
- remaining blockers;
- next 10 concrete actions.

STOP CONDITIONS

Stop only for:

- public publication approval needed;
- destructive action approval needed;
- missing credentials for an external upload;
- unresolved privacy/license issue;
- repeated validation blocker after real fix attempts;
- user interruption that changes scope.

Do not stop merely because the polish work is broad. Complete the next safe,
validated improvement slice and leave exact evidence.
````

## Short starter version

Use this shorter block when the target agent has limited context length:

```text
In <repo-root>, continue the DueCare / Gemma
4 Kaggle hackathon showcase. Treat the Kaggle datasets and notebooks as a
professional, reviewer-friendly learning artifact. Verify the two public
datasets, nine public notebooks, manifest hashes, and remote notebook output
artifacts. Improve dataset cards, schema docs, safe previews, notebook
visualizations, and navigation so a Kaggle reviewer can understand the project
quickly. Do not overclaim: no hidden chain-of-thought, no GPU training, no
adapter, no model lift, and no new public release readiness unless exact artifacts
prove it. Keep future private candidates private unless explicit approval is given. Run
focused script checks plus validate_public_surface, pytest collect-only,
validate_main_kaggle_kernels, validate_kaggle_page_sources, and git diff
--check. Final report must include Kaggle slugs, row counts, output artifacts,
manifest hashes, validation results, changed files, and remaining blockers.
```

## Operator notes

- This is intentionally a showcase/polish prompt, not just a build prompt.
- The tone should be professional: transparent, educational, reproducible, and
  restrained.
- The Kaggle hackathon framing should improve clarity, not inflate claims.
- If live Kaggle state differs from this file, live Kaggle state wins.
