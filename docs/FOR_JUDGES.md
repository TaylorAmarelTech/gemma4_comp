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

Same harness powers a **chat playground** for individual workers and
a **structured-output classifier** for NGO triage dashboards. Ships
as **5 public Kaggle notebooks** + **17 PyPI packages**. MIT licensed.
Runs on a laptop. Zero data egress.

---

## Two-minute verification path

If you have two minutes to decide if this is real:

1. **Read the writeup.** [`docs/writeup_draft.md`](./writeup_draft.md)
   (1,437 words, under the 1,500-word cap). Frames the problem (3 LLM
   blind spots), the harness (4 layers), the 5 notebooks, and the two
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

## The five Kaggle notebooks (the submission surface)

| # | Notebook | Wheels dataset | Purpose |
|---|---|---|---|
| 1 | [duecare-live-demo](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) | `duecare-llm-wheels` | Full safety-harness pipeline + 22-slide deck + audit Workbench. The hosted live URL. |
| 2 | [duecare-bench-and-tune](https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune) *(TBD)* | `duecare-bench-and-tune-wheels` | Smoke benchmark + Unsloth SFT/DPO + GGUF export + HF Hub push. |
| 3 | [duecare-chat-playground](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground) | `duecare-chat-playground-wheels` | Raw Gemma 4 chat. NOT the safety harness. The baseline for the comparison story. |
| 4 | [duecare-chat-playground-with-grep-rag-tools](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools) | `duecare-chat-playground-with-grep-rag-tools-wheels` | **The headline demo.** Same chat UI with 4 toggle tiles + multi-persona library + custom rule additions + 204-prompt Examples library + per-response Pipeline modal. |
| 5 | [duecare-gemma-content-classification-evaluation](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-content-classification-evaluation) | `duecare-gemma-content-classification-evaluation-wheels` | **The Agency / NGO dashboard.** Form-based content submission → structured JSON classification with risk vectors + threshold-filterable history queue + 16 example items (6 with SVG document mockups). |

---

## Five-minute verification path

### Verify the technology is real (Technical Depth & Execution = 30 pts)

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp
pip install duecare-llm-chat duecare-llm-core duecare-llm-models
python -c "
from duecare.chat.harness import GREP_RULES, RAG_CORPUS, _TOOL_DISPATCH, EXAMPLE_PROMPTS, CLASSIFIER_EXAMPLES
print(f'GREP rules: {len(GREP_RULES)}')        # expect 22
print(f'RAG docs:   {len(RAG_CORPUS)}')        # expect 18
print(f'Tools:      {len(_TOOL_DISPATCH)}')    # expect 4
print(f'Example prompts:    {len(EXAMPLE_PROMPTS)}')      # expect 204
print(f'Classifier examples: {len(CLASSIFIER_EXAMPLES)}') # expect 16
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
| GREP rule citations | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py:GREP_RULES` | 22 rules across 5 categories, each with `citation` + `indicator` fields naming ILO conventions, POEA/BP2MI/Nepal/HK statutes |
| RAG corpus | `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py:RAG_CORPUS` | 18 docs covering ILO C029/C181/C095/C189 + POEA MCs + BP2MI Reg + HK statutes + IJM/Polaris briefs |
| 204 example prompts | `packages/duecare-llm-chat/src/duecare/chat/harness/_examples.json` | 190 from public Kaggle benchmark notebooks (jurisdictional-hierarchy, amplification-known-attacks, victim-revictimization, financial-crime-blindness sets) + 14 hand-curated |
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

---

## What this submission is NOT claiming

- We did **not** build a 12-agent autonomous swarm. We built a
  toggleable harness with 4 layers (Persona / GREP / RAG / Tools).
- We did **not** ship 76 notebooks as the submission. The 76-notebook
  research pipeline lives in `kaggle/kernels/` for reproducibility but
  the **submission is the 5 notebooks listed above**.
- We are **not** claiming a fine-tuned Gemma 4 model is shipped at
  submission time. The bench-and-tune notebook (#2) is the planned
  Unsloth SFT/DPO + GGUF + HF Hub push — status TBD by the 2026-05-18
  deadline.

What we ARE claiming: a working safety harness wrapping Gemma 4 that
demonstrably transforms the model's response to migrant-worker
exploitation scenarios from "operational advice" to "ILO-cited
refusal + NGO referral," visualized end-to-end in a per-response
Pipeline modal, deployable in three modes, MIT licensed, with full
provenance tracking.

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
