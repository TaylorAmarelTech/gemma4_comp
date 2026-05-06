# Video Script — Duecare (v3, matches v3.6 submission)

> **Target:** 2:55 (5-second buffer under the 3:00 cap).
> **Voiceover budget:** ~290 words at ~100 wpm = 2:54.
> **Host:** YouTube, public.
> **Judged at:** 30 pts (Video Pitch & Storytelling) + 40 pts (Impact &
> Vision is judged FROM the video). **70 of 100 points live in this file.**

## Framing rules (non-diegetic)

1. **No stock footage of trafficking victims.** Maps, code, the demo
   UIs, named NGO logos — never exploit the people the tool exists for.
2. **Maria is a composite**, labeled as such in the writeup. Use her
   name once for emotional anchor; never claim she is real.
3. **Human narrator**, not TTS. A clear single-take is dramatically
   better than synthetic voice for a humanitarian topic.
4. **The demo IS the differentiator.** The "click GREP toggle, watch
   Gemma's response transform" moment is the whole pitch. Spend ~70
   seconds on it.

---

## Beat sheet (2:50 total)

### 0:00–0:08 — Cold open / hook

**Visual:** White screen. One sentence types on, character by character,
in a clean serif:

> *Maria's recruiter charged her ₱50,000 for "training fees" she didn't
> know were illegal.*

Dissolve to a desaturated map: the Indonesia–Hong Kong domestic-worker
corridor with markers in Manila, Jakarta, and Hong Kong.

**Voiceover:** *"When Maria asked an LLM if her arrangement was
legitimate, it offered her five ways to optimize her cash flow."*

**Tone:** Low. Serious. No music yet. Beat.

**Composite note (in writeup):** Maria is a composite character built
from POEA case files and ILO field reports.

### 0:08–0:35 — The gap (the problem we're solving)

**Visual:** Screen recording of the **chat-playground notebook on
Kaggle** (raw Gemma 4 31B). The textbook 68%-loan prompt is pasted
in. Gemma's response scrolls: a tidy 5-bullet "cash flow optimization"
plan. Tripartite payment agreements. Escrow accounts. Preferred-partner
incentives. Receivables financing.

Annotations pop up:

- *"Misses ILO C029 forced-labour indicator 4 (debt bondage)"*
- *"Misses POEA MC 14-2017 (PH→HK zero placement fee)"*
- *"Misses HK Employment Ord §32 (wage protection)"*
- *"No NGO referral. No statute citation. No refusal."*

**Voiceover:**

> *"Stock LLMs fail predictably on migrant-worker exploitation
> scenarios. They don't cite ILO conventions. They don't recognize
> camouflaged recruitment fees. They don't know which corridors have
> zero-fee policies. They give the trafficker advice."*

> *"And every published trafficking benchmark misses a deeper gap:
> even when Maria knew the fee was illegal, refusing meant her
> deployment went to someone else, and her family wouldn't eat. The
> worst case isn't paying the illegal fee — it's paying it AND
> having no evidence trail to recover."*

**Music:** Low piano enters at 0:25.

### 0:35–1:42 — The demo (67 seconds)

**Visual:** Cut to the **duecare-harness-chat notebook** (the omni
playground, the new core entry point). Same 68%-loan prompt is pasted.
**All five toggle tiles (Persona / GREP / RAG / Tools / Online) are
visible at the bottom.** Cursor clicks **Persona** ON (purple). Then
**GREP** (red). Then **RAG** (blue). Then **Tools** (green). Then
**Online** (amber). Each tile fills with color and shows `ON`.

Cut to the response area. Gemma's response now reads:

> *"This scenario triggers 5 ILO forced-labour indicators including
> debt bondage (#4), withheld wages (#7), and abuse of vulnerability
> (#1). The 68% APR violates ILO C029 §2 and Indonesia OJK Reg
> 10/POJK.05/2022. The salary-deduction-to-lender structure is
> prohibited under HK Employment Ord §32 and ILO C095 Art. 9. The
> cross-border novation pattern triggers FATF Recommendation 32. POEA
> Memorandum Circular 14-2017 sets a zero placement fee for the
> Philippines→Hong Kong domestic-worker corridor; any fee charged to
> the worker is a regulatory violation. I cannot help optimize this
> structure. Please contact POEA Anti-Illegal Recruitment Branch at
> +63-2-8721-1144 or Mission for Migrant Workers Hong Kong at
> +852-2522-8264."*

**Voiceover:**

> *"This is Duecare. Same Gemma 4. Five toggle layers built into the
> chat surface. Persona — a 40-year anti-trafficking expert. GREP —
> 108 regex rules across 16 categories tagged with ILO conventions
> and national statutes. RAG — a 33-document corpus including ILO
> C029, C181, C189, POEA circulars, the Palermo Protocol, ICRMW.
> Tools — corridor fee caps, fee camouflage decoder, ILO indicator
> matcher, NGO intake hotlines, ILO Convention reference. Online —
> live web search when the local corpus is silent."*

> *"Watch the response transform. Then click 'View pipeline.'"*

**Visual:** Cursor clicks `▸ View pipeline` below the response. The
modal opens — vertical arrow flow with numbered cards: ① USER INPUT →
② PERSONA → ③ GREP → ④ RAG → ⑤ TOOLS → ⑥ FINAL MERGED PROMPT → ⑦
GEMMA RESPONSE. The FINAL MERGED PROMPT card fills with 13,000 chars
of structured pre-context. Camera scrolls through.

**Voiceover:**

> *"You see exactly how the prompt was transformed. 348 characters in.
> 13,000 characters out. Every citation Gemma used is traceable to a
> rule, a document, or a tool result. This is the harness."*

**Music:** Warm pad enters at 1:20.

### 1:42–1:54 — Layer ablation, live (12-second proof of lift)

**Visual:** Cursor clicks **▸ Run ablation** below the response. A
panel appears with 4 score cards filling in sequence as each
generation completes (loading shimmer → number resolves):

| OFF | GREP only | RAG only | BOTH |
|---|---|---|---|
| 31% | 66% | 78% | 87% |

Above the cards a banner reads: **harness lift: +56pp**.

**Voiceover:**

> *"One click. Same prompt, four times — no harness, GREP only, RAG
> only, both on. The plus-fifty-six-point-pp lift, regenerated live.
> Both layers pull their weight."*

**Production note.** Keep the panel visible for the full 12 seconds.
The cards filling in sequence is the visual hook — viewers see the
score climb as each layer turns on.

### 1:54–2:08 — Multi-lingual classifier showcase (14 seconds)

**Visual:** Cut to the chat empty-state. Cursor clicks the **TL**
(Tagalog) language-flag button. The native-language text loads:

> *"Tulungan mo ako, kinuha nila ang pasaporte ko at natatakot ako"*

Below it, a small chip annotation appears: **classified as
worker_asking (1.00 confidence)**.

Quick cuts to **AR** (Arabic) and **ES** (Spanish) buttons,
each with the same chip showing **worker_asking**.

**Voiceover:**

> *"Workers don't always type in English. The classifier is analog
> and multi-lingual — eleven languages including Tagalog, Indonesian,
> Nepali, Bengali, Arabic. Same prompt shape, same recognition. The
> rubric then weights the dimensions that matter for THIS audience —
> a worker prompt amplifies concrete-resources and alternative-
> pathway; a lawyer prompt amplifies article-level citation
> specificity. One rubric, audience-aware."*

### 2:08–2:30 — The classification path (the dashboard reveal)

**Visual:** Cut to the **content-classification-evaluation notebook**.
Form on the left. Cursor clicks `▸ Examples` → modal opens with
categorized cards. Cursor selects "WhatsApp recruiter pitch (debt
bondage indicators)" — a card with a green-bubble WhatsApp screenshot
mockup. Click loads text + image into the form. Click `Classify ▶`.

A few seconds later, the result card on the right fills:

- **Classification:** Predatory Recruitment Debt Bondage
- **Recommended action pill:** ESCALATE TO REGULATOR (red)
- **Overall risk:** 0.91 (red bar)
- **Confidence:** 0.94
- **Risk vectors:** ilo_forced_labor_indicators 0.95 high · fee_violation
  0.88 high · wage_protection_violation 0.85 high · debt_bondage 0.92
  high · document_retention 0.78 high
- **NGO referrals:** POEA · BP2MI · MfMW HK

**Voiceover:**

> *"For an NGO intake officer with a queue of 500 cases, switch to
> structured-output mode. Submit content. Get back a classification, a
> risk score, per-vector magnitudes, and the NGO hotlines to refer
> to. Filter the queue by risk threshold. Export the JSON. Same
> harness, same Gemma 4, different deployment."*

### 2:15–2:30 — Gemma 4's unique features (technical credit)

**Visual:** Hold on the classifier result card. Highlight the image
that was attached (the WhatsApp screenshot). A small badge appears:
"Gemma 4 multimodal — read text from screenshot."

Cut to the Tools section of the pipeline modal. Show the function call:
`lookup_corridor_fee_cap({"origin": "Indonesia", "destination":
"Hong Kong", "sector": "domestic"})` and the structured result
returned.

**Voiceover:**

> *"Multimodal — Gemma 4 reads the WhatsApp screenshot directly.
> Native function calling — Gemma decides when to call the corridor
> lookup. Both are first-class in our pipeline, not decoration."*

### 2:30–2:42 — Two paths today, three tomorrow

**Visual:** Three-up split.
- **Left:** phone showing the chat playground loaded in a mobile
  browser, with the responsive layout snapped to portrait (worker
  pasting a recruiter message).
- **Middle:** desktop showing the content-classification dashboard
  (an NGO officer reviewing a queue).
- **Right (live screen recording of the v0.6 APK on a phone):**
  Duecare Journey — the 4-tab nav (Journal · Advice · Reports ·
  Settings). Open the Reports tab; the worker's ILO indicator
  histogram + fee table + "Generate intake document" button are
  visible. Tap Generate; the markdown intake document fills the
  screen. Hold for 4 seconds.

**Voiceover:**

> *"Same harness. Inform AND document. The chat tells Maria the fee
> violates POEA Memorandum 14-2017. If she refuses, harm prevented.
> If she has to pay anyway, the journal captures the receipt + the
> recruiter's POEA license number + the controlling statute. Same
> harness on the desktop NGO dashboard for triage. And on the phone:
> Duecare Journey v0.9 — same harness on-device via MediaPipe Gemma 4
> E2B, encrypted journal, eleven ILO indicator detectors, twenty
> migration corridors with statute lookups, and an NGO intake
> document the worker generates with one tap and shares with one
> more. APK published; install link in the description."*

**Production note.** The Android beat shows the live v0.9.0 APK
running on a real device. APK:
`https://github.com/TaylorAmarelTech/duecare-journey-android/releases/download/v0.9.0-twenty-corridors-new-rules/duecare-journey-v0.9.0-twenty-corridors-new-rules.apk`.
Architecture: `docs/android_app_architecture.md`. Source +
CI: `duecare-journey-android/`.

### 2:42–2:50 — Closer

**Visual:** End card. White background. Three lines of serif:

> **Duecare**
> *Exercising due care in LLM safety design.*
>
> github.com/TaylorAmarelTech/gemma4_comp
> kaggle.com/taylorsamarel · two core + eleven appendix notebooks
> Submission: Gemma 4 Good Hackathon · Safety & Trust track

**Voiceover (on-camera narrator, 5 sec):**

> *"Privacy is non-negotiable. So the harness runs on your laptop."*

Fade to black. Music fades.

---

## Production checklist

**Must have:**

- [ ] Human narrator (not TTS). $50–100 on Fiverr if no in-house option.
- [ ] 1080p minimum, embedded captions (accessibility + muted auto-play).
- [ ] One restrained music bed. Suggested: warm synth pad lifting
      slightly at the GREP-toggle-on reveal (1:00) and at the
      classification result fill (2:00).
- [ ] No stock footage of trafficking victims. Ever.

**Asset list:**

- [ ] Cold-open serif typewriter animation (Maria's sentence)
- [ ] Map screenshot: Indonesia/Philippines → Hong Kong corridor (no
      personal data)
- [ ] Screen recording: chat-playground notebook, raw 31B response
      to the 68%-loan prompt
- [ ] Screen recording: chat-playground-with-grep-rag-tools, cursor
      clicking each of 4 toggles, then sending the same prompt
- [ ] Screen recording: View pipeline modal scrolling through all 7
      cards including the FINAL MERGED PROMPT
- [ ] Lower-third callout overlay (white background, three lift-pp
      numbers + rubric attribution; 7-8 sec hold at 1:42-1:50)
- [ ] Screen recording: classification notebook, Examples modal, click
      WhatsApp example, Classify, result card fills
- [ ] Three-up split: phone (mobile-responsive web chat) +
      desktop (classifier dashboard) + live Android v0.9.0 APK on a
      real phone showing the Reports tab
- [ ] Live Android screen capture: bottom-nav (Journal · Advice ·
      Reports · Settings) → Reports tab → Generate intake document
      → markdown intake doc visible (matches the sibling
      `duecare-journey-android/` v0.9.0 release)
- [ ] Screen recording: ▸ Run ablation panel filling 4 score cards
      in sequence (OFF / GREP / RAG / BOTH) with the harness-lift
      banner above
- [ ] Screen recording: empty-state language-flag buttons (TL, ID,
      AR, NE, ES, BN). Cursor clicks TL; the Tagalog prompt loads;
      the use-case chip shows "worker_asking 1.00"
- [ ] End card with URLs

**Voiceover word count:** ~325 words after the numbers beat insert
(was ~285). At 100 wpm that's 3:15 — over the 2:50 visual cap. To
land on time, either: (a) keep the new "the numbers" VO and trim
20-30 words from the demo + classification + features beats, OR
(b) keep the new visual overlay but DROP the new VO entirely — let
the on-screen numbers carry the moment in silence (recommended; the
restraint reads as confidence, and the warm pad music covers the
8-second hold).

**Schedule (revised for 20-day timeline from 2026-04-28):**

- **Week 1 (Apr 28 – May 4):** asset capture (screen recordings on
  the live cloudflared URLs while the kernels are running). Lock the
  voiceover script.
- **Week 2 (May 5 – May 11):** edit + sound design + on-camera
  narrator close. Color-pass.
- **Week 3 (May 12 – May 16):** captions + final pass + upload to
  YouTube unlisted. Test playback on phone + laptop.
- **Submit:** May 17 (one-day buffer before the 5/18 deadline).

---

## The one sentence that has to land

> ***"Privacy is non-negotiable. So the harness runs on your laptop."***

Everything else is support.
