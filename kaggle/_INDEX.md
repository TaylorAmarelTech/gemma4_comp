# Kaggle Kernel Index

## Active Submission Path

Only three Kaggle script kernels are active for the current competition scope.
The first two are the primary recording path; A-00 is the quantitative proof
and training/evaluation path:

| Order | Folder | Kaggle slug | Title | Purpose |
|---|---|---|---|---|
| 01 | `01-duecare-exploration-workbench` | `taylorsamarel/duecare-app` | **DueCare App** | Full reviewer workbench: chat, harness comparison, bulk file review, knowledge extraction, search, sharing, traces, and activity logs. |
| 02 | `02-live-demo` | `taylorsamarel/duecare-live-demo` | **DueCare Live Demo** | Focused live demo for judges and video capture. Hosts the recording-grade pitch deck at `/start` and `/slides`. |
| A-00 | `A-00-omni-experiment-workbench` | `taylorsamarel/duecare-fine-tuning-and-evaluation` | **DueCare Fine-tuning and Evaluation** | Quantitative proof path for baseline, harnessed, synthetic-data, fine-tuning, judging, checkpointing, and report artifacts. |

Each active kernel is intended to be copied into Kaggle, run on T4 x2 with Internet enabled, install DueCare from GitHub, write outputs under `/kaggle/working`, launch the local server, and print a public `https://*.trycloudflare.com` URL.

Version boundary reviewed 2026-07-15: the A-00 Kaggle URL is live and the
public notebook attaches `taylorsamarel/duecare-proof-finetuning-data`. The
proof dataset is ready on Kaggle; the run still needs a terminal Kaggle status
plus artifact review before it is cited as a completed A-00 proof run. A
separate, deliberately small Gemma 4 adapter study is public and is bounded as
a learning artifact. Five public training-data/evidence datasets and expanded
companion notebooks are available; their exact claims are listed below.

## Optional Evaluation Surface

This repository also includes optional benchmark kernels that are useful for
post-submission comparison work but are not required for the primary recording
path:

| Folder | Kaggle slug | Title | Purpose |
|---|---|---|---|
| `03-universal-llm-benchmark` | `taylorsamarel/duecare-universal-llm-benchmark` | **DueCare Universal LLM Benchmark** | Benchmarks arbitrary OpenAI-compatible, Anthropic Messages, or raw JSON endpoints against DueCare prompt/rubric/evidence cues, with Claude Opus judging when an Anthropic key is configured. |
| `04-kaggle-community-benchmark` | `taylorsamarel/duecare-kaggle-community-benchmark` | **DueCare Kaggle Community Benchmark** | Publishes DueCare safety rows as `kaggle_benchmarks` tasks so model calls can use Kaggle's model proxy and benchmark leaderboard flow. |

## Shared Dataset Surfaces

These directories do not change the active-kernel count:

| Folder | Status | Purpose |
|---|---|---|
| `shared-datasets/trafficking-prompts` | Existing | Shared prompt/rubric surface. |
| `shared-datasets/eval-results` | Existing | Evaluation-result metadata and reproduction notes. |
| [`shared-datasets/training-data`](shared-datasets/training-data/) | Documentation and contract map | Explains the manifest-bound supervised fine-tuning, preference, reward-label, loading, and publication contracts. Generated Kaggle payloads remain under gitignored release directories. |

## Auxiliary Public Training Proofs

These are public companions to A-00, not additional active submission kernels:

| Kaggle slug | Type | Purpose | Status reviewed 2026-07-15 |
|---|---|---|---|
| `taylorsamarel/duecare-proof-finetuning-data` | Combined dataset | Approved 24-row supervised fine-tuning preview plus 24 preference pairs, 4 validation rows, and 4 test rows. | Ready |
| `taylorsamarel/duecare-visible-reasoning-sft-preview` | Derived dataset | Exact-row supervised fine-tuning and held-out view. | Ready |
| `taylorsamarel/duecare-preference-pairs-preview` | Derived dataset | Exact-row preference and held-out view. | Ready |
| `taylorsamarel/duecare-training-data-integrity-audit` | Central-processing-unit notebook | Re-verifies file/row hashes, model revision, and split-family isolation. | Complete |
| `taylorsamarel/duecare-gemma-4-lora-training-starter` | Central-processing-unit notebook with graphics-processing-unit opt-in cell | Writes the pinned supervised-fine-tuning-to-preference-optimization plan; the default public run does not train. Low-Rank Adaptation means training small adapter weights beside a frozen base model. | Complete |
| `taylorsamarel/duecare-four-arm-fine-tuning-evaluation` | Central-processing-unit notebook | Freezes the four-arm evaluation plan and held-out prompts. | Complete |

The derived datasets are purpose-specific views of one approved source release,
not independent experimental evidence. The notebook collection does not include
adapter weights or a completed baseline-versus-adapter result.

## Public advanced training-data showcase

These packages passed exact manifest-bound publication approval, privacy,
license, checksum, split-isolation, and local notebook-execution gates before
Kaggle version 4 was made public on 2026-07-15.

| Kaggle dataset ID | Contents | Verified identity | State |
|---|---|---|---|
| [`taylorsamarel/duecare-multiperspective-finetuning-corpus`](https://www.kaggle.com/datasets/taylorsamarel/duecare-multiperspective-finetuning-corpus) | 25,600 supervised fine-tuning train, 25,600 preference train, 2,048 validation, and 2,048 test rows | Candidate `7cc7573e34aa9300`; release-manifest SHA-256 `ea644df422d9e8c43003805f49a227d441e3a952d6deb3ea3e6fb3b6b579211d` | Public Kaggle version 4; downloaded explorer output verifies 15 Portable Network Graphics charts and 7 comma-separated-value tables |
| [`taylorsamarel/duecare-measured-response-training-corpus`](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-response-training-corpus) | 791 supervised fine-tuning rows and preference pairs (649/66/76), 1,582 reward rows, and raw-text-free inventory/quarantine | Candidate `7fc563c8d583fd7a`; release-manifest SHA-256 `56fa69c19990c524002e4f91b833faef58648a66d87729a8f4c61dd56722b74b` | Public Kaggle version 4; downloaded explorer output verifies 11 charts and 10 tables; benchmark-contaminated for independent evaluation |
| [`taylorsamarel/duecare-measured-review-curriculum-200k`](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-review-curriculum-200k) | 207,680 supervised training rows, 207,680 preference-training pairs, 528 validation rows, and 608 test rows | Candidate `37e5e6108f549150e966f0485dad77b2cb05f223df399d185cc8dc62c2b26547`; release-manifest SHA-256 `1b062ce12fe43494f7d63659a53017c857e0ac0103759d8f71b3340f63bdc2b7` | Public; synthetic descendants preserve parent hashes and must not be counted as independent examples |
| [`taylorsamarel/duecare-gemma4-adapter-learning-study`](https://www.kaggle.com/datasets/taylorsamarel/duecare-gemma4-adapter-learning-study) | Two real local Gemma 4 E2B Low-Rank Adaptation runs, relative adapter weights, optimization logs, paired outputs, four-arm evidence, two frozen frontier-judge audits, and a checksummed broader harness receipt | Release-manifest SHA-256 `4c300a3b277009e1488979bb6579859a59f0dbfeecf4c31a0d4251ea837572f4`; 12-step adapter SHA-256 `dae76f3b29e529916f95a88af5ed5da36c8081521076b219ba3c36043eaf4d43`; 60-step adapter SHA-256 `93fcb82460b8d7ae21737e1cd88fea711cb8c1f3ee5e82d4f313edc54bcc5347` | Public learning study; narrow format result, 6/6 recorded harmful-request harness wins, +1.73/10 over 911 paired benchmark prompts, and +4.39/10 over 140 adversarial transforms; no field-detection claim |
| [`taylorsamarel/duecare-grounded-byte-model-learning-study`](https://www.kaggle.com/datasets/taylorsamarel/duecare-grounded-byte-model-learning-study) | Two complete byte-level transformers initialized from random weights, directly loadable model configs and NumPy archives, six graphics, learning curves, before/after text, and exact reload receipts | Release-manifest SHA-256 `9bc416a67de030243429857fa7af4ee7087bead4c85ef2566a3838f6f95e7d4a`; model SHA-256 values `bf24e8782d8bfd08e5ba4d68163f356fc0763c906a9da4e6f809be2e36a3a629` and `5db70df032b7b1dbc1c98eaeca80d81390fcc7a3c23c8b08e029b5c930afb830` | Public central-processing-unit mechanism study; no pretrained checkpoint, adapter, or domain-lift claim |

Reviewer notebook route:

1. [Load both datasets](https://www.kaggle.com/code/taylorsamarel/duecare-training-data-loading-quickstart).
2. [Inspect the cross-dataset quality dashboard](https://www.kaggle.com/code/taylorsamarel/duecare-training-data-quality-dashboard).
3. Review the measured-response
   [integrity](https://www.kaggle.com/code/taylorsamarel/duecare-response-corpus-integrity),
   [training plan](https://www.kaggle.com/code/taylorsamarel/duecare-response-training-plan),
   [visual explorer](https://www.kaggle.com/code/taylorsamarel/duecare-response-dataset-visual-explorer),
   and [small central-processing-unit baseline](https://www.kaggle.com/code/taylorsamarel/duecare-response-quality-baseline).
4. Review the multiperspective
   [integrity notebook](https://www.kaggle.com/code/taylorsamarel/duecare-large-corpus-integrity-and-exploration),
   and [visual explorer](https://www.kaggle.com/code/taylorsamarel/duecare-large-corpus-visual-explorer).
5. Inspect the [207,680-row curriculum atlas](https://www.kaggle.com/code/taylorsamarel/duecare-200k-curriculum-visual-atlas).
6. Read the real-run
   [learning curves](https://www.kaggle.com/code/taylorsamarel/duecare-gemma4-learning-curves)
   and [four-arm before/after study](https://www.kaggle.com/code/taylorsamarel/duecare-gemma4-four-arm-before-after).
7. Audit the [grounded lineage and training receipts](https://www.kaggle.com/code/taylorsamarel/duecare-grounded-lineage-and-training-receipts),
   [frontier-judge measurement](https://www.kaggle.com/code/taylorsamarel/duecare-frontier-judge-measurement-audit),
   and [integrated evidence-to-triage system and publication showcase](https://www.kaggle.com/code/taylorsamarel/duecare-training-publication-toolchain).
8. Follow the [Gemma 4 Tensor Processing Unit training lab](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-tpu-lora-training-lab)
   for the quota-conscious distributed continuation.

Real Gemma 4 E2B training ran locally on a graphics processing unit and
produced two relative adapters. The stronger run completed 60 optimizer steps,
trained 817,152 parameters, and changed the declared structural score from
0.516667 to 0.666667 on eight held-out grounded-remix rows, a +0.15 delta. The
four-arm manifest is
`ac0a3258aabca5f49f1c8d0476bbf718618e584d8938526bf36e3cad762845f3`.
A frozen, blinded, both-orders GLM-5.2 judge study completed all 32 requested
verdicts but did not support a positive training-lift claim. No merged weights,
independent victim-identification or field-detection lift, legal-quality
result, or production-ready model is claimed. A separate frozen study over the
six recorded harmful-request pairs completed all 12 verdicts and preferred the
DueCare harness response in every pair and presentation order.

A separate central-processing-unit compatibility run initialized two
byte-level transformers from random weights. Both complete model archives,
now published in the [Grounded Byte Model Learning Study](https://www.kaggle.com/datasets/taylorsamarel/duecare-grounded-byte-model-learning-study),
passed exact reload verification; held-out next-byte loss moved from 5.5479 to
5.1164 for the 74,304-parameter arm and from 5.5990 to 4.7361 for the
452,224-parameter arm. This is two-step mechanism evidence, not a domain-lift
claim. The public Tensor Processing Unit notebook remains the larger execution
route and must report its actual accelerator before any Tensor Processing Unit
claim is made.

## Archived Notebooks

The former `03-duecare-video-pitch` notebook, appendix notebooks `A-01`
through `A-24`, the headless `A-30` GPU training snapshot, and task-notebook
snapshots have been moved to `kaggle/_archive/notebooks/`. They remain
reference material only; they are not part of active validation, recording,
or the required Kaggle run path.

Root `kaggle/` should not contain appendix `A-*` folders other than active
`A-00-omni-experiment-workbench`. The only root `04-*` folder should be
`04-kaggle-community-benchmark`; other `04-*` notebook snapshots belong under
`kaggle/_archive/notebooks/`.

## A-00 Proof Path

A-00 now opens with two choices:

| Card | Use |
|---|---|
| Preconfigured Harness, Training, and Evaluation | One guided pipeline: base Gemma, base+harness, candidate supervised fine-tuning and preference rows, manifest and held-out gates, optional Low-Rank Adaptation (LoRA) supervised fine-tuning followed by Direct Preference Optimization (DPO), trained base, trained+harness, combined Gemma+rules grading, completion manifest, and final report. |
| Custom | Full control surface for prompt sets, adapters, imports, research graph, knowledge packs, and partial reruns. |

The current repository source adds manifest-bound supervised fine-tuning and
preference files,
lineage-safe train/validation/holdout assignments, exact base revisions,
privacy and licensing fields, requested preference-stage enforcement, and completion
manifests. Those July changes are now pushed to the public A-00 notebook with
the proof dataset attached. The external importer can inspect loose artifacts,
final answers, citations, and deliberately authored visible rationales, but
only a fully validated bundle may train; private hidden chain-of-thought
remains prohibited.
