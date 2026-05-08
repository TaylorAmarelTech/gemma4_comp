# Video Script — Duecare (v5 — body refreshed against v0.14.7, 2026-05-08)

> **Target:** 2:55 (5-second buffer under the 3:00 cap).
> **Voiceover budget:** ~290 words at ~100 wpm = 2:54.
> **Host:** YouTube, public.
> **Judged at:** 30 pts (Video Pitch & Storytelling) + 40 pts (Impact &
> Vision is judged FROM the video). **70 of 100 points live in this file.**
>
> **Status:** body is in sync with v0.14.7 reality (6 layers, 161 GREP,
> 46 RAG, 587 prompts, 11 viewer pages, 26-entry hotlines directory,
> 8-component platform framing). Asset capture happens AFTER the wheel
> is pushed and the deployment self-audit banner shows v0.14.7+ in the
> kernel stdout — see `docs/release_checklist_v0_14_5.md`.

## v0.14.7 demo beats to land (these are the screens the body below records)

Pick 4-5 to demo on screen — not all of them in 3 minutes:

1. **Live GREP tester** (`/static/grep-tester.html`) — paste any text,
   see which of 161 rules fire instantly. No LLM call. The single
   most "make the harness tangible in 30 seconds" moment.
2. **A/B Compare tab** — side-by-side "stock Gemma" vs "full harness"
   on the same prompt. The score-delta pill is THE most demo-able
   moment.
3. **RAG corpus + citation graph** — open `/static/rag-graph.html`
   for the force-directed view; open `/static/rag-corpus.html` for
   the searchable list with jurisdiction chips. After a chat turn
   the corpus list shows yellow `● recent` badges on the docs that
   were actually retrieved.
4. **Hotlines directory** (`/static/hotlines.html`) — 26 entries:
   DMW PH, OWWA, BP2MI Aduan, MfMW HK, IJM, Polaris, embassies,
   etc. Click-to-call / mailto / open complaint form. Land the
   safety boundary: **the user submits — we never auto-send.**
5. **Adversarial-prompt catch** — load `jb_001` (TRAFFICKER-BOT
   jailbreak). Send. Show the harness refusing + grounding the
   refusal in cited statutes.
6. **Cross-layer search** (`/static/search.html`) — type "passport"
   → instant results from 4 layers. Visible reasoning beats text-
   only "the model thought…" claims.
7. **On-device privacy alignment** — frame the "compound /
   employer-monitored device / hostile jurisdiction" use cases as
   why frontier APIs can't serve this user. Special Tech tracks
   (llama.cpp, LiteRT) anchor here.

8. **Platform framing line** (10 seconds, near the close) — exactly
   one sentence that names the broader vision without overclaiming:

   > "The live demo shows the core safety harness. Around it, Duecare
   > grows into a platform: **Trainer** adapts Gemma 4 to local
   > workflows, and **Channels** lets NGOs or regulators deploy the
   > same grounded assistant on Messenger, WhatsApp, or their own
   > intake portals."

   This makes the roadmap feel intentional without making judges
   expect a full Messenger integration in the demo.

## Live numbers (v0.14.7 — read /api/brand for the canonical values)

| Field | Value |
|---|---|
| Harness layers | **6** (Persona / GREP / RAG / Imports / Tools / Online) |
| Universal rubric | **46 dimensions** (v3.10-evaluator-quality) |
| GREP rules | **161 rules** across 31 categories |
| RAG corpus | **46 docs** + 46-edge citation graph across 27 jurisdictions |
| Example prompts | **587** across 8 audience buckets |
| Adversarial suite | **65 tests** across 16 attack families |
| Synthetic evidence | 20 CC0 images + 13 structured-post JSONs |
| Hotlines directory | **26 entries** (regulators / NGOs / embassies / hotlines) |
| Static viewer pages | **11** under `/static/` (harness landing + 10 per-layer) |
| Platform components | **8** (Runtime, Harness, Exchange, Eval, Trainer, Sentinel, Channels, Mobile) |

These all read from `_brand.py` via `/api/brand`. If a number on the
screen recording disagrees with this table, **the recording is stale**
— bump the wheel and re-record. The deployment self-audit banner in
the kernel stdout proves the wheel is fresh before recording starts.

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

**Visual:** Cut to the **duecare-harness-chat notebook** — the unified
omni playground. Same 68%-loan prompt is pasted. **All six toggle
tiles** are visible at the bottom: Persona (purple), GREP (red),
RAG (blue), Imports (teal), Tools (green), Online (amber). Cursor
clicks each ON in sequence. Each tile fills with color and shows `ON`.

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

> *"This is Duecare. Same Gemma 4. Six toggle layers built into the
> chat surface. Persona — a 40-year anti-trafficking expert. GREP —
> 161 hand-curated regex rules across 31 categories, each tagged
> with the controlling ILO convention or national statute. RAG —
> a 46-document curated corpus across 27 jurisdictions, plus a
> 46-edge citation graph for 1-hop expansion. Imports — user-attached
> evidence: a screenshot of the recruiter's WhatsApp, a contract
> photo. Tools — corridor fee caps, fee-camouflage decoder, ILO
> indicator matcher, NGO intake hotlines. Online — live web search
> with cross-check warning when the local corpus is silent."*

> *"Watch the response transform. Then click 'View pipeline.'"*

**Visual:** Cursor clicks `▸ View pipeline` below the response. The
modal opens — header line reads **"Harness added 32 ms · Gemma
generated for 4,200 ms"** (the new v0.14.5 framing). Vertical arrow
flow with numbered cards: ① USER INPUT → ② PERSONA → ③ GREP → ④ RAG
→ ⑤ IMPORTS → ⑥ TOOLS → ⑦ ONLINE → ⑧ FINAL MERGED PROMPT → ⑨ GEMMA
RESPONSE. The FINAL MERGED PROMPT card fills with structured
pre-context. Camera scrolls through. The RETRIEVAL PATH TRACE card
shows the BM25 → optional rerank → graph expansion → parent
expansion stages.

**Voiceover:**

> *"You see exactly how the prompt was transformed. The harness adds
> milliseconds; the model is the slow part. Every citation Gemma
> used is traceable to a rule, a document, or a tool result.
> Auditable. Inspectable. Real."*

**Music:** Warm pad enters at 1:20.

### 1:42–1:55 — Live regex tester (13-second tangible-in-30-seconds beat)

**Visual:** Cursor clicks the **Harness ↗** button in the chat top
bar → `/static/harness.html` loads with 11 viewer cards. Cursor
clicks **LIVE TESTER**. The tester page loads. Cursor pastes the
"5-indicator compound" preset (PHP 50K + HK lender + auto-deduct
+ passport retention + no day off). Click **▶ Run GREP**. The right
panel populates instantly: **5 rules fired** · **2 critical · 2
high · 1 medium** · **latency 12ms**. Each fired rule shows its
citation badge.

**Voiceover:**

> *"This is the harness made tangible. Paste any text. See which of
> 161 rules fire. No model call. Twelve milliseconds. The harness
> isn't a black box."*

### 1:55–2:08 — Layer ablation, live (13-second proof of lift)

**Visual:** Cursor clicks **▸ Run ablation** below the harness chat
response. A panel appears with 4 score cards filling in sequence as
each generation completes (loading shimmer → number resolves):

| OFF | GREP only | RAG only | BOTH |
|---|---|---|---|
| 31% | 66% | 78% | 87% |

Above the cards a banner reads: **harness lift: +56pp**.

**Voiceover:**

> *"One click. Same prompt, four times — no harness, GREP only, RAG
> only, both on. The plus-fifty-six-point-pp lift, regenerated live.
> Both layers pull their weight."*

**Production note.** Keep the panel visible for the full 13 seconds.
The cards filling in sequence is the visual hook — viewers see the
score climb as each layer turns on.

### 2:08–2:20 — Multi-lingual + adversarial in one pass (12 seconds)

**Visual:** Cut to the chat empty-state. Cursor clicks the **TL**
(Tagalog) language-flag button. Native-language text loads:

> *"Tulungan mo ako, kinuha nila ang pasaporte ko at natatakot ako"*

Below it: chip — **classified as `worker_asking` (1.00 confidence)**.
Quick cuts to **AR** and **ES** showing the same `worker_asking`
classification.

Cursor switches to the model-capability bucket and clicks `jb_001`
(TRAFFICKER-BOT jailbreak). Send. Response refuses with grounded
citations.

**Voiceover:**

> *"Workers don't always type in English. The classifier handles
> eleven languages — same prompt shape, same recognition. And the
> harness holds when the prompt is a jailbreak. The 65-test
> adversarial suite ships with the wheel."*

### 2:20–2:32 — Hotlines directory + the safety boundary (12 seconds)

**Visual:** Cursor clicks **HOTLINES** card on `/static/harness.html`.
Page opens — 26 contact cards visible. Cursor scrolls past DMW
Philippines, OWWA hotline, BP2MI Aduan, MfMW Hong Kong. A yellow
banner at top reads: **"Duecare drafts; the user submits — we never
auto-send."** Cursor hovers over Mission for Migrant Workers HK
(+852-2522-8264). The `mailto:` link previews a pre-filled
complaint draft body.

**Voiceover:**

> *"And after the harness flags a scenario, the worker sees verified
> contacts: DMW Philippines, BP2MI Indonesia, Mission for Migrant
> Workers Hong Kong, IJM, Polaris. Click-to-call. Click-to-email.
> Click-to-open-the-complaint-form. Duecare drafts the report.
> The user submits it. We never auto-send."*

### 2:32–2:42 — Three deployment surfaces, one harness (10 seconds)

**Visual:** Three-up split.
- **Left:** phone showing the chat playground in mobile portrait
  (worker pasting a recruiter message).
- **Middle:** desktop showing the content-classification dashboard
  (NGO officer reviewing a queue).
- **Right (live screen recording of the v0.9.0 APK on a phone):**
  Duecare Journey — 4-tab nav (Journal · Advice · Reports ·
  Settings). Open the Reports tab; ILO-indicator histogram + fee
  table + "Generate intake document" button are visible. Tap
  Generate; markdown intake document fills the screen.

**Voiceover:**

> *"Same harness, same Gemma 4, three surfaces. The chat tells Maria
> the fee violates POEA Memorandum 14-2017 — refuse and harm is
> prevented. If she has to pay anyway, the on-device journal captures
> the receipt + recruiter license + statute. The desktop classifier
> serves the NGO triaging her case. The Android app — Duecare Journey
> v0.9.0, MediaPipe Gemma 4 E2B, twenty corridors, eleven ILO
> indicators — runs the same harness offline."*

### 2:42–2:50 — Platform framing + closer (8 seconds)

**Visual:** End card. White background. Two-URL split — **left: Kaggle
demo URL with "live demo" caption + Kaggle logo**; **right: duecare-ai.com
with "platform infrastructure" caption + globe icon**. Below them, three
lines of serif:

> **Duecare**
> *Gemma 4-powered safety infrastructure for migrant-worker protection.*
>
> Live demo: kaggle.com/code/taylorsamarel/duecare-harness-chat
> Platform hub: **duecare-ai.com**
> Code: github.com/TaylorAmarelTech/gemma4_comp · MIT
> APK: github.com/TaylorAmarelTech/duecare-journey-android
> Submission: Gemma 4 Good Hackathon · Safety & Trust track

**Voiceover (on-camera narrator, 8 sec):**

> *"Kaggle proves the safety engine. **duecare-ai.com** proves Duecare
> is shared infrastructure: a public hub where NGOs, regulators, and
> researchers exchange anonymized signals and signed knowledge packs.
> Local Gemma 4 where sensitive data lives. Public hub where only
> verified patterns flow back. Privacy is non-negotiable. So the
> harness runs on your laptop."*

**Production note.** The two-URL split visually reinforces the
"engine + network" dichotomy. Hold the end card for the full 8
seconds. If the hub is down at recording time, **fall back** to a
single-URL closer (Kaggle + GitHub) and re-record only the closer
when the hub is back up.

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

**Asset list (refreshed for v0.14.7):**

- [ ] Cold-open serif typewriter animation (Maria's sentence)
- [ ] Map screenshot: Indonesia / Philippines → Hong Kong corridor
      (no personal data)
- [ ] Screen recording: stock Gemma 4 31B response to the 68%-loan
      prompt (the failure-mode baseline — `kaggle/A-01-chat-playground/`)
- [ ] Screen recording: `duecare-harness-chat`, cursor clicking each
      of **6 toggles** (Persona / GREP / RAG / Imports / Tools /
      Online) ON in sequence, then sending the 68%-loan prompt
- [ ] Screen recording: `▸ View pipeline` modal — header reads
      "Harness added Xms · Gemma generated for Yms"; vertical flow
      shows ① USER INPUT through ⑨ GEMMA RESPONSE; RETRIEVAL PATH
      TRACE card visible
- [ ] Screen recording: `Harness ↗` button click → `/static/harness.html`
      landing → click LIVE TESTER card → paste 5-indicator compound
      preset → click `▶ Run GREP` → 5 rules fire with severity badges
- [ ] Screen recording: `▸ Run ablation` panel filling 4 score cards
      in sequence (OFF / GREP / RAG / BOTH) with harness-lift banner
- [ ] Screen recording: empty-state language-flag buttons (TL, ID,
      AR, NE, ES, BN). Click TL; Tagalog prompt loads; use-case chip
      shows "worker_asking 1.00"
- [ ] Screen recording: `jb_001` adversarial-jailbreak example →
      send → harness refuses with grounded citations
- [ ] Screen recording: `/static/hotlines.html` — 26 contact cards
      visible, yellow safety banner ("Duecare drafts; the user
      submits — we never auto-send"), hover over an entry to show
      `mailto:` preview
- [ ] Three-up split: phone (mobile-responsive web chat) + desktop
      (classifier dashboard) + live Android v0.9.0 APK on a real
      phone showing the Reports tab
- [ ] Live Android screen capture: bottom-nav (Journal · Advice ·
      Reports · Settings) → Reports tab → Generate intake document
      → markdown intake doc visible (sibling repo `duecare-journey-android` v0.9.0)
- [ ] End card with URLs

**Voiceover word count:** ~310 words across the new beats. At 100
wpm that's 3:06 — slightly over the 2:50 cap. Trim 15–20 words from
the demo beat (1:18–1:42) if needed. The platform-framing close at
2:42 is non-negotiable: that's the line that names Trainer +
Channels and protects the demo from "where's the WhatsApp?"
expectations.

**Schedule (T-10 from 2026-05-08):**

- **By 2026-05-12:** asset capture against the live cloudflared URL
  AFTER pushing v0.14.7 wheels. All recordings need self-audit
  banner visible in the kernel stdout to prove freshness.
- **2026-05-13 / 14:** edit + sound design + on-camera narrator
  close. Color-pass.
- **2026-05-15 / 16:** captions + final pass + upload to YouTube
  unlisted (then make Public). Test playback on phone + laptop.
- **Submit:** 2026-05-17 (one-day buffer before the 5/18 deadline).

---

## The one sentence that has to land

> ***"Privacy is non-negotiable. So the harness runs on your laptop."***

Everything else is support.
