# Path 2 — Curator role

Detailed responsibilities, weekly rhythm, and escalation paths for
the knowledge-hub curator(s). Read this if you are taking on the
curator role for an NGO network deploying path 2, or designing the
curator function for a new network.

## What a curator is

A curator is a peer reviewer who decides what enters the shared
`duecare-knowledge-pack-<region>` from member NGO submissions.
They are the substantive-quality filter. The anonymisation gate is
the PII filter (automated); the curator is the rest.

A curator is **not**:
- A security gatekeeper. Members are trusted within the network.
- A research authority. Their job is to apply consistent review
  criteria, not to make new legal-research claims.
- A software developer. They use the workbench's curator dashboard;
  no code changes required.

## Weekly rhythm

A typical week for a curator running a 60-member network:

| Day | Activity | Time |
|-----|----------|------|
| Mon | Review weekend submissions; flag any anonymisation re-checks needed | 1 hr |
| Tue | Approve clear-pass envelopes; ping submitters of envelopes needing revision | 1 hr |
| Wed | Citation-accuracy spot-check on 20% of week's GREP / RAG envelopes | 1 hr |
| Thu | Network sync call (optional) with peer curators; resolve flagged conflicts | 0.5 hr |
| Fri | Cut weekly pack version `<YYYY.MM.DD>`; publish release notes | 1 hr |
| As-needed | Hotfix corrections for accuracy issues that ship before Friday | variable |

Total: 4 to 6 hours per week. Scales sub-linearly with network size
— a 200-member network with healthy contributor distribution does
not need 4× the curator time, more like 2 to 3×.

## The review pipeline

```
submitter → workbench "Contribute to hub" button
   │
   ↓
[anonymisation gate]   ← automatic; fails closed
   │
   ↓ (passes)
[envelope queued in review queue]   ← Notion / GitHub Issues
   │
   ↓
[curator triage]   ← coarse: in-scope / out-of-scope / hold-for-discussion
   │
   ├──→ rejected   (with reason; submitter can revise + resubmit)
   ├──→ approved-pending-peer-review   (substantive: 2nd curator looks at it)
   ├──→ approved   (cleared for next pack version)
   ↓
[Friday cut]   ← curator merges approved envelopes; bumps pack version
   │
   ↓
[publish to hub]   ← Kaggle Dataset / git push
   │
   ↓
[members sync]   ← duecare knowledge sync on each member's workbench
```

## What the curator checks (in order)

### 1. PII re-verification (30 seconds per envelope)

The submitter's anonymisation gate already ran. The curator
re-runs it as a paranoid second pass, especially on `rationale` and
`summary` fields, which the gate sometimes misses (caseworker
narration tends to slip in worker initials, employer names,
specific addresses).

```bash
duecare anonymise envelope --check envelope-id-9f8c4d2
```

If anything trips: REJECT with reason "PII detected in {field}";
ask submitter to resubmit a sanitised version.

### 2. Citation accuracy (variable, 1 to 5 minutes per envelope)

For `grep_rule`, `rag_doc`, `template`, `ilo_convention` envelopes:
verify the cited statutes / conventions / case-law actually exist
and say what the envelope claims they say.

The minimum standard:
- A statute named in `citation` must exist and be current. Look it
  up in the official register (POEA Memorandum Circulars site,
  national legal database, ILO NORMLEX for conventions).
- An ILO convention reference must include the convention number
  AND the specific article(s) AND a substantive quote or
  paraphrase the curator can verify.
- A case-law reference must include the case name, year, court,
  AND the substantive holding.

If anything fails: HOLD-FOR-DISCUSSION; ask submitter for the
source URL. Do not silently drop the envelope.

### 3. Substance-over-form check (1 to 3 minutes per envelope)

For `grep_rule` envelopes specifically: does the rule actually
detect the pattern in plausible test text? The curator runs the
regex against:

- The submitter's `rationale` text
- A short composite synthetic example the submitter should provide
- One or two cases from the workbench's bundled adversarial corpus
  (sanitised; not real cases)

If it does not fire on the synthetic example: REJECT; ask
submitter to fix the pattern.

### 4. Region-relevance tags (30 seconds per envelope)

A PH-HK pattern should not be tagged `["global"]` unless it
plausibly generalises. A `["EU"]` tag should not appear on a
US-specific TVPRA section.

If tags look wrong: APPROVED-WITH-CORRECTION (curator fixes tags
in-place, notes the correction in the merge log).

### 5. Duplicate check (1 to 2 minutes per envelope)

Has an existing pack rule already covered this case? The workbench's
`duecare knowledge search "<keywords>"` command surfaces near-
duplicates by ID, title, and pattern.

If a near-duplicate exists: HOLD; propose a `correction` envelope
instead, or merge the two into a stronger combined rule.

## When two curators disagree

- For substantive disagreements (does this pattern really
  generalise? is this corridor cap stale?), escalate to a peer-
  consensus discussion in the network's review queue. Two of
  three curators vote.
- For procedural disagreements (which pack version should this go
  in?), the lead coordinator decides.
- For legal-accuracy disagreements (does this statute say what we
  claim?), pause and consult external counsel or a member NGO with
  jurisdiction expertise. Do not merge until resolved.

## Escalation paths

| Situation | Escalation |
|-----------|------------|
| Submitter repeatedly submits PII-leaking envelopes | Coordinator contacts submitter's NGO leadership; provide refresher training; do not merge until pattern stops |
| Pattern is so corridor-specific it should not be in the regional pack | Move to a smaller pack (e.g., `duecare-knowledge-pack-ph-hk` instead of `-asia-pacific`); the network may want to support sub-packs |
| Pattern surfaces an active criminal-investigation lead | DO NOT publish to the open pack. Use point-to-point sharing between the relevant NGOs and law enforcement. Pack is for systemic patterns, not operational intelligence |
| Hub host (Kaggle / git repo) is compromised | Coordinator rotates credentials; members re-sync from backup mirror; review audit log of recent pushes for malicious envelopes |
| Curator becomes unavailable | Coordinator promotes a designated backup curator; network is notified; review queue does not stall |

## Release-notes template (Friday cut)

Every weekly cut publishes a short release-notes file:

```markdown
# duecare-knowledge-pack-gaatw 2026.05.22

## Added (this week)
- 4 GREP rules covering Cambodia-Thailand fishing-vessel recruitment
  (sourced from Damayan + ATLEU pooled cases)
- 2 RAG documents on Vietnam Decree 38/2020/ND-CP enforcement
  pattern shifts
- 1 corridor fee cap update: PH-Saudi Arabia (new POEA cap
  effective 2026-05-15)
- 1 template: NGO survivor narrative — corridor-agnostic version

## Changed
- Corrected ILO C181 Art. 7 quote in `b_fee_camouflage_*` rules
  (was paraphrase; now verbatim)
- Updated NGO contact: HOME Singapore phone number changed

## Removed
- (none)

## Pending review
- 3 envelopes held for citation verification

Synced by: duecare knowledge sync --pack duecare-knowledge-pack-gaatw
```

## What success looks like

- Members report that the weekly pack updates land at least one
  useful pattern per week
- Curator queue stays at fewer than 10 pending envelopes most weeks
- Zero PII incidents detected in production envelopes over 12 months
- New member NGOs onboard in under 1 day (install workbench, sync
  pack, run first case)
- Member NGO survey: 80%+ "the hub makes our work better"

## What failure looks like

- Curator queue grows beyond 30 pending envelopes for more than 2
  weeks
- A PII incident reaches the published pack (forces a corrections
  release + post-mortem)
- Members stop submitting because the curation feels arbitrary
- Citation-accuracy errors compound: members trust hub data, member
  NGOs file complaints on bad citations, regulator rejects complaints

The mitigation for all of these is the same: more curator
bandwidth, clearer review criteria, peer-review backstop.

## See also

- [`02_network_hub_bootstrap.md`](02_network_hub_bootstrap.md) —
  hub setup, envelope schema, sync mechanics
- [`01_ngo_caseworker_quickstart.md`](01_ngo_caseworker_quickstart.md) —
  what each contributor's workflow looks like before the envelope
  reaches you
- `.claude/rules/10_safety_gate.md` — full PII rules the curator
  enforces
