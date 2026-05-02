# Two-week submission plan (T-16 to T-0)

> **Goal.** Land the strongest possible Gemma 4 Good Hackathon
> submission by 2026-05-18, given the actual constraints + capacity.
>
> **Time horizon.** 16 days (2026-05-02 to 2026-05-18).
>
> **Prepared.** 2026-05-02. Updated each Sunday during the window.

## What's already done (don't re-do)

- ✅ Android v0.9 APK (20 corridors, 42 GREP rules, 11 ILO indicators) live on GitHub Releases
- ✅ Docker stack (`make demo`) works end-to-end
- ✅ 14 persona walkthroughs in `docs/scenarios/`
- ✅ 5 ADRs documenting the load-bearing architecture decisions
- ✅ Multi-tenant token + cost meter + rate-limit + OTel + Prometheus
- ✅ Helm chart with HPA + PDB + NetworkPolicy
- ✅ 13-platform cloud deploy cookbook
- ✅ All 17 PyPI wheels built locally
- ✅ 6 + 5 Kaggle notebook source code complete + tested locally
- ✅ Press kit, comparison-vs-alternatives, FAQ, CHANGELOG, CITATION.cff
- ✅ Tagalog + Spanish drafts of worker-self-help.md
- ✅ Cross-NGO trends federation design + privacy contract
- ✅ Maria's case end-to-end narrative (writeup + video material)
- ✅ Ecosystem overview with Mermaid diagrams (renders on GH Pages)
- ✅ MkDocs Material site config + GH Actions deploy workflow
- ✅ Notebook QA companion (per-notebook test checklist)

## What only YOU can do (no AI substitute)

These are the items only the human submitter can complete:

1. **Record the video.** Script is locked at
   `docs/video_script.md`; voice-over guidance is there. ~3 min
   final cut. **Highest-leverage single deliverable left.**
2. **Test each notebook on Kaggle.** Use
   [`docs/notebook_qa_companion.md`](notebook_qa_companion.md) as
   your per-notebook checklist.
3. **Push notebooks to Kaggle.** Daily push rate-limit applies —
   plan to spread pushes across 3-4 days. Order in the QA
   companion's "After all 11 are tested" section.
4. **Run bench-and-tune (A2) on Kaggle T4×2** when GPU quota resets.
   See [`docs/bench_and_tune_readiness.md`](bench_and_tune_readiness.md).
5. **Push fine-tuned weights to HF Hub** as
   `taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0`.
6. **Submit on the Kaggle competition page** on or before
   2026-05-18.

## What I (Claude / AI) can keep doing

If you want continued doc work between now and submission:

- Refine specific notebook builders based on what you find during
  testing
- Update the writeup_draft.md as the fine-tune numbers come in
- Refresh FOR_JUDGES.md as notebooks transition from
  "publish pending" → live
- Add more language drafts of worker-self-help.md (Bahasa, Nepali,
  Bangla, Arabic) — same draft + native-review-needed pattern
- Add more corridors as your testing surfaces gaps
- Build any specific persona / scenario / explainer that an early
  reviewer asks for
- Wire any specific integration the bench-and-tune output suggests
  (e.g., an HF Hub model card with the actual numbers)

## The 16-day plan

### Week 1 (T-16 to T-9): testing + publishing

| Day | Focus | Deliverable |
|---|---|---|
| **T-16 (today, 5/2)** | This planning doc + the QA companion + the ecosystem overview + Maria narrative | All shipped |
| **T-15 (5/3)** | Test notebook 1 (chat-playground) + 2 (chat-playground-with-grep-rag-tools — the headline) | Both confirmed runnable on Kaggle; #2 polished |
| **T-14 (5/4)** | Test #5 (NGO dashboard) + #6 (live-demo) | Both confirmed; live-demo has the full 22-slide deck working |
| **T-13 (5/5)** | Test #3 + #4 (sandbox notebooks) | Both confirmed |
| **T-12 (5/6)** | Test A4 + A5 (agentic research + jailbroken comparison) | Both confirmed |
| **T-11 (5/7)** | Test A1 + A3 (prompt generation + research graphs) | Both confirmed |
| **T-10 (5/8)** | Push notebooks #2 + #6 + #5 to Kaggle (highest-priority 3) | 3 of 11 live with public URLs |
| **T-9 (5/9)** | Push notebooks #3 + #4 + A4 + A5 to Kaggle | 7 of 11 live |

### Week 2 (T-8 to T-2): fine-tune + video + final docs

| Day | Focus | Deliverable |
|---|---|---|
| **T-8 (5/10)** | Push remaining notebooks (A1 + A3) | All 11 notebooks live |
| **T-7 (5/11)** | GPU quota resets — start A2 bench-and-tune run | Smoke test passes |
| **T-6 (5/12)** | A2 run continues; record video while waiting | Video draft |
| **T-5 (5/13)** | A2 completes (or fallback to "scheduled post-hackathon") + push fine-tuned weights to HF Hub | RESULTS.md updated |
| **T-4 (5/14)** | Video edit + finalization + caption pass | Video locked |
| **T-3 (5/15)** | Final pass on writeup_draft.md + FOR_JUDGES.md + README to reflect all numbers | All docs SHA-pinned |
| **T-2 (5/16)** | Smoke-test the entire submission from a logged-out browser | Submission validated |

### Final stretch (T-1 to T-0)

| Day | Focus |
|---|---|
| **T-1 (5/17)** | Buffer day. Submit on the Kaggle competition page. |
| **T-0 (5/18)** | Submission deadline. |

## Decision points along the way

You'll hit these branches; pre-decide your defaults so you don't
deliberate at the wrong moment:

### Branch 1: Bench-and-tune fails on T4×2

**Probability:** ~20-30% (Unsloth+CUDA versioning is fragile).

**Default action:** Document A2 as "scheduled post-hackathon" in
RESULTS.md. The harness-lift report (already complete, +56.5pp on
207 prompts) is the stronger headline number; A2's lift is
incremental on top of that.

### Branch 2: Notebook publishing rate-limited

**Probability:** Near-certain (Kaggle's daily push cap).

**Default action:** Spread pushes across 3 days minimum. Push the
3 highest-priority notebooks first (#2, #6, #5). Lower-priority
notebooks can land in the final week.

### Branch 3: Video not done by T-4 (5/14)

**Probability:** Real risk if recording starts late.

**Default action:** Use a static-frame video with voiceover only.
Worse than a polished video, infinitely better than no video.
Even a 90-second voiceover-over-still-frame submission works for
the rubric's "Video Pitch" 30-point category. Don't let perfect
be the enemy of submitted.

### Branch 4: A reviewer flags a specific gap

**Probability:** Low; submission window is mostly closed-door.

**Default action:** Triage. If the gap is < 1 day to fix, fix +
re-pin. If > 1 day, document as known-limitation in writeup +
move on.

### Branch 5: HF Hub push of fine-tuned weights fails

**Probability:** Low (HF Hub is reliable).

**Default action:** Manual upload via the HF web UI as a fallback.
Or document as "weights staged for post-hackathon push" — RESULTS.md
honestly notes this if needed.

## Daily standup template

Each day during the 16, ask yourself in 5 minutes:

1. What I tested / shipped yesterday
2. What I'm testing / shipping today
3. What's blocked + what I need to unblock
4. Am I on track for the T-2 (5/16) freeze?

If "no" to #4 for two days running: drop a P1 / P2 task from the
plan. Submission > completeness.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Video doesn't ship | Medium | High (30 points) | Fallback to voiceover-over-static-frame |
| 3+ notebooks fail Kaggle test | Low | Medium | Each notebook has a fallback "publish pending" framing |
| GPU quota exhausted before A2 completes | Medium | Medium (~5 points) | Document as scheduled post-hackathon |
| HF Hub model card breaks | Low | Low | Manual upload via web UI |
| Submission missed on 2026-05-18 | Very low | Catastrophic (forfeit) | Submit on T-1 (5/17) for a one-day buffer |

## Score projection (per `docs/rubric_evaluation_v07.md`)

Going into the final stretch:

| Category | Points | Today | Floor (if everything goes badly) | Ceiling (if everything goes well) |
|---|---|---|---|---|
| Impact & Vision (40) | 40 | 32 | 28 | 38 |
| Video Pitch (30) | 30 | 5 | 5 | 28 |
| Technical Depth (30) | 30 | 28 | 26 | 30 |
| **Total** | **100** | **65** | **59** | **96** |

**Realistic landing zone (P50): 85-91 points.** Competitive for
the Safety & Trust track ($10K). Plausible for higher-tier
recognition if execution is strong.

The 3 things that move the projection most:

1. **Ship the video** (+25 points on the realistic estimate)
2. **Push notebooks 3-6 + A1, A3-A5** to Kaggle (+5 points)
3. **Run A2 fine-tune successfully** (+3-5 points)

## What to NOT do in the final 2 weeks

- ❌ Add new corridors or GREP rules unless they fix a specific
  testing finding
- ❌ Refactor any package that's currently passing tests
- ❌ Reach out to NGOs for endorsements (timeline doesn't support it)
- ❌ Build new persona walkthroughs (14 is enough)
- ❌ Invent new languages for the worker-self-help translations
  (Tagalog + Spanish is enough for hackathon scope)
- ❌ Polish any doc that's already at "good enough" — submitter's
  attention is the scarcest resource

## What to optimistically do if everything else lands by T-5

If you're somehow ahead of schedule:

- Polish the GH Pages site landing page with screenshots
- Add a short demo GIF/animation to the README
- Build out the cross-NGO trends federation reference implementation
  beyond the design doc
- Add native-language-reviewed translations of worker-self-help.md
  (if you have a contact who can review Bahasa / Nepali / Arabic)

These are nice-to-haves. The hackathon submission is solid without them.

## Adjacent reads

- [Notebook QA companion](notebook_qa_companion.md) — per-notebook test checklist
- [Bench-and-tune readiness](bench_and_tune_readiness.md) — what to do when GPU quota resets
- [Rubric evaluation](rubric_evaluation_v07.md) — per-component grades vs the rubric
- [Maria's case end-to-end](marias_case_end_to_end.md) — narrative for the video + writeup
- [Ecosystem overview](ecosystem_overview.md) — the strategic frame
- [`RESULTS.md`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/RESULTS.md) — reproducibility provenance
- [`docs/video_script.md`](video_script.md) — the locked video script
- [`docs/writeup_draft.md`](writeup_draft.md) — the locked writeup
