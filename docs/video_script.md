# Video Script — Duecare (v2, matches actual submission)

> **Target:** 2:50 (10-second buffer under the 3:00 cap).
> **Voiceover budget:** ~285 words at ~100 wpm = 2:51.
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

> *"The organizations that most need to evaluate LLMs for this work
> — frontline NGOs, recruitment regulators, labor ministries — can't
> send sensitive case data to frontier APIs. Privacy is non-negotiable."*

**Music:** Low piano enters at 0:25.

### 0:35–1:50 — The demo (the headline 75 seconds)

**Visual:** Cut to the **chat-playground-with-grep-rag-tools notebook**.
Same 68%-loan prompt is pasted. **All four toggle tiles (Persona /
GREP / RAG / Tools) are visible at the bottom.** Cursor clicks
**Persona** ON (purple). Then **GREP** (red). Then **RAG** (blue).
Then **Tools** (green). Each tile fills with color and shows `ON`.

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

> *"This is Duecare. Same Gemma 4. Four toggle layers built into the
> chat surface. Persona — a 40-year anti-trafficking expert. GREP —
> 22 regex rules tagged with ILO conventions and national statutes.
> RAG — an 18-document corpus of ILO C029, C181, C095, POEA circulars,
> BP2MI regulations, HK statutes. Tools — corridor fee caps, fee
> camouflage decoder, ILO indicator matcher, NGO intake hotlines."*

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

### 1:50–2:15 — The classification path (the dashboard reveal)

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

### 2:30–2:42 — Two paths, one harness

**Visual:** Side-by-side. Left: phone showing the chat playground
loaded in a mobile browser (a worker pasting a recruiter message).
Right: desktop showing the content-classification dashboard (an NGO
officer reviewing a queue).

**Voiceover:**

> *"Same harness. Two audiences. A migrant worker pastes a recruiter
> message into the chat. An NGO officer triages 500 cases through the
> dashboard. Same Gemma 4 weights. Same zero inference cost. Same
> no-data-leaves-your-machine guarantee."*

### 2:42–2:50 — Closer

**Visual:** End card. White background. Three lines of serif:

> **Duecare**
> *Exercising due care in LLM safety design.*
>
> github.com/TaylorAmarelTech/gemma4_comp
> kaggle.com/taylorsamarel · five public Kaggle notebooks
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
- [ ] Screen recording: classification notebook, Examples modal, click
      WhatsApp example, Classify, result card fills
- [ ] Side-by-side phone/desktop split (the "two audiences" beat)
- [ ] End card with URLs

**Voiceover word count:** ~285 words. Trim 10–15 if read feels rushed.

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
