# Codex handoff — 2026-05-18

> Snapshot of the DueCare submission state at end of the 2026-05-18
> work session. Read this top-to-bottom before picking up the
> submission; it tells you what landed today, what is intentionally
> unchanged, what is pending, and the one or two open decisions Taylor
> still needs to make.

## TL;DR

We landed eight commits today (see *Commit log*) that:

1. Ported the duecare-ai design hand-off into the live-demo slide
   deck — `/slides` is now a 23-slide, 1920×1080 paper-style deck
   with a real workbench frame, FB-post mockup, dropzones, stage
   rows, score bars, mini graph SVG, and a 4-tile uniqueness slide.
2. Renamed the three judge-facing kernels:
   `01-duecare-exploration-workbench` → **DueCare App**,
   `A-00-omni-experiment-workbench` → **DueCare Fine-tuning and
   Evaluation**. `02-live-demo` keeps its name. Folder paths and
   internal symbols (`A00_*`, `/api/a00/...`, `set_kernel_id(...)`)
   are intentionally unchanged.
3. Rewrote `docs/writeup_draft.md` (1444 / 1500 words) to a
   technical/HOW orientation: capability gap, prior-art, concrete
   failure modes of frontier LLMs here, why training+eval alone
   doesn't fix it, the substrate components in detail, A-00 control
   plane, run-on-Kaggle instructions, "Try it in 30 seconds" hero.
4. Added the same 30-second try-it-now hero to `README.md`.
5. Fixed a statutory mis-citation in `slides_cache.py` (RA 11227 →
   RA 8042 §6 with the RA 10022 amendment).
6. Softened benchmark claims — the deck-handoff placeholder scores
   (62.0 / 81.5 / 74.8 / 88.2 %) are removed from the deck and
   writeup; the four-arm framing now describes A-00 as a *capability*
   ("facilitates benchmarking, synthetic data, LoRA fine-tune,
   combined judging, report export") with the promise to publish
   actual lift numbers from a final A-00 run.
7. Added an "Anonymized sharing" 6th card to the website use-cases
   page so the website matches the deck's six lanes.
8. Added a "Download the knowledge packs" slide that links the
   judge straight to six shipped sample bundles via
   `/wb-static/samples/*`.

All 93 tests pass (server 58/58, website 21/21, slides contract 14/14).

## Commit log (newest first)

```
d3115b4 Add 'Download the knowledge packs' slide (take-it-home)
391ec01 Expand 'What makes this unique' to 4 tiles (add on-device APK)
f108644 Add 'What makes this unique' 3-tile slide before conclusion
a0aa4f9 Add 'cached, replays in ~3s' subtext to each deck demo runner
d1b3e83 Writeup -> technical/HOW orientation; slides -> benefits framing
fffd3b7 Soften A-00 claims + add 6th use-case (Anonymized sharing) to website
b2d8815 Rename kernels + rewrite writeup + fix statutes + add 30s onboarding
36073ef Port slide deck design from duecare-ai handoff
```

All eight pushed to `origin/master`.

## Canonical names (post-rename)

| Old | New display | New Kaggle slug | Folder (unchanged) |
|---|---|---|---|
| Exploration Workbench | **DueCare App** | `taylorsamarel/duecare-app` | `kaggle/01-duecare-exploration-workbench/` |
| Live Demo | **DueCare Live Demo** | `taylorsamarel/duecare-live-demo` | `kaggle/02-live-demo/` |
| A-00 Omni Experiment Workbench | **DueCare Fine-tuning and Evaluation** | `taylorsamarel/duecare-fine-tuning-and-evaluation` | `kaggle/A-00-omni-experiment-workbench/` |

**Intentionally not renamed** (stable contract surfaces):
- folder paths under `kaggle/`
- internal symbols `A00_MODEL_RUNTIME`, `set_kernel_id("a-00-omni-experiment-workbench")`, etc.
- endpoint family `/api/a00/...`
- harness profile names like `chat_no_online`, `baseline_harness_profile=none`

## Files most-recently touched (judge-facing)

| File | What it is |
|---|---|
| `packages/duecare-llm-server/src/duecare/server/static/slides.html` | 23-slide pitch deck. Source of truth for the recording. |
| `packages/duecare-llm-server/src/duecare/server/slides_cache.py` | Cached chat-slot generator (`/api/slides/cached-io`). RA 8042 fix applied. |
| `packages/duecare-llm-server/src/duecare/server/static/start.html` | Two-tile landing at `/start`. |
| `packages/duecare-llm-server/src/duecare/server/static/slides-setup.html` | Cached chat-row generator at `/slides/setup`. |
| `docs/writeup_draft.md` | The ≤1500-word Kaggle writeup. 1444 words now. |
| `README.md` | GitHub front page with the "Try in 30 seconds" hero. |
| `kaggle/_INDEX.md` | Three-kernel index (slug + title columns). |
| `kaggle/01-duecare-exploration-workbench/README.md` | DueCare App README. |
| `kaggle/02-live-demo/README.md` | DueCare Live Demo README with 5-click bootstrap. |
| `kaggle/A-00-omni-experiment-workbench/README.md` | Fine-tuning and Evaluation README with 5-click bootstrap. |
| `apps/duecare-ai.com/app/templates/use-cases.html` | Website 6-card lane page. |
| `apps/duecare-ai.com/app/templates/kernels.html` | Website kernel cards (slugs updated). |

## Tests in their current state

```
pytest packages/duecare-llm-server/tests/         ->  58/58 pass
pytest apps/duecare-ai.com/tests/test_app.py      ->  21/21 pass
pytest packages/duecare-llm-server/tests/test_slides_surface.py -> 14/14 pass
```

The slides-contract test (`test_slides_surface.py`) pins these
literals — do not delete them without updating the test:

- slide IDs: `title`, `demo-chat`, `case-analysis-overview`,
  `knowledge-sharing-demo`, `module-ecosystem`, `benchmarks`
- demo-runner attributes: `data-demo-run="moderation|case|phone|chat|research|sharing"`
- localStorage key: `duecare.slides.demo.chat`
- copy phrases:
  - "Exploitation continues because the protective workflow is fragmented"
  - "Five comparable workflows, one shared local substrate"
  - "Gemma 4 is not another lane"
- forbidden strings: `Filipina`, `class="slide dark"`,
  `class="slide accent"`, `--camera-safe-right`, `arrows / space`

## Open decisions for Taylor (and Codex if delegated)

### 1. Publishing the renamed Kaggle slugs

The new slugs (`duecare-app`, `duecare-fine-tuning-and-evaluation`)
don't exist on Kaggle yet — they're only the new metadata. Before
submission:
- decide whether to publish under the new slugs (cleanest) or keep
  the old `duecare-exploration-workbench` slug live and have the
  writeup point at it instead;
- if publishing under new slugs, the old URLs will 404 (or stay live
  as orphans). Recommendation: publish under new, leave the old as
  redirect-style placeholders in their description.

Per CLAUDE.md rule 50, Kaggle pushes are manual — Codex should not
run `kaggle kernels push` without Taylor's explicit OK.

### 2. Final A-00 run for real benchmark numbers

The deck and writeup currently say "we'll publish specific lift
numbers from a final A-00 run alongside the submission." Codex /
Taylor should:
- run `A-00` end-to-end on the canonical PH-HK prompt set with the
  shared Gemma 4 model and the `chat_no_online` harness profile;
- record the four arm scores (base / +harness / fine-tuned /
  fine-tuned+harness);
- back-fill those numbers into:
  - the deck `What A-00 produces` slide (currently has 4 capability
    cards, can add a small score sub-panel)
  - the writeup section 5
- keep the qualitative framing as the lead; the numbers are the
  evidence underneath.

### 3. Synthetic-evidence harness integration

There's a sister repo at
`C:/projects/major_cases/synthetic_test_evidence/` with a 184-entry
release zip, closed-set indicator vocabulary, prompt packs (v1 / v2),
and per-lane sample cases. It is referenced in the writeup's
section 7 as prior art / influence. Open decisions:
- copy one cherry-picked case (e.g.
  `duecare_showcase/02_caseworker_demo/case_DC-SYN-CEP-1100_domestic/`,
  ~247 KB) into `packages/duecare-llm-chat/.../static/samples/` as
  an additional rich sample bundle?
- mirror the closed-set RISK_INDICATORS vocabulary into the GREP
  rules JSON?
- publish the sister repo on GitHub so the writeup link works for
  judges?

Scoped out today to avoid churn close to the deadline.

### 4. Apps / duecare-ai.com deploy

The website was updated (6th use-case card, new kernel slugs) but
not redeployed today. Confirm what `https://duecare-ai.com/` shows
now vs the new templates and redeploy if drift exists.

### 5. Video script alignment

`docs/video_script.md` has not been touched today and may still
reference the old kernel names or any soft-deleted benchmark
numbers. Re-read it before recording.

## What's already covered in the deck (so you know what NOT to redo)

23 slides in this order:

1. Title — "AI infrastructure to combat migrant-worker exploitation"
2. Stakes — scale + capability gap (28M / $236B / 169M / 3×)
3. Solution — 5 lanes + shared substrate
4. Moderation overview (3 FB cards)
5. Moderation demo (FB post + 5-stage harness)
6. Case-analysis overview (pipeline + lanes)
7. Case-analysis demo (dropzone + typed edges)
8. Information access overview (phone + cards)
9. demo-chat (cached worker question slot)
10. Research overview (graph SVG + cards)
11. Research demo (dropzone + cluster results)
12. Anonymized-sharing overview (4-step flow)
13. Anonymized-sharing demo (dropzone + KO candidates)
14. Components (6 substrate lanes)
15. Download knowledge packs (NEW — 6 download cards)
16. Module ecosystem (reinforcement loop)
17. Benchmarks (A-00 capability framing, no hard percentages)
18. Why Gemma 4 (6 lanes)
19. What makes this unique (4 tiles: substrate counts / on-device APK / sharing reinforcement / evolving eval)
20. Conclusion
21. Resources (3 kernel cards with new slugs)
22. FAQ
23. Appendix

## Pointer: how to run the deck locally to verify

```bash
cd /path/to/gemma4_comp
python -m venv .venv && source .venv/bin/activate
pip install -e packages/duecare-llm-server
python -c "
from duecare.server import create_app
from duecare.server.state import ServerState
import tempfile, pathlib, uvicorn
tmp = tempfile.mkdtemp()
pathlib.Path(tmp, 'out').mkdir(parents=True, exist_ok=True)
s = ServerState(db_path=str(pathlib.Path(tmp)/'t.duckdb'),
                pipeline_output_dir=str(pathlib.Path(tmp)/'out'))
uvicorn.run(create_app(s), host='127.0.0.1', port=8771)
"
```

Then open `http://127.0.0.1:8771/start`, click *Project slides*,
arrow through all 23. Open `http://127.0.0.1:8771/slides/setup` to
pre-bake the cached worker question for the `/slides#demo-chat`
slide.

## Pointer: the live demo flow for the recording

1. **Open `/start`** — show the two-tile landing.
2. **Click *Project slide setup*** — pick an audience + use case →
   *Generate* → *Save for slides*. The cached row is now in
   localStorage.
3. **Click *Project slides*** — walk through the 23-slide deck
   end-to-end. Each demo slide has a "Run harness" / "Process
   bundle" / "Ask graph" / "Replay conversation" button that
   replays its canned animation in ~3 seconds with a visible
   "cached · replays in ~3s" label.
4. **On `/slides#demo-chat`** — the cached prompt + response from
   step 2 appears immediately. No GPU wait.
5. **Optional**: from `/start`, click *Bulk File Review*
   (`/wb-static/process.html`) and drop in the
   `case_files_streamlined_demo.zip` sample for the live process
   demo with real Gemma 4 if the model is loaded.

## Communication style notes (pulled from CLAUDE.md feedback)

For any follow-up by another agent:

- Don't headline "Privacy is non-negotiable" — the project frames
  privacy as one boundary among many, not the slogan.
- Don't use "ship/shipping" verbs — Taylor has rejected the metaphor.
- Composite agency names (Sunburst, HK Domestic Jobs) must carry a
  visible "(composite)" label in any published artifact.
- "Filipina" must never appear in published copy.
- No specific benchmark lift percentages without a measured A-00
  run to back them up.

## Recommended next session priorities

1. Refresh `docs/video_script.md` to use the new kernel display
   names, the softened benchmark framing, and the 23-slide deck
   structure (current order).
2. Wider drift sweep on `docs/` for any remaining "DueCare
   Exploration Workbench" or "A-00 omni experiment" literals (a
   drift audit is running and will land its findings in a follow-up
   commit).
3. Run A-00 end-to-end and back-fill the lift numbers.
4. Decide Kaggle publishing strategy (new slugs vs keep old) and
   execute the manual push.
5. Redeploy the duecare-ai.com website with the new templates.

Submission deadline: **2026-05-18** (today by the project context;
adjust if Taylor has confirmed a different deadline).

Good luck.
