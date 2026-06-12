# Video Script - DueCare Gemma 4 Good Submission

Current as of 2026-05-18. Target runtime: 2:50-2:58. Host the final
video publicly on YouTube. The recording should use the live-demo
kernel at `/start` and `/slides`; optional live product cuts can come
from `/wb-static/process.html`, `/slides/setup`, and the sibling
Android APK.

## Submission Title

**DueCare: A Gemma 4 Safety Ecosystem for Migrant-Worker
Protection**

**Subtitle:** A self-hostable multi-faceted Gemma 4 implementation for content
moderation, case analysis, worker support, research, and anonymized
knowledge sharing.

## Recording Principles

- Open with scale and system gaps, then anchor the demos in the named
  composite (Maria — labeled composite) and close with named NGOs per
  rule 00 (the rubric's "human story" requirement).
- Use the same clean slide surface throughout. Do not record helper
  controls, browser DevTools, or model-loader modals unless explaining
  the local runtime.
- Keep the bottom-right corner visually quiet for the camera overlay.
- Every demo segment should look interactive: visible button press,
  short loading state, trace/result reveal, and cited output.
- Use personal examples only inside use-case demos, and label composite
  names as composite.
- Use "case analysis" as the product-lane label.
- Do not promise a live GPU result if the slide is using cached output.
  Say "cached replay" or show the real activity log.

## 3-Minute Beat Sheet

### 0:00-0:15 - Title and Scale

Visual: slide 1, then slide 2. Show the title and the scale numbers:
forced labor, illicit profit, migrant-worker risk, and fragmented
protective workflows.

Voiceover:
"Migrant-worker exploitation is not a niche content problem. It is a
global safety, evidence, and access problem. Generic AI can sound
confident while missing the statute, the fee cap, the retaliation risk,
or the evidence a caseworker needs next."

### 0:15-0:35 - The System Gap

Visual: slide 2 problem framing and slide 3 ecosystem diagram.

Voiceover:
"Exploitation continues because protective work is fragmented:
platform moderation is too generic, case analysis is slow and legacy,
workers need offline answers, researchers lack shared evidence graphs,
and verified knowledge does not flow back into the tools."

### 0:35-0:55 - Solution and Gemma 4 Engine

Visual: slides 3 and 18. Keep Gemma 4 visually under the lanes, not as
a lane itself.

Voiceover:
"DueCare is one local safety stack across six lanes: platform moderation,
NGO and regulator case analysis, worker support, research,
anonymized knowledge sharing, and developer integration. Gemma 4 is the engine underneath: tool-capable,
fine-tunable with Unsloth, multimodal for file review, and small enough
to run locally."

### 0:55-1:25 - Content Moderation Demo

Visual: slides 4-5. Click the demo button. Show a recruitment listing,
the harness stages, fired indicators, citations, and refusal boundary.

Voiceover:
"In moderation, the harness catches patterns generic moderation misses:
fee camouflage, wage assignment, restricted provider choice, document
retention, and retaliation language. The response is not just a label;
it shows which rules fired, which sources were retrieved, and what the
model is allowed to do next."

### 1:25-1:55 - Case Analysis Demo

Visual: slides 6-7 or `/wb-static/process.html` with
`case_files_streamlined_demo.zip`. Show upload, progress, Gemma edge
creation, graph/result cards, and a typed edge with row citation.

Voiceover:
"For a case bundle, DueCare parses documents, extracts people,
payments, dates, locations, journey stages, and typed graph edges.
Local Gemma proposes additional edges from text and media context, but
the reviewer confirms them before graph chat or export."

### 1:55-2:15 - Worker Access Demo

Visual: slide 8 and slide 9 cached worker question, or the Android APK
if stable. Show plain-language answer, formal protections, practical
retaliation risk, contacts, and evidence preservation.

Voiceover:
"Take Maria — a composite of real Filipino domestic-worker cases. She
pastes a recruiter message and gets plain language back: the
fifty-thousand-peso training fee is illegal, what evidence to preserve,
where to report safely, and what retaliation risk remains in practice.
The Android path keeps that help offline."

### 2:15-2:32 - Research and Sharing Demo

Visual: slides 10-13. Show a research question grouping agencies,
accounts, or repeated fee patterns, then a redacted knowledge object
candidate.

Voiceover:
"For researchers and regulators, the graph can surface repeated
patterns across cases. Reviewed facts can become anonymized knowledge
objects: a fee paid, a refund pathway, a small-claim outcome, or a new
agency pattern that improves the next local pack without centralizing
raw case files."

### 2:32-2:50 - Evidence and Benchmarks

Visual: slide 17. Show the A-00 matrix; optionally cut to the lift
evidence on the compare page. Avoid hard-to-read detail.

Voiceover:
"Same prompts, same judge: the harness lifts stock Gemma 4 by six
points, and fine-tuned plus harness scores nearly twelve over stock —
fine-tuning shapes refusals; the harness supplies the statutes, fee
caps, and forced-labor indicators. In a separate 911-prompt benchmark,
an independent judge scored harnessed Gemma 4 31B plus-1.7 out of ten —
a 73-percent win rate."

### 2:50-3:00 - Close

Visual: slides 20-21. Show GitHub, Kaggle kernels, live demo route,
and duecare-ai.com.

Voiceover:
"DueCare drafts; workers, caseworkers, and reviewers decide — built so
groups like Polaris, IJM, and POEA-licensed legal aid get statute-grade
answers on hardware they already own. Local Gemma 4 where sensitive
data lives."

## Required On-Screen Proof Points

- `/start` and `/slides` load from the live-demo kernel.
- Demo runners are visibly labelled as cached replays when cached.
- Bulk File Review shows upload, progress, Gemma edge creation, and
  reviewer confirmation.
- A-00 slide shows measured 2026-05-18 numbers, not future caveats.
- Title and subtitle match the submission text above.
- The final card includes GitHub, the Kaggle kernels, and the current
  live demo URL.
