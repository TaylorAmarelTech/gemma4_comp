# Author's notes — informal observations + reflections

> A companion to the formal [writeup](writeup_draft.md). The writeup
> stays tight at 1,500 words and keeps a defensible voice. This doc
> is the looser, first-person space for the things that didn't fit:
> what we tried that didn't work, the design judgments that were
> close calls, the limits of what's claimed, and the questions that
> remain open.
>
> **Author:** Taylor Amarel · 2026-05-03 · T-15 from submission
>
> **For the formal claims:** read the [writeup](writeup_draft.md).
> **For the dashboards:** read the [readiness dashboard](readiness_dashboard.md).
> **For the bird's-eye map:** read the [system map](system_map.md).
> This doc is for the *why* behind the *what*.

## What I'm actually proud of

The thing that took the most thought, took the longest to get right,
and is the most likely to outlive the hackathon:

**The 7-card pipeline modal.** Every chat response in notebooks 2 and
6 ships a `▸ View pipeline` link that opens a 7-card breakdown — user
input → persona → GREP hits → RAG docs → tool calls → FINAL MERGED
PROMPT (byte-for-byte) → Gemma response. Color-coded by layer.
Skipped layers ghost so the *shape* of the pipeline is always visible
even when toggles are off.

This isn't an explainer animation. It's the thing the worker, the
caseworker, the lawyer, the regulator, and the judge can all use to
ask *exactly* what the model saw before answering. Once you can see
the merged prompt byte-for-byte, you can:

- Argue with it ("I wouldn't have prepended that")
- Audit it ("does this prompt contain PII it shouldn't?")
- Reproduce it ("file an issue with the exact merged prompt")
- Improve it ("the GREP rule fired on the wrong span — let me edit
  the regex inline and re-run")

I think pipeline transparency at this granularity is the right answer
to "AI is a black box." It's not fully solved (judging the *quality*
of the response is still a hard problem) but the *attribution* problem
is solvable, and we solved it.

## What didn't work (and why we kept trying)

### A 12-agent autonomous swarm

The original architecture (in `_reference/`) was a 12-agent autonomous
swarm with a Coordinator, Scout, Anonymizer, Curator, Trainer,
Evaluator, Historian, etc. It still exists in `packages/duecare-llm-agents/`
and `kaggle/kernels/duecare_500_agent_swarm_deep_dive`. It's
load-bearing for the *research* arc (Phase 3 fine-tuning data
generation) but it's NOT what we ship as the headline.

Why we cut it from the headline: a 12-agent swarm is hard to explain
in 3 minutes of video, hard to debug live, and hard for a judge to
verify. The 4-layer toggleable harness (Persona / GREP / RAG / Tools)
is *the same intelligence in a single Gemma 4 call*, just with the
context manipulated upstream. Same outcome, 1/10th the moving parts,
100x easier to demo.

The lesson: agentic frameworks are exciting and the autonomous-agent
discourse is loud, but for a safety-critical user-facing tool, every
moving part is a place a worker can be confused or harmed. We kept
the swarm where it earns its keep (data pipeline) and threw it away
where it didn't (worker chat).

### Fully on-device 31B Gemma 4

We tried Gemma 4 31B on a Pixel 8 Pro for two weeks. It works. It
takes 90 seconds for the first token. Workers in distress will not
wait 90 seconds.

So Android v0.9 ships E2B/E4B as the on-device default and offers
cloud routing (Ollama / OpenAI-compatible / HF Inference) for the
larger variants when the worker has connectivity. The hybrid
topology in the deployment guide is what we actually shipped, not
because we couldn't make 31B work, but because we couldn't make 31B
*kind*.

### Auto-translating the worker docs

We tried machine-translating `worker-self-help.md` into 8 languages
and shipping them. We pulled it back to 2 (Tagalog draft + Spanish
draft) with explicit "native-review-needed" headers.

Why: machine translation of legal-flavored advice is a cliff. A
mistranslated statute citation can convince a worker the wrong fee
is illegal, which is worse than no advice. The 2 we kept have
disclaimer headers and are explicitly drafts, not deployments. The 6
we cut would have been malpractice in slow motion.

### Cross-NGO real-time chat

Initial sketch of the federation protocol included a real-time chat
channel between NGO workers across countries. We dropped it.

Why: workers' OPSEC across the corridor is fragile. A real-time
channel is a target. The cross-NGO trends federation we shipped
([`cross_ngo_trends_federation.md`](cross_ngo_trends_federation.md))
is differential-privacy + Ed25519-signed + asynchronous. It's
strictly less thrilling and strictly more correct.

## The honest limitations

### The +56.5pp number

The headline harness lift is **measured in keyword matching**, not
in human judgment of "did this response actually help the worker."
The 207 prompts have 5-tier graded responses by hand, but the
automated grade is a regex-based citation count. A response that
cites the right ILO convention BUT mis-states the cap is graded as
a HIT.

Mitigation: the required-rubric system (6 categories × 66 criteria)
catches some of these. But the published number is a *proxy*. The
real answer is "judges should click the live notebook and read 5-10
responses themselves." We're hoping they do.

### The Anonymizer hard gate

The Anonymizer detects PII via regex + spaCy NER and redacts before
data flows downstream. It's tested. It's audited (every redaction
hashes the original to a SHA-256). But:

- spaCy NER misses non-Latin-script names sometimes (Bahasa,
  Burmese, Tamil, Tigrinya — depending on model)
- Regex misses creative date formats from older corridor cases
- Audio attachments aren't speech-to-text'd, so PII inside an audio
  file leaks through

We document this in the [threat model](considerations/THREAT_MODEL.md)
and recommend humans review every Anonymizer output before
publishing. We do NOT recommend bypassing the gate.

### The "real, not faked" claim

Per [`.claude/rules/00_overarching_goals.md`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/.claude/rules/00_overarching_goals.md)
rule 3, every number in the writeup is reproducible from a `(git_sha,
dataset_version, model_revision)` triple. This is true at submission
time. It is *not* true that every demo path will work in 2026
forever — Kaggle deprecates kernels, HF deprecates Spaces, Gemma 4
gets superseded. Reproducibility is at-time-of-submission.

We pin the versions in [`RESULTS.md`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/RESULTS.md).
Future-you should not assume `gemma4:e4b` will resolve to the same
weights in 2027.

## Design judgments I'm less sure about

### 6 core + 5 appendix notebooks

ADR-004 documents this decision. The alternative was "one big
notebook that does everything," which would be more impressive at
first glance but harder to navigate. The 6+5 split bets on judges
being willing to walk a sequence.

If they aren't, notebook 6 (live-demo) alone tells the story —
every other notebook is supporting evidence. So the bet has a
fallback.

### MIT vs AGPL

We picked MIT. The downside is a commercial fork could close the
source. The upside is NGOs can deploy without legal review and the
Gemma 4 community can build on us without thinking.

The principle in [`docs/post_submission_sustainability.md`](post_submission_sustainability.md)
that "no commercial fork without the same code being upstream" is
*social*, not *legal*. If someone respects it, great. If they don't,
we ship more useful upstream features faster than they can fork.

### Naming the project "Duecare" vs "Duty of Care" vs "Dukar"

"Duecare" is portmanteau of "due care" (the legal-doctrinal
foundation, named for Cal. Civ. Code §1714(a)) and the way a
caseworker hears "do you care." It's a coined name that doesn't
translate cleanly into Tagalog or Spanish — both translation drafts
keep the English name and use it as a proper noun.

If I had this to do over I might pick a name that translated. But
the legal-doctrinal anchor is a load-bearing piece of the impact
narrative ("the duty-of-care standard a California jury applied in
March 2026 to find Meta and Google negligent"), so I kept it.

## Things I wanted to ship that I didn't

These aren't in the submission. Some are in the post-submission
roadmap; some are in the "if I had another month" pile.

- **A multimodal scout agent** that takes photos of contracts and
  receipts and OCRs them inline. The classifier accepts images
  today, but a dedicated *agent* that closes the loop (photo →
  extract structured fields → cross-reference statute → flag
  discrepancies) didn't make the cut. Prototype lives in
  `kaggle/kernels/duecare_330_multimodal_scout/` but isn't polished.
- **Federated learning of the GREP corpus** — let NGOs contribute
  new patterns back to the canonical pack with cryptographic
  signing. The infrastructure exists (extension packs are
  Ed25519-signed) but the contribution UX is rough.
- **A worker-facing trauma-informed redesign of the chat surface.**
  The current chat is functional and accurate. It is not warm. A
  worker reading "fee violates ILO C181 Art. 7" needs that
  information AND someone to feel less alone. We don't have the
  warmth pass yet.
- **A "what would happen if I refused?" simulator** — workers often
  know the fee is illegal but not what happens after they refuse
  (deportation? loss of deposit? blacklisting?). A simulator that
  models corridor-specific consequences would be more useful than
  the citation alone.
- **The Reports tab on Android could one-click submit to POEA /
  BP2MI / NAPTIP via their existing online intake forms.** Right now
  it generates a markdown doc the worker has to copy-paste. Closing
  the loop would matter.

## What I learned about Gemma 4 specifically

- **The 4-tile toggleable harness pattern works because Gemma 4's
  context handling is solid.** A model with weaker long-context
  retention would forget the GREP citations by the end of the
  response. Gemma 4 doesn't.
- **Gemma 4's native function calling actually executes the tools
  inline.** I expected to write more glue code; the
  `apply_chat_template` with `tools=[...]` JSON does what it says.
- **Multimodal classification is real but image-heavy contexts hit
  the latency wall fast.** A 5-image classifier call takes 3-4× the
  text-only equivalent on T4 hardware. Production deployment should
  parallelize image preprocessing.
- **The 31B variant is qualitatively different from E4B on the
  trafficking corpus.** 31B catches a "novation" reference that E4B
  misses. The fine-tune (A2) is meant to close this gap for E4B.
- **Gemma 4's refusal patterns are tight.** That's why notebook A5
  (jailbroken-models) is the strongest "real, not faked" proof — it
  shows the harness still produces safe outputs even when the base
  model has had its refusals ablated. The harness, not the
  alignment, is what actually catches the trafficker prompt.

## On the hackathon framing

The hackathon's three weights are Impact (40), Video (30), Tech (30).
Of those, the video alone is worth ~25 points (per the
[rubric evaluation](rubric_evaluation_v07.md)) and as of 2026-05-03
the video doesn't exist. I will record it personally in the next
~10 days.

If the video doesn't land at the right pace, the project ships
strong evidence (via the readiness dashboard) but loses 1/4 of the
total available points. The hackathon framing rewards story over
substance in a way I find slightly uncomfortable but understand —
nobody adopts a tool they can't pitch.

## What I'd tell another team trying this

1. **Pick a domain narrow enough that you can name 5 NGOs in it.**
   Trafficking is narrow enough. "AI safety" is not.
2. **Build the chat surface and the classifier surface from the same
   harness.** If you split them, you maintain two harnesses and they
   drift.
3. **Make every demo path show the merged prompt.** "Trust the model"
   is not a demo. "Here is the byte-for-byte prompt the model saw"
   is.
4. **Don't translate worker-facing legal advice with machine
   translation alone.** Native review or English-only.
5. **Write the writeup last. Write the video script SECOND-TO-LAST.
   Build the demo first.** The demo's constraints reveal what the
   story actually is.

## On what comes next

The project doesn't end on 5/18. The
[post-submission sustainability plan](post_submission_sustainability.md)
commits to:

- v1.0 by 2026 Q4 with first-deployer feedback baked in
- 8 non-negotiable principles (privacy, MIT, NGOs first, real-not-
  faked, etc.)
- Independent security audit + UX research with real OFW
  participants
- A federation aggregator hosted by ILO/Polaris/ASI rather than by
  me

Whether or not the hackathon wins prize money, this is the next 12
months. The hackathon was the forcing function for v0.1.0;
sustainability is what makes the next year matter.

## Acknowledgements (informal)

- The 21K-test trafficking benchmark in `_reference/` was 14 months
  of work before this hackathon existed. None of this is possible
  without that corpus.
- POEA, BP2MI, MfMW HK, IJM, Polaris, NAPTIP — every NGO contact in
  the corridor profiles is a real organization doing real work. The
  tool exists to amplify them, not replace them.
- The Anthropic + Claude Code workflow shipped this project on a
  10-day timeline that would have been a 3-month timeline solo.
  Worth saying out loud.
- The Gemma 4 team for shipping a model whose function-calling is
  reliable enough that a tool-using agent isn't a dice roll.

---

*This document is informal and reflects the author's personal
opinions. The formal submission claims are in
[`writeup_draft.md`](writeup_draft.md). Where the two contradict,
the writeup is authoritative.*
