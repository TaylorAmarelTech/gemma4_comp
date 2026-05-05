# Notebook test + push action list

> **One-row-per-notebook table** with Kaggle URL, current state, exact
> action you need to take, and verification steps.
>
> **Generated:** 2026-05-03 (T-15 from deadline). Refresh after each
> Kaggle push session.
>
> **For the per-notebook test plan in detail:** see
> [`docs/notebook_qa_companion.md`](notebook_qa_companion.md).
> **For the pre-Submit checklist:** see
> [`docs/submission_gate_checklist.md`](submission_gate_checklist.md).

## TL;DR — what you need to do

1. **Rebuild 9 wheels** (the `duecare-llm-chat` wheel changed when 5 GREP rules backported 2026-05-03 → notebooks bundling chat need fresh wheels). Run `make build` or rebuild on Kaggle CI.
2. **Push 8 notebooks** to Kaggle (3 of 11 already live; rate-limited at ~5–10/day; spread across 3–4 days starting today).
3. **Run A2 bench-and-tune** on Kaggle T4×2 once GPU quota resets (uploads HF Hub model when complete).
4. **Verify each** per the row's "verify" column.

> ⚠️ **Slug-drift heads-up.** Kaggle locks the slug at the kernel's
> first push (derived from title). If you later rename the local
> title, the live slug *does not move*. Notebook #1 has this case:
> live URL is `duecare-gemma-chat-playground` (Kaggle), but
> `kernel-metadata.json` declares `duecare-chat-playground`. Other
> notebooks may have similar drift — run
> `python scripts/verify_kaggle_urls.py` to detect.

## The 11 notebooks

Status legend:
- 🟢 **LIVE** — pushed to Kaggle; URL works
- 🟡 **PUSH PENDING** — built locally, waiting on Kaggle push
- 🔴 **NEEDS WHEEL REBUILD** — chat package changed; wheel must refresh before push
- 🔵 **GPU RUN PENDING** — needs Kaggle T4×2 to actually run

### Core (6 notebooks — walk in order during testing)

| # | Notebook | Kaggle URL | Status | Wheel needs rebuild? | GPU? | Your action |
|---|---|---|---|:-:|:-:|---|
| 1 | duecare-chat-playground (live slug: **`duecare-gemma-chat-playground`** ⚠️) | [link](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-chat-playground) | 🟢 LIVE | 🔴 YES (chat wheel) | CPU | Rebuild chat wheel → re-push wheels dataset → re-run notebook on Kaggle to confirm 42-rule load. **Decide:** keep legacy slug OR `kaggle kernels delete taylorsamarel/duecare-gemma-chat-playground -y` then push fresh at canonical slug |
| 2 | duecare-chat-playground-with-grep-rag-tools | [link](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-chat-playground-grep-rag-tools) | 🟢 LIVE ⭐ | 🔴 YES (chat wheel) | CPU | **HEADLINE DEMO** — rebuild chat wheel → re-push dataset → re-run + verify Pipeline modal shows 49 GREP rules in the count badge |
| 3 | duecare-content-classification-playground | [link](https://www.kaggle.com/code/taylorsamarel/duecare-content-classification-playground) | 🟡 PUSH PENDING | 🔴 YES (chat wheel) | CPU | Rebuild chat wheel → push wheels dataset → push notebook → run + verify 4 schema modes |
| 4 | duecare-content-knowledge-builder-playground | [link](https://www.kaggle.com/code/taylorsamarel/duecare-content-knowledge-builder-playground) | 🟡 PUSH PENDING | 🔴 YES (chat wheel) | T4 | Rebuild chat wheel → push wheels dataset → push notebook → run + verify can add custom GREP rule and see it fire |
| 5 | duecare-gemma-content-classification-evaluation | [link](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-content-classification-evaluation) | 🟢 LIVE | 🔴 YES (chat wheel) | CPU | Rebuild chat wheel → re-push dataset → re-run + verify 16 classifier examples render including 6 SVG mockups |
| 6 | duecare-live-demo | [link](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) | 🟢 LIVE ⭐ | ⚪ NO (server-bundled) | T4 | **POLISHED PRODUCT** — re-run on Kaggle, verify 22-slide deck loads + Workbench works + cloudflared URL prints |

### Appendix (5 notebooks — extension + research)

| # | Notebook | Kaggle URL | Status | Wheel needs rebuild? | GPU? | Your action |
|---|---|---|---|:-:|:-:|---|
| A1 | duecare-prompt-generation | [link](https://www.kaggle.com/code/taylorsamarel/duecare-prompt-generation) | 🟡 PUSH PENDING | 🔴 YES (chat wheel) | T4 | Rebuild chat wheel → push wheels dataset → push notebook → run + verify generates 5 graded examples for at least 3 prompts |
| A2 | duecare-bench-and-tune | [link](https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune) | 🟡 PUSH PENDING + 🔵 GPU RUN PENDING | ⚪ NO | T4×2 | **HIGHEST EFFORT** — push notebook → run on T4×2 (~6h) → verify HF Hub model lands at `taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0`. Pre-flight: [`docs/bench_and_tune_readiness.md`](bench_and_tune_readiness.md) |
| A3 | duecare-research-graphs | [link](https://www.kaggle.com/code/taylorsamarel/duecare-research-graphs) | 🟡 PUSH PENDING | 🔴 YES (chat wheel) | CPU | Rebuild chat wheel → push wheels dataset → push notebook → run + verify all 6 Plotly charts render |
| A4 | duecare-chat-playground-with-agentic-research | [link](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-agentic-research) | 🟡 PUSH PENDING | 🔴 YES (chat wheel) | T4 | Rebuild chat wheel → push wheels dataset → push notebook → run + verify 5th toggle (agentic research) fires DuckDuckGo |
| A5 | duecare-chat-playground-jailbroken-models | [link](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-jailbroken-models) | 🟡 PUSH PENDING ⭐ | 🔴 YES (chat wheel) | T4 | **STRONGEST "REAL" PROOF** — rebuild chat wheel → push wheels dataset → push notebook → run with default abliterated model → verify harness still produces safe outputs |
| A6 | duecare-grading-evaluation | [link](https://www.kaggle.com/code/taylorsamarel/duecare-grading-evaluation) | 🟡 PUSH PENDING ⭐ | ⚪ NO (chat wheel already current) | T4 | **DEDICATED LIFT EVALUATOR** — push notebook → run on T4 (~15 min for 5 prompts × 2 conditions) → verify it produces `duecare_lift_eval.json` + `duecare_lift_eval.md` with mean lift, per-dimension status changes, citation grounding %. The headline +56.5pp number, regenerated live. |

## Step-by-step recipe per notebook

For each notebook, the order is:

```bash
# 1. (only if wheel needs rebuild) — from repo root:
make build                                                    # builds all 17 wheels
# OR rebuild only the chat wheel:
python -m build --wheel packages/duecare-llm-chat
# Then copy the rebuilt wheel into each notebook's wheels/ folder:
cp packages/duecare-llm-chat/dist/duecare_llm_chat-0.1.0-py3-none-any.whl \
   kaggle/<notebook>/wheels/

# 2. push the wheels dataset (if changed):
kaggle datasets version -m "Refresh chat wheel: 49 GREP rules (was 37)" \
       -p kaggle/<notebook>/wheels/

# 3. push the notebook:
cd kaggle/<notebook>/
kaggle kernels push

# 4. wait ~30s for Kaggle to ingest, then check status:
kaggle kernels status taylorsamarel/duecare-<notebook>

# 5. open the URL in a browser — run the notebook (Run All button)

# 6. when it completes, verify the row's "verify" column is satisfied
```

Recommended push order (highest impact first):

| Day | Push these | Why |
|---|---|---|
| Day 1 (today) | #2 + #6 + #5 (rebuild chat wheel first) | The 3 already-live notebooks — refresh them so they show 42 rules |
| Day 2 | #3 + #4 + A5 | Sandbox notebooks + the strongest "real" proof |
| Day 3 | A1 + A3 + A4 | Research graphs + extension notebooks |
| Day 4 | A2 (push) | Then start the T4×2 fine-tune run; ~6h |

## Common gotchas

- **Kaggle daily push rate-limit** — after ~5–10 `kaggle kernels push` operations the API returns 429 until the UTC reset. Spread your pushes.
- **Slug ≠ kernel-metadata.json id** — Kaggle derives the slug from the title, not the metadata id. If a slug 404s after push, the live notebook may still use the old slug from a previous title. See `~/.claude/projects/.../memory/feedback_kaggle_slug_derivation.md`.
- **Wheels dataset re-version** — when you update wheels, push a NEW version (`kaggle datasets version`), not a new dataset (`kaggle datasets create`).
- **GPU quota** — a Kaggle account gets ~30h/week of T4 time. Bench-and-tune (A2) eats most of one day's quota. Schedule it.
- **Abliterated model in A5** — the default `dealignai/Gemma-4-31B-JANG_4M-CRACK` is a 31B variant; it needs the GPU memory of T4×2.

## What's "verified" mean per notebook

| # | Verified =                                                                                                  |
|---|---|
| 1 | Notebook runs end-to-end; baseline Gemma 4 chat responds with no harness                                    |
| 2 | All 4 toggle tiles visible; clicking ON/OFF updates Pipeline modal; merged-prompt card shows full text      |
| 3 | All 4 schema modes render; merged prompt + raw response + parsed JSON all visible                           |
| 4 | Add a custom GREP rule via UI; submit a matching prompt; verify the new rule appears in `▸ View pipeline`   |
| 5 | Form submits; structured JSON has classification + risk vectors + recommended action; history queue updates  |
| 6 | 22-slide deck navigates; Workbench tab loads; cloudflared URL prints (live demo URL); chat works at that URL |
| A1 | Generates ≥ 3 new prompts each with 5-tier graded responses                                                 |
| A2 | Smoke benchmark prints baseline → SFT runs → DPO runs → GGUF exports → HF Hub push succeeds                 |
| A3 | All 6 Plotly charts render (entity graph, Sankey, bars, heatmap, ILO hits, RAG sunburst)                    |
| A4 | 5th toggle visible; submit a prompt; agentic research card shows DuckDuckGo + Wikipedia results in pipeline |
| A5 | Default abliterated model loads; submit "how do I traffic workers"-shape prompt; harness STILL refuses safely |

## Where to record what you find

For each notebook tested, log:
- Date tested
- Kaggle commit SHA the wheel + notebook ran against
- ✅ verified vs ⚠️ partial vs ❌ broken
- Any specific issue (with exact error text + the cell number it fired in)

Suggested location: `docs/notebook_test_log_2026-05.md` (create on first test).

If a notebook is broken: file an issue at
[github.com/TaylorAmarelTech/gemma4_comp/issues](https://github.com/TaylorAmarelTech/gemma4_comp/issues)
with the `notebook` label.
