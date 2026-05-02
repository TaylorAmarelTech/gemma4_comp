# For Judges — Verify Duecare in 5 Minutes

> A focused walkthrough for Gemma 4 Good Hackathon judges. This
> document exists so you don't have to spelunk the codebase to verify
> our claims. Every claim in the [writeup](./writeup_draft.md) and
> [video](./video_script.md) is backed by a file or a Kaggle notebook
> link below.

---

## The 30-second pitch

Stock Gemma 4 fails predictably on migrant-worker exploitation
scenarios — it cites no ILO conventions, recognizes no camouflaged
recruitment fees, and gives traffickers operational advice. **Duecare
wraps Gemma 4 with four toggleable safety layers** (Persona, GREP,
RAG, Tools) and shows the *exact* prompt transformation in a
per-response Pipeline modal.

The product north star is **harm reduction, not paternalism**: the
chat tells the worker which statute the fee violates and which NGO
handles refund claims for that corridor. The worker may refuse —
preventing the harm — or pay anyway under their corridor's real
constraints, in which case the journal captures the receipt + the
recruiter's POEA license number + the controlling statute and
pre-stages the refund-claim packet.

Same harness powers a **chat playground** for individual workers and
a **structured-output classifier** for NGO triage dashboards. Ships
as **6 core public Kaggle notebooks + 5 appendix notebooks** + **17
PyPI packages** + an **on-device Android companion** (LiteRT, v0.1.0
APK published). MIT licensed. Runs on a laptop. Zero data egress.

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
those citations trace directly back to the bundled 26-doc RAG corpus
or 37-rule GREP catalog.

Reproduce: `python scripts/rubric_comparison.py`.

---

## Two-minute verification path

If you have two minutes to decide if this is real:

1. **Read the writeup.** [`docs/writeup_draft.md`](./writeup_draft.md)
   (1,437 words, under the 1,500-word cap). Frames the problem (3 LLM
   blind spots), the harness (4 layers), the notebooks (6 core + 5 appendix), and the two
   deployment modes.

2. **Watch the video.** Script at [`docs/video_script.md`](./video_script.md)
   (2:50 target). Opens with Maria (a composite character, labeled as
   such). Headline beat at 0:35–1:50: cursor clicks Persona / GREP /
   RAG / Tools tiles ON one at a time, sends the textbook 68%-loan
   prompt, response transforms from "5 cash flow strategies" to "5 ILO
   indicators triggered, contact POEA + MfMW HK." Closes on the
   `▸ View pipeline` modal scrolling through 7 cards.

3. **Click the headline notebook.**
   [Duecare Chat Playground with GREP RAG Tools](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools).
   Run it (T4 ×2 + Internet ON + `HF_TOKEN`). When the cloudflared URL
   appears, click. Toggle all 4 tiles ON. Submit any example prompt.
   Click `▸ View pipeline` below the response. **That visualization
   is the demo.**

---

## The Kaggle notebooks (the submission surface)

The submission is structured as **6 core notebooks** (sufficient for
end-user deployment) plus **5 appendix notebooks** (advanced extension
workflows, research visualization, agentic web-research, and a
jailbroken-models proof). Judges should walk the core notebooks IN
ORDER — each builds context for the next. The "What the harness
actually does, quantified" section above already shows the harness
delta as a single table; the core notebooks below are the click-to-
verify version of that claim.

### Core (6 notebooks — walk in order)

The chat playgrounds (1-2) introduce the chat surface. The two
playgrounds (3-4) introduce classification and knowledge-building
each on their own. The classifier dashboard (5) shows the production
NGO shape. The live-demo (6) is the polished combined product.

| # | Notebook | Wheels dataset | Purpose |
|---|---|---|---|
| 1 | [duecare-chat-playground](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground) | `duecare-chat-playground-wheels` | Raw Gemma 4 chat — NO harness. Baseline for the comparison story. |
| 2 | [duecare-chat-playground-with-grep-rag-tools](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools) | `duecare-chat-playground-with-grep-rag-tools-wheels` | **The headline demo.** Same chat UI with 4 toggle tiles + multi-persona library + custom rule additions + 394-prompt Examples library + per-response Pipeline modal. |
| 3 | [duecare-content-classification-playground](https://www.kaggle.com/code/taylorsamarel/duecare-content-classification-playground) *(TBD)* | `duecare-content-classification-playground-wheels` *(TBD)* | Hands-on classification sandbox. 4 schema modes (single-label / multi-label / risk-vector / custom). Shows merged prompt + raw response + parsed JSON. **Pre-live-demo intro to classification.** |
| 4 | [duecare-content-knowledge-builder-playground](https://www.kaggle.com/code/taylorsamarel/duecare-content-knowledge-builder-playground) *(TBD)* | `duecare-content-knowledge-builder-playground-wheels` *(TBD)* | Hands-on knowledge-base sandbox. Add GREP rules + RAG docs; test what fires; export full JSON. **Pre-live-demo intro to knowledge building.** |
| 5 | [duecare-gemma-content-classification-evaluation](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-content-classification-evaluation) | `duecare-gemma-content-classification-evaluation-wheels` | **The polished Agency / NGO dashboard.** Form-based content submission → structured JSON classification with risk vectors + threshold-filterable history queue + 16 example items (6 with SVG document mockups). |
| 6 | [duecare-live-demo](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) | `duecare-live-demo-wheels` | **The user-facing live URL.** Full safety-harness pipeline + 22-slide deck + audit Workbench. Combines classification + knowledge-building (notebooks 3 + 4) into one polished product. |

### Appendix (5 notebooks — advanced extension + research)

These notebooks are **not required for deployment**. A1–A2 extend
Duecare to new domains; A3 visualizes the harness data; A4 is a
proof-of-concept for agentic web research; A5 demonstrates the
harness against jailbroken/abliterated models. The core 6 notebooks
above already work end-to-end with the bundled 394 prompts, 37 GREP
rules, 26 RAG docs, and 207 hand-graded 5-tier rubrics — judges can
verify the submission *without* running any of these.

| # | Notebook | Wheels dataset | Purpose |
|---|---|---|---|
| A1 | [duecare-prompt-generation](https://www.kaggle.com/code/taylorsamarel/duecare-prompt-generation) *(TBD)* | `duecare-prompt-generation-wheels` *(TBD)* | Use Gemma 4 to generate new evaluation prompts (in the smoke_25 row shape) + 5 graded response examples per prompt (worst → best). Output feeds A2. |
| A2 | [duecare-bench-and-tune](https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune) *(TBD)* | `duecare-bench-and-tune-wheels` | Smoke benchmark on stock Gemma 4 → Unsloth SFT (LoRA on harness-distilled or A1-generated pairs) → DPO → re-benchmark → GGUF Q8_0 export → HF Hub push. |
| A3 | [duecare-research-graphs](https://www.kaggle.com/code/taylorsamarel/duecare-research-graphs) *(TBD)* | `duecare-research-graphs-wheels` *(TBD)* | 6 interactive Plotly charts (entity graph, corridor Sankey, per-category benchmark bars, fee-camouflage heatmap, ILO indicator hits, RAG corpus sunburst). CPU-only, ~30 sec. |
| A4 | [duecare-chat-playground-with-agentic-research](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-agentic-research) *(TBD)* | `duecare-chat-playground-with-agentic-research-wheels` ✓ live | Same chat UI as Core #2 + a 5th toggle for **agentic web research**. Gemma 4 multi-step loop using DuckDuckGo + httpx + Wikipedia. All open-source, no API keys. **Proof-of-concept** — supplements GREP/RAG/Tools with fresh web context. |
| A5 | [duecare-chat-playground-jailbroken-models](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-jailbroken-models) *(TBD)* | `duecare-chat-playground-jailbroken-models-wheels` ✓ live | Same chat UI as Core #2 + 4-toggle harness, but loads an **abliterated / cracked / uncensored** Gemma 4 variant (default: `dealignai/Gemma-4-31B-JANG_4M-CRACK`). Demonstrates the harness still produces safe outputs even when the base model has had its refusals ablated. **The strongest "real, not faked" proof.** |

---

## Five-minute verification path

### Verify the technology is real (Technical Depth & Execution = 30 pts)

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp
pip install duecare-llm-chat duecare-llm-core duecare-llm-models
python -c "
from duecare.chat.harness import (
    GREP_RULES, RAG_CORPUS, _TOOL_DISPATCH,
    EXAMPLE_PROMPTS, CLASSIFIER_EXAMPLES,
    RUBRICS_5TIER, RUBRICS_REQUIRED,
)
print(f'GREP rules:           {len(GREP_RULES)}')              # expect 37
print(f'RAG docs:             {len(RAG_CORPUS)}')              # expect 26
print(f'Tools:                {len(_TOOL_DISPATCH)}')          # expect 4
print(f'Example prompts:      {len(EXAMPLE_PROMPTS)}')         # expect 394
print(f'Classifier examples:  {len(CLASSIFIER_EXAMPLES)}')     # expect 16
print(f'5-tier rubrics:       {len(RUBRICS_5TIER)}')           # expect 207
print(f'Required-rubric cats: {len(RUBRICS_REQUIRED)}')        # expect 6
"
```

Or with no install: open [`packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py)
and read the rule definitions, RAG corpus, tool dispatcher inline.

### Verify Gemma 4's unique features are load-bearing, not decorative

| Claim | Where to verify |
|---|---|
| **Native function calling** drives the Tools layer | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py` — see `_tool_lookup_corridor_fee_cap`, `_tool_lookup_fee_camouflage`, `_tool_lookup_ilo_indicator`, `_tool_lookup_ngo_intake` registered in `_TOOL_DISPATCH`. The classifier kernel's `gemma_call` uses `tokenizer.apply_chat_template` with chat templates that support tool calls. |
| **Multimodal understanding** drives the classifier | `packages/duecare-llm-chat/src/duecare/chat/classifier.py` — `_build_messages` includes uploaded images as content chunks; the kernel passes them to Gemma 4's multimodal `apply_chat_template`. The classifier examples include 6 SVG document mockups that demo this end-to-end. |

### Verify reproducibility

| Result | Where it came from | How to reproduce |
|---|---|---|
| The pipeline transformation | `packages/duecare-llm-chat/src/duecare/chat/app.py:_run_harness` + `_resolve_messages` | Click `▸ View pipeline` on any chat response. The "FINAL MERGED PROMPT" card shows the byte-for-byte text Gemma saw. |
| GREP rule citations | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py:GREP_RULES` | **37 rules** across 5 categories (multi-party arrangements, governed-by-clause stripping, in pari delicto, sub-agent layering, huroob/NGO retaliation threats, archaic legal language, etc.), each with `citation` + `indicator` fields naming ILO conventions, POEA/BP2MI/Nepal/HK statutes |
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
| Worker-side (Kaggle / local laptop) | [`docs/deployment_local.md`](./deployment_local.md) | Migrant worker pastes recruiter message, gets back ILO citations + corridor fee caps + NGO hotlines. No data leaves the device. |
| Agency / NGO dashboard | The classifier notebook (#5 above) | Intake officer triages 500 cases via structured JSON + risk vectors + threshold-filterable history. |
| Enterprise integration (Dockerized API) | [`docs/deployment_enterprise.md`](./deployment_enterprise.md) | `POST /api/classifier/evaluate` from your existing service. Customizable per-team rules / docs / corridor caps. |
| **Android (stretch — v1 in development)** | [`docs/android_app_architecture.md`](./android_app_architecture.md) (this repo) + [`duecare-journey-android/`](../../duecare-journey-android/) (sibling repo) | **Duecare Journey** — fully on-device Gemma 4 E2B (LiteRT) + encrypted journal + journey-aware advice + one-tap complaint-packet PDF. The architecture lives here in the Python research repo for judges to read alongside the rest of the submission; the buildable APK skeleton + GitHub Actions APK-build pipeline live in the sibling repo (separated so Android Gradle/SDK tooling doesn't collide with the Python workflow). v1 MVP build lands week of 2026-05-19. |

---

## What this submission is NOT claiming

- We did **not** build a 12-agent autonomous swarm. We built a
  toggleable harness with 4 layers (Persona / GREP / RAG / Tools).
- We did **not** publish 76 notebooks as the submission. The 76-notebook
  research pipeline lives in `kaggle/kernels/` for reproducibility but
  the **submission is the 6 core + 5 appendix notebooks listed above**.
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
| [Just Good Work](https://justgood.work/) (ETI + Our Journey) | Static migrant-recruitment-journey app for Kenya→Qatar | Generative legal Q&A grounded in 26-doc RAG; PH/ID/NP/BD→HK/Saudi corridor |
| [Polaris 2017 Typology of Modern Slavery](https://polarisproject.org/the-typology-of-modern-slavery/) | 25 trafficking types × 120 fields taxonomy | Upstream taxonomy our concern schema maps to (cited) |
| [Tella by Horizontal](https://tella-app.org/) | Open-source human-rights documentation app, SQLCipher-encrypted | Same threat model + SQLCipher journal + share-to-NGO design — our Android v1 MVP studies this directly |
| [HarmBench](https://github.com/centerforaisafety/HarmBench) / [AILuminate v1.0](https://mlcommons.org/working-groups/ai-safety/ailuminate-v1-0/) | General-purpose LLM safety benchmarks (400+ behaviors) | Trafficking is one row of dozens for them; Duecare goes deep on one domain with quantified harness lift (+87.5/+51.2/+34.1 pp on three legal-grounding dimensions) |
| [Janie Chuang — "Exploitation Creep"](https://digitalcommons.wcl.american.edu/facsch_lawrev/686/) | Foundational legal scholarship on the trafficking-continuum framing | Cited as the conceptual anchor for the harness's substance-over-form analysis |

---

## Where everything lives

| Thing | Path |
|---|---|
| Source code (17 packages) | [`packages/duecare-llm-*/`](../packages/) |
| Five Kaggle notebooks | [`kaggle/<notebook>/kernel.py`](../kaggle/) |
| The harness module (rules, corpus, tools, examples) | [`packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`](../packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py) |
| Chat app + classifier app | [`packages/duecare-llm-chat/src/duecare/chat/app.py`](../packages/duecare-llm-chat/src/duecare/chat/app.py), [`classifier.py`](../packages/duecare-llm-chat/src/duecare/chat/classifier.py) |
| Writeup | [`docs/writeup_draft.md`](./writeup_draft.md) |
| Video script | [`docs/video_script.md`](./video_script.md) |
| Provenance | [`RESULTS.md`](../RESULTS.md) |
| Local install | [`docs/deployment_local.md`](./deployment_local.md) |
| Dockerized API | [`docs/deployment_enterprise.md`](./deployment_enterprise.md) |
| MIT license | [`LICENSE`](../LICENSE) |

---

> **Privacy is non-negotiable. So the harness runs on your laptop.**
