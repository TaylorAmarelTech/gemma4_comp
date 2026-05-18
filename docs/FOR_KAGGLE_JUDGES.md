# For Hackathon Judges - Verify DueCare in 5 minutes

> **Canonical reviewer entry doc:** [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md).
> This page is the hackathon-specific quick path. The peer-review doc is
> the broader verification roster aimed at any reviewer (academic,
> journalist, policy analyst, NGO technical lead, or hackathon judge).
> Both link to the same kernels, packs, and live surfaces; this doc
> focuses on the 5-minute hackathon-rubric verification flow.

> The DueCare submission for the Gemma 4 Good Hackathon
> (2026-04-02 → 2026-05-18). This doc exists so you don't have to
> spelunk the repo to verify any claim — every claim below points to
> a specific file, kernel, or live URL.

> **In a hurry?** Run `kaggle/02-live-demo/kernel.py`, open `/start`,
> and click **Project slides**. The deck works without a model; live
> Gemma 4 is used for chat and optional Bulk File Review edge creation.

## What it is, in one paragraph

**DueCare is a Gemma 4 safety ecosystem for migrant-worker
protection.** This submission has three active Kaggle kernels: the
DueCare App workbench, the DueCare Live Demo, and DueCare Fine-tuning
and Evaluation. Together they prove the same end-to-end substrate:
Gemma 4 runtime, safety harness, Bulk File Review case analysis,
graph extraction, anonymized sharing, contact routing, and the A-00
stock/fine-tuned/harness evaluation matrix. The public hub at
[duecare-ai.com](https://duecare-ai.com) is the companion website for
the judges-facing story, kernel links, knowledge-pack registry, and
anonymized signal intake. Code for the hub is in
[`apps/duecare-ai.com/`](../apps/duecare-ai.com/) and deploys to Render
via the repo-root `render.yaml`.

The harness wraps Gemma 4 with retrieval (BM25 + optional hybrid
dense-retrieval), structural document chunking, 165+ hand-curated
trafficking-pattern rules, a 55+ document RAG corpus + citation
graph, and a multi-mode grading stack — turning stock Gemma into a
domain-specialised LLM safety judge for migrant-worker trafficking
scenarios. The five canonical lanes are **(1) Platform safety,
(2) NGO & regulator, (3) Individual worker / mobile, (4) Researcher,
and (5) Developer / integration partner**. Those five lanes support
three outcomes: prevent exploitation before it spreads, assist victims
and at-risk workers, and help stakeholders understand what is happening
and why. Filipino overseas workers are one demo persona, not the product
category. Built specifically for partners who cannot send sensitive
case data to frontier APIs, with validated local/demo surfaces now
and a sibling DueCare Journey Android APK proving the LiteRT/offline
edge path.

**Notebook status note:** the current judge-facing Kaggle path is the
three-kernel set in `kaggle/_INDEX.md`: exploration workbench, live demo, and
DueCare Fine-tuning and Evaluation. Retired notebook-era surfaces are historical.

## Where to verify each claim

| Claim | Verify at |
|---|---|
| **Multi-dimension universal rubric** | `packages/duecare-llm-chat/src/duecare/chat/harness/_rubric_universal.json` |
| **165+ GREP rules across active categories** (crypto / scam-compound / gig-economy / BNPL / Ukrainian + Afghan corridors / Pacific RSE-PALM / sub-Saharan / EU posted workers / climate-displaced / intra-community / domestic-to-sex-work transition / cross-platform signals) | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py` (`GREP_RULES = [...]`) |
| **Large example prompt library across audience buckets** (model_capability / enterprise_moderation / ngo_intake / individual_query / research / image_prompts / data_intelligence / regulator_audit) | `packages/duecare-llm-chat/src/duecare/chat/harness/_examples.json` |
| **Bundled CC0 synthetic-evidence images + structured-post JSONs** with watermarks + sidecar JSONs + cross-platform-signal links | `packages/duecare-llm-chat/src/duecare/chat/static/synthetic/` + `static/synthetic/posts/` |
| **55+ document curated RAG corpus** (ILO C29/C95/C97/C143/C181/C188/C189/C190/P029, fair-recruitment guidance, POEA/BP2MI/Nepal/HK/SG/UAE statutes, WHO Global Code, EU 2024 ATD amendment, ASEAN ACTIP, CoE 197, CEDAW GR 38, UNCRC, UNODC/IOM/FATF typologies, Pacific Climate Mobility, Bali Process) | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py` (`RAG_CORPUS = [...]`) |
| **Citation graph** for 1-hop graph expansion at retrieval time | `packages/duecare-llm-chat/src/duecare/chat/harness/_citations.json` |
| **Adversarial validation suite across multiple attack families** including new structured-data-attack / image-injection / regulator-impersonation / multilingual-jailbreak | `scripts/adversarial_validate.py` + `reports/adversarial_*.md` (run output) |
| **`evaluator_call` hook for separating LLM-judge model from chat model** (v0.13.0; abliterated / frontier / larger-Gemma patterns supported, Kaggle-default in-process self-grade due to VRAM) | `packages/duecare-llm-chat/src/duecare/chat/app.py:_evaluator_model_call` |
| **Hybrid retrieval** — BM25 + optional dense + RRF fusion, with reranker hook | `app.py:_hybrid_fuse_with_dense` + `kernel_helpers/embedding.py` |
| **Path tracing** — every retrieval-pipeline stage logged | `app.py:_path_trace_record` + chat UI's "RETRIEVAL PATH TRACE" card |
| **A/B Compare tab** — same prompt, two harness configurations, side-by-side grades | `kaggle/01-duecare-exploration-workbench/kernel.py` live; UI button next to "About" |
| **License + attribution** — every bundled asset, every model, every third-party reference | `LICENSES.md` |
| **Public hub** — knowledge-pack registry + anonymized signal intake + public-source proposal intake | [duecare-ai.com](https://duecare-ai.com) (code at [`apps/duecare-ai.com/`](../apps/duecare-ai.com/), deployed via repo-root `render.yaml`) |
| **Hub API surface** — `GET /api/hub/knowledge-packs`, `POST /api/hub/signals`, `POST /api/hub/opencrawl/updates`, `GET /api/hub/trends`, `GET /api/hub/status`, `GET /api/health` | [duecare-ai.com/docs](https://duecare-ai.com/docs) (FastAPI auto-generated OpenAPI) |
| **Recording-grade deck and demo routes** | `kaggle/02-live-demo/kernel.py` prints a `*.trycloudflare.com` tunnel; open `/start`, `/slides`, and `/wb-static/process.html` |
| **Video script and recording path** | `docs/video_script.md` plus `/slides/setup` or `scripts/prebake_slide_cached_io.py` for the cached worker-question row |
| **Fine-tuned adapter evidence** | exported by the A-00 pipeline when training is enabled; see `/kaggle/working` report and manifest |
| **LiteRT / on-device path** | sibling DueCare Journey Android APK and bundled harness manifest |

## Hackathon track qualification

Competition overview alignment checked on 2026-05-18 against public
Gemma 4 Good summaries: the project should be filed under Impact
Track -> Safety & Trust, with Special Technology evidence for Unsloth
and LiteRT. The same overview emphasizes local frontier intelligence,
native function calling, multimodal understanding, a working demo,
public code, technical analysis, and a 3-minute video; the repository
maps each requirement to a concrete surface below.

| Track | Why this submission qualifies | Anchored to |
|---|---|---|
| **Impact Track → Safety & Trust** | Core concept is LLM safety for the most vulnerable migrant-worker populations. The harness directly targets known trafficking-detection failure modes. | The 50-prompt adversarial suite + the harness-on-vs-harness-off A/B comparison. |
| **Special Tech → Unsloth** | Fine-tune is via Unsloth + LoRA on Gemma 4. A-00 preserves the training config, checkpoints, adapter path, and comparison report. | `kaggle/A-00-omni-experiment-workbench/kernel.py` + exported A-00 report bundle |
| **Special Tech → LiteRT** | The sibling Android app bundles harness metadata and uses the LiteRT path for the worker-facing offline surface. | `C:/Users/amare/OneDrive/Documents/duecare-journey-android` + GitHub Actions APK artifact |
| **Main Track** | Pursued in parallel; depends on overall execution + video. | All of the above bundled. |

## Five-minute walkthrough

Run `kaggle/02-live-demo/kernel.py` or open the current Cloudflare URL
printed by that kernel. The route sequence below is stable:

1. **Open `/start`.** Confirm the two-tile landing: Project slides and
   Workbench.
2. **Open `/slides`.** Walk the 23-slide deck. The demo slides use
   cached replay controls, so a recording does not wait on GPU output.
3. **Open `/slides/setup`** if you want to refresh the cached worker
   chat row, or use `scripts/prebake_slide_cached_io.py` to preload it.
4. **Open `/wb-static/process.html`.** Drop
   `case_files_streamlined_demo.zip`, then watch upload, processing,
   review, graph creation, and optional local Gemma 4 edge generation.
5. **Ask a graph question** after confirming extracted intelligence.
   The answer should cite row IDs, evidence edges, and extracted
   entities from the local staging directory.
6. **Open the DueCare App kernel** for the full chat harness and A/B
   comparison surfaces.
7. **Open the A-00 kernel report** to verify the stock, harness,
   fine-tuned, and fine-tuned-plus-harness evaluation matrix.

If you can do all 7 steps, you have empirical verification of the
writeup's live-demo, local-processing, and evaluation claims.

## Design note: which model grades the LLM-based scoring?

The chat package's "LLM-Based" and "Combined" grading modes (G-Eval /
MT-Bench / Auto-J style) ask a model one yes/no question per rubric
dimension. **In this Kaggle deployment**, that is the SAME Gemma
instance loaded for chat — an on-device self-grade. The deployment
constraint that forces this choice is real and worth naming
explicitly:

> **Kaggle T4 / dual-T4 sessions are VRAM-bounded.** The loaded chat
> model (Gemma 4 E2B / E4B / 26B-A4B / 31B variants) saturates VRAM
> at load time. Holding a SECOND model in memory for grading
> (abliterated variant, frontier-via-API stub, larger Gemma) would
> require unloading the chat model mid-session — slow, breaks user
> state, and undermines the live-demo flow that judges click through.
> For the hackathon Kaggle deployment we therefore run in-process
> self-grade by necessity, not by design preference.

The chat package nevertheless treats the chat model and the LLM-judge
model as independently-configurable hooks (the `evaluator_call`
parameter on `create_app`, v0.14.2+). The hook is documented
architecture for **production deployments outside the Kaggle memory
constraint** where you have headroom for two model loads or a network
call to a separate judge process. Three production patterns the hook
supports — commentary only on this submission since none of them run
in the Kaggle session:

1. **Frontier judge** (GPT-4 / Claude 3.5 / Gemini 1.5 Pro) — gold-
   standard accuracy via API. The chat model stays on-device for the
   privacy-preserving Individual worker use case; the judge runs separately,
   the G-Eval / MT-Bench / Auto-J methodology. Network requirement
   means it doesn't fit the on-device-only Kaggle exercise.
2. **Abliterated Gemma** (e.g. `dealignai/Gemma-4-31B-JANG_4M-CRACK`)
   — engages with adversarial responses the safety-tuned chat model
   would refuse to grade. Materially better for adversarial-suite
   scoring at production scale where you have VRAM headroom for two
   model loads.
3. **Larger Gemma** (e.g. Gemma 4 31B-it grading while chat runs E2B)
   — better grading without giving up the chat-side speed. Same
   VRAM-headroom precondition.

The Kaggle-deployed kernel ships with `evaluator_call=None` (the
default) so the judges-time experience matches what the writeup
claims. The hook stays as documented architecture for the
post-hackathon production-deployment story. To swap (in a non-Kaggle
deployment with VRAM headroom), one line in `kernel.py`:

```python
app = create_app(
    gemma_call=loaded.backend,             # E4B for chat
    evaluator_call=heavier_loaded.backend, # 31B-abliterated for grading
    # NOT advisable on Kaggle — would OOM the session.
    ...,
)
```

## What this submission deliberately does NOT do

- It does not bundle real-person evidence imagery. Every image
  shipped in the wheel is auto-generated CC0 synthetic with visible
  watermark + composite character names + reserved-for-fictional-use
  phone-number prefixes. See `LICENSES.md` for the synthetic-
  disclaimer.
- It does not claim to detect every trafficking pattern in the world.
   165+ GREP rules + 55+ RAG docs + 46 citation edges cover the major
  documented vectors well, but new patterns appear weekly — the
  curator-block JSON pattern lets stakeholders contribute updates
  without a code change.
- It does not replace human caseworkers. The harness's design
  explicitly routes to named NGOs / regulators / embassies rather
  than offering itself as the answer.

## Reading order if you have 30 minutes

1. `docs/writeup_draft.md` — the 1,500-word submission writeup
2. `LICENSES.md` — full attribution + license declarations
3. `docs/USER_TODO.md` — author's submission-day checklist
4. `reports/adversarial_<latest>.md` — the empirical evidence
5. The current Cloudflare URL printed by `kaggle/02-live-demo/kernel.py`

## Reading order if you have 5 minutes

1. This document
2. The Kaggle live demo URL (technical depth)
3. [duecare-ai.com](https://duecare-ai.com) (platform infrastructure)
4. The video
