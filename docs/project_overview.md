# Project Overview - Gemma Migrant-Worker Safety Judge

## Competition context

- **Hackathon:** Gemma 4 Good Hackathon (Kaggle)
- **URL:** https://www.kaggle.com/competitions/gemma-4-good-hackathon
- **Window:** 2026-04-02 through 2026-05-18 (~5 weeks)
- **Prize pool:** $200,000 across three tracks
  - Main Track — $100K (1st $50K / 2nd $25K / 3rd $15K / 4th $10K)
  - Impact Track — $50K ($10K each: Health & Sciences, Global Resilience,
    Education, Digital Equity, **Safety & Trust**)
  - Special Technology Track — $50K ($10K each: Cactus, **LiteRT**,
    **llama.cpp**, Ollama, **Unsloth**)
- **Judging weights:**
  - Impact & Vision — 40 points
  - Video Pitch & Storytelling — 30 points
  - Technical Depth & Execution — 30 points

## Concept (revised 2026-04-10)

**Fine-tune Gemma 4 E4B on the author's existing 21K-test migrant-worker
trafficking safety benchmark to produce an on-device LLM safety judge.**

### The problem
Frontier LLMs still fail predictably on migrant-worker exploitation scenarios
(documented in the author's prior gpt-oss-20b Red-Teaming Challenge writeup).
The organizations with the greatest need to evaluate LLMs for this use case
are frontline NGOs, Gulf/Southeast-Asia recruitment regulators, and labor
ministries — and those organizations cannot send sensitive case data to
frontier APIs due to legal, regulatory, and operational constraints. They
need a local, private evaluator.

### The solution
A fine-tuned Gemma 4 E4B model that accepts `(scenario prompt, candidate LLM
response)` and returns:
- A grade on the worst/bad/neutral/good/best scale
- Specific missed safety indicators, referenced to ILO / IOM / Palermo /
  Kafala / POEA source documents
- Expected documentation references the candidate should have cited

The model ships as:
- GGUF weights for llama.cpp (desktop CLI + web UI)
- LiteRT conversion for mobile/edge deployment
- A FastAPI demo that makes the judge callable from a browser

### Why this beats alternatives
- **vs. "Survivor Documentation Assistant"** (earlier candidate concept):
  requires scraping and structuring public court filings from scratch in one
  month; this concept reuses an existing 21K-test benchmark with graded
  examples.
- **vs. a plain trafficking-detection classifier:** the judge is more
  valuable because it evaluates *other models' outputs* rather than just
  flagging user input — that's the workflow NGOs actually need.
- **vs. running the judge via a cloud API:** defeats the purpose; the whole
  point is that the target users can't send data to the cloud.

## Tracks targeted simultaneously

| Track | Prize | How we qualify |
|---|---|---|
| Impact Track -> Safety & Trust | $10K | Core concept is LLM safety for the most vulnerable migrant-worker populations. |
| Special Technology -> Unsloth | $10K | Fine-tune is via Unsloth; publishing weights + benchmarks on HF Hub. |
| Special Technology -> llama.cpp | $10K | Ship GGUF + desktop demo running in llama.cpp. |
| Special Technology -> LiteRT | $10K | Ship LiteRT conversion + mobile/edge demo. |
| Main Track | up to $50K | Depends on execution quality and video. |

Projects can win both a Main Track prize and a Special Technology prize per
the hackathon rules, so a strong execution could plausibly land two payouts.

## Deliverables (per hackathon rules)

1. **Kaggle writeup** (<=1,500 words) — draft at `docs/writeup_draft.md`
2. **YouTube video** (<=3 minutes, public) — script at `docs/video_script.md`
3. **Public code repository** (GitHub/Kaggle Notebook) — this repo
4. **Live public demo** — `src/demo/`, deployment TBD (Cloud Run / HF Spaces)
5. **Uses Gemma 4** — yes (E4B, fine-tuned via Unsloth)

## Timeline (5 weeks, due 2026-05-18)

| Week | Dates | Focus |
|---|---|---|
| 1 | Apr 10-16 | **Set up.** Reference copy done. Data curation: extract the 21K benchmark + graded examples from `_reference/trafficking_llm_benchmark/` into a clean Unsloth training dataset. Choose E2B vs E4B. Kaggle API token set up. |
| 2 | Apr 17-23 | **First fine-tune.** Unsloth + LoRA. End-to-end pipeline working. Initial eval on held-out test suite. |
| 3 | Apr 24-30 | **Iterate.** Tune hyperparameters, address failure modes. Convert to GGUF. Smoke-test llama.cpp locally. |
| 4 | May 1-7 | **Ship the demo.** FastAPI evaluator + web UI. Optional: LiteRT conversion. Deploy the live demo. |
| 5 | May 8-14 | **Writeup + video.** Finalize benchmark numbers. Record and edit the 3-min video. Polish the public repo. |
|  | May 15-18 | **Buffer + submit.** |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Fine-tune quality is worse than baseline Gemma | Have a judge ensemble fallback (embedding similarity to graded examples is already implemented in the source framework). |
| 21K tests is too much / too little for a week-1 fine-tune | Start with ~5K stratified sample; scale up if stable. |
| LiteRT conversion is flaky | Treat as stretch goal; llama.cpp is the primary deploy target. |
| Video story is weak | Lead with the NPR Meta/YouTube trafficking-verdict context and the author's prior red-teaming findings; let the domain work itself do the storytelling. |
| Data provenance concern: publishing graded examples that reference real cases | The 21K benchmark is already public via the GitLab repo; we're not publishing anything that isn't already public. |

## Open questions (as of 2026-04-10)

1. Unsloth experience level — needs pipeline walkthrough?
2. E2B vs E4B — leaning E4B for quality, but E2B fits on more devices.
3. llama.cpp vs LiteRT priority — leaning llama.cpp first.
4. Video hosting channel — who holds the YouTube account.
5. Live demo deployment target — HF Spaces is easiest.
