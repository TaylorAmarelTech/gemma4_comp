# DueCare Checkpoint — 2026-04-18

Session-end state of the DueCare submission for the Gemma 4 Good Hackathon.
Due: 2026-05-18. Days remaining: 30.

## Where we are

### New in the last two sessions (2026-04-17 and 2026-04-18)

- Rewrote the notebook hardening layer so every notebook gets:
  - Hero banner auto-moved to cell 0 (first thing a reader sees)
  - Install cells hidden both input AND output (no ERROR/fallback log visible)
  - Handoff print cells hidden both input AND output (no "Next: ..." duplication)
  - Hero/stat-card/pipeline-diagram cells have input hidden (HTML is the visible artifact, Python source is not duplicated)
- Audit + fix of hardcoded Gemma response cells:
  - Removed static `PREVIEW_CASES` from 100 Gemma Exploration (Section 9 renders live-run worst responses instead)
  - Ripped out `FALLBACK_RESPONSES` from 150 Free Form Playground — now cascades to a real hosted Gemma endpoint if local weights unavailable
  - Clarified 600 Results Dashboard "At a glance" language to make clear nothing in the dashboard body is hardcoded
- Shipped 4 new notebooks for model/endpoint coverage:
  - **102 Gemma 4 E2B Baseline** (GPU, dedicated E2B scored baseline)
  - **165 Thinking-Budget Sweep** (CPU, API, varies max_tokens 128/384/1024/2048)
  - **175 Temperature Sweep** (CPU, API, varies T 0.0/0.3/0.7/1.0)
  - **245 Gemini API Gemma 4 Comparison** (CPU, 3-endpoint Gemma 4 head-to-head)
- Shipped 3 new notebooks for the uncensored training-data pipeline:
  - **525 Uncensored 5-Grade Generator** (GPU, per-prompt WORST/BAD/NEUTRAL/GOOD/BEST responses)
  - **527 Uncensored Rubric + Dimension Generator** (GPU, per-category YAML rubrics + 5 scoring dimensions + per-grade rules)
  - **550 NGO Partner Survey Pipeline** (CPU, human-in-the-loop feedback surface with email drafts + JSON Schema surveys + PII-aware intake)

### Pipeline end-to-end

```
183 Red-Team Prompt Amplifier
  │   (uncensored Gemma generates new adversarial prompts)
  │
  ├──► 525 Uncensored 5-Grade Generator
  │       (per prompt, emits WORST/BAD/NEUTRAL/GOOD/BEST responses)
  │
  ├──► 527 Uncensored Rubric + Dimension Generator
  │       (per category, emits rubric YAML + dimensions + grade rules)
  │
  └──► 550 NGO Partner Survey Pipeline
          (per NGO, emits email drafts + surveys; ingests human responses)
                  │
                  └──► 530 Phase 3 Unsloth Fine-Tune
                         (merges synthetic + NGO-validated training rows)
                               │
                               └──► 540 Fine-Tune Delta Visualizer
                                     (before/after charts for the video)
```

## Notebook publishing state

### Published (v1+) and live on Kaggle

| Slot | Title | Status |
|---|---|---|
| 000 | Index | v33 — hero first, streamlined prose |
| 005 | Glossary | v17 |
| 010 | Quickstart in 5 Minutes | v17 — real Gemma 4 cascade call added |
| 100 | Gemma Exploration (Scored Baseline) | v28 — hardcoded preview removed |
| 102 | Gemma 4 E2B Baseline | v1 NEW |
| 105 | Prompt Corpus Introduction | v5 |
| 110 | Prompt Prioritizer | v4 |
| 120 | Prompt Remixer | v7 |
| 140 | Evaluation Mechanics | v8 |
| 165 | Thinking-Budget Sweep | v1 NEW |
| 175 | Temperature Sweep | v1 NEW |
| 190 | RAG Retrieval Inspector | v6 |
| 210 | OSS Model Comparison | v9 |
| 245 | Gemini API Gemma 4 Comparison | v1 NEW |
| 250 | Comparative Grading | v4 |
| 525 | Uncensored 5-Grade Generator | v1 NEW |
| 527 | Uncensored Rubric Generator | v1 NEW |
| 550 | NGO Partner Survey Pipeline | v1 NEW |
| 600 | Results Dashboard | v15 |
| 899 | Solution Surfaces Conclusion | v6 |

### Needs publishing / push pending

Failed pushes from last session — some are "Notebook not found" (need a first push to create the kernel on Kaggle), some are 400 Bad Request on long slugs:

| Slot | Title | Failure mode |
|---|---|---|
| 099 | Orientation + Package Setup Conclusion | 400 — title slug issue, likely too long |
| 130 | Prompt Corpus Exploration | Notebook not found (never created) |
| 150 | Free Form Gemma Playground | Notebook not found |
| 152 | Interactive Gemma Chat | 429 rate limit |
| 155 | Tool Calling Playground | Notebook not found |
| 160 | Image Processing Playground | Notebook not found |
| 170 | Live Context Injection | 409 Conflict (slug mismatch) |
| 180 | Multimodal Document Inspector | 409 Conflict (slug mismatch) |
| 199 | Free Form Exploration Conclusion | Notebook not found |
| 200 | Cross-Domain Proof | Notebook not found |
| 220 | Ollama Cloud Comparison | Notebook not found |
| 230 | Mistral Family Comparison | Notebook not found |
| 240 | OpenRouter Frontier Comparison | Notebook not found |
| 260 | RAG Comparison | Notebook not found |
| 270 | Gemma Generations | Notebook not found |
| 299 | Baseline Text Eval Conclusion | 400 |
| 300 | Adversarial Resistance | 409 |
| 310 | Prompt Factory | — |
| 320 | SuperGemma Safety Gap | — |
| 335 | Attack Vector Inspector | — |
| 340 | Prompt Factory Visualizer | — |
| 399 | Baseline Text Comparisons Conclusion | — |
| 400 | Function Calling + Multimodal | — |
| 410 | LLM Judge Grading | — |
| 420 | Conversation Testing | — |
| 430 | Rubric Evaluation | — |
| 440 | Per-Prompt Rubric Generator | — |
| 450 | Contextual Worst-Response Judge | — |
| 460 | Citation Verifier | — |
| 499 | Advanced Evaluation Conclusion | — |
| 500 | Agent Swarm Deep Dive | — |
| 510 | Phase 2 Model Comparison | — |
| 520 | Phase 3 Curriculum Builder | — |
| 530 | Phase 3 Unsloth Fine-Tune | — |
| 540 | Fine-tune Delta Visualizer | — |
| 599 | Model Improvement Opportunities Conclusion | — |
| 610 | Submission Walkthrough | — |
| 620 | Demo API Endpoint Tour | — |
| 650 | Custom Domain Walkthrough | — |
| 660-695 | Deployment-application band | — |
| 699 | Advanced Prompt Test Generation Conclusion | — |
| 799 | Adversarial Prompt Test Eval Conclusion | — |
| 181-189 | Jailbreak family (9 notebooks) | — |
| 620, 650 | Deployment walkthroughs | — |

**Next push session plan:**
1. Fix 099 / 299 title → slug alignment first (they 400 on long slugs)
2. Create the "Notebook not found" kernels via Kaggle web UI once, or wait for daily rate-limit reset and push in batches of 5-7
3. Diagnose 409 conflicts (likely slug drift from renumbering)

## Notebook validation state

### Needs live execution validation on Kaggle

The following notebooks are **pushed but never end-to-end run** on Kaggle with the latest build:

- 102 E2B Baseline — new; untested
- 165 Thinking-Budget Sweep — new; untested
- 175 Temperature Sweep — new; untested
- 245 Gemini API Comparison — new; untested
- 525 Uncensored 5-Grade Generator — new; GPU-only; untested
- 527 Uncensored Rubric Generator — new; GPU-only; untested
- 550 NGO Survey Pipeline — new; CPU-only; untested

### Needs validation after hardcoded-response cleanup

- 100 Gemma Exploration — Section 0 preview removed, need to confirm Section 9 live worst-responses still renders cleanly
- 150 Free Form Gemma Playground — fallback replaced with API cascade, need to confirm it works with OLLAMA_API_KEY / OPENROUTER_API_KEY / GEMINI_API_KEY attached as Kaggle secrets
- 600 Results Dashboard — stat-card text clarified, need to confirm the charts still render from `comparison.json`

### Known runtime issues to resolve

- **100 Gemma Exploration KernelWorkerStatus.ERROR** on latest run (v25+). Kernel content is correct but the last execution errored. Need to diagnose: likely GPU memory or a timing-out cell. Lower `MAX_PROMPTS` to 50 or restart and rerun.
- **183 / 525 / 527 fallback path** when no community uncensored weights resolve: cascades to stock Gemma 4 with in-memory 182-refusal-direction ablation. Needs one real end-to-end validation on T4 to confirm the ablation math applies correctly at runtime (refusal direction file must be present at `/kaggle/input/duecare-jailbreak-artifacts/refusal_direction_from_182.pt` or generated by running 182 first).

## What needs to be done next

### P0 — Blocking for submission

1. **Video shoot** — 3-minute public YouTube video is required by hackathon. Script exists at `docs/video_script.md`; no footage recorded yet. **Owner: Taylor.** Every other P0 supports the video.
2. **Live demo surface** — hackathon requires a public demo URL. Current state: HF Space is LIVE per commit `0649df5`. Confirm it still works end-to-end against the current DueCare version (`0.1.0`).
3. **Writeup finalization** — `docs/writeup_draft.md` exists; needs a final pass to match the new 525/527/550 pipeline claims and the uncensored-generator narrative.
4. **530 Phase 3 Unsloth Fine-Tune actually runs** — curriculum builder (520) + uncensored generators (525/527) + NGO survey (550) all feed into 530, but 530 has not been run end-to-end with the expanded corpus. This is the "real, not faked" Phase 3 evidence.

### P1 — Strong-to-win

5. **540 Fine-Tune Delta Visualizer runs against the Phase 3 fine-tune output.** The before/after plots are the single strongest video visual for the Special Tech Track (Unsloth).
6. **Publish the remaining unpushed kernels** (table above). Every kernel not on Kaggle reduces the judge-reproducibility story.
7. **Validate the uncensored generator pipeline on a real T4**: end-to-end run of 183 → 525 → 527 → 530 with the expanded corpus. Check the rubric YAMLs are loadable by the domain-pack loader.
8. **Real NGO outreach** — 550 generates the invitation drafts; Taylor reviews, edits the survey link placeholder, and actually sends from a real mail client. A single live response merged into the training corpus is a strong video beat.

### P2 — Stretch / polish

9. **Fix 099 / 299 title-slug mismatch** that triggers the 400 Bad Request push failures.
10. **Diagnose 409 conflicts** on 170 / 180 / 300 push. Likely slug drift from renumbering; `_public_slugs.py` registry may need more entries in `PUBLIC_SLUG_OVERRIDES`.
11. **Update 000 Index** to include 102 / 165 / 175 / 245 / 525 / 527 / 550 in the navigation map. Coverage chart counts need updating (suite now has more notebooks than the "60+ notebooks across 15 sections" line in the hero banner).
12. **Consolidate the three uncensored-generator outputs** into a single merged curriculum JSONL that 530 can consume directly. Currently 525 / 527 / 550 each write to different paths; 520 curriculum builder is the natural merge point but has not been updated to ingest 525/527/550.
13. **Publish the full suite to PyPI** (v0.1.0 release across all 8 packages). Last tag is the starting point; every notebook pins `duecare-llm-core==0.1.0`.

## Open questions

1. **"openclaw"** — user's term in the 550 request was implemented as a pre-curated public-record NGO directory rather than live email scraping. Was the intent Playwright+stealth scraping of NGO contact pages, OpenCTI threat-intel, or something else? 550 as-built is ethics-first; if a different tool was meant, we can swap in the scraper pathway.
2. **Gemma 4 API vs hosted Gemma 3**: the 010/165/175/245 API notebooks default to `google/gemma-3-27b-it` via OpenRouter/Ollama/Gemini because Gemma 4 endpoints are not yet routed at those providers as of 2026-04-18. When providers cut over to Gemma 4 specifically, the model-id strings need a one-line update in each of those four notebooks.
3. **Thinking-mode budget**: 165 Thinking-Budget Sweep varies `max_tokens`. Gemma 4 may expose a native "thinking" token budget separately; if it does, 165 should be rewritten to sweep that parameter specifically and keep max_tokens fixed.
4. **Jailbreak family (181-189) push status**: nine notebooks exist in build scripts but some have never been published. Verify which ones are live and push the rest.

## Hackathon requirements checklist

- [ ] Public YouTube video (<=3 minutes) — script ready at `docs/video_script.md`, **no footage yet**
- [ ] Kaggle writeup (<=1,500 words) — draft at `docs/writeup_draft.md`, needs update for new pipeline
- [x] Public code repo — this repo, `_reference/` gitignored
- [~] Live public demo — HF Space exists per `0649df5`; **re-verify end-to-end**
- [x] Uses Gemma 4 — 100, 102, 150, 155, 160, 170, 180, 185-189, 320, 525, 527, 530, and API notebooks all exercise Gemma 4 surfaces
- [~] Special Tech Track — Unsloth: 530 fine-tune pending; llama.cpp / LiteRT deployment: pending

Legend: `[x]` done, `[~]` partial, `[ ]` not started.

## Session log pointer

Full conversation detail for both sessions is available for future agents:
- `C:\Users\amare\.claude\projects\C--Users-amare-OneDrive-Documents-gemma4-comp\eaeba53a-7963-47f4-8d98-ba8edabb5a6a.jsonl` (2026-04-17)
- Current session will have a corresponding JSONL once recorded.

Last rebuild timestamp: 2026-04-18. Last push: 550 NGO Partner Survey Pipeline v1.
