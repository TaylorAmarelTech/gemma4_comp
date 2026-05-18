# Codex handoff — 2026-05-18 (final session snapshot)

> Snapshot of the DueCare submission state at end of the 2026-05-18
> work session. Read this top-to-bottom before picking up the
> submission; it tells you what landed today, what's intentionally
> unchanged, what's still open, and the precise files to touch next.

## Submission deadline

**2026-05-18 23:59 UTC** (Gemma 4 Good Hackathon close).

## TL;DR

Eleven commits live on `origin/master` over today's session, plus the
final review pass in this working tree. The submission is in a
**judge-ready** state pending four manual actions Taylor owns
(publish renamed Kaggle slugs, redeploy duecare-ai.com, record the
video, file the Kaggle writeup). Every code surface is aligned with
the new kernel names. The writeup and deck now include the measured
2026-05-18 A-00 smoke matrix instead of future benchmark caveats.
Statutory mis-citation fixed
project-wide and pinned by a contract test. Attribution doc
(`docs/CREDITS.md`) added. Writeup (`docs/writeup_draft.md`,
1494 / 1500 words) positions DueCare for the **Impact Track →
Safety & Trust ($10K)** plus **Special Technology → Unsloth ($10K)**
and **LiteRT ($10K)** prizes.

## Commit log (this session, newest first)

```
[local]    Final review pass: title/subtitle + measured A-00 smoke matrix
6142a55    Writeup v4 (Gemma 4 features + tracks + challenges) + CREDITS + prebake CLI + 5 new tests
0b6fea2    Sweep judge-facing docs for kernel rename + benchmark caveats; add Codex handoff
d3115b4    Add 'Download the knowledge packs' slide (take-it-home)
391ec01    Expand 'What makes this unique' to 4 tiles (add on-device APK)
f108644    Add 'What makes this unique' 3-tile slide before conclusion
a0aa4f9    Add 'cached, replays in ~3s' subtext to each deck demo runner
d1b3e83    Writeup -> technical/HOW orientation; slides -> benefits framing
fffd3b7    Soften A-00 claims + add 6th use-case (Anonymized sharing) to website
b2d8815    Rename kernels + rewrite writeup + fix statutes + add 30s onboarding
36073ef    Port slide deck design from duecare-ai handoff
```

All pushed to `origin/master`.

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

## What's in the writeup (v4)

`docs/writeup_draft.md`, 1494 / 1500 words. Structure:

```
1.  The problem at a scale generic AI is not closing
2.  Why "DueCare" — Cal. Civ. Code §1714(a) duty-of-care
3.  Solution: five lanes, one local substrate (5-lane table)
4.  How Gemma 4's unique features are load-bearing
    - native function calling (tool dispatch)
    - multimodal understanding (Bulk File Review vision queue)
    - local frontier intelligence
    - fine-tunable (Unsloth)
5.  The substrate — components in detail
    (165+ GREP rules, 55+ knowledge packs, persona,
     graph extraction, privacy gates, refusal head, grading)
6.  Main server architecture (FastAPI + harness contract)
7.  Evidence and observations (measured A-00 smoke matrix)
8.  Design decisions and challenges overcome
    (statute error caught + pinned, Kaggle T4 memory budget,
     recording-safe deck)
9.  Future work
10. Prior art and attribution (full per-file in docs/CREDITS.md)
11. Close
```

Track positioning declared up top: **Safety & Trust** (Impact),
**Unsloth + LiteRT** (Special Technology).

## What's in the deck (23 slides)

```
01. Title — "Local Gemma 4 safety infrastructure for migrant-worker protection"
02. Stakes — scale + capability gap (28M / $236B / 169M / 3x)
03. Solution — 5 lanes + shared substrate
04. Moderation overview (3 FB cards)
05. Moderation demo (FB post + 5-stage harness)
06. Case-analysis overview (pipeline + lanes)
07. Case-analysis demo (dropzone + typed edges)
08. Information access overview (phone + cards)
09. demo-chat (cached worker question slot)
10. Research overview (graph SVG + cards)
11. Research demo (dropzone + cluster results)
12. Anonymized-sharing overview (4-step flow)
13. Anonymized-sharing demo (dropzone + KO candidates)
14. Components (6 substrate lanes)
15. Download knowledge packs (6 download cards) ← NEW
16. Module ecosystem (reinforcement loop)
17. Benchmarks (measured A-00 smoke matrix)
18. Why Gemma 4 (6 lanes)
19. What makes this unique (4 tiles: substrate counts /
    on-device APK / sharing reinforcement / evolving eval)
20. Conclusion
21. Resources (3 kernel cards with new slugs)
22. FAQ
23. Appendix
```

## Files most-recently touched (judge-facing)

| File | What it is |
|---|---|
| `docs/writeup_draft.md` | 1494-word writeup (cap 1500). Track-positioned, prior art attributed. |
| `docs/CREDITS.md` | Full library + statute + influence attribution. NEW. |
| `docs/codex_handoff_2026_05_18.md` | THIS FILE. |
| `packages/duecare-llm-server/src/duecare/server/static/slides.html` | 23-slide pitch deck. |
| `packages/duecare-llm-server/src/duecare/server/slides_cache.py` | Cached chat-slot generator. RA 8042 fix applied. |
| `packages/duecare-llm-server/src/duecare/server/static/slides-setup.html` | Cached chat-row generator at `/slides/setup`. |
| `packages/duecare-llm-server/src/duecare/server/static/start.html` | Two-tile landing at `/start`. |
| `packages/duecare-llm-server/tests/test_slides_surface.py` | Contract tests (19 now, was 14). |
| `scripts/prebake_slide_cached_io.py` | NEW CLI. Pre-bakes the 6×7=42 cached chat rows. |
| `README.md` | GitHub front page with "Try in 30 seconds" hero. |
| `kaggle/_INDEX.md` | Three-kernel index (slug + title columns). |
| `kaggle/01-duecare-exploration-workbench/README.md` | DueCare App README. |
| `kaggle/02-live-demo/README.md` | DueCare Live Demo README with 5-click bootstrap. |
| `kaggle/A-00-omni-experiment-workbench/README.md` | Fine-tuning and Evaluation README with 5-click bootstrap. |
| `apps/duecare-ai.com/app/templates/use-cases.html` | Website 6-card lane page. |
| `apps/duecare-ai.com/app/templates/kernels.html` | Website kernel cards (new slugs). |

## Tests in their current state

```
pytest packages/duecare-llm-server/tests/                              ->  63/63 pass
pytest apps/duecare-ai.com/tests/test_app.py                          ->  21/21 pass
pytest packages/duecare-llm-server/tests/test_slides_surface.py       ->  19/19 pass
```

`test_slides_surface.py` now pins (as of today):

- slide IDs: `title`, `demo-chat`, `case-analysis-overview`,
  `knowledge-sharing-demo`, `module-ecosystem`, `benchmarks`,
  `unique`, `knowledge-packs`
- demo-runner attrs: `data-demo-run="moderation|case|phone|chat|research|sharing"`
- localStorage key: `duecare.slides.demo.chat`
- knowledge-pack download hrefs at `/wb-static/samples/*`
- canonical Kaggle slugs (`duecare-app`,
  `duecare-fine-tuning-and-evaluation`); old slugs forbidden
- `RA 8042` mandatory in PH placement-fee cached responses;
  `RA 11227` forbidden
- cached-replay labels (`cached &middot; replays in`)
- placeholder benchmark percentages (62.0/81.5/74.8/88.2)
  forbidden
- copy phrases: "Exploitation continues because the protective
  workflow is fragmented", "Five comparable workflows, one shared
  local substrate", "Gemma 4 is not another lane"
- forbidden strings: `Filipina`, `class="slide dark"`,
  `class="slide accent"`, `--camera-safe-right`, `arrows / space`

## Scripts available

```
scripts/prebake_slide_cached_io.py
  python scripts/prebake_slide_cached_io.py --list
  python scripts/prebake_slide_cached_io.py --js-snippet worker/ph_hk_placement_fee
  python scripts/prebake_slide_cached_io.py --out prebaked_42_rows.json --pretty
```

Generates all 42 (6 audience × 7 use case) cached chat rows so
Taylor can pick one per recording take and paste a single JS snippet
into the browser DevTools to populate `localStorage['duecare.slides.demo.chat']`
without using the `/slides/setup` UI.

## Open decisions Taylor still owns

### 1. Publishing the renamed Kaggle slugs

The new slugs (`duecare-app`, `duecare-fine-tuning-and-evaluation`)
don't exist on Kaggle yet. Before submission:

- decide whether to publish under the new slugs (recommended) or
  keep `duecare-exploration-workbench` live and point the writeup
  back at it instead;
- if publishing new, the old URLs will 404 or become orphans.
  Recommendation: publish new, leave old as redirect-style
  archive-note pages.

Per CLAUDE.md rule 50, Kaggle pushes are **manual** — Codex must not
run `kaggle kernels push` without Taylor's explicit OK.

### 2. A-00 smoke matrix now reflected

The deck and writeup include the 2026-05-18 `e2b-full-train-eval`
smoke matrix: 29.5% stock, 35.6% stock + chat-offline harness,
26.4% fine-tuned, and 41.2% fine-tuned + harness. A larger final
run is optional, not required to remove a placeholder.

### 3. Redeploy duecare-ai.com

The website templates were updated today (6th use-case card, new
kernel slugs). Confirm what `https://duecare-ai.com/` shows now vs
the new templates and redeploy if drift exists.

### 4. Record the video

`docs/video_script.md` was rewritten today around the current
23-slide deck, measured A-00 matrix, and Bulk File Review demo. Re-read
before recording to confirm timings and beats. Submission needs:

- 3-minute YouTube video, publicly viewable, no login
- Cover image (required to file the Kaggle writeup)

### 5. File the Kaggle writeup

Once the Kaggle pages, website deploy, and video are ready:

- new Kaggle writeup with Title / Subtitle / Track from
  `docs/writeup_draft.md`
- attach video URL
- attach GitHub repo URL
- attach live demo URL (the `*.trycloudflare.com` from the running
  live-demo kernel, or the redeployed duecare-ai.com)
- attach cover image
- click Submit

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
slide — or use the new `scripts/prebake_slide_cached_io.py` CLI.

## Pointer: the live demo flow for the recording

1. **Open `/start`** — show the two-tile landing.
2. **Click *Project slide setup*** — pick an audience + use case →
   *Generate* → *Save for slides*. Cached row in localStorage.
3. **Click *Project slides*** — walk through all 23 slides. Each
   demo runner is labelled "cached · replays in ~3s".
4. **On `/slides#demo-chat`** — cached prompt + response appears
   immediately.
5. **Optional**: from `/start`, click *Bulk File Review*
   (`/wb-static/process.html`) and drop in the
   `case_files_streamlined_demo.zip` sample (downloadable from the
   new knowledge-packs slide #15).

## Communication style notes (project conventions)

- Don't headline "Privacy is non-negotiable" — privacy is one
  boundary among many, not the slogan.
- Don't use "ship/shipping" verbs — Taylor has rejected the metaphor.
- Composite agency names ("Sunburst", "HK Domestic Jobs") must
  carry a visible "(composite)" label in any published artifact.
- "Filipina" must never appear in published copy.
- No specific benchmark lift percentages without a measured A-00
  run to back them up.

## Recommended next-session priorities (in order)

1. Re-read `docs/video_script.md` and confirm it's recording-ready.
2. Decide Kaggle publishing strategy and execute the manual push.
3. Redeploy duecare-ai.com with the new templates.
4. Record the video.
5. File the Kaggle writeup with the cover image.

Submission deadline: **2026-05-18 23:59 UTC**.

Good luck.
