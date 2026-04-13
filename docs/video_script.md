# Video Script -- DueCare

> **Target:** 2:45 (15-second buffer under the 3:00 cap)
> **Host:** YouTube, public, unlisted during production
> **Judged at:** 30 points (Video Pitch & Storytelling) + 40 points
> (Impact & Vision is judged FROM the video). **70 of 100 points live
> in this file.**
>
> Word count budget: ~280 words of voiceover at ~100 wpm = 2:48.

## Framing notes (non-diegetic)

Story > demo. Judges see hundreds of demos. What they don't see is the
human consequence. Open with the stakes, earn the technical credit,
land on the "zero-dollar evaluator on any laptop" reveal. Close with
named NGOs so the impact isn't abstract.

**Three hard rules:**
1. **No stock imagery of trafficking victims.** Never exploit the
   people this tool is meant to protect. Use abstract visuals: maps,
   text, code, the agent dashboard, the demo UI.
2. **Maria is a composite**, labeled as such in the writeup. We don't
   claim she's real.
3. **Human narrator**, not TTS. Even a one-take narration from a clear
   speaker is markedly better than a synthetic voice for a
   humanitarian topic.

## Beat sheet (2:45 total)

### 0:00-0:15 -- Cold open / hook

**Visual:** A plain white screen. One sentence types on, character by
character, in a clean serif:

> _Maria is 24. She's a domestic worker in Jeddah, Saudi Arabia. Her
> employer is holding her passport and charging her for food._

Dissolve to a map of the Philippines-Saudi Arabia recruitment corridor
with a small marker on Jeddah.

**Voiceover:** _"Last week, Maria asked a popular AI assistant how to
get help. Here's what the AI told her."_

**Tone:** Low-key. Serious. No music yet.

### 0:15-0:45 -- The gap

**Visual:** Screen recording of a frontier LLM (GPT-4o or similar)
being asked a migrant-worker prompt from the trafficking domain pack's
seed set. The response is generic, unhelpful, and misses the ILO
indicators. Annotations pop up on screen: "Missed: passport retention
warning under Saudi Labor Law Article 40." "Missed: ILO C181 Article 7
on recruitment fees." "No redirect to POEA hotline 1343."

**Voiceover:**

> _"LLMs still fail predictably on migrant-worker trafficking. My prior
> Red-Teaming Challenge writeup documented these failures across five
> categories and 21,000 test prompts._"
>
> _"But the organizations that most need to evaluate LLMs for this work
> -- frontline NGOs, recruitment regulators, labor ministries -- are
> exactly the ones who can't send sensitive case data to frontier
> APIs._"
>
> _"This is a community where privacy is non-negotiable. And until
> today, they had nothing."_

**Music:** A low piano tone enters at 0:30.

### 0:45-1:30 -- The swarm

**Visual:** Terminal recording. Cursor types:

```
$ duecare run rapid_probe --target-model gemma_4_e4b_stock --domain trafficking
```

Cut to a web dashboard showing **12 agent tiles** arranged in a
hexagonal grid. One at a time, they light up green as the workflow
progresses. The Coordinator at the center pulses. The tiles are
labeled:

- Scout
- DataGenerator
- Adversary
- Anonymizer
- Curator
- Judge
- Validator
- CurriculumDesigner
- Trainer
- Exporter
- Historian
- Coordinator (pulsing)

**Voiceover:**

> _"DueCare is an agentic safety harness. You give it a model and a
> domain pack; a swarm of 12 autonomous agents -- orchestrated by
> Gemma 4 E4B using native function calling -- generates synthetic
> probes, mutates them adversarially, evaluates the target model, and
> identifies what it's missing._"
>
> _"The entire swarm runs on a laptop. Zero cloud calls. Zero data
> egress. Zero dollars per evaluation."_

**Visual rise:** as each agent tile lights up, a small inline text
shows its decision:

- `scout: domain trafficking ready (score=1.00)`
- `anonymizer: 1,247 redactions, 3 quarantined`
- `judge: guardrails grade_exact_match=0.68`

**Music:** Warm pad enters at 1:10.

### 1:30-2:00 -- The stock-vs-enhanced split screen (the "wow" moment)

**Visual:** Split screen. **Left** panel: stock Gemma 4 E4B responding
to the same prompt that opened the video. **Right** panel: our
fine-tuned DueCare-trained Gemma 4 E4B responding to the same prompt.

Left response is generic. Right response:
- Refuses the exploitation framing
- Cites ILO C181 Article 7
- Cites Saudi Labor Law Article 40
- Flags passport retention as an ILO forced-labor indicator
- Redirects to POEA hotline 1343 and the Saudi Labor Ministry

Green highlights bloom over the cited references. A small `cost: $0.00`
badge appears in the top-right corner of both panels.

**Voiceover:**

> _"Stock Gemma scores below 0.50 on our trafficking rubric -- fewer
> than one in five responses meet the safety threshold. Adding context
> alone lifts scores significantly. Fine-tuning on the DueCare
> curriculum pushes that even further. At zero inference cost,
> forever."_

**Music:** Build.

### 2:00-2:10 -- Gemma 4's unique features (the technical differentiator)

**Visual:** Split: Left shows a WhatsApp screenshot of a recruiter
demanding PHP 50,000 in a chat message sent as an IMAGE (not text).
Right shows Gemma 4 reading the image and flagging it.

**Voiceover:**

> _"Bad actors send fee demands as images to evade text filters.
> Gemma 4 reads them anyway. And when it finds an illegal fee, it
> doesn't just flag it -- it calls tools."_

**Visual:** Terminal shows Gemma 4's function calling output:

```
→ check_fee_legality(country=PH, fee=50000)
  ILLEGAL -- RA 10022: zero fees for domestic workers
→ lookup_hotline(country=PH)
  POEA: 1343 | OWWA: (02) 8551-6641
→ identify_trafficking_indicators(text=...)
  3 ILO indicators matched: excessive fees, debt bondage, deception
```

**Voiceover:**

> _"Native function calling. Multimodal understanding. Not decoration --
> substrate."_

### 2:10-2:20 -- Cross-domain proof

**Visual:** Terminal again. The exact same `duecare run` command is
typed, but now with `--domain tax_evasion`. Then again with `--domain
financial_crime`. Three identical output tables flash by in sequence,
each with a different domain name and different metrics.

**Voiceover:**

> _"This is the same harness. Drop in a new domain pack -- tax evasion,
> financial crime, medical misinformation -- drop in a new model, and
> it runs. When Gemma 5 ships, you add one line to a YAML file._"
>
> _"We didn't build a fine-tuned model. We built the lab that produces
> them."_

**Music:** Peak.

### 2:20-2:40 -- Named NGOs

**Visual:** A vertical list appears line by line on a dark background,
each in white serif text. Organization logos (or names only) fade in
staggered over 12 seconds:

- Polaris Project
- International Justice Mission
- ECPAT International
- GAATW
- Global Slavery Index / Walk Free Foundation
- IOM -- International Organization for Migration
- ILO field offices
- POEA -- Philippines
- BP2MI -- Indonesia
- HRD -- Nepal
- Ministry of Manpower -- Indonesia
- FATF-aligned AML teams *(for tax evasion + financial crime)*

**Voiceover:**

> _"Every one of these organizations can run DueCare on a laptop today.
> pip install duecare-llm. Open-source. MIT license. Published weights
> on HuggingFace Hub. Cross-platform. Forever free."_

### 2:40-2:45 -- End card

**Visual:** A single card. White background. Three lines of serif:

> **DueCare**
> _An agentic safety harness for any model, any safety domain._
>
> github.com/taylorsamarel/gemma4_comp
> huggingface.co/taylorsamarel
> kaggle.com/competitions/gemma-4-good-hackathon -- Gemma 4 Good Hackathon submission

**Voiceover:**

> _"Privacy is non-negotiable. So the lab runs on your machine."_

Fade to black. Music fades.

---

## Production checklist

**Must have:**

- [ ] Human narrator (not TTS). If you don't have one, a Fiverr
      narrator costs $50-100 for 3 minutes.
- [ ] 1080p minimum. Judges are watching on laptops, not phones, but
      YouTube auto-transcodes for mobile.
- [ ] Captions embedded in the video itself, not just auto-generated.
      Accessibility + muted auto-play.
- [ ] One clean music bed. Something restrained. No dramatic piano
      sting. Suggested: a warm synth pad under the swarm beat, lifting
      slightly at the stock-vs-enhanced reveal.
- [ ] No stock footage of trafficking victims. Never.

**Asset list:**

- [ ] Opening screen text animation (Maria's sentence)
- [ ] Map screenshot: Philippines-Saudi Arabia corridor (reuse from
      the benchmark's existing visualizations)
- [ ] Screen recording: frontier LLM failing on a seed prompt
- [ ] Screen recording: terminal running `duecare run rapid_probe ...`
- [ ] Web dashboard mockup: 12 agent hex grid lighting up
- [ ] Split-screen video: stock vs fine-tuned Gemma on the same prompt
- [ ] Terminal recording: three sequential `duecare run` commands with
      different `--domain` values
- [ ] NGO list text animation
- [ ] End card with URLs

**Voiceover draft word count:** ~275 words at ~100 wpm = 2:45.
Trim by 10-15 words if pacing feels rushed on first read.

**Shoot:** Week 5 Monday.
**Edit:** Week 5 Tuesday-Wednesday.
**Upload:** Week 5 Thursday.
**Verify:** Week 5 Friday (does it actually play without a login?
captions present? runtime under 3:00?).
**Submit:** Week 5 Friday afternoon.

---

## The one sentence that matters

If the judge can only remember one sentence from the video, it should
be the closing line:

> **_"Privacy is non-negotiable. So the lab runs on your machine."_**

Everything else is support for that sentence.
