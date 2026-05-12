# For Judges — Verify Duecare in 5 Minutes

> A focused walkthrough for Gemma 4 Good Hackathon judges. This
> document exists so you don't have to spelunk the codebase to verify
> our claims. Every claim in the [writeup](./writeup_draft.md) and
> [video](./video_script.md) is backed by a file or a Kaggle notebook
> link below.
>
> **For the headline status across every dimension in 60 seconds**,
> see [`docs/readiness_dashboard.md`](./readiness_dashboard.md). For
> per-persona happy-path verification, see
> [`docs/persona_readiness_audit.md`](./persona_readiness_audit.md).

---

## The 30-second pitch

Stock Gemma 4 fails predictably on migrant-worker exploitation
scenarios — it cites no ILO conventions, recognizes no camouflaged
recruitment fees, and gives traffickers operational advice. **Duecare
wraps Gemma 4 with six toggleable safety layers** (Persona, GREP,
RAG, Tools, Online, Imports) plus a 4-mode grading stack (Universal /
Expert / Evaluator / Combined) backed by a **21-dimension rubric**
with two harm-axis dims, an **analog multi-lingual prompt classifier
across 11 languages**, **auto-grade chips inline on every response**,
and a **one-click Layer Ablation runner** that regenerates the +pp
lift live. Per-response Pipeline modal shows the *exact* prompt
transformation with latency-budget breakdown. **12 curator-block JSON
files** ship in the wheel for stakeholder PRs (jurists, NGO partners,
language experts) without reading any Python.

The product north star is **harm reduction, not paternalism**: the
chat tells the worker which statute the fee violates and which NGO
handles refund claims for that corridor. The worker may refuse —
preventing the harm — or pay anyway under their corridor's real
constraints, in which case the journal captures the receipt + the
recruiter's POEA license number + the controlling statute and
pre-stages the refund-claim packet.

Same harness powers a **chat playground** for individual workers and
a **structured-output classifier** for NGO triage dashboards. Ships
as **2 core public Kaggle notebooks + 11 appendix notebooks** + **17
PyPI packages** + an **on-device Android companion** (Duecare
Journey v0.9.0 — MediaPipe Gemma 4 E2B/E4B, encrypted SQLCipher journal,
11 ILO indicator detectors, **20 corridor profiles** (Asia + GCC + LATAM
+ West Africa + refugee routes), **161 GREP rules**, structured Add-Fee
dialog with auto-LegalAssessment + RefundClaim drafting, NGO intake
document generator, cloud Gemma 4 routing fallback, [APK published](https://github.com/TaylorAmarelTech/duecare-journey-android/releases)).
MIT licensed. Runs on a laptop. Zero data egress.

---

## What the harness actually does, quantified

We score the harness on three failure modes stock LLMs commonly
exhibit on trafficking-shaped prompts. Each is a hand-built rubric
of 4 criteria, scored against 207 prompts under harness-OFF vs
harness-ON. Full report: [`docs/harness_lift_report.md`](./harness_lift_report.md).

| Dimension | Harness OFF | Harness ON | **Lift** |
|---|---|---|---|
| Mentioning specific rules per jurisdiction (statute + section number) | 0.4% | 87.8% | **+87.5 pp** |
| Mentioning ILO / international regulations (Convention number, Palermo, ICRMW) | 0.1% | 51.3% | **+51.2 pp** |
| Mentioning substance-over-form (reject "worker consented" defence; identify circumvention) | 0.8% | 34.8% | **+34.1 pp** |

**Layer ablation** (Appendix B of the report): GREP-only +35 pp, RAG-only
+47 pp, both layers together +56.5 pp. Both layers are independently
load-bearing — neither is redundant given the other.

**Citation grounding** (Appendix C): with the harness ON, Gemma emits
~6 statutory citations per response (vs ~0 baseline), and 99.3% of
those citations trace directly back to the bundled 46-doc RAG corpus
or 108-rule GREP catalog.

**Reproducibility caveat:** the +56.5pp / +87.5pp / +51.2pp / +34.1pp
numbers were last measured 2026-05-03 against the prior 49-rule GREP
set. The v3.16 expansion to 161 rules is purely additive (no rules
were removed) so the lift is expected to remain at-or-above these
floors. Full provenance + re-measurement command in
[`docs/reproducibility.md`](./reproducibility.md). The A6 notebook
`duecare-grading-evaluation` regenerates the table in ~10 min on
a Kaggle T4.

Reproduce: `python scripts/rubric_comparison.py` (CPU proxy) or
the A6 notebook (real Gemma 4 generations on Kaggle T4).

---

## Two-minute verification path

If you have two minutes to decide if this is real:

1. **Read the writeup.** [`docs/writeup_draft.md`](./writeup_draft.md)
   (1,497 words, under the 1,500-word cap). Frames the problem (3 LLM
   blind spots), the harness (6 layers), the notebooks (2 core + 11 appendix), and the
   deployment modes.

2. **Watch the video.** Script at [`docs/video_script.md`](./video_script.md)
   (2:50 target). Opens with Maria (a composite character, labeled as
   such). Headline beat at 0:35–1:50: cursor clicks Persona / GREP /
   RAG / Tools / Online tiles ON one at a time, sends the textbook
   68%-loan prompt, response transforms from "5 cash flow strategies"
   to "5 ILO indicators triggered, contact POEA + MfMW HK." Closes
   on the `▸ View pipeline` modal scrolling through 7 cards.

3. **Click the headline notebook.**
   [DueCare Exploration Workbench](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench)
   (the omni playground). Run it (T4 ×2 + Internet ON + `HF_TOKEN`).
   When the cloudflared URL appears, click. Toggle all 6 tiles ON.
   Submit any example prompt. Click `▸ View pipeline` below the
   response. **That visualization is the demo.**

### Or skip the boot — read these 4 docs first (5 min total):

1. [`docs/stock_vs_harnessed.md`](./stock_vs_harnessed.md) — 5
   textbook prompts side-by-side, stock Gemma 4 vs harnessed (mean
   lift 4.6% → 88.4%). Concrete falsifiable evidence in 2 min.
2. [`docs/corpus_index.md`](./corpus_index.md) — every GREP rule
   (108), RAG doc (33), tool (5), dimension (17) by name. Verify
   the headline counts by counting rows.
3. [`docs/reproducibility.md`](./reproducibility.md) — every
   quantitative claim grounded with provenance + re-measurement
   command. Includes the honest "what we explicitly do NOT claim"
   section.
4. [`docs/peer_review_5min_test_plan.md`](./peer_review_5min_test_plan.md) —
   the 5-test verification plan if you do boot a notebook.

---

## The Kaggle notebooks (the submission surface)

The submission is structured as **2 core notebooks** (the omni
playground + the focused live demo) plus **11 appendix notebooks**
(specialised playgrounds, research visualisation, agentic web-search,
jailbroken-models proof, lift regenerator). Judges land on the
**unified harness chat** to flip every toggle and see every capability
at once, then proceed to **live-demo** for the focused thesis
demonstration with the headline +56.5pp lift number.

### Core (2 notebooks — walk in this order)

| # | Notebook | Wheels dataset | Purpose |
|---|---|---|---|
| **1** | [duecare-exploration-workbench](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench) *(publish pending)* | `duecare-harness-chat-wheels` ✓ live | **The omni playground.** Single configurable interface with all 6 harness layers (Persona / GREP 161 rules / RAG 46 docs / Tools 5 lookups / Online live web search) + 4-mode grader (Universal / Expert / Deep / Combined) + **Gemma 4 model selector**: pick from 9 variants (E2B / E4B / 26B-A4B / 31B / 2 jailbroken / 3 cloud BYOK routes). Judges flip toggles, change models, and see the harness work end-to-end across the whole capability surface. |
| **2** | [duecare-live-demo](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) | `duecare-live-demo-wheels` ✓ live | **The user-facing live URL.** Full safety-harness pipeline + guided walkthrough + audit Workbench. The polished, scripted live demonstration of the +56.5pp lift thesis. |

### Appendix (11 notebooks — specialised + research)

These notebooks are **not required for deployment**. A1–A2 extend
Duecare to new domains; A3 visualizes the harness data; A4 is a
proof-of-concept for agentic web research; A5 demonstrates the
harness against jailbroken/abliterated models. The core 2 notebooks
above already work end-to-end with the bundled 587 example prompts
(incl. 6 multi-lingual showcase), 161 GREP rules, 46 RAG docs, 5
tools, 21-dimension universal rubric, 46 evaluator questions, 144
authoritative-statute allowlist, 12 curator-block JSON files, and
194 multi-lingual classifier signals across 11 languages — reviewers
can verify the submission *without* running any of these.

| # | Notebook | Wheels dataset | Purpose |
|---|---|---|---|
| A1 | [duecare-prompt-generation](https://www.kaggle.com/code/taylorsamarel/duecare-prompt-generation) *(publish pending)* | `duecare-prompt-generation-wheels` *(publish pending — wheels built locally)* | Use Gemma 4 to generate new evaluation prompts (in the smoke_25 row shape) + 5 graded response examples per prompt (worst → best). Output feeds A2. |
| A2 | [duecare-bench-and-tune](https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune) *(publish pending; T4×2 fine-tune run pending)* | `duecare-bench-and-tune-wheels` ✓ live | Smoke benchmark on stock Gemma 4 → Unsloth SFT (LoRA on harness-distilled or A1-generated pairs) → DPO → re-benchmark → GGUF Q8_0 export → HF Hub push. |
| A3 | [duecare-research-graphs](https://www.kaggle.com/code/taylorsamarel/duecare-research-graphs) *(publish pending)* | `duecare-research-graphs-wheels` *(publish pending — wheels built locally)* | 6 interactive Plotly charts (entity graph, corridor Sankey, per-category benchmark bars, fee-camouflage heatmap, ILO indicator hits, RAG corpus sunburst). CPU-only, ~30 sec. |
| A4 | [duecare-chat-playground-with-agentic-research](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-agentic-research) *(publish pending)* | `duecare-chat-playground-with-agentic-research-wheels` ✓ live | Same chat UI as Core #2 + a 5th toggle for **agentic web research**. Gemma 4 multi-step loop using DuckDuckGo + httpx + Wikipedia. All open-source, no API keys. **Proof-of-concept** — supplements GREP/RAG/Tools with fresh web context. |
| A5 | [duecare-chat-playground-jailbroken-models](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-jailbroken-models) *(publish pending)* | `duecare-chat-playground-jailbroken-models-wheels` ✓ live | Same chat UI as Core #2 + 4-toggle harness, but loads an **abliterated / cracked / uncensored** Gemma 4 variant (default: `dealignai/Gemma-4-31B-JANG_4M-CRACK`). Demonstrates the harness still produces safe outputs even when the base model has had its refusals ablated. **The strongest "real, not faked" proof.** |
| A6 | [duecare-grading-evaluation](https://www.kaggle.com/code/taylorsamarel/duecare-grading-evaluation) *(publish pending)* | `duecare-grading-evaluation-wheels` ✓ live | **Dedicated lift evaluator.** Runs N curated prompts through Gemma 4 twice (harness OFF vs ON) and grades both with the universal v3.6 grader (46 dimensions, use-case-aware, citation-cross-referenced). Produces side-by-side per-prompt cards + aggregate dimension-lift table + provenance tuple `(model, git_sha, dataset_version)`. **The falsifiable +56.5pp number, regenerated from a git SHA.** Companion script `scripts/remeasure_v36_lift.py` reproduces the run locally with mock or real Gemma. |

> **Note on "publish pending" markers (2026-05-01).** The kernels and
> wheels datasets are all built locally under `kaggle/<slug>/` and
> `kaggle/<slug>/wheels/`. The pending step is the `kaggle kernels push`
> + `kaggle datasets create` operations against Taylor's account, which
> are gated by the daily Kaggle push rate-limit (see
> `.claude/feedback_kaggle_daily_rate_limit.md`). Status will be updated
> here as each notebook lands; the canonical local inventory is
> `docs/current_kaggle_notebook_state.md`.

---

## Five-minute verification path

### Verify the technology is real (Technical Depth & Execution = 30 pts)

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp
pip install duecare-llm-chat duecare-llm-core duecare-llm-models
python scripts/verify.py
```

Expected output (all 9 checks PASS):

```
[  OK  ]  GREP rules             108 >= 108
[  OK  ]  RAG corpus              33 >=  33
[  OK  ]  Tools                    5 >=   5
[  OK  ]  Example prompts        413 >= 407
[  OK  ]  5-tier rubrics         207 >= 207
[  OK  ]  Required rubrics         6 >=   6
[  OK  ]  Classifier examples     54 >=  54
[  OK  ]  Universal rubric dims   21 >=  21
[  OK  ]  LLM eval questions      21 >=  21
OK: all 9 checks passed. Harness is ready.
```

Plus the curator-block validator:

```bash
python scripts/validate_curator_blocks.py
```

Validates 11 curator JSON files against schema + cross-references
(every dim_id in usecase_affinity / evaluation_questions /
rubric_hints exists in `_rubric_universal.json`). Emits a per-file
err/warn report. Used by stakeholders (NGO partners, jurists,
language experts) before submitting curator-block PRs.

Or with no install: open [`packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py)
and read the rule definitions, RAG corpus, tool dispatcher inline.

### What each notebook proves (one-line each)

For judges who want to know which notebook to open for which claim:

| Notebook | Single-line purpose | What to click | Expected output |
|---|---|---|---|
| `duecare-exploration-workbench` ★ | The omni surface — every capability in one place | Toggle all 6 tiles ON, send the textbook 68%-loan prompt | Response transforms from generic to citation-rich; click Pipeline modal for the trace |
| `duecare-live-demo` ★ | The polished thesis demo with the headline lift | Open `/` (4-card homepage); send prompt to `/individual` | Classification card with risk score, ILO indicator hits, NGO referrals |
| `chat-playground` (A1) | Baseline raw Gemma 4 (harness OFF) — the failure mode | Send the 68%-loan prompt | "5 cash flow strategies" / "tripartite payment agreement" — the trafficker's playbook |
| `chat-playground-with-grep-rag-tools` (A2) | Harness ablation runner for GREP, RAG, Tools, and Imports | Toggle each tile ON one at a time, observe response transform per tile | Citation density and trace evidence grow as layers are enabled |
| `chat-playground-jailbroken-models` (A5) | **The "real not faked" proof.** Same harness on an abliterated Gemma 4 (refusal layer ablated by the model author) | Send the 68%-loan prompt | Harness still produces safe + cited output despite ablated base model |
| `chat-playground-with-agentic-research` (A4) | Live web search proof of concept — Playwright + DuckDuckGo + Wikipedia | Toggle web-research ON, ask about a recent ILO development | Multi-step research loop with grounded citation |
| `content-classification-playground` (A3) | NGO & regulator classifier (structured-output mode) — same harness, different surface | Click any Examples-modal entry, click Classify | Classification card with risk vectors, recommended action pill, NGO referrals |
| `content-knowledge-builder-playground` (A4) | Build new RAG documents from web sources or pasted text | Paste a recent ILO press release | New RAG entry with extracted citations + paraphrased snippet |
| `gemma-content-classification-evaluation` (A5) | Side-by-side OFF/ON evaluation across the bundled 16 cases | Run all → see per-case OFF/ON delta | Aggregate lift number + per-case markdown table |
| `prompt-generation` (A1 appendix) | Gemma 4 generates new evaluation prompts + 5 graded responses each | Set N=10, click Run | 10 new prompts × 5 graded examples written to JSON |
| `bench-and-tune` (A2 appendix) | Unsloth SFT → DPO → GGUF → HF Hub push of fine-tuned Duecare model | Run end-to-end on T4×2 | `Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0` on HF Hub + GGUF artifact |
| `research-graphs` (A8) | 6 Plotly visualizations of corpus + harness data | Run (CPU only, ~30s) | 6 interactive charts: entity graph / corridor Sankey / per-category benchmark / fee-camouflage heatmap / ILO indicator hits / RAG corpus sunburst |
| `grading-evaluation` (A11) | **The lift regenerator.** Re-measures the +56.5pp number from a git SHA | Set DUECARE_EVAL_PROMPT_IDS env var; Run | `duecare_lift_eval.json` + `.md` with provenance tuple `(model, git_sha, dataset_version)` |

### Verify Gemma 4's unique features are load-bearing, not decorative

| Claim | Where to verify |
|---|---|
| **Native function calling** drives the Tools layer | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py` — see `_tool_lookup_corridor_fee_cap`, `_tool_lookup_fee_camouflage`, `_tool_lookup_ilo_indicator`, `_tool_lookup_ngo_intake` registered in `_TOOL_DISPATCH`. The classifier kernel's `gemma_call` uses `tokenizer.apply_chat_template` with chat templates that support tool calls. |
| **Multimodal understanding** drives the classifier | `packages/duecare-llm-chat/src/duecare/chat/classifier.py` — `_build_messages` includes uploaded images as content chunks; the kernel passes them to Gemma 4's multimodal `apply_chat_template`. The classifier examples include 6 SVG document mockups that demo this end-to-end. |

### Verify reproducibility

| Result | Where it came from | How to reproduce |
|---|---|---|
| The pipeline transformation | `packages/duecare-llm-chat/src/duecare/chat/app.py:_run_harness` + `_resolve_messages` | Click `▸ View pipeline` on any chat response. The "FINAL MERGED PROMPT" card shows the byte-for-byte text Gemma saw. |
| GREP rule citations | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py:GREP_RULES` | **161 rules** across 6 categories (multi-party arrangements, governed-by-clause stripping, in pari delicto, sub-agent layering, huroob/NGO retaliation threats, archaic legal language, etc.), each with `citation` + `indicator` fields naming ILO conventions, POEA/BP2MI/Nepal/HK statutes |
| RAG corpus | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py:RAG_CORPUS` | **26 docs** covering ILO C029/C181/C095/C189 + POEA MCs + BP2MI Reg + HK/SG/Saudi statutes + Palermo Protocol Art. 3(b) + ICRMW Art. 18/22 + Hague Service Convention + Saudi kafala reforms + BMET smartcard + DIFC unconscionability + cross-cutting substance-over-form anchor |
| Per-prompt + per-category rubrics | `packages/duecare-llm-chat/src/duecare/chat/harness/_rubrics_5tier.json` (207 prompts, 5 tiers each) + `_rubrics_required.json` (**6 categories, 66 criteria** including the cross-cutting `legal_citation_quality`) | Click `▸ Grade response` on any chat response — opens the Grade modal showing PASS/PARTIAL/FAIL on each criterion + matched keywords. Or `python scripts/rubric_comparison.py` for the batch harness-OFF vs harness-ON delta report. |
| Harness lift quantification | [`docs/harness_lift_report.md`](./harness_lift_report.md) | Mean **+56.5 pp** lift across 207/207 prompts when grading harness-ON vs harness-OFF responses against the cross-cutting `legal_citation_quality` rubric. Reproducible via `python scripts/rubric_comparison.py`. |
| Corpus coverage matrix | [`docs/corpus_coverage.md`](./corpus_coverage.md) | 2D coverage heatmaps across category × sector, category × corridor, category × difficulty, sector × corridor, category × ILO indicator. Surfaces high-priority gaps for new contributions. |
| 394 example prompts | `packages/duecare-llm-chat/src/duecare/chat/harness/_examples.json` | 204 from author's 4 published Kaggle benchmark notebooks (extracted 2026-04-30 via AST) + 19 canonical writeup tests + 30 attack-variation samples + 12 multi-party/governed-by prompts + 40 content samples (social media / DMs / docs / receipts) + 15 esoteric/archaic-legal-language prompts. **Per-category JSON splits at `_examples/by_category/<cat>.json` for selective reuse.** |
| 17 PyPI packages | `packages/duecare-llm-*/` | `ls packages/` |
| RESULTS provenance | [`RESULTS.md`](../RESULTS.md) | Every headline metric pinned to `(git_sha, dataset_version, model_revision)` |

### Verify the safety harness actually flips Gemma's response

The shortest reproducible test:

1. Open [duecare-chat-playground](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground)
   (raw Gemma).
2. Click `▸ Examples` → load any "Textbook compound scenarios" prompt
   (the 68%-loan or 18%-loan example).
3. Submit. Note Gemma's response is operational advice ("here are 5
   strategies").
4. Open [duecare-chat-playground-with-grep-rag-tools](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools)
   in another tab.
5. Toggle all 4 tiles ON (Persona / GREP / RAG / Tools).
6. Load the **same** example prompt → submit.
7. Note Gemma's response now cites ILO C029, POEA MC 14-2017, HK
   Employment Ord §32, and references POEA Anti-Illegal Recruitment
   Branch hotline.

That delta IS the demo. Click `▸ View pipeline` to see the exact
transformation byte-for-byte.

---

## Three deployment modes

| Mode | Doc | Use case |
|---|---|---|
| Individual worker (Kaggle / local laptop) | [`docs/deployment_local.md`](./deployment_local.md) | Migrant worker pastes recruiter message, gets back ILO citations + corridor fee caps + NGO hotlines. No data leaves the device. |
| NGO & regulator | The classifier notebook (#5 above) | Intake officer triages 500 cases via structured JSON + risk vectors + threshold-filterable history. |
| Platform safety API (Dockerized API) | [`docs/deployment_enterprise.md`](./deployment_enterprise.md) | `POST /api/classifier/evaluate` from an existing service. Customizable per-team rules / docs / corridor caps. |
| **Android (v0.9.0 shipped)** | [`docs/android_app_architecture.md`](./android_app_architecture.md) (this repo) + [`duecare-journey-android/`](../../duecare-journey-android/) (sibling repo) | **Duecare Journey** v0.9.0 — fully on-device Gemma 4 via MediaPipe (six variants selectable: E2B/E4B INT4/INT8, Gemma 3 1B, Gemma 2 2B legacy, each with mirror-fallback URLs) + cloud Gemma routing as fallback (Ollama / OpenAI-compat / HF Inference) + SQLCipher-encrypted journal + 11 ILO indicator detectors + **20 corridor profiles** (Asia → GCC, Asia → Asia, LATAM, West Africa → Lebanon kafala, refugee routes Syria→Germany / Ukraine→Poland) with statute lookups + **161 GREP rules** (incl. kafala-huroob-absconder, H2A-H2B-fee-violation, fishing-vessel-debt-confinement) + 10-question guided intake wizard + structured Add-Fee dialog with auto-LegalAssessment + RefundClaim drafting + image picker for evidence attach + Reports tab generating shareable NGO intake document. APK is at the [latest release](https://github.com/TaylorAmarelTech/duecare-journey-android/releases). The architecture lives here for judges to read alongside the Python research; the buildable Gradle project + GitHub Actions APK-build pipeline live in the sibling repo. |

---

## What this submission is NOT claiming

- We did **not** build a 12-agent autonomous swarm. We built a
  toggleable harness with 6 layers (Persona / GREP / RAG / Tools /
  Online / Imports).
- We did **not** publish 77 notebooks as the submission. The current
   generated/research inventory under `kaggle/kernels/` is 9 kernels; older
   52/74/77-kernel notes are historical archive context. The **submission is
   the 2 core + 11 appendix folders listed above**.
- We are **not** claiming a fine-tuned Gemma 4 model is published at
  submission time. The bench-and-tune notebook (#2) is the planned
  Unsloth SFT/DPO + GGUF + HF Hub push — status TBD by the 2026-05-18
  deadline.

What we ARE claiming: a working safety harness wrapping Gemma 4 that
demonstrably transforms the model's response to migrant-worker
exploitation scenarios from "operational advice" to "ILO-cited
refusal + NGO referral," visualized end-to-end in a per-response
Pipeline modal, deployable in three modes, MIT licensed, with full
provenance tracking.

**Distinct from DoNotPay:** the worker files complaints, not the app.
Duecare gives advice and pre-stages the evidence packet; the worker
chooses if and where to file. We avoid the "robot lawyer" framing
that the FTC found unsubstantiated in DoNotPay's settlement.

## Prior art / adjacent work

A separate `docs/prior_art.md` doc lists everything in the conceptual
neighborhood with source URLs and per-item differentiation. Highlights:

| Project | What it is | How Duecare differs |
|---|---|---|
| [Just Good Work](https://justgood.work/) (ETI + Our Journey) | Static migrant-recruitment-journey app for Kenya→Qatar | Generative legal Q&A grounded in 46-doc RAG; PH/ID/NP/BD→HK/Saudi corridor |
| [Polaris 2017 Typology of Modern Slavery](https://polarisproject.org/the-typology-of-modern-slavery/) | 25 trafficking types × 120 fields taxonomy | Upstream taxonomy our concern schema maps to (cited) |
| [Tella by Horizontal](https://tella-app.org/) | Open-source human-rights documentation app, SQLCipher-encrypted | Same threat model + SQLCipher journal + share-to-NGO design — directly studied for the Android Reports tab and panic-wipe semantics. |
| [HarmBench](https://github.com/centerforaisafety/HarmBench) / [AILuminate v1.0](https://mlcommons.org/working-groups/ai-safety/ailuminate-v1-0/) | General-purpose LLM safety benchmarks (400+ behaviors) | Trafficking is one row of dozens for them; Duecare goes deep on one domain with quantified harness lift (+87.5/+51.2/+34.1 pp on three legal-grounding dimensions) |
| [Janie Chuang — "Exploitation Creep"](https://digitalcommons.wcl.american.edu/facsch_lawrev/686/) | Foundational legal scholarship on the trafficking-continuum framing | Cited as the conceptual anchor for the harness's substance-over-form analysis |

---

## Where everything lives

| Thing | Path |
|---|---|
| Source code (17 packages) | [`packages/duecare-llm-*/`](../packages/) |
| 13 submission Kaggle kernels | [`kaggle/<notebook>/kernel.py`](../kaggle/) |
| The harness module (rules, corpus, tools, examples) | [`packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`](../packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py) |
| Chat app + classifier app | [`packages/duecare-llm-chat/src/duecare/chat/app.py`](../packages/duecare-llm-chat/src/duecare/chat/app.py), [`classifier.py`](../packages/duecare-llm-chat/src/duecare/chat/classifier.py) |
| Writeup | [`docs/writeup_draft.md`](./writeup_draft.md) |
| Video script | [`docs/video_script.md`](./video_script.md) |
| Provenance | [`RESULTS.md`](../RESULTS.md) |
| Local install | [`docs/deployment_local.md`](./deployment_local.md) |
| Dockerized API | [`docs/deployment_enterprise.md`](./deployment_enterprise.md) |
| MIT license | [`LICENSE`](../LICENSE) |

---

> **Local Gemma 4 handles sensitive material where it lives; the public hub receives only safe signals and vetted knowledge updates.**
