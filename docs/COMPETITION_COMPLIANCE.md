# Competition compliance map

A rule-by-rule map from The Gemma 4 Good Hackathon's Official Competition Rules
to the evidence in this repository, written so a reviewer can check compliance
without reverse-engineering it from the tree.

Section numbers refer to the Official Competition Rules at
<https://www.kaggle.com/competitions/gemma-4-good-hackathon/rules>. Where a rule
does not apply, that is stated rather than skipped.

## Track declaration

- **Impact Track — Safety & Trust** (primary). Declared at the top of
  [`writeup_draft.md`](writeup_draft.md) and
  [`kaggle_writeup_paste_ready.md`](kaggle_writeup_paste_ready.md).
- **Special Technology Track — Unsloth** (Gemma 4 LoRA fine-tuning) and
  **LiteRT** (on-device inference in the sibling Android app).

The project also uses Ollama and llama.cpp substantially, but claims only
Unsloth and LiteRT because that is what the submitted writeup declared. Nothing
here retrofits a broader claim after the fact.

## §2.5 — Winner License (CC-BY 4.0)

The rule requires a winner to license the Submission and the source code used to
generate it under **CC-BY 4.0**.

**Status: grantable, no conflict.** All DueCare-authored code is MIT
(`LICENSE`) and solely owned by the author, so it can additionally be offered
under CC-BY 4.0 on request without needing any third party's permission. MIT
does not restrict that, and neither licence limits commercial use.

§2.5.a carves out inputs carrying incompatible licences. For this project those
are:

| Component | Licence | Note |
|---|---|---|
| Gemma 4 base weights | Apache 2.0 | Not redistributed; obtained by the operator from Google |
| Third-party evaluated models | various vendor terms | Run as measurement subjects only; never redistributed |
| Retrieval models (`mxbai-rerank-xsmall-v1`, `all-MiniLM-L6-v2`) | Apache 2.0 | Lazy-downloaded at runtime, not bundled |

The published LoRA adapters are Derivative Works of Gemma 4 and remain under
Apache 2.0 — see [`../NOTICE`](../NOTICE).

## §2.6 — External Data and Tools

The rule requires External Data to be publicly available and equally accessible
to all Participants at no cost, or to satisfy the Reasonableness Standard.

- **The prompt corpora are public.** The trafficking seed corpus
  (`configs/duecare/domains/trafficking/seed_prompts.jsonl`, 74,640 rows) and
  every benchmark corpus under `configs/duecare/benchmarks/` are committed to
  the public repository, so any Participant has identical access at no cost.
  They derive from a benchmark authored by this project's author, who holds the
  rights to publish them.
- **No proprietary dataset purchase is required** to reproduce anything.
- **Model access costs are small and substitutable.** Open-weight models run
  locally through Ollama at no licence cost. Closed frontier models appear only
  in optional comparison lanes routed through OpenRouter at ordinary
  pay-per-token rates — far below the Reasonableness Standard's example of a
  licence exceeding the value of a prize. The headline harness-lift result does
  not depend on any paid model; it reproduces against local open weights.
- **No hand labelling of any test set** was used (§3.4.b). Grades come from
  documented rule-based and model-judge pipelines.

## §2.8 — Winner's Obligations (reproducibility)

The rule requires training code, inference code, a description of the required
computational environment, and a methodology description detailed enough to
reproduce the approach.

| Required | Where |
|---|---|
| Training code | `packages/duecare-llm-training/`, `kaggle/A-00-omni-experiment-workbench/kernel.py` |
| Training recipe (E4B path) | `configs/duecare/training/unsloth_e4b.yaml` — 3 epochs, per-device batch 4, learning rate 2e-4, max sequence length 2048, `adamw_8bit` optimiser |
| Hyper-parameters of the **published** adapters | Those are **E2B** runs and did not execute the E4B recipe above to completion. Authoritative per-run values live in each run's `metrics.json` / `run-manifest.json` in the adapter dataset — run-01: 12 steps, epoch 0.75; run-02: 60 steps, epoch 1.875; both peak lr 2e-4. Summarised in [`MODEL_CARD_DRAFT.md`](MODEL_CARD_DRAFT.md) |
| Adapter shape per run | `adapter_config.json` inside each `runs/run-*/adapter/` of the published adapter dataset (base checkpoint, rank, target modules) |
| Inference code | `packages/duecare-llm-chat/src/duecare/chat/gemma4_runtime.py` (canonical loader) plus the active Kaggle kernels |
| Computational environment | `docs/deployment_local.md`, `requirements.txt`, and the accelerator/attachment requirements in each `kaggle/*/README.md` |
| Methodology | `docs/research/training_methodology.md`, `docs/research/evaluation_methodology.md` |
| Claim provenance | [`reproducibility.md`](reproducibility.md) maps each headline number to the command that regenerates it |

Published weights and benchmarks — requested by the Overview for projects that
train a model — are at
`kaggle.com/datasets/taylorsamarel/duecare-gemma4-adapter-learning-study`.

## §3.6 — Submission code requirements (open source)

§3.6.c requires open source code used to generate the Submission to be under an
OSI-approved licence that does not limit commercial use.

**Status: satisfied.** The core dependency path is MIT / BSD-3-Clause /
Apache-2.0 throughout, inventoried by licence in
[`../LICENSES.md`](../LICENSES.md). A scan of 184 installed distributions found
no GPL, AGPL, or SSPL code in that path, and none is bundled in any published
wheel.

One item is disclosed for completeness: `pyphen` (GPLv2+ **or** LGPLv2+) is
pulled transitively by `textstat`, which exists only in `duecare-llm-kit`'s
**opt-in** `nlp` extra. A default install pulls neither, and neither participates
in generating any Submission artefact — `textstat` is used in one notebook
builder for readability statistics. Where a user opts in, `pyphen`'s LGPL option
applies.

§3.6.a (no private code sharing) does not apply: this is a solo entry and the
repository is public.

## §3.14 — Warranty (original work, non-infringement, non-defamation)

- **Original work.** The harness, corpora, benchmark design, and analysis are
  the author's own. Third-party components are enumerated in
  [`CREDITS.md`](CREDITS.md), [`../LICENSES.md`](../LICENSES.md), and
  [`../THIRD_PARTY_LICENSES.md`](../THIRD_PARTY_LICENSES.md) — including a
  Kaggle install technique credited to community member @bwandowando.
- **No defamation.** Every person, company, agency, licence number, and case ID
  in the prompt corpora is a fabricated composite. Names are deliberately
  plausible so the benchmark tests realistic inputs, but none refers to a real
  organisation. Stated in `configs/duecare/benchmarks/README.md` and
  `configs/duecare/domains/trafficking/README.md`.
- **No third-party PII.** No real worker data, case files, or personal contact
  details are committed. The only contact information published is
  organisational — public helplines and agency addresses — carrying per-entry
  provenance and a documented correction/removal route.
- **Trademarks.** Apache 2.0 grants no trademark rights. "Gemma" and "Google"
  appear only descriptively, to identify the upstream model. The published
  derivative is titled "Duecare Safety Harness — Gemma 4 E4B Fine-tuned": the
  product name is DueCare's, with Gemma named as the base. No Google
  endorsement is claimed or implied.

## §3.1 / §2.7 — Eligibility

Solo entry from a single Kaggle account (§3.5.a); not a Competition Entity
employee. The maximum team size of five and the one-Submission-per-team limit
are satisfied trivially.

## Submission requirement checklist

| Requirement | Status |
|---|---|
| Kaggle Writeup, ≤1,500 words, Track selected | `docs/writeup_draft.md` / `docs/kaggle_writeup_paste_ready.md`; Safety & Trust declared |
| Public YouTube video ≤3 min, viewable without login | Linked from the writeup |
| Public code repository, well-documented | <https://github.com/TaylorAmarelTech/gemma4_comp> — MIT, no login or paywall |
| Live demo, publicly accessible | Kaggle kernels printing a public Cloudflare URL, plus <https://duecare-ai.com> |
| Media gallery with cover image | Attached to the writeup |

## Known limitations, stated rather than hidden

Technical Depth is judged on whether the technology is "real, functional,
well-engineered, and not just faked for the demo". Two things are therefore
stated plainly instead of smoothed over:

- The published adapters are a **bounded learning artefact, not an improved
  model**. A frozen frontier-judge audit did not support a positive
  training-lift claim for them, and that negative result is published alongside
  them.
- The headline lift numbers measure **response quality on a benchmark**, not
  real-world victim identification or field detection. Every results surface
  repeats that boundary.
