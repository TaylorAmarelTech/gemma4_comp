# Kaggle workflow — publishing + polish checkpoint + useful commands

> Auto-loaded by Claude Code at the project memory level. Extracted
> from CLAUDE.md so the per-rule files stay scoped.

## Kaggle publication workflow

**Authorized (2026-07-20):** Taylor has cleared Claude Code to **actively publish and
run Kaggle kernels — including GPU/TPU training kernels — and to create/publish
datasets/models**, without asking first. This removes the earlier "manual by default /
Kaggle training is user-driven / never push notebook source" constraints. Still applies:
keep the safety and PII gates, prefer a dry-run/validate when a change is uncertain, and
do not carelessly rewrite live public links. When a kernel is a training run, pushing it
executes it on Kaggle GPU/TPU — verify accelerator + attached data in the metadata first.

Kaggle notebook generation is archived. Do **not** create `.ipynb` notebooks
for the judge-facing submission by default. The source of truth for Kaggle
bundles is the folder README plus `kernel.py`; Taylor copies `kernel.py` into
Kaggle manually for showcasing and publication. Any historical `.ipynb` wrapper
belongs under `_archive/kaggle-notebook-previews-2026-05-11/`, not in active
`kaggle/*/` folders.

Builder scripts under `scripts/build_notebook_*.py` are historical research
helpers unless Taylor explicitly asks for a preview rebuild. They must not
write root submission `.ipynb` files.

Every Kaggle bundle that remains in the submission must be runnable from a
clear bootstrap path instead of hidden local state. The first executable cells
or top-of-file setup block should:

1. State required Kaggle settings up front: accelerator, internet, attached
   datasets/model sources, and secrets such as `HF_TOKEN`.
2. Fail fast with a helpful message if the required GPU/secret/dataset is
   missing. If a sample/offline fallback exists, it must be clearly labeled in
   the output and opening markdown so it is never mistaken for live inference.
3. Install DueCare from a reproducible, transparent source. For the current
   rapid Kaggle copy/paste workflow, the active kernels may fall back to
   GitHub source install from `DUECARE_REPO` / `DUECARE_COMMIT_SHA` when
   release wheels are missing. Always print the repo, ref, resolved package
   imports, and DueCare version. For a final frozen submission, prefer a
   commit SHA or release wheel over a moving branch.
4. Validate imports and print the resolved DueCare version/source before any
   model load or demo output.
5. Never require `_reference/`, local `.venv`, root-level legacy mirrors, or
   untracked files to make a public kernel run.

Default agent behavior:

1. Edit source files and kernel bundles locally only.
2. Run validators and dry-runs (public-surface audits, root metadata checks,
   and Kaggle dry-run checks) to prove readiness.
3. Prepare paste-ready kernel text, metadata, and link checklists.
4. Leave the final Kaggle UI steps to Taylor: manual copy/paste into
   Kaggle, manual save/run/publish, then manual link updates after the
   public URLs exist.

Only run real Kaggle push/publish commands after an explicit user request
that says to publish/push/upload. When in doubt, run dry-run/status only.

## Kaggle notebook polish checkpoint (2026-05-11)

Current active Kaggle state is deliberately smaller than the older archived
research suite:

- The former generated/research kernel inventory under `kaggle/kernels/*` is
   archived with its notebook wrappers under
   `_archive/kaggle-notebook-previews-2026-05-11/`. Older 52/74/77-kernel
   notes are historical unless Taylor explicitly asks for restore or migration work.
- The judge-facing submission folders under `kaggle/` are now the active
   three-folder set: `01-duecare-exploration-workbench`, `02-live-demo`, and
   `A-00-omni-experiment-workbench`. Their `kernel.py` and `README.md` files
   are the source of truth; notebook wrappers are archived.
- Appendix folders A-01 through A-24 and `03-duecare-video-pitch` are archived
   for the current push. Do not treat them as active blockers unless Taylor
   asks for restore/migration work.
- A conservative first polish pass has already fixed reproducible bootstrap
   drift, notebook preview cell metadata, visible demo PII placeholders, A-08
   design-token drift, and A-09 displayed-result truncation.
- Older install-policy tests were written for a frozen publication pass.
   Current active kernels prioritize copy/paste Kaggle reliability: attached
   wheels when available, otherwise GitHub source fallback with explicit repo
   and ref logging. If Taylor asks for a freeze, switch defaults to an
   immutable commit SHA.
- If a reviewer or subagent reports `kaggle/01-duecare-harness-chat/kernel.py`,
   treat it as stale context first. As of this checkpoint, that path does not
   exist and is not tracked by git.
- Latest validation after the conservative pass: targeted Kaggle install and
   utility tests passed, active notebook files were archived, root Kaggle
   metadata points to script kernels, and `scripts/validate_public_surface.py`
   reported 0 findings.

Next safe pass for Claude Code: review the shared FastModel runtime, Kernel 01
comparison harness wiring, and A-00 preconfigured pipeline parity. Do not
broaden into archived notebooks, broad redesigns, or Kaggle publish actions
without explicit Taylor approval.

## Useful commands

```bash
# ── Local evaluation via Ollama (no Kaggle needed) ──
ollama pull gemma4:e4b                        # download model (~4GB in Q4)
python scripts/run_local_gemma.py --max-prompts 10   # quick test
python scripts/run_local_gemma.py --graded-only      # 204 graded prompts
python scripts/run_local_gemma.py --model gemma4:e2b  # smaller model

# ── Extract prompts from the benchmark ──
python scripts/extract_benchmark_prompts.py   # 74K+ prompts → seed_prompts.jsonl

# ── Knowledge surface verification (pure stdlib, no pip required) ──
python scripts/verify_knowledge_surfaces.py   # AST counts + smoke render

# ── Build and test ──
python -m pytest packages --collect-only -q   # quick package collection check (675 collected on 2026-05-19)
make test                                     # full package + top-level pytest run; only claim "passed" after it completes
make build                                    # rebuild all 17 workspace wheels
make adversarial                              # adversarial validation + stress test
make cleanroom                                # clean-room install test

# ── Kaggle validation / dry-run only by default ──
python scripts/publish_kaggle.py auth-check
python scripts/publish_kaggle.py --dry-run push-notebooks
python scripts/publish_kaggle.py status-notebooks

# ── Notebook previews are archived; active submission is kernel.py only ──
# Do not create root submission notebooks by default. Use kernel.py and
# folder README as the Kaggle copy/paste source. Historical previews live
# under _archive/kaggle-notebook-previews-2026-05-11/.
```
