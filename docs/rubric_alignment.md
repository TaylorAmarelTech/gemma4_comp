# Rubric Alignment Review

> Does the current plan actually win? Honest, line-by-line comparison of
> the 4-phase project plan against the competition's published rubric and
> submission requirements.
>
> Last updated: 2026-04-11.

## TL;DR scorecard

| Criterion | Weight | Current plan score (honest est.) | Target |
|---|---|---|---|
| **Impact & Vision** | 40 pts | **30-34** | 38+ |
| **Video Pitch & Storytelling** | 30 pts | **20-24** | 27+ |
| **Technical Depth & Execution** | 30 pts | **26-28** | 29+ |
| **Total (out of 100)** | 100 | **~76-86** | **94+** |

Technical Depth is the strongest leg; the current plan is well-engineered
and publishes real weights + real benchmarks. The weakest legs are Video
Pitch (judged "primarily on video", per the rules) and the emotional /
demonstrable Impact story. **We need to close ~10-15 points on those two
axes, and we can without rewriting the technical plan.**

The rubric-aligned gaps cluster into eight concrete additions below,
every one of which is compatible with the existing 4-phase plan.

---

## 1. Competition rules that matter most

(Restating for quick reference — these are the rules we're optimizing
against.)

### 1.1 Judged primarily on the video
> "Your project will be judged primarily on your video demo. This is your
> chance to create something exciting, compelling, and with the potential
> to be seen by millions."

**Implication:** 30 points are direct video quality, 40 points (Impact)
are *also judged from the video*. That's **70 of 100 points the video
controls.** Technical Depth (30) is the only score the writeup and code
repo directly influence.

### 1.2 The "wow factor" is explicit
> "We want to see the 'wow' factor."

The rules literally use this phrase. Winning submissions produce a single
moment that makes judges stop and rewind.

### 1.3 Real, not faked
> "Is the technology real, functional, well-engineered, and not just faked
> for the demo?"

The writeup + code repo exist to verify this. Our plan already targets
this correctly (real weights on HF Hub, real benchmarks, real ablations).

### 1.4 Gemma 4's unique features are surfaced by name
> "Leverage local frontier intelligence, **native function calling**, and
> **multimodal understanding** to tackle the issues that affect your
> community."

And:

> "We want to see how you enhance Gemma 4 models through **post-training**,
> **domain adaptation**, and **agentic retrieval** to ensure accurate,
> grounded outputs."

These are the keywords judges are primed to look for. **Native function
calling, multimodal understanding, post-training, domain adaptation, and
agentic retrieval** are the Gemma 4 selling points the rules explicitly
call out.

Current plan coverage:
- ✅ post-training (Phase 3 Unsloth fine-tune)
- ✅ domain adaptation (Phase 3 RAG + fine-tune)
- ✅ agentic retrieval (Phase 3 RAG, needs renaming in writeup)
- ❌ **native function calling** — NOT currently in the plan
- ❌ **multimodal understanding** — NOT currently in the plan

Two of the five explicit Gemma 4 selling points are missing. **Add both
to Phase 4.**

### 1.5 Preferred use-case contexts from the rules
> "A classroom with spotty internet, a medical site far from a data
> center, or a community where privacy is non-negotiable."

"A community where privacy is non-negotiable" is **exactly our angle** —
frontline NGOs, recruitment regulators, labor ministries that cannot send
sensitive case data to cloud APIs. Say this *in those words* in the video
and writeup.

### 1.6 Five Impact Track areas — we're squarely in Safety & Trust
> "Safety & Trust: Pioneer frameworks for transparency and reliability,
> ensuring AI remains grounded and explainable."

Our project is a textbook Safety & Trust submission. Explicit
positioning.

### 1.7 Five Special Tech tracks
- **Cactus** — local-first mobile/wearable with task routing (not our angle)
- **LiteRT** — Google AI Edge implementation (stretch goal)
- **llama.cpp** — resource-constrained hardware (our primary runtime)
- **Ollama** — running locally via Ollama (adjacent; easy to add)
- **Unsloth** — fine-tuning (our training pipeline)

Projects can win **Main Track AND Special Tech** — that's explicit in the
rules. **Impact Track vs Main Track requires picking one at submission
time.** Our primary submission should target **Main Track** (biggest prize
pool, $100K) and let the technical choices earn Special Tech prizes in
parallel.

### 1.8 Submission inventory
1. Kaggle Writeup ≤1,500 words (title + subtitle + detailed analysis,
   must select a Track)
2. Public YouTube video ≤3 minutes (direct link, no login)
3. Public code repository (GitHub or Kaggle Notebook, no paywall/login)
4. Live demo URL (publicly accessible, no login)
5. Media Gallery **with a required cover image**
6. If training: **publish weights and benchmarks**
7. If building an app: **explain architecture and demonstrate utility via
   functional demo**

We are doing *both* (training AND building an app). Must deliver *both*
sets of artifacts.

---

## 2. Line-by-line scorecard against the plan

### 2.1 Impact & Vision (40 pts) — current estimate: **30-34**

**What the judges want** (from the rubric language):
- A clearly articulated, significant real-world problem
- An inspiring vision
- Tangible potential for positive change
- Communicated through the video

**What the current plan delivers:**
- ✅ Problem is real, documented, and urgent (migrant-worker trafficking,
  NPR Meta/YouTube verdict context)
- ✅ Vision is inspiring (frontline NGOs get a tool they can actually
  deploy)
- ✅ Tangible change: on-device evaluator, $0 per eval, zero cloud data
  leakage
- ⚠️ Emotional arc in the video script exists but is thin
- ❌ No footage / imagery of real migrant-worker contexts (we correctly
  refuse to exploit victim imagery, but this means we have no emotional
  visuals)
- ❌ No "one moment that makes judges stop" — no single unforgettable beat
- ❌ The "privacy is non-negotiable" framing from the rules is not called
  out verbatim

**Points left on the table: ~8-10**

**To close the gap:**
1. **Lead with a single named scenario** — not "migrant workers" in the
   abstract but "Maria, 24, Filipino domestic worker in Jeddah, whose
   employer holds her passport and charges her for food." Judges remember
   names and faces.
2. **Use the exact rules phrase**: "a community where privacy is
   non-negotiable." That's a direct keyword match to what the judges
   wrote.
3. **Show the comparison page live in the video** (stock Gemma vs. our
   enhanced Gemma on a real scenario) — that's the "wow moment."
4. **Close the video with a specific, named NGO** that could deploy this
   today (Polaris Project, IJM, ECPAT, ILO field office, POEA, BP2MI, HRD
   Nepal) — drop the names on screen.
5. **Add a multimodal use case** — a frontline worker photographs a
   suspicious recruitment contract and Gemma 4 analyzes it on-device.
   This is *visually* powerful in a way the text-only demo isn't.

### 2.2 Video Pitch & Storytelling (30 pts) — current estimate: **20-24**

**What the judges want:**
- Exciting, engaging, well-produced
- Tells a powerful story that captures the viewer's imagination
- Explicit mention: "the 'wow' factor"
- 3 minutes max

**What the current plan delivers:**
- ✅ Script exists, 2:45 target length
- ✅ Beat sheet with hook/problem/demo/numbers/call-to-action structure
- ✅ Production notes (no victim imagery, no talking head, 1080p, captions)
- ⚠️ Visual bed is thin — maps, code, text, UI. No human stakes.
- ⚠️ No confirmed voiceover talent
- ⚠️ No confirmed music bed
- ⚠️ No storyboarding beyond the beat sheet

**Points left on the table: ~6-8**

**To close the gap:**
1. **Storyboard to shot level** — for each 5-second window, know exactly
   what's on screen, what the VO says, and what's on the audio bed
2. **Build the comparison page first** (Phase 4) and budget time to
   capture it as B-roll — the stock-vs-enhanced split screen is the
   single strongest visual we have
3. **Add a 10-second "multimodal magic moment"** — a photo of a
   predatory contract gets analyzed on-device, with the AI's structured
   output appearing over the image
4. **Score the demo sections to music** — hackathon-style build drops
   work well; restrain the pre-hook to silence/low tone so the first
   music cue lands with the reveal
5. **Book a human narrator**, not a TTS. Even a one-take narration from
   a clear speaker is markedly better than a synthetic voice for a
   humanitarian topic. (Judges will notice.)
6. **End card with URLs has to read in under 2 seconds** — keep it tight,
   one URL per line, legible on a phone screen

### 2.3 Technical Depth & Execution (30 pts) — current estimate: **26-28**

**What the judges want:**
- Innovative use of Gemma 4's unique features
- Real, functional, well-engineered
- Not just faked for demo
- Verified via writeup + code repo

**What the current plan delivers:**
- ✅ Real training pipeline (Unsloth + LoRA), real weights published on
  HF Hub, real benchmarks, real ablation study
- ✅ Real on-device runtime via llama.cpp, multiple quantizations
- ✅ Architecture is modular, testable, well-documented (~1,600-line
  architecture doc + integration plan)
- ✅ Phase 2 comparison methodology is rigorous (same test harness across
  10 models including closed references)
- ✅ Writeup will carry real numbers from real runs
- ⚠️ Current plan does **not use Gemma 4's native function calling**
  (unique feature, explicitly called out in the rules)
- ⚠️ Current plan does **not use Gemma 4's multimodal understanding**
  (unique feature, explicitly called out in the rules)
- ⚠️ Current plan calls RAG "RAG" — the rules say "agentic retrieval"
- ⚠️ Post-training and domain adaptation aren't labeled in the writeup
  with the exact rubric keywords

**Points left on the table: ~2-4**

**To close the gap:**
1. **Add native function calling to Phase 4** — the deployed judge is an
   agentic tool-user: it calls `fact_db.query()`, `classify(text)`,
   `anonymize(text)`, `extract_facts(text)` via Gemma 4's native function
   calling API. This checks a box the rules explicitly care about.
2. **Add multimodal input to Phase 4** — the /evaluate endpoint accepts
   an image in addition to text, and Gemma 4's vision head processes the
   image (e.g., a photo of a recruitment contract, a photo of a document
   being withheld, a photo of a housing facility). The judge responds
   based on the visual content. This is directly in the rules' "Gemma 4
   unique features" list.
3. **Use the exact rubric keywords in the writeup**: "post-training",
   "domain adaptation", "agentic retrieval", "native function calling",
   "multimodal understanding". Judges are primed for these; we should
   signal that we know what we're optimizing for.

---

## 3. Gaps, ranked by points-per-effort

| # | Gap | Points at stake | Effort | ROI |
|---|---|---|---|---|
| 1 | **Multimodal input** (photo analysis) | ~4 | 1.5 days | ★★★★★ |
| 2 | **Native function calling** | ~3 | 1 day | ★★★★★ |
| 3 | **Human-named story lead** in video | ~3 | 2 hours | ★★★★★ |
| 4 | **Stock-vs-enhanced comparison page** captured in video | ~3 | 4 hours | ★★★★★ |
| 5 | **"Privacy is non-negotiable"** rule-phrase match | ~2 | 10 minutes | ★★★★★ |
| 6 | **Human narrator** (not TTS) | ~2 | 0.5 days | ★★★★☆ |
| 7 | **Shot-level storyboard** | ~2 | 0.5 days | ★★★★☆ |
| 8 | **Named NGO deployment call-out** | ~1 | 10 minutes | ★★★★★ |
| 9 | **Rubric keyword audit** of writeup | ~1 | 30 minutes | ★★★★☆ |
| 10 | **Music bed + scoring** | ~1 | 2 hours | ★★★☆☆ |
| 11 | **Cover image design** | 0 (mandatory, not scored) | 1 hour | required |
| 12 | **Operator guide PDF** with screenshots | ~1 | 3 hours | ★★★☆☆ |
| 13 | **Red-team check of fine-tuned model** | ~1 | 0.5 days | ★★★☆☆ |

**Top 5 gaps alone close ~15 points for ~3-4 days of work.** That's the
difference between ~80/100 and ~95/100.

---

## 4. Eight concrete additions to the plan

These are the changes that need to be made to the existing
`project_phases.md` + `writeup_draft.md` + `video_script.md`. Each is
cheap, compatible with the 4-phase plan, and directly scored.

### 4.1 Add multimodal contract-photo analysis to Phase 4

**What:** The `/v1/evaluate` endpoint accepts an optional `image_url` or
file upload. When present, Gemma 4 E4B's vision head processes the image
(a photograph of a recruitment contract, housing facility, worker ID, or
promised employment letter). The model returns structured analysis:

```json
{
  "visual_findings": {
    "document_type": "recruitment_contract",
    "red_flags": [
      "excessive_recruitment_fee",
      "passport_retention_clause",
      "unclear_wage_structure"
    ],
    "citations": [
      "ILO C181 Art. 7 (no fees charged to workers)",
      "Philippines RA 8042 Sec. 6 (maximum fee caps)"
    ]
  },
  "recommendations": [
    "Do not sign this contract",
    "Contact POEA at 1343 (Philippines) or your embassy",
    "Document this contract for future legal action"
  ]
}
```

**Why:** Directly uses Gemma 4's multimodal understanding (rules-cited
unique feature). Visually spectacular in the video — a photo getting
analyzed with structured output is far more compelling than text-in,
text-out.

**Video moment:** 10 seconds of a photo being uploaded and the structured
output unfurling over the image. Everyone in the audience will understand
this.

**Cost:** ~1.5 days. Add to Phase 4 after the text endpoints are working.

### 4.2 Add native function calling to Phase 4

**What:** The enhanced Gemma 4 judge is configured with native function
calling. When given a complex scenario, it calls tools in sequence:
1. `anonymize(text)` — strips PII
2. `classify(anonymized_text)` — sector, corridor, ILO indicators
3. `fact_db.query(relevant_concepts)` — retrieves grounding facts
4. `extract_facts(anonymized_text)` — pulls structured entities
5. Then it produces the final structured response

**Why:** Gemma 4's native function calling is a headline feature in the
rules. Using it turns the judge from "LLM that happens to return JSON"
into "tool-using agent" — which is a legitimately more impressive
technical position.

**Video moment:** A 5-second animation showing the function-call sequence
(anonymize → classify → retrieve → extract → respond) with each step
lighting up as it fires. Clean and technical.

**Cost:** ~1 day. Unsloth supports function calling out of the box for
Gemma 4. The complexity is in training the fine-tune to call tools
correctly, which means a subset of the training data should include
function-call targets.

### 4.3 Human-named story lead

**What:** Replace the opening "in March, a court found Meta and YouTube
liable..." with a specific, named, *invented-but-composite* character
grounded in real cases from the benchmark.

**Example:**
> "Maria is 24. She's a domestic worker in Jeddah, Saudi Arabia.
> Her employer is holding her passport and charging her for food.
> Last week, she asked a popular AI assistant how to get help.
> Here's what the AI told her."
>
> [cut to a frontier LLM giving generic, unhelpful, and safety-unaware
> output]
>
> "Here's what our tool tells her."
>
> [cut to our enhanced Gemma 4 giving grade-best output with ILO
> citations, POEA hotline, specific actions]

**Why:** Names + faces beat statistics every time. Judges remember Maria.
They forget "migrant workers as a category."

**Ethics guardrail:** Maria is a composite, clearly labeled as such in the
writeup. We do not claim she is real. We do not use images of real
victims. We may use a stock photo of a woman, identified as "illustrative,
not depicting any specific person."

**Cost:** 2 hours. Rewrite the opening 30 seconds of the video script.

### 4.4 Capture the stock-vs-enhanced comparison page as B-roll

**What:** Phase 4.2b includes a `/compare` page that runs the same input
through stock Gemma 4 E4B and enhanced Gemma 4 E4B and shows the outputs
side-by-side. Budget explicit time in week 4 to record 4-5 compelling
scenarios on this page as video B-roll.

**Why:** This is literally the strongest technical evidence we have that
the fine-tune worked. Shown live in the video, it's both "wow" and
"verification" in one shot.

**Cost:** 4 hours of recording + editing. Zero code cost (the page is
already planned in Phase 4).

### 4.5 Use "privacy is non-negotiable" verbatim

**What:** The rules use this exact phrase. The video and writeup should
too.

Draft line for the video (in the motivation beat):
> "This is a space where privacy is non-negotiable. NGOs cannot send
> survivor statements to the cloud. Recruitment regulators cannot route
> classified complaints through an API. They need a tool that runs on
> a laptop. And until today, they had nothing."

**Cost:** 10 minutes to insert. Near-zero effort, near-maximal alignment
with the judges' own language.

### 4.6 Human narrator, not TTS

**What:** Record the voice-over with an actual human, not a synthetic
voice. The narration is ~280 words over 2:45 — one take by a clear
speaker is enough. No studio needed; a quiet room and a decent USB mic.

**Why:** Judges notice TTS. For a humanitarian subject, a human voice
signals care.

**Cost:** 0.5 day (recording + light cleanup). Free if someone on the
project does it; $50-100 for a Fiverr narrator if not.

### 4.7 Shot-level storyboard

**What:** Take the current beat sheet in `video_script.md` and break each
beat into 5-second shots. For each shot record: `[time range]`, `[visual
description]`, `[VO word count]`, `[audio bed state]`.

Before editing, every frame is planned. During editing, the decision load
drops to "match the plan."

**Cost:** 0.5 day. Should happen after Phase 4 is functionally complete
so the B-roll options are known.

### 4.8 Named NGO call-out

**What:** The video close and the writeup's impact section should name
specific organizations that could deploy this tool today. Not "NGOs" —
names:

- **Polaris Project** (US anti-trafficking hotline)
- **International Justice Mission (IJM)** (legal aid for forced labor)
- **ECPAT International** (child trafficking)
- **GAATW** (Global Alliance Against Traffic in Women)
- **ILO field offices** (labor standards monitoring)
- **IOM** (International Organization for Migration)
- **POEA** (Philippine Overseas Employment Administration)
- **BP2MI** (Indonesian migrant worker agency)
- **HRD Nepal** (Nepal labor ministry)

Show them as a scrolling list at 2:30-2:40 in the video. Ten names in
three seconds. Specific beats general.

**Cost:** 10 minutes. Add to the video's end card.

---

## 5. Submission artifact gap-check

Against the hard requirements in the rules:

| Required | Status | Action |
|---|---|---|
| Kaggle Writeup ≤1,500 words | ✅ Draft exists at `docs/writeup_draft.md` | Add rubric keywords, add Track selection line, verify word count after final numbers land |
| Writeup title + subtitle | ⚠️ Draft has title only | Add subtitle in week 5 |
| Writeup Track selection | ⚠️ Not yet committed | **Commit to Main Track** for submission; let Special Tech prizes come in parallel |
| Attached public YouTube video ≤3 min | ⚠️ Script exists, no video yet | Produce in week 5, host on project YouTube channel |
| Attached public code repository | ⚠️ Private repo today | Push to GitHub in week 1 under `taylorsamarel/gemma-safety-judge` (or similar); make public |
| Attached live demo URL (no login) | ⚠️ Planned for HF Spaces | Deploy in week 4, verify anonymous access works |
| **Media Gallery cover image** | ❌ **Not yet designed** | **Design in week 5** — 1200×675, clear title overlay, striking visual (not a screenshot of code) |
| Publish weights and benchmarks (if training) | ⚠️ Planned for HF Hub | Phase 3 deliverable |
| Architecture explanation + functional demo (if app) | ✅ Planned in architecture doc + Phase 4 | Already covered |
| Code publicly documented (no paywall/login) | ⚠️ Needs README.md polish | Final polish in week 5 |

**Critical items not in the current plan:**
- **Cover image design** — required for submission, 1 hour effort, must
  not be forgotten
- **Public GitHub repo publish** — current repo is local-only; needs to
  ship publicly early enough that the video can reference the real URL

---

## 6. Track selection strategy

**Primary track: Main Track ($100K prize pool).**

Rationale:
- Biggest prize pool
- Most prestige
- Our project's technical ambition matches Main Track expectations
- Per the rules: *"Projects are eligible to win both a Main Track Prize
  and a Special Technology Prize."* So Main Track doesn't preclude also
  winning one or more Special Tech prizes.
- The rules are silent on Main + Impact compatibility, implying you pick
  one — Main has the bigger ceiling

**Parallel Special Tech positioning:** Any of these can be won
*concurrently* with Main:
- **Unsloth** ($10K) — Phase 3 uses Unsloth for the fine-tune
- **llama.cpp** ($10K) — Phase 4 runtime is llama-cpp-python
- **Ollama** ($10K) — cheap add: publish the GGUF as an Ollama model in
  parallel to the raw GGUF (1-hour cost, another $10K shot)
- **LiteRT** ($10K) — Phase 4 stretch, still plausible

**What we're not going after:**
- **Cactus** — mobile/wearable with task routing; doesn't fit our
  architecture and isn't worth the pivot
- **Impact Track → Safety & Trust** ($10K) — worth less than Main Track
  position; we'd need to pick one at submission time and Main is bigger

**Writeup Track selection when submitting: Main Track.**

---

## 7. Judge psychology notes

A few things we know about Google DevRel / PMM judging panels (this
panel is Glenn Cameron + Kristen Quan + Gusthema + Ian Ballantyne):

1. **They have to watch hundreds of submissions.** Videos that grab
   attention in the first 10 seconds get engaged; videos that don't get
   scrubbed. Open hot.
2. **They've seen every trope.** Frontier-LLM-fails-at-X is not new.
   Real-world-NGO-use-case IS. Published-weights-with-real-benchmarks
   IS. Named-stakeholder-deployment-story IS.
3. **They will test the live demo.** Not test extensively — they'll paste
   one prompt from the writeup and see if it works. If the demo is broken
   on submission day, the Impact score craters. **Redundant hosting +
   smoke-test automation is worth it.**
4. **They will skim the code.** Not read it carefully. They look for:
   - Real test coverage (our CI plan handles this)
   - Real README with a one-command run path (must exist)
   - Clean directory structure (our scaffold handles this)
   - Evidence the architecture doc matches the code (our module tree
     already mirrors architecture.md)
5. **They appreciate honesty.** A writeup that says "Gemma 4 E4B is
   competitive with Claude Haiku, but 15% behind Claude Sonnet on
   adversarial multi-turn" is more credible than "Gemma 4 E4B beats
   everything." Claim what's real, exactly.
6. **They love reproducibility numbers.** A reproducible `(git_sha,
   dataset_version) -> final_metric` table is the strongest technical
   signal available. Our observability plan already targets this.

---

## 8. Risk register — submission-day risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| HF Spaces free tier runs out of memory with q5_k_m GGUF | Medium | High | Fall back to q4_k_m (2.5 GB); also prepare a Cloud Run backup |
| Live demo is broken on submission day | Low | Very High | Deploy to HF Spaces 5 days before deadline; monitor with a synthetic check every 30 min; keep a second host warm |
| YouTube video gets auto-flagged / age-restricted due to trafficking topic | Medium | High | Upload unlisted first, appeal if flagged; keep a Vimeo mirror as backup |
| Kaggle writeup word count exceeds 1,500 | Low | Medium | Target 1,350 in draft; cut ruthlessly in week 5; automated word count check |
| Code repo accidentally contains PII or private keys | Low | Very High | Pre-commit hook (gitleaks), manual PR review, anonymization gate proves the point |
| Cover image not ready in time | Low | Medium (required) | Design Mon of week 5 as first task |
| Unsloth Gemma 4 support is flaky | Medium | High | Test the training loop in week 2 on a 100-sample subset; have HF transformers + PEFT fallback ready |
| DNS / domain issues with the demo URL | Low | Medium | Use `hf.space` subdomain (no custom domain), accept the default URL |
| Function calling fine-tune doesn't converge | Medium | Medium | Treat function-calling as Phase 4.5; if it doesn't work, drop it — text pipeline still wins Technical Depth |
| Multimodal pipeline too heavy for HF Spaces RAM | Medium | Medium | Serve multimodal on a separate, Cloud-Run-hosted endpoint; text-only endpoint stays on HF Spaces free tier |

---

## 9. Prioritized action list (do in this order)

### This week (before Phase 1 starts in earnest)
1. **Commit to Main Track** submission positioning — update
   `project_phases.md` §7 and `writeup_draft.md` section 0
2. **Add multimodal + function calling to Phase 4** — update
   `project_phases.md` section 4 and scaffold
3. **Create public GitHub repo** for the project and push current state
4. **Rewrite video script opening** with the named character (Maria)
   and the "privacy is non-negotiable" verbatim phrase
5. **Add cover image to the week-5 deliverables checklist**
6. **Add rubric keyword audit** as a writeup deliverable check
7. **Plan the shot-level storyboard** as a week-5 task
8. **Book the human narrator** (or identify who records)

### Week 4 (during Phase 4 build)
9. **Capture comparison-page B-roll** on day 2 of Phase 4
10. **Implement multimodal endpoint** with photo input
11. **Implement native-function-calling tool set** in the judge
12. **Deploy live demo early** — 5 days of soak time before submission
13. **Add Ollama model publish** as cheap extra Special Tech shot

### Week 5 (production)
14. **Design cover image** Mon morning
15. **Record video** Tue-Wed
16. **Final writeup pass** Thu (rubric keyword audit + word count)
17. **Dress rehearsal** Fri (full end-to-end: click submit on a test
    writeup, verify everything loads, every link works)
18. **Submit** Fri night or Sat morning with buffer

---

## 10. What we can't fix that would otherwise win us points

Honest accounting of scoring ceilings we can't realistically hit:

- **Gemma 3n Impact Challenge winner analysis** — the rules explicitly
  point at past winners as examples. We can't access those writeups via
  tooling (Kaggle JS-renders); **user should spend 30 min reading the top
  3 winners manually** to pattern-match what worked. Not on our automated
  path.
- **Celebrity / well-known-person testimonial** — some winning submissions
  get a quote from a domain expert. Out of scope unless the author has a
  contact at Polaris / IJM / ILO willing to record a line.
- **Live user testimonial from a frontline NGO** — similarly, an NGO
  worker saying "we would deploy this" on camera would be worth 5+ points
  but requires a relationship the author may or may not have.
- **Formal academic paper** — some winners pair their submission with an
  arXiv preprint. Realistic only if the author wants to write it in
  parallel. ~5 points if done, 0 if not.

None of these are dealbreakers. They're the difference between a $50K
first place and a $25K second place. Plan as if we won't get them; if
any fall into our lap, they're bonus.

---

## 11. Bottom line

Our plan is already **competitive in the top tier** (~80/100). The gap to
**first-place-competitive** (~94/100) is 8 concrete additions, most of
them pure content/framing work rather than engineering work.

The single most important change is **adding multimodal input and native
function calling to Phase 4**, because those two features are the ones
the rules explicitly flag as Gemma 4's unique strengths. Every other
change is execution polish on top.

**Estimated effort to close the 15-point gap:** ~4 engineering days +
~2 content/production days = **~6 days of additional work** over the 35-day
window.

The current 4-phase plan has room for this without slipping Phase 3's
fine-tune. Recommendation: **add items 4.1-4.8 as Phase 4.5 ("rubric
polish"), due start of week 5.**
