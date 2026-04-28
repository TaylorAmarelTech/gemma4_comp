# `skunkworks/` — exploratory work outside the core submission

Notebooks and scripts that are **interesting research** but not
load-bearing for the 3-notebook hackathon submission. Kept tracked,
indexed, and tested — but separated from the core 60-ish notebooks
that judges read first.

## What's in here

### `notebooks/` — 10 experimental notebooks

**Jailbreak research (181-189)**

A 9-notebook deep-dive into the *attack surface* of Gemma 4 — refusal
direction visualizers, abliteration in-kernel, uncensored community
weights, prompt-level jailbreaks, the works. Cool material; explicitly
NOT the safety-harness story we tell judges. The harness is about
*using* the model well, not breaking it.

| ID | Notebook | Purpose |
|---|---|---|
| 181 | `181_jailbreak_response_viewer` | Side-by-side response viewer for the 186-189 family |
| 182 | `182_refusal_direction_visualizer` | Per-layer PCA of the refusal direction (the abliteration target) |
| 183 | `183_redteam_prompt_amplifier` | 10-20× corpus expansion via uncensored model in a feedback loop |
| 184 | `184_frontier_consultation_playground` | Gemma uses native function calling to escalate to a frontier model |
| 185 | `185_jailbroken_gemma_comparison` | CPU-only comparator for slots produced by 186-189 |
| 186 | `186_jailbreak_stock_gemma` | Baseline + DAN-preamble + roleplay on stock E4B |
| 187 | `187_jailbreak_abliterated_e4b` | In-kernel abliteration with 30+30 calibration |
| 188 | `188_jailbreak_uncensored_community` | Community uncensored weight probe (rank-list of HF ids) |
| 189 | `189_jailbreak_cracked_31b` | 31B 4-bit on L4×4 / A100 (skips on T4) |

**Comparison overflow (220)**

| ID | Notebook | Purpose |
|---|---|---|
| 220 | `220_ollama_cloud_comparison` | Gemma 4 vs 7 OSS via Ollama Cloud (overlaps 210/230/240) |

## What's NOT in here

- The 3 hackathon notebooks (in [`../kaggle/`](../kaggle/))
- The 60-ish core research notebooks for the 76-notebook pipeline
  (in [`../notebooks/`](../notebooks/))
- Legacy / discontinued code (in [`../_archive/`](../_archive/))

## Why split

The 10 skunkworks notebooks are about the *attack surface* of LLMs in
general (jailbreaks, abliteration, refusal-direction analysis) — that's
a research line of its own that runs in parallel with DueCare's
*safety-harness* story. Both are valuable. They get told separately so
the safety-harness pitch stays focused.

A judge clicking into [`../notebooks/`](../notebooks/) sees a clean
arc from baseline → comparison → adversarial → fine-tune → results.
A reader curious about the jailbreak research path clicks into here.

## Build pipeline

The 10 build scripts that produce these notebooks live at
`../scripts/build_notebook_<id>_*.py` (still in the main scripts/
folder). They write the .ipynb output here via
`NB_DIR = ROOT / "skunkworks" / "notebooks"`. The rest of the pipeline
(validation, kaggle metadata, test gates) is unchanged.

## When to add to skunkworks

Add a notebook here when:
- It's a research tangent rather than a step in the safety-harness arc
- It would dilute the core submission story if read first
- It's interesting enough to keep tracked (otherwise → `../_archive/`)

When in doubt, keep it in `../notebooks/`. Skunkworks is for things
you'd happily defend in a follow-up paper, not things you're hiding.
