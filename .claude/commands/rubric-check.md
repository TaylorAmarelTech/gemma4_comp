---
description: Measure the current project state against the hackathon rubric
---

Perform a rubric-alignment check against the three hackathon judging
criteria as stated in `.claude/rules/00_overarching_goals.md`:

1. **Impact & Vision** (40 pts)
2. **Video Pitch & Storytelling** (30 pts)
3. **Technical Depth & Execution** (30 pts)

## Inputs to read

- `.claude/rules/00_overarching_goals.md` — the authoritative rubric
- `docs/rubric_alignment.md` — the gap analysis
- `docs/writeup_draft.md` — the current Kaggle writeup
- `docs/video_script.md` — the current video script
- `docs/project_phases.md` — the execution plan
- `docs/the_forge.md` — the north-star vision (if it exists)
- `README.md` — the public-facing project description

## What to produce

A scorecard in this format:

```
| Criterion         | Weight | Current est. | Target | Gap |
|-------------------|--------|--------------|--------|-----|
| Impact & Vision   | 40     | <honest #>   | 38+    | <#> |
| Video Pitch       | 30     | <honest #>   | 27+    | <#> |
| Technical Depth   | 30     | <honest #>   | 29+    | <#> |
| Total             | 100    | <sum>        | 94+    | <#> |
```

Then:

1. **Three-sentence honest summary** of where the submission stands
   today on each criterion.

2. **Top 3 gap-closers** — the highest-ROI changes to apply right now,
   each with:
   - Estimated point recovery
   - Estimated effort (hours or days)
   - Which doc/file to edit
   - Whether it blocks or unblocks other work

3. **Red flags** — anything in the current state that would cost
   significant points if a judge saw it today. Be specific: file + line
   if possible.

4. **Green flags** — things the current state does well that the video
   should emphasize.

5. **Next concrete action** — the single most important next thing to
   do, in one sentence. Bias toward video-visible work (70 points live
   in the video per the overarching goals rule).

Keep the whole output under 700 words. Be brutally honest — the purpose
of this command is to surface problems, not to encourage.
