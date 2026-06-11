# Path 4 — Platform specialist-tier integration

For a platform whose Trust & Safety stack already operates at scale
(Meta, ByteDance, Reddit, Discord, Snap, Pinterest, Telegram, X,
TikTok, classifieds boards like Craigslist / OLX / Marktplaats /
LeBonCoin). You have a primary trafficking-detection classifier
running at billions of inferences per day. You need a specialist
secondary review that:

- Catches what the primary classifier misses on niche corridors
  (Tagalog domestic-worker recruitment in PH-Saudi, Bengali
  construction recruitment to Malaysia, Vietnamese compound-scam
  recruitment in Cambodia)
- Returns auditable, statute-cited reasoning that your policy team
  can defend to regulators and the press
- Runs at a per-call cost that is feasible for the volume of
  primary-classifier escalations (not for the full firehose)

This is the **specialist tier** in a two-tier waterfall. You keep
your primary classifier; DueCare sits behind it for the cases your
primary cannot decide.

## The waterfall

```
┌────────────────────────────────────────────────────────────────┐
│ All user-generated content (billions/day across the platform)  │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ TIER 1 — your primary classifier (Llama / Sapphire / Hive /    │
│   internal model). Fast. Cheap. High recall.                   │
│                                                                │
│   Outcome:                                                     │
│   - clearly OK         → pass through                          │
│   - clearly violating  → auto-action (remove / shadowban)      │
│   - suspicious         → ESCALATE to specialist tier           │
└────────────────────────────────────────────────────────────────┘
                            ↓ (escalations only — usually <1% of firehose)
┌────────────────────────────────────────────────────────────────┐
│ TIER 2 — DueCare specialist (Gemma 4 E4B + knowledge layer).   │
│ Specialised. Auditable. ~$0.005 per inference on T4-class GPU. │
│                                                                │
│   Outcome:                                                     │
│   - indicators present + grounded in statute → suggested       │
│       enforcement action with citation                         │
│   - ambiguous, no indicators                  → enrichment     │
│       metadata only (no enforcement)                           │
│   - request is jailbreak / prompt-attack       → flagged,      │
│       returned to Tier 1 with a "do not auto-classify" tag     │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Your moderation queue / policy team                            │
│ - sees DueCare specialist verdict + citation matrix             │
│ - decides final enforcement action                              │
│ - decision logged in your existing audit infra                  │
└────────────────────────────────────────────────────────────────┘
```

## Request / response shape

Specialist tier integration is a single internal endpoint. Your
primary classifier (or routing layer) calls it with the content +
the primary's signal.

```http
POST /api/specialist/triage HTTP/1.1
Content-Type: application/json
Authorization: Bearer <platform-internal-token>

{
  "content_id": "post-abc123",
  "content_text": "...verbatim post / ad / message...",
  "content_locale": "tl",
  "primary_classifier_signal": {
    "category": "labour_recruitment",
    "score": 0.62,
    "categories_above_threshold": ["labour_recruitment", "fee_solicitation"]
  },
  "content_metadata": {
    "posted_at": "2026-05-22T09:14:00Z",
    "platform_surface": "marketplace",
    "post_type": "job_ad",
    "country": "PH"
  }
}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "content_id": "post-abc123",
  "specialist_verdict": "indicators_present",
  "model_version": "gemma-4-e4b@0.1.0-duecare",
  "knowledge_pack_version": "2026-05-22-platform-tier",
  "indicators": [
    {
      "id": "fee_camouflage_training_advance",
      "severity": "high",
      "evidence_excerpt": "PHP 50,000 training fee deducted from Saudi salary over 6 months",
      "citation": "POEA MC 14-2017 Sec. 3(a); ILO C181 Art. 7",
      "verbatim_statute_text": "..."
    }
  ],
  "suggested_action": "remove_and_warn_poster",
  "policy_rationale": "Job ad on platform surface=marketplace from PH to Saudi domestic-worker corridor. Includes worker-paid fee for training in violation of POEA MC 14-2017 Sec. 3(a) which requires employer-paid training fees. ILO C181 Art. 7 forbids worker-charged recruitment fees.",
  "confidence": 0.91,
  "latency_ms": 387
}
```

## Why Gemma 4 E4B specifically

The specialist tier's value depends on three things being
simultaneously true. Gemma 4 E4B is uniquely positioned because:

1. **Small enough to self-host at platform scale.** ~4B effective
   parameters. Runs on a T4 / L4 GPU. A platform receiving 10M
   primary escalations/day at 1% to specialist tier = 100K
   specialist calls/day. One node handles that. Cost is a single-
   digit-thousands of dollars per month, not the millions you'd
   need for frontier-API inference.

2. **Good enough on niche corridors.** Gemma 4 is multilingual at
   the language level (Tagalog, Bahasa, Vietnamese, Bengali, etc.)
   AND on the safety-rubric level once fine-tuned with the DueCare
   training set. Frontier-API models cover the languages but not
   the specialised migrant-labour rubric.

3. **Open enough to deploy.** Gemma 4 license permits commercial
   self-host. The DueCare LoRA weights are open. You can deploy
   on your infrastructure, run on your security perimeter, and
   audit the model + knowledge pack however your compliance team
   requires.

## Knowledge layer (what the specialist tier knows)

The DueCare knowledge layer that ships with the specialist tier:

- 439 GREP detection rules organised across 31 categories
  (recruitment-fee camouflage, debt bondage, document retention,
  contract substitution, kafala, threats, supply-chain, gig-platform,
  seasonal-visa, refugee, AI-deepfake, child-trafficking, organ-
  trafficking, sham-marriage, sham-asylum, port + offshore, etc.)
- 859 RAG documents covering ILO conventions (15), Palermo
  Protocol, regional treaties (EU 2011/36, ASEAN ACTIP, SAARC, Bali
  Process), 26 destination + origin-country statutes, 15 public-
  record case studies, 6 landmark court cases (ECtHR Siliadin /
  Rantsev / J. and Others / S.M., US Kil Soo Lee, ECOWAS
  Hadijatou Mani), national LE units, UN Special Rapporteur
  mandates, GRETA + IASC oversight bodies, research institutes
  (MPI, Amnesty, BHRRC, ECPAT, HRW)
- 36 complaint and narrative templates
- 37 audience-aware personas (worker, NGO, regulator, clinician,
  survivor advocate, FIU officer, engineer, etc.)
- 38 corridor fee-cap entries
- 36 NGO contact bundles
- Versioned and verifiable via `verify_knowledge_surfaces.py`

Every specialist-tier output cites the knowledge object behind each
indicator. Your policy team can audit "why did the model flag this"
without consulting the model itself.

## What you provide

| Resource | Pilot | Production |
|----------|-------|------------|
| GPU compute | 1 T4/L4-class for pilot | Scale per primary-escalation volume |
| Network | Internal-only ingress from your primary classifier | Same |
| Integration engineer | 1 engineer, part time, 4 to 6 weeks for pilot | Same person can maintain steady state |
| Policy reviewer | 1 person on your policy team to validate specialist outputs | Same person; quarterly review |
| Language support | List of corridors / locales your platform wants prioritised | Same |
| Pilot corridor | 1 high-leverage corridor to start (e.g., Tagalog PH→Saudi, Bengali BD→MY) | Add more after pilot success |

## Pilot scope (30 to 60 days)

**Week 1:** Spin up specialist tier on a sandbox GPU node; bind to
your primary-classifier integration endpoint as a stub; verify the
request/response round trip works.

**Week 2:** Replay 1,000 historical primary-classifier escalations
in the pilot corridor through the specialist tier (read-only —
specialist verdicts are NOT applied to live content). Your policy
team compares specialist verdicts against the actions that were
taken historically.

**Week 3 to 4:** Tune the specialist tier's response format and
confidence thresholds for your team's workflow. Adjust which
indicators surface as "remove and warn" vs "enrichment only."

**Week 5 to 8:** Shadow mode in production. Specialist tier
receives live escalations but its verdicts are advisory only. Your
moderators see them as suggestions in the queue; final action is
human. Measure: agreement rate with moderator action, time-to-
decision, false-positive rate.

**End of week 8:** Decision gate. If shadow-mode performance meets
your thresholds, promote to limited production. If not, iterate the
knowledge layer with your specific corridor's gaps.

## Steady-state operations

After pilot, the specialist tier becomes a part of your standard
moderation infra. Operational concerns:

| Concern | How handled |
|---------|-------------|
| **Knowledge layer updates** | DueCare ships quarterly knowledge pack updates. Your platform reviews each update before promoting to production. Updates are versioned and reversible. |
| **Model updates** | DueCare ships model updates (re-trained on expanded data) less frequently — 6 to 12 month cycle. Each release is a new LoRA you can test side-by-side. |
| **Latency** | p50 ~400 ms, p95 ~1 s on T4-class. If your primary expects synchronous specialist responses, budget for this. Async integration is usually better. |
| **Cost** | At 100K specialist calls/day, a single T4 node sustains the load. Add nodes for redundancy + spike capacity. |
| **Audit** | Every specialist verdict logged with content hash, indicator citations, knowledge pack version, model version. Your policy team can replay any verdict at any time. |
| **PII** | Specialist tier doesn't persist content. It produces verdicts + indicator references, not stored content. Your existing content-handling policies apply unchanged. |

## What kinds of content the specialist tier handles well

Areas where the specialist tier outperforms general primary
classifiers:

- **Niche-corridor recruitment ads.** PH→Saudi domestic worker
  pretexts; BD→MY construction; VN→Compound-scam; NP→Gulf
  construction; ID→Taiwan factory; LK→Kuwait domestic.
- **Substance-over-form schemes.** "Assignment to collection
  agent", "novated loan", "payment plan" framings that disguise
  illegal recruitment fees.
- **Fee-camouflage labels.** Training, medical, processing,
  uniform, repatriation deposit, deployment fee — 45 distinct
  fee-camouflage labels recognised.
- **ILO indicator language.** Substance-of-debt-bondage, freedom-
  of-movement restriction, document retention, isolation, threats.
- **Trafficking pretexts.** Sham marriage, sham religious worker
  (R-1), au pair / J-1 abuse, sham asylum brokering, diplomatic
  household worker (A-3/G-5), compound-scam recruitment, organ
  trafficking pretexts.
- **Worker first-person posts.** A worker asking "is this fair?"
  about their own situation — the specialist tier recognises the
  worker-as-victim framing and avoids the over-refusal that
  victim-blames the worker.

## What kinds of content the specialist tier does NOT handle well

Known limitations to communicate clearly to your moderation team:

- **CSAM detection.** Use your existing CSAM-specific classifier.
- **Generic spam / scam unrelated to recruitment.** Use your
  existing spam classifier.
- **Adult content moderation.** The specialist tier surfaces sex-
  trafficking signals, NOT adult-content policy enforcement. Those
  are different problems.
- **Real-time abuse in DMs at full firehose scale.** The specialist
  tier is too expensive to run on the full DM stream; it should
  only receive escalations.
- **Languages outside Gemma 4's coverage.** Roughly 25 languages
  are well-supported. Outside that set, the specialist tier degrades
  to English-translation-then-analyse, which loses fidelity. If
  your platform has critical languages outside that set, raise it
  in the pilot scoping.

## Procurement bullets

- **Model license:** Gemma 4 license; commercial self-host
  permitted.
- **DueCare license:** MIT for the harness + knowledge layer.
- **Deployment model:** Self-hosted on platform infrastructure.
  No SaaS, no third-party API for the specialist tier.
- **Cost:** Hardware + ops. No per-call licensing fees.
- **Data handling:** Platform's existing data-handling policies
  apply unchanged. Specialist tier does not persist content.
- **Vendor risk:** Open-source codebase + open knowledge layer +
  open model. If the DueCare team disappears tomorrow, platform
  can continue running indefinitely and fork the codebase.
- **Source:** `github.com/TaylorAmarelTech/gemma4_comp`. Platform
  self-hosts a private fork.
- **Support:** Open-source community + paid commercial support
  available if needed.

## Joint governance

Recommended structure for the platform / DueCare relationship in
steady state:

| Body | Cadence | Purpose |
|------|---------|---------|
| Joint Review Board | Quarterly | Knowledge layer updates: what's new this quarter; review proposed changes; sign off on production promotion |
| Incident Review | As-needed | If a moderation action based on specialist verdict is challenged externally, joint review of the rationale + fix |
| Annual Audit | Yearly | Third-party audit of specialist tier performance + safety + bias |
| Public Transparency Report | Yearly | Platform's annual transparency report includes specialist-tier statistics where appropriate |

## What can go wrong + how to handle it

| Failure | Mitigation |
|---------|------------|
| Specialist tier hallucinates a statute citation | Citation matrix is bundled, not generated. Every citation surfaces with its bundled verbatim text. Moderator sees both, can verify in one click |
| Knowledge layer update breaks an existing policy decision | Platform replays the previous version's verdicts on a regression set before promoting an update to production |
| Latency spike from a knowledge-layer update | Performance regression suite runs before each update; updates that exceed latency budget are held |
| Adversary discovers a prompt-attack pattern that fools the specialist tier | Specialist tier returns `prompt_attack_resilience` indicator when triggered; primary classifier sees this and routes to human review |
| Specialist tier and primary classifier disagree systematically | Joint Review Board reviews; root cause analysis; either retune the primary or update the specialist's knowledge layer |
| Government issues a takedown request the specialist tier would not have suggested | Standard transparency-reporting process; specialist verdict is one input among many to the platform's decision |

## See also

- [`04_platform_cto_pitch.md`](04_platform_cto_pitch.md) — pitch
  outline for the initial CTO conversation
- [`04_platform_pilot_demo.md`](04_platform_pilot_demo.md) — the
  30 to 60 second demo specification that goes with the pitch
- [`03_government_api_integration.md`](03_government_api_integration.md) —
  the government-side cousin of this integration; similar shape,
  different mission
- `packages/duecare-llm-server/` — the FastAPI service that backs
  this integration
