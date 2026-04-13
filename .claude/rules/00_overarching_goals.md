# Overarching goals — every prompt, every action

> This rule file is auto-loaded by Claude Code at the project memory level.
> Every decision, every code change, every document edit, every CLI
> command we take on this project MUST be measured against these three
> goals. If a proposed action doesn't advance at least one of them, it
> gets cut.

## The goals (from the hackathon rubric)

**Impact & Vision — 40 points.** As demonstrated in the video, how
clearly and compellingly does the project address a significant real-
world problem? Is the vision inspiring and does the solution have
tangible potential for positive change?

**Video Pitch & Storytelling — 30 points.** How exciting, engaging, and
well-produced is the video? Does it tell a powerful story that captures
the viewer's imagination?

**Technical Depth & Execution — 30 points.** As verified by the code
repository and writeup, how innovative is the use of Gemma 4's unique
features? Is the technology real, functional, well-engineered, and not
just faked for the demo?

**70 of 100 points are under the video's control.** The other 30 are
verified by the code + writeup.

## Concrete implications for every action

1. **The video is the product.** Every engineering decision should be
   evaluated by "does this produce something visible and compelling in
   the final video?" A beautiful abstraction that doesn't show up on
   screen is neutral, not positive.

2. **The story is a human one.** Lead with a named (composite, labeled)
   character. Close with named NGOs (Polaris, IJM, ECPAT, POEA, BP2MI,
   HRD Nepal). Avoid abstractions when a concrete person or institution
   would land harder.

3. **"Real, not faked" is an enforced invariant.** Every number in the
   writeup must be reproducible from `(git_sha, dataset_version)` per
   the architecture doc. Every demo pathway must actually run. Judges
   will test the live demo and skim the code — no Potemkin villages.

4. **Gemma 4's unique features must be load-bearing, not decorative.**
   Native function calling and multimodal understanding are explicitly
   named in the rules. They must be substrate of the solution (the
   Coordinator agent using function calling to orchestrate; the
   multimodal Scout agent taking document photos as input), not
   demo-only showpieces.

5. **"Privacy is non-negotiable"** is the exact phrase from the rules.
   Use it verbatim in the video and writeup. It directly frames our
   migrant-worker-NGO angle.

6. **Cross-domain proof (trafficking + tax_evasion + financial_crime)
   is evidence of generalization.** One command across three domain
   packs demonstrates the harness is real, not a single-purpose tool.

## How to apply to different action types

### When writing code
- Does this code produce output that will appear in the video? Yes → prioritize.
- Is this code exercised by a test? If not, add one. "Not faked for demo"
  means tests are real.
- Does this code depend on Gemma 4's unique features (function calling,
  multimodal, post-training, domain adaptation, agentic retrieval)?
  Yes → flag it in the writeup.

### When writing documentation
- Is this doc something a judge would read? If no → keep it short.
- Does it help a future AI reader navigate the module tree? Yes →
  follow the folder-per-module pattern (PURPOSE, AGENTS, INPUTS_OUTPUTS,
  HIERARCHY, DIAGRAM, TESTS, STATUS).

### When proposing architecture
- Does this architecture survive a stock-vs-enhanced side-by-side video
  clip? If not, simplify.
- Does the architecture's complexity pay off in the impact story? If
  not, cut it.

### When spending compute / API budget
- Does this experiment produce a number that goes in the headline
  table? Yes → run it.
- Is this a backup pathway in case the primary fails? Worth budgeting.
- Is this curiosity? Defer post-hackathon.

### When making time tradeoffs
- P0 items block the submission. Protect them ruthlessly.
- P1 items are the difference between "shipped" and "winning." Do them
  in the last 30% of the window.
- P2 items are stretch. Do them only if P0+P1 are clear.

## The kill test

Before starting any task, ask:
1. Does this advance Impact & Vision? (video story)
2. Does this advance Video Pitch & Storytelling? (demo material)
3. Does this advance Technical Depth & Execution? (code / writeup / reproducibility)

If the answer is "no" to all three — **the task gets cut**.

## When the three goals conflict

Impact > Video > Tech, ties broken by impact.

Example: a beautifully engineered agent that doesn't appear in the
video loses to a simpler agent with visible output in the demo. Tech
depth still matters (30 points is 30 points) but it's verified after
the video, not before.

## Never forget

The video is three minutes. That's ~270 words of voiceover. **Every
architectural decision should fit in one line of that voiceover or it
doesn't matter for the submission.** If you can't describe a feature
in six seconds, simplify or cut.
