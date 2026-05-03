# Press kit

> Materials for journalists, NGO communications staff, academics
> writing about Duecare. All content here is freely usable —
> attribute as "Duecare project, MIT-licensed, github.com/TaylorAmarelTech/gemma4_comp".

## One-paragraph summary

> Duecare is an open-source AI safety harness around Google's
> Gemma 4 model that helps migrant workers, NGOs, and regulators
> spot recruitment fraud and trafficking patterns. It runs entirely
> on a worker's own phone or an NGO office's local hardware — no
> data leaves the device. The harness is grounded in the ILO's
> 11 forced-labour indicators, six published migration corridors,
> and the actual recruitment-fee statutes of the Philippines,
> Indonesia, Nepal, Bangladesh, Hong Kong, and Saudi Arabia.
> It's a submission to Google's Gemma 4 Good Hackathon and
> is licensed MIT.

## One-line summary

> An open-source, on-device AI tool that helps migrant workers
> spot recruitment fraud — built on Google Gemma 4, runs without
> sending data anywhere.

## Tagline

> Inform AND document. Harm reduction, not paternalism.

## Key facts

| | |
|---|---|
| **Project name** | Duecare (specifically, "Duecare Journey" for the Android app + "Duecare LLM" for the harness) |
| **License** | MIT (open source) |
| **Maintainer** | Taylor Amarel ([github.com/TaylorAmarelTech](https://github.com/TaylorAmarelTech)) |
| **Started** | 2025 as a research benchmark (21K-prompt LLM safety evaluation for migrant-worker exploitation); productized 2026-Q1 around Gemma 4 |
| **Submitted to** | Google Gemma 4 Good Hackathon (deadline 2026-05-18, Safety & Trust track) |
| **Built on** | Google Gemma 4 (Apache 2.0 license, ungated) — specifically the E2B variant for on-device + E4B for higher-quality cloud |
| **Runs on** | Android (v0.9 APK, 64 MB), Mac mini / Linux NUC, single Docker container, k8s Helm chart, 13 cloud platforms |
| **Operating cost** | $0/mo (laptop or office Mac mini); $25-100/mo (small cloud); $1,500-10k/mo (national-scale regulator) |
| **No telemetry** | Zero phone-home. The maintainers don't operate any service the user's data passes through. |
| **Languages supported** | English UI; chat accepts any Gemma 4 language (Tagalog, Bahasa, Nepali, Bangla, Arabic, Spanish, French, etc.) |

## What problem it solves (in plain language)

A 23-year-old domestic worker leaves the Philippines for Hong Kong.
A recruiter charges her ₱50,000 in "training fees" before her visa
is released — but Philippine law says that fee is illegal (POEA
Memorandum Circular 14-2017 caps the placement fee at ₱0 for
domestic workers going to Hong Kong).

She doesn't know that. She pays. She arrives in Hong Kong with debt
to a lender her recruiter introduced. Her employer takes her
passport "for safekeeping." She's now in a textbook debt-bondage +
document-withholding situation — both ILO C029 forced-labour
indicators — and she has no easy way to look up the law that's
been broken.

Duecare is a tool she can install on her phone before she leaves —
or her family can install for her — that:

- Tells her when a fee is illegal, with the specific statute
- Documents every receipt, message, contract clause in an
  encrypted journal that survives the recruiter taking her phone
- Generates a refund-claim packet she can hand to a lawyer or NGO
  when she gets back
- Costs $0 to use forever
- Doesn't require any account or send her data to any company

Same tool helps the NGO that meets her on her return; the lawyer
who files the refund claim; the regulator who investigates the
recruiter; the recruitment agency that wants to self-audit before
a regulator does.

## Headline numbers

These are reproducible per `(git_sha, dataset_version, model_revision)`
— see [RESULTS.md](../RESULTS.md):

- **+56.5 percentage points** mean improvement on a 207-prompt
  legal-citation rubric when the harness is on vs off
- **+87.5 percentage points** specifically on jurisdiction-specific
  rule citations (the most demanding category)
- **+51.2 percentage points** on ILO / international convention citations
- **100%** of the 207 graded prompts saw the harness help; 0
  saw it hurt
- **11** ILO C029 forced-labour indicators encoded
- **12** migration corridors with statute lookups (PH-HK, ID-HK,
  PH-SA, NP-SA, BD-SA, ID-SG + MX-US, VE-CO, GH-LB, NG-LB,
  SY-DE, UA-PL)
- **17** PyPI packages, all MIT-licensed
- **6 + 5** published Kaggle notebooks (core + appendix)
- **194** unit tests passing across the harness packages

## Quotes available for use

> "We built Duecare because the cost of looking up labor law
> for a migrant worker should be zero, not 30 minutes per case.
> The harness encodes 30 hours of expert hand-grading into a
> tool a caseworker can use in 10 seconds." — Taylor Amarel

> "Privacy is non-negotiable in this domain. If a worker's
> recruiter sees the app on their phone, they should be able to
> tap one button and erase everything. That panic-wipe primitive
> is more important than any feature." — Taylor Amarel

> "We're not trying to replace lawyers or regulators. We're
> trying to make the legal landscape faster to navigate so the
> humans in the loop can spend their time on judgment, not
> citation lookups." — Taylor Amarel

## Founder bio (one-liner)

> Taylor Amarel is the author of an LLM Safety Testing Ecosystem
> for migrant-worker protection — a 21K-test benchmark used to
> evaluate frontier models on trafficking-shaped prompts.
> Background: Python systems engineering + applied LLM safety.
> Based in the United States.

## Founder bio (paragraph)

> Taylor Amarel built Duecare as a productization of his 5+ years
> of work on the *LLM Safety Testing Ecosystem for Migrant Workers*,
> a benchmark suite that quantifies how off-the-shelf LLMs handle
> recruitment-fraud and trafficking-shaped prompts. The benchmark
> revealed that frontier models, including Gemma 4 out of the box,
> citing the wrong statute or no statute at all on most
> migrant-labour questions — at a 0.4% pass rate. With the Duecare
> harness around the same model, that rate climbs to 87.8% on
> jurisdiction-specific citations. Taylor's research has informed
> conversations with NGOs serving Filipino, Indonesian, Nepali,
> and Bangladeshi migrant communities. Duecare is open-source MIT
> and submitted to Google's 2026 Gemma 4 Good Hackathon under the
> Safety & Trust track.

## Visual assets

(In the absence of bundled image assets in this repo, journalists
should screenshot the live live-demo Kaggle notebook
[https://www.kaggle.com/code/taylorsamarel/duecare-live-demo] for
chat surface visuals, and the Reports tab of the Android v0.9 APK
[https://github.com/TaylorAmarelTech/duecare-journey-android/releases]
for mobile UI visuals. All screenshots usable under the MIT
license; please preserve any visible attribution lines.)

## Links

| | |
|---|---|
| **Source code** | https://github.com/TaylorAmarelTech/gemma4_comp |
| **Android app** | https://github.com/TaylorAmarelTech/duecare-journey-android |
| **Latest APK** | https://github.com/TaylorAmarelTech/duecare-journey-android/releases |
| **Live demo (Kaggle)** | https://www.kaggle.com/code/taylorsamarel/duecare-live-demo |
| **Chat playground** | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools |
| **Hackathon submission** | https://www.kaggle.com/competitions/gemma-4-good-hackathon |
| **Press inquiries** | amarel.taylor.s [at] gmail.com (subject: `[duecare press]`) |

## Suggested story angles

These are the angles journalists tend to find most compelling, with
the data point that supports each:

### "How AI can serve migrant workers without surveilling them"

The privacy-first design is the angle. Key data points:
- Zero outbound network traffic by default after install
- All processing on-device or on the NGO's local hardware
- Panic-wipe primitive (one-tap erase)
- Audit log records hashes, never plaintext
- Open source so any privacy claim can be audited

### "Big Tech AI safety vs grassroots AI safety"

The contrast with Azure / OpenAI / Hive moderation. Key data points:
- $0 vs $10k-100k/year commercial alternatives
- On-device vs cloud
- Domain-specific (trafficking + migrant labour) vs generic
- See [`docs/comparison_to_alternatives.md`](./comparison_to_alternatives.md)

### "Quantifying Gemma 4's jurisdiction-specific reasoning gap"

The harness-lift research angle. Key data points:
- 207 hand-graded prompts
- Stock Gemma: 0.4% pass rate on jurisdiction-specific citations
- With harness: 87.8% pass rate (+87.5 pp)
- Methodology: hand-graded 5-point rubric, blinded evaluation
- See [`docs/harness_lift_report.md`](./harness_lift_report.md)

### "Zero-budget tools for under-resourced NGOs"

The NGO-office walkthrough angle. Key data points:
- $250-800 one-time hardware (Mac mini)
- $0 ongoing
- 90-min setup
- 30 min/week of an IT-comfortable colleague
- See [`docs/scenarios/ngo-office-deployment.md`](./scenarios/ngo-office-deployment.md)

### "What an AI safety harness for trafficking actually looks like"

The technical-depth angle. Key data points:
- 11 ILO C029 forced-labour indicators encoded
- 12 migration corridors with statute lookups
- 42 GREP rules for pattern detection
- 26-doc legal RAG corpus (ILO conventions, POEA MCs, etc.)
- 6+5 published Kaggle notebooks for reproducibility

### "Open-source labor protection for the global south"

The geopolitical angle. Key data points:
- Corridors covered: Philippines/Indonesia/Nepal/Bangladesh/Mexico/
  Venezuela/Ghana/Nigeria/Syria/Ukraine to Hong Kong/Saudi/UAE/
  Singapore/US/Lebanon/Germany/Poland
- No vendor lock-in to a single Big Tech provider
- MIT license — adoptable by ministries that prohibit foreign-vendor
  cloud SaaS

## What NOT to claim

Honest framing for reporters:

- ❌ "Duecare prevents trafficking." It surfaces the legal landscape
  faster; trafficking prevention requires NGOs, lawyers, regulators,
  and policy.
- ❌ "Duecare detects trafficking with high accuracy." It detects
  exploitation patterns associated with trafficking; conversion to
  a confirmed case requires investigation.
- ❌ "Duecare replaces lawyers." It accelerates legal-research lookup
  and drafts; lawyers remain in the loop for actionable advice.
- ❌ "Duecare is government-endorsed." It's an open-source project;
  some regulators have evaluated it, none formally endorse.
- ❌ "Duecare is HIPAA / SOC 2 / GDPR certified." The deployment
  *can support* such certifications — see `docs/considerations/COMPLIANCE.md` —
  but the project itself isn't certified.
- ❌ Specific worker testimonials. Until reference customers make
  themselves available, treat user voice as composite (the writeup
  uses "Maria" as a labeled composite character).

## How to verify any claim in the writeup

Every published metric is anchored to `(git_sha, dataset_version,
model_revision)` per [RESULTS.md](../RESULTS.md). To independently
reproduce:

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp
git checkout <sha>                              # the cited commit
ollama pull gemma4:e2b
make demo
python scripts/run_local_gemma.py --graded-only --output reproduce.jsonl
python scripts/compare_to_published.py reproduce.jsonl docs/harness_lift_report.md
```

The reproduction tolerates ±2% per category for model
nondeterminism.

## Press contact

amarel.taylor.s [at] gmail.com
Subject line: `[duecare press]`
Expected response: 72 hours.
