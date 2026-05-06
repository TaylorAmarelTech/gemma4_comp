# Investigative journalist — using Duecare for trafficking + recruitment-fraud reporting

> **Persona.** You're an investigative reporter / freelance journalist
> covering migrant labor, trafficking, recruitment fraud, or refugee
> exploitation. You have a tip, a leaked document, a worker who'll
> talk on background, or a publicly-scraped dataset of suspicious
> job ads. You need to verify patterns + understand the legal
> landscape + protect your sources.
>
> **What this gives you.** A privacy-first analysis tool that runs
> on your laptop, doesn't require an account, doesn't log queries
> to anyone's cloud, and cites the actual statute behind every
> claim it makes. Works offline after install.
>
> **What it is NOT.** It's not a fact-checker (you still verify).
> It's not a source-protection tool (use Tor + SecureDrop + Signal
> for that). It's not a court-admissible evidence tool (chain of
> custody is your editor's lawyer's domain).

## TL;DR

| You're trying to... | Use Duecare to... |
|---|---|
| Verify whether a recruitment fee in a leaked contract is illegal | Paste the contract clause into the chat surface; get the controlling statute citation in 5s |
| Pattern-match 10,000 scraped Facebook job ads for trafficking signals | Run the GREP layer over the dataset; get back per-ad rule firings (10k posts/sec on CPU) |
| Understand the kafala system without a 2-week reading list | Ask the chat surface; get plain-language explanations citing ILO C189 + Saudi MoHR + Lebanon General Security |
| Map fee-camouflage patterns across an investigation | The Reports tab structures fee data with legality flags + corridor-specific cost rollups |
| Build a publishable methodology section | Reproducibility provenance via `(git_sha, dataset_version, model_revision)` + the 207-prompt rubric in `docs/harness_lift_report.md` |
| Get the right NGO contact for a story's quote / source | Bundled directory: 3-4 vetted NGOs per corridor, with phones + URLs |

## Source protection — read this first

Duecare doesn't compromise your sources by itself. But the workflow
matters:

- **Don't type your source's name into the chat.** Use composite
  labels ("Source A", "the worker from Lebanon"). Even though
  the chat surface is local-only by default, screen recordings,
  shoulder-surfing, and your laptop's filesystem cache are real
  attack surfaces.
- **Don't email an unredacted Duecare report to your editor.**
  Generate the markdown report → redact identifying details →
  hand off via Signal or your newsroom's encrypted-document
  workflow.
- **Don't enable cloud routing if your source could be retaliated
  against.** Settings → Cloud model in the Android app, or
  `OLLAMA_HOST` env var on the server. Both are off by default.
  Leave them off.
- **Don't run on your work laptop.** Use a dedicated burner
  laptop or an air-gapped VM if your investigation involves
  state-actor adversaries. The standard threat model in
  [`docs/considerations/THREAT_MODEL.md`](../considerations/THREAT_MODEL.md)
  doesn't cover state-actor compromises of your hardware.
- **Don't share queries with the maintainer.** The maintainer
  can't see your queries (no Duecare cloud service) but if you
  email them a transcript for support, they can — so don't.

For higher-grade source protection: SecureDrop, Tails, GrapheneOS,
Signal disappearing messages, hardware-encrypted USB drives,
Faraday bags. Duecare composes with all of these — it's one
analytical tool, not a complete OPSEC stack.

## Workflow 1 — Verify a single document

You have a leaked recruitment contract. You want to know which
clauses are unlawful.

```bash
# Pull up the chat playground (Kaggle is fine for this — no PII)
# https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools

# Or locally:
make demo
open http://localhost:8080
```

In the chat, paste the clause:

> "Section 12: The Worker shall reside at the Employer's residence
> and shall not leave the premises without express permission of
> the Employer. The Worker's passport shall be held by the Employer
> for safekeeping during the term of this Agreement."

The chat returns:
- ILO C029 indicator #5 (restriction of movement) + #8 (passport
  withholding) fired
- Cites ILO C189 Article 9 + Saudi MoHR Domestic Worker Regulation
  Art. 6 + HK Foreign Domestic Helper Code of Practice
- Notes that even with worker consent the clause is unenforceable
  per Palermo Protocol Art. 3(b)

Verify each citation against the original source (linked in the
RAG corpus) before you publish. The harness is fast research, not
authoritative.

## Workflow 2 — Pattern-match a scraped dataset

You scraped 10,000 job ads from Facebook recruitment groups in
the PH-HK corridor. You want to flag the ones with trafficking
indicators.

```python
import json
from duecare.chat.harness import apply_grep_rules

with open("scraped_ads.jsonl") as f:
    ads = [json.loads(line) for line in f]

flagged = []
for ad in ads:
    hits = apply_grep_rules(ad["body"])
    if hits:
        flagged.append({
            "ad_id": ad["id"],
            "url": ad["url"],
            "rules_fired": [h["rule"] for h in hits],
            "highest_severity": max(
                (h["severity"] for h in hits), default="low"
            ),
        })

# Triage: critical first
critical = [a for a in flagged if a["highest_severity"] == "critical"]
print(f"{len(critical)} of {len(ads)} ads triggered critical patterns.")

with open("flagged_ads.jsonl", "w") as f:
    for a in flagged:
        f.write(json.dumps(a) + "\n")
```

That's a defensible methodology section: deterministic GREP rules,
fully audited, runs in seconds on a laptop. Cite the rule pack +
its commit SHA in your story's methodology footnote.

For a deeper analysis with Gemma 4 reasoning per ad, see
[`docs/scenarios/researcher-analysis.md`](./researcher-analysis.md)
Workflow 2.

## Workflow 3 — Build the legal-landscape sidebar

Stories about trafficking + recruitment fraud need a sidebar
explaining the legal framework. Use the chat surface to draft:

> "Explain the kafala system in 200 words for a general-audience
> news article. Cite the specific Saudi and Lebanese statutes."

> "What's POEA Memorandum Circular 14-2017 and why does it matter
> for Filipino domestic workers in Hong Kong?"

> "What's the difference between an H-2A and H-2B visa for Mexican
> agricultural workers in the US?"

The harness returns plain-language explanations + statute
citations. Edit, fact-check, then publish.

The bundled corpus covers 20 corridors as of v0.9 — see
[`docs/gemma4_model_guide.md`](../gemma4_model_guide.md) for the
list. For corridors not covered, the harness honestly says
"consult local counsel" rather than fabricating.

## Workflow 4 — Get the right NGO source

For each corridor, the bundled directory has 2-3 vetted NGOs (with
phones + URLs):

> "I'm reporting on Ethiopian domestic workers in Lebanon. Which
> NGOs would speak on the record?"

The chat returns the NGO contacts for ET-LB:
- Anti-Racism Movement (ARM Beirut) — Migrant Domestic Workers
  Center + crisis hotline
- KAFA (Enough Violence and Exploitation)
- Good Shepherd Sisters — Ethiopia office

Each entry has a phone or URL. Reach out via your normal sourcing
process. Disclose Duecare's role in surfacing the contact if your
publication's standards require it.

## Citing Duecare in your story

If Duecare's harness analysis is load-bearing in your story:

> "Patterns in the leaked contracts were identified using Duecare,
> an open-source content-safety harness around Google's Gemma 4
> model. The analysis ran on the reporter's laptop without sending
> queries to any cloud service. Each pattern citation was verified
> against the source statute."

If you used the published rubric numbers:

> "Independent reproducibility analysis published by Duecare's
> harness-lift report (207 hand-graded prompts, +56.5 percentage
> points mean improvement) shows that off-the-shelf large language
> models miss jurisdiction-specific recruitment-fee regulations 99.6%
> of the time without an external research layer."

Bibtex for academic-style references: see
[`docs/scenarios/researcher-analysis.md`](./researcher-analysis.md)
"Citation".

## What NOT to claim about Duecare in your story

- ❌ "AI catches trafficking." — It catches patterns associated
  with trafficking; conversion to confirmed cases requires
  investigation by you, the lawyer, the regulator.
- ❌ "Open-source AI replaces vetted journalism." — It accelerates
  research; your editorial judgment remains primary.
- ❌ "Privacy-first AI from a Big Tech alternative." — Duecare is
  built on Google's Gemma 4 (which is open-weights Apache 2.0 but
  trained by Google). The harness is independent; the model is
  Google's.
- ❌ "Government-endorsed." — It's an independent open-source
  project. Some regulators have evaluated it; none formally endorse.

## Story-pitch starters

If you're looking for an angle, here are five your editor will
react to:

1. **"How $0/year open-source AI is outperforming Big Tech moderation
   on trafficking-specific prompts"** — the +87.5 pp jurisdiction-
   specific lift is the headline number; the open-source-vs-Hive-
   Sift cost comparison is the body.
2. **"The recruitment-fee underground that an Android app exposes"**
   — pick one corridor (PH-HK, ID-HK, ET-LB) and walk through how
   the harness flags illegal fees that workers + caseworkers
   currently miss because lookup costs them 30 minutes per case.
3. **"Why migrant workers can't trust Big Tech with their data —
   and what's being built instead"** — the privacy-by-design angle.
   Panic-wipe primitive, on-device model, zero phone-home, audit
   log of hashes-not-plaintext.
4. **"How Indonesian domestic workers in Taiwan are bypassing
   recruiters via the Direct Hiring Service Center"** — the ID-TW
   corridor walkthrough surfaces an underused legal channel.
5. **"The kafala system, explained — by an AI that's read every
   ILO convention"** — accessible explainer using the chat surface
   to draft, your reporting to verify + add narrative.

## Press contact

If you're writing about Duecare itself: `amarel.taylor.s [at]
gmail.com`, subject `[duecare press]`. The press kit at
[`docs/press_kit.md`](../press_kit.md) has the one-paragraph
summary + key facts + quotes available for use.

If you're using Duecare as a tool for a different story: no
press contact needed. The MIT license permits commercial use
including journalism.

## Adjacent reads

- [`docs/scenarios/researcher-analysis.md`](./researcher-analysis.md) — academic / batch analysis workflow
- [`docs/scenarios/lawyer-evidence-prep.md`](./lawyer-evidence-prep.md) — what counsel does with the same intake
- [`docs/considerations/THREAT_MODEL.md`](../considerations/THREAT_MODEL.md) — threat model (read carefully if your investigation is high-risk)
- [`docs/press_kit.md`](../press_kit.md) — facts, quotes, story angles
