# Manual TODO checklist (Taylor)

Things you must do that I cannot. Roughly priority-ordered for the
2026-05-18 hackathon deadline. Each item is a 1-2 line description
with the why; details live in the linked docs.

---

## 0. CRITICAL — verify hackathon facts I assumed but couldn't confirm

The Kaggle competition pages are login-walled and the public secondary
sources don't quote the rubric verbatim. I built `CLAUDE.md`, the
project_overview, and the writeup against assumptions that need
confirming from inside Kaggle:

- [ ] **Verify the 40/30/30 judging-axis weights** from the official
      Kaggle competition rubric. Project notes assume Impact 40 /
      Video 30 / Tech 30. If the actual page differs, update
      `CLAUDE.md` + `.claude/rules/00_overarching_goals.md` +
      `docs/writeup_draft.md` accordingly.
- [ ] **Verify the 5 Impact Track sub-tracks** (Health & Sciences,
      Global Resilience, Education, Digital Equity, Safety & Trust).
      Confirm Safety & Trust qualifies what we claim.
- [ ] **Verify the 5 Special Technology sub-tracks** including
      llama.cpp + LiteRT — these specifically were not externally
      verifiable. If they don't exist as dedicated tracks, the
      writeup's "we qualify for 4 tracks" claim needs to drop to
      what's actually offered.
- [ ] **Confirm submission deliverable caps**: writeup word cap (we
      assume ≤1,500), video duration cap (we assume ≤3 min), public-
      repo requirement, public-demo requirement.
- [ ] **Confirm multi-track winnability**: can a project win
      Main + Impact + Special-Tech, or one prize only?
- [ ] **Read the content-policy clauses** in the rules — verify our
      bundled CC0 synthetic evidence imagery (with watermark + fictional
      composite names + safety disclaimers) doesn't trip any prohibition.

---

## 1. Push v0.14.7 to Kaggle

Without this, none of v0.4 → v0.14.7 reaches a judge. Run before any
video capture or live verification.

```bash
# Pre-flight (local, no Kaggle):
py -3.10 scripts/v141_check_static_js.py
py -3.10 scripts/v141_smoke_all_endpoints.py
py -3.10 scripts/v141_word_count.py
# All three must pass before pushing.

cd kaggle/01-duecare-exploration-workbench/wheels
kaggle datasets version -m "v0.14.7: 8-component platform framing (Runtime/Harness/Exchange/Eval/Trainer/Sentinel/Channels/Mobile) + deployment self-audit gate + sanitizer for Gemma 4 thinking-channel artifacts + 26-entry hotlines directory + live GREP tester + cross-layer search + RAG retrieval overlay + GREP fire-count leaderboard + 11 dedicated viewer pages — see docs/release_checklist_v0_14_5.md for the full verification checklist"

# Then for each appendix wheel folder you want bumped:
cd ../../../kaggle/02-live-demo/wheels
kaggle datasets version -m "v0.14.7 wheel sync"
# … repeat for A-01..A-11 if you want them on the latest
```

Then on Kaggle:

- [ ] Restart `01-duecare-exploration-workbench` from the Kaggle UI so the new
      wheel actually loads.
- [ ] **Critical:** scroll the notebook stdout for the `DUECARE
      SELF-AUDIT · chat-package 0.14.7` banner with all minimums met.
      If the banner says an older version, the wheel did not refresh
      — bump the dataset version and restart again.
- [ ] Open `docs/release_checklist_v0_14_5.md` (filename is stable;
      content tracks v0.14.7) and run Phases 3a / 3b / 3c against
      the live cloudflared URL.
- [ ] Verify each viewer page loads cleanly: `/static/harness.html` →
      `/static/grep-rules.html` → `/static/grep-tester.html` (paste
      the 5-indicator-compound preset, run, see ≥5 rules fire) →
      `/static/rag-graph.html` (force-directed view with arrowheads,
      search, jurisdiction filter, ⬇ SVG export) → `/static/rag-corpus.html`
      (citation neighbors, recently-retrieved overlay) →
      `/static/hotlines.html` (26 contacts, click-to-call / mailto /
      form-URL, "user submits — never auto-send" banner) →
      `/static/search.html` (cross-layer "passport" query).

## 2. Capture screenshots from the live deployment

These feed the video + writeup. Capture each at full resolution:

- [ ] Empty-state landing page (with the Examples ▸ + Compare buttons
      visible in the top bar).
- [ ] Examples modal showing the 8 audience buckets + the "Audience"
      filter chips at the top.
- [ ] Image-prompt example with the synthetic recruitment receipt
      auto-attached (one of the v10_img_receipt_* entries).
- [ ] A chat response with deep-fetch ON, showing the pipeline modal
      with the RETRIEVAL PATH TRACE card visible (BM25 → rerank →
      graph → parent_expand stages listed).
- [ ] The Compare tab side-by-side after a real run — variant A
      (stock) vs variant B (full harness) on a debt-bondage prompt.
- [ ] The RAG ▸ View & Configure panel showing the retrieval-mode
      radios + parent-expansion radios + cache stats.
- [ ] An adversarial-prompt response (load `jb_001` from the
      model_capability bucket) with the harness catching it — show
      the GREP hits + RAG citation graph in the trace.

## 3. Run the adversarial validation suite against the live deployment

Generates the artifact that anchors the Tech Depth axis claims:

```bash
# From the repo root, with the chat server running locally OR pointing
# at the Cloudflared URL of the live Kaggle deployment.
py -3.10 scripts/adversarial_validate.py \
    --base-url <your-cloudflared-or-localhost-url> \
    --grade-mode universal \
    --max-prompts 50

# Outputs land in reports/adversarial_<ts>.{md,json}
```

- [ ] Run the full 50-prompt suite. Capture pass-rate per family.
- [ ] Drop the resulting `.md` report into `docs/RESULTS.md` as the
      headline empirical evidence.
- [ ] If any test fails, decide: is it a real harness gap (fix it) or
      a brittle-test issue (refine the test).

## 4. Manual image authoring

Drop your manually-anonymized real images alongside the auto-generated
synthetics. Per `packages/duecare-llm-chat/src/duecare/chat/static/synthetic/README.md`:

- [ ] Pick 10-20 real evidence images you've collected (receipts,
      contract pages, social-media screenshots, passport stamps).
- [ ] Anonymize per the README checklist: faces blurred or cropped,
      names + IDs solid-black-redacted, EXIF stripped, business
      names replaced with `(composite)` tags.
- [ ] Drop PNGs into `packages/duecare-llm-chat/src/duecare/chat/static/synthetic/`
      with sidecar JSONs declaring license + synthetic_disclaimer.
- [ ] Add matching `image_prompts` entries to `_examples.json` with
      `synthetic_image: "/static/synthetic/your-file.png"`.
- [ ] Re-run `py -3.10 -m build --wheel ... packages/duecare-llm-chat`
      and bump to v0.11.1 (or v0.12.0 if substantial).

## 5. Fine-tune training run

The submission concept is "fine-tune Gemma 4 E4B on the 21K-test
benchmark." Track current state:

- [ ] Confirm the Unsloth fine-tune notebook (kaggle/A-07-bench-and-tune)
      runs end-to-end. Look at `docs/bench_and_tune_walkthrough.md`.
- [ ] Run the actual training. Capture wall-clock + GPU usage as
      writeup material.
- [ ] Export to GGUF (llama.cpp special-track requirement). Smoke-
      test via llama-cpp-python locally.
- [ ] Optional: convert to LiteRT for the LiteRT special-track.
- [ ] Push the final model to HF Hub at
      `TaylorScottAmarel/duecare-gemma-4-e4b-safetyjudge-v0.1.0`
      with a model card per the special-tech-track requirements.

## 6. Cloud / Kaggle deployment

The "live public demo" deliverable:

- [ ] Pick the deployment surface — Kaggle Notebook with Cloudflared
      tunnel (current path) is fine if the URL stays stable through
      the judging window. Alternatives: HF Spaces, Cloud Run.
- [ ] Set the Cloudflared tunnel to a named hostname you control if
      the judges need a stable URL across days. Otherwise note in the
      writeup that the URL is generated per-session.
- [ ] Test the deployed URL FROM A FRESH BROWSER with no Kaggle
      cookies, like a judge would. Verify: load time, model picker
      flow, first chat success, image-attach flow, Compare flow,
      adversarial-prompt flow.

## 7. Update the writeup

The writeup at `docs/writeup_draft.md` predates the v0.4 → v0.11 work.
It needs to be refreshed (I left this as a separate v0.11 task because
it requires your voice). Specific things to inject:

- [ ] Hybrid retrieval (BM25 + dense + RRF) — the technical detail
      that signals real engineering, not chatbot wrapper.
- [ ] Structural chunking + parent expansion — answers the "what
      happens with a 200-page court filing" question.
- [ ] 1-hop citation graph — 46 hand-curated edges over 35 docs.
- [ ] 65-test adversarial suite + the pass-rate result from step 3
      above.
- [ ] 34 grading dimensions across cross-cultural / sectoral /
      child-protection / on-device-privacy axes.
- [ ] 161 GREP rules across 24+ categories including emerging
      vectors (crypto, scam-compound, gig-economy, BNPL, Ukrainian
      and Afghan corridors).
- [ ] Bundled synthetic evidence imagery (CC0, watermarked) for
      multimodal probes — the demo-visible artifact.
- [ ] On-device privacy alignment — the submission's distinguishing
      feature for the Safety & Trust track.

Keep within the 1,500-word cap.

## 8. Update the video script

`docs/video_script.md` should land the 3-min beats hard. Suggested
beats (rough order):

- [ ] **0:00-0:20** — A real worker scenario (composite Maria) frames
      the problem. Visual: bundled synthetic recruitment receipt.
- [ ] **0:20-0:50** — Why frontier APIs aren't an option for this
      use case (privacy, regulatory, employer-monitored device).
      Visual: shows operator-monitored-device adversarial test.
- [ ] **0:50-1:30** — Live demo: paste the case, harness catches the
      indicators, model cites the statute. Visual: pipeline modal
      with RETRIEVAL PATH TRACE card showing BM25 → rerank → graph
      expansion stages.
- [ ] **1:30-2:00** — A/B Compare: same prompt, stock Gemma vs full
      harness. Show the score delta.
- [ ] **2:00-2:30** — Adversarial validation: jailbreak attempt,
      harness refuses + grounds the refusal. Bundle into headline
      pass-rate stat.
- [ ] **2:30-3:00** — Tracks named (Safety & Trust, Unsloth,
      llama.cpp/LiteRT pending verification). Closing visual: the
      Examples bucket switcher showing all 6 audience views.

Record + edit + upload to your YouTube channel as Public.

## 9. FOR_KAGGLE_JUDGES doc

`docs/FOR_KAGGLE_JUDGES.md` is the doc judges read FIRST. Update it to:

- [ ] Per-track qualification table — each row anchored to a
      specific file path or commit hash so a judge clicking
      through finds proof.
- [ ] One-paragraph summary of what to demo, in what order, with
      a fallback if the live URL is down.
- [ ] Link to the live demo URL + the writeup + the video.
- [ ] License declaration pointer to LICENSES.md.

## 10. Repo presentation polish

Things judges will see in a 60-second skim:

- [ ] README at repo root — does it open with a clear "what this is +
      why it matters" 3-line summary?
- [ ] Are the bundled synthetic images visible from a `static/` HTML
      gallery so judges can see them without running anything?
- [ ] Is `LICENSES.md` linked from the README?
- [ ] Is `docs/RESULTS.md` linked from the README?
- [ ] No `_archive/` / `legacy_src/` content prominently visible in
      the README; keep it for the curious deep-dive.

## 11. Submission day

- [ ] Pin the Kaggle dataset versions you submit against (so a later
      bump can't break the linked notebook).
- [ ] Pin the wheel versions in the kernel notebook so a re-run
      doesn't pull a newer wheel that wasn't submitted.
- [ ] Capture a screen recording of the demo end-to-end as a backup
      in case the live URL goes down during judging.
- [ ] Submit before 2026-05-18 23:59 UTC. Set a calendar alarm at
      2026-05-17 12:00 UTC to give yourself a 24-hour buffer.

---

## What I CAN do remotely if you ask

- More content (prompts, dims, GREP rules) — say what's missing and
  I'll author.
- More UI polish — point at a specific screen and I'll improve it.
- More tests — extend `scripts/adversarial_validate.py` or write a
  new validator for a specific axis.
- Update writeup / video script / FOR_KAGGLE_JUDGES — I can draft prose and
  you edit.
- Documentation cleanup — sweep stale docs / dead links in `docs/`.
- Adversarial run analysis — if you paste the report.json content
  back, I can tell you which failures are real harness gaps vs
  brittle tests.

## What I CAN'T do without you

- Push to Kaggle (your credentials).
- Restart the deployed kernel (Kaggle UI action).
- Capture screenshots from the live deployment (browser session).
- Record + edit + upload the video (your face, your voice).
- Run the fine-tune (your GPU budget).
- Verify Kaggle's official rules from inside the login wall.
- Provide manually-anonymized real evidence images (your sourcing).
