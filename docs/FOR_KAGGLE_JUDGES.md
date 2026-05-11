# For Hackathon Judges — Verify Duecare in 5 minutes

> The Duecare submission for the Gemma 4 Good Hackathon
> (2026-04-02 → 2026-05-18). This doc exists so you don't have to
> spelunk the repo to verify any claim — every claim below points to
> a specific file, kernel, or live URL.

## What it is, in one paragraph

**Duecare is a Gemma 4-powered safety infrastructure platform for
migrant-worker protection.** This submission has **two surfaces**:
the **Kaggle live demo** ([kaggle.com/code/taylorsamarel/duecare-harness-chat](https://www.kaggle.com/code/taylorsamarel/duecare-harness-chat))
proves technical depth — Gemma 4 + the 6-toggle harness running
end-to-end — and the **public hub** at
[duecare-ai.com](https://duecare-ai.com) proves platform
infrastructure: knowledge-pack registry, anonymized signal intake,
public-source continuous-update proposals. Code for the hub is in
this repo at [`apps/duecare-ai.com/`](../apps/duecare-ai.com/) and
deploys to Render via the repo-root `render.yaml`. The Kaggle
submission ships the **live core** — Runtime + Harness + Eval
(partial) + Contacts — plus a **prototype Trainer** in the A-07
appendix notebook. The full platform is described by the public
component map (see [`docs/product_definition.md`](product_definition.md)):
Exchange and the Public Information Research Monitor are
**hub-scaffolded**. Their proposal-intake and signal-intake endpoints
exist on the live hub; the autonomous crawler and vetted-pack format
behind them are post-hackathon.
Channels is documented but post-hackathon.

The harness wraps Gemma 4 with retrieval (BM25 + optional hybrid
dense-retrieval), structural document chunking, 161 hand-curated
trafficking-pattern rules, a 46-doc RAG corpus + 46-edge citation
graph, and a 4-mode grading stack — turning stock Gemma into a
domain-specialised LLM safety judge for migrant-worker trafficking
scenarios. The five canonical lanes are **(1) Platform safety,
(2) NGO & regulator, (3) Individual worker / mobile, (4) Researcher,
and (5) Developer / integration partner**. Those five lanes support
three outcomes: prevent exploitation before it spreads, assist victims
and at-risk workers, and help stakeholders understand what is happening
and why. OFWs are a demo persona, not the product category. Built
specifically for partners who cannot send sensitive case data to
frontier APIs, with validated local/demo surfaces now and on-device
GGUF (llama.cpp) plus LiteRT deployment paths tracked for the edge
story.

**Notebook status note:** the final judge-facing path is **13 notebooks**
(2 core + 11 appendix). The two core notebooks are the primary live
entry points; appendix notebooks are transparently marked live or
`publish pending` in the table below until Taylor completes the manual
Kaggle UI publish steps.

## Where to verify each claim

| Claim | Verify at |
|---|---|
| **46 grading dimensions** (universal rubric v3.10) | `packages/duecare-llm-chat/src/duecare/chat/harness/_rubric_universal.json` |
| **161 GREP rules across 31 categories** (crypto / scam-compound / gig-economy / BNPL / Ukrainian + Afghan corridors / Pacific RSE-PALM / sub-Saharan / EU posted workers / climate-displaced / intra-community / domestic-to-sex-work transition / cross-platform signals) | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py` (`GREP_RULES = [...]`) |
| **587 example prompts across 8 audience buckets** (model_capability / enterprise_moderation / ngo_intake / individual_query / research / image_prompts / data_intelligence / regulator_audit) | `packages/duecare-llm-chat/src/duecare/chat/harness/_examples.json` |
| **20 bundled CC0 synthetic-evidence images + 13 structured-post JSONs** with watermarks + sidecar JSONs + cross-platform-signal links | `packages/duecare-llm-chat/src/duecare/chat/static/synthetic/` + `static/synthetic/posts/` |
| **46-doc curated RAG corpus** (ILO C29/C95/C97/C143/C181/C188/C189/C190/P029, POEA/BP2MI/Nepal/HK/SG/UAE statutes, WHO Global Code, EU 2024 ATD amendment, ASEAN ACTIP, CoE 197, CEDAW GR 38, UNCRC, Pacific Climate Mobility, Bali Process) | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py` (`RAG_CORPUS = [...]`) |
| **46-edge citation graph** for 1-hop graph expansion at retrieval time | `packages/duecare-llm-chat/src/duecare/chat/harness/_citations.json` |
| **65-test adversarial validation suite across 16 attack families** including new structured-data-attack / image-injection / regulator-impersonation / multilingual-jailbreak | `scripts/adversarial_validate.py` + `reports/adversarial_*.md` (run output) |
| **`evaluator_call` hook for separating LLM-judge model from chat model** (v0.13.0; abliterated / frontier / larger-Gemma patterns supported, Kaggle-default in-process self-grade due to VRAM) | `packages/duecare-llm-chat/src/duecare/chat/app.py:_evaluator_model_call` |
| **Hybrid retrieval** — BM25 + optional dense + RRF fusion, with reranker hook | `app.py:_hybrid_fuse_with_dense` + `kernel_helpers/embedding.py` |
| **Path tracing** — every retrieval-pipeline stage logged | `app.py:_path_trace_record` + chat UI's "RETRIEVAL PATH TRACE" card |
| **A/B Compare tab** — same prompt, two harness configurations, side-by-side grades | `kaggle/01-duecare-exploration-workbench/kernel.py` live; UI button next to "About" |
| **License + attribution** — every bundled asset, every model, every third-party reference | `LICENSES.md` |
| **Public hub** — knowledge-pack registry + anonymized signal intake + public-source proposal intake | [duecare-ai.com](https://duecare-ai.com) (code at [`apps/duecare-ai.com/`](../apps/duecare-ai.com/), deployed via repo-root `render.yaml`) |
| **Hub API surface** — `GET /api/hub/knowledge-packs`, `POST /api/hub/signals`, `POST /api/hub/opencrawl/updates`, `GET /api/hub/trends`, `GET /api/hub/status`, `GET /api/health` | [duecare-ai.com/docs](https://duecare-ai.com/docs) (FastAPI auto-generated OpenAPI) |
| **Live demo URL** | (set after deployment — see `docs/USER_TODO.md` step 6) |
| **Live YouTube video** | (set after recording — see `docs/USER_TODO.md` step 8) |
| **Fine-tuned weights on HF Hub** | `TaylorScottAmarel/duecare-gemma-4-e4b-safetyjudge-v0.1.0` (after step 5 in USER_TODO) |
| **GGUF for llama.cpp** | exported from the bench-and-tune notebook (see step 5) |

## Hackathon track qualification (subject to verification)

> **Note for the project author:** the Kaggle pages were login-walled
> when the research agent tried to fetch them. The track names below
> match what's documented in project notes; the author should verify
> against the official rules page before submission. See
> `docs/USER_TODO.md` step 0.

| Track | Why this submission qualifies | Anchored to |
|---|---|---|
| **Impact Track → Safety & Trust** | Core concept is LLM safety for the most vulnerable migrant-worker populations. The harness directly targets known trafficking-detection failure modes. | The 50-prompt adversarial suite + the harness-on-vs-harness-off A/B comparison. |
| **Special Tech → Unsloth** | Fine-tune is via Unsloth + LoRA on Gemma 4 E4B. Weights published to HF Hub. | `kaggle/A-07-bench-and-tune/kernel.py` + HF model card |
| **Special Tech → llama.cpp** | Fine-tuned weights exported as GGUF for desktop deployment. | bench-and-tune export step + llama-cpp smoke-test |
| **Special Tech → LiteRT** *(if track exists)* | LiteRT conversion for mobile/edge — operationally critical for the worker-side use case where the worker's device is monitored by the operator/employer. | LiteRT export step (deferred to post-fine-tune) |
| **Main Track** | Pursued in parallel; depends on overall execution + video. | All of the above bundled. |

## Five-minute walkthrough (post-deploy)

Once the live URL is known (post `USER_TODO.md` step 1):

1. **Click into the live URL.** Pick the `gemma-4-e2b-it` variant (fastest load).
2. **Click "About"** in the top bar — see the 30-second pitch + the
   architecture overview.
3. **Click an example prompt** in the `image_prompts` audience bucket —
   one of the `v10_img_receipt_PH_HK` or `v10_img_contract_passport`
   entries. The bundled synthetic image auto-attaches.
4. **Send the prompt.** Wait for Gemma to respond.
5. **Click the "▸ View pipeline"** link below the response. Expand the
   "RETRIEVAL PATH TRACE" card — see the actual retrieval-stage chain
   (BM25 → optional rerank → graph expansion → parent expansion).
6. **Click "Compare"** in the top bar. Load the same prompt. Set
   variant A to "Stock (no harness)" and variant B to "All layers on".
   Click Run. Wait. The side-by-side delta shows the harness lift
   live.
7. **Try an adversarial prompt** — load `jb_001` from
   `model_capability` bucket. Send. Verify the harness catches the
   jailbreak.

If you can do all 7 steps, you have empirical verification of every
"real, not faked for demo" claim in the writeup.

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
   privacy-preserving worker-side use case; the judge runs separately,
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
   161 GREP rules + 46 RAG docs + 46 citation edges cover the major
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
5. The live demo URL (post-deploy)

## Reading order if you have 5 minutes

1. This document
2. The Kaggle live demo URL (technical depth)
3. [duecare-ai.com](https://duecare-ai.com) (platform infrastructure)
4. The video
