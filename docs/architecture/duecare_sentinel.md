# Public Information Research Monitor — continuous-update agent + server

**Status: Proposal-intake endpoint live at [duecare-ai.com](https://duecare-ai.com); autonomous crawler is roadmap.**

The proposal-ingestion shape lives in this repo at
[`apps/duecare-ai.com/`](../../apps/duecare-ai.com/) and exposes
`POST /api/hub/opencrawl/updates` for public-source crawler-style
proposals. The autonomous crawler that *fills* that
endpoint with continuously-discovered candidates is post-hackathon.

A continuously-updating safety-intelligence server that tracks laws,
regulations, public reports, NGO guidance, platform abuse patterns,
and partner feedback, then **proposes** vetted updates to Duecare's
rules, RAG corpus, rubrics, contacts, and evaluation sets.

## Why the human-in-the-loop is mandatory

The research monitor must **never** silently mutate production safety behavior.
A wrong rule that auto-deploys could:

- Misclassify legitimate recruitment posts (false positives)
- Fail to flag new scam patterns (false negatives — the more
  dangerous case)
- Surface a stale or wrong contact, sending workers to a number
  that's been disconnected
- Inject hallucinated legal claims into the RAG corpus
- Skew rubric scoring in ways that mask quality regressions

The flow is:

```text
crawler / agent finds update
        ↓
proposal object
        ↓
automated validation
        ↓
human curator review
        ↓
evaluation regression suite (Duecare Quality Testing Framework)
        ↓
vetted pack release (Duecare Exchange)
        ↓
clients pull update
```

Even with the agent fully built, the **release** step is humans. Only.

## Agent functions

| Function | Description |
|---|---|
| Law / regulation tracker | Watches labor laws, migration rules, anti-trafficking policy |
| NGO / stakeholder tracker | Watches public NGO reports, advisories, campaigns |
| Contact verifier | Flags stale phone / email / form URLs |
| RAG proposer | Converts public sources into candidate RAG docs |
| GREP proposer | Suggests new detection phrases from public / partner signals |
| Rubric proposer | Suggests new evaluation dimensions or indicators |
| Research-pack builder | Produces benchmark / evaluation updates |
| Release manager | Builds vetted versioned packs after approval |

## Tiered access (matches Exchange)

| Actor | Submit | Approve | Publish |
|---|---:|---:|---:|
| Individual migrant worker | optional anonymized feedback | no | no |
| NGO partner | yes | maybe (own jurisdiction) | no / global limited |
| Government / regulator | yes | maybe (official contacts/laws) | no / global limited |
| Researcher | yes | benchmark / RAG proposals | no / global limited |
| Maintainer | yes | yes | yes |

## Today's bridge

Until the research monitor ships, contact freshness is checked by
`scripts/v141_validate_contacts.py` — a read-only HEAD-request
validator that pings `web_url` and `web_form_url` for every entry
in `_contacts.json` and flags non-2xx responses. It does **not**
email anyone or call any phone numbers; humans verify those.

## What the research monitor does NOT do

- **No auto-publishing.** A finding becomes a proposal becomes a PR
        becomes a human review becomes an evaluation gate becomes a vetted pack.
        The monitor is not allowed to skip steps.
- **No raw case ingestion.** The monitor pulls from public sources
  (regulator websites, NGO reports, news). Worker chats and case
  data stay local — that's Exchange's domain with explicit consent.
- **No outbound calls / emails on a user's behalf.** Same boundary
  as the Mobile checker: we draft, the user submits.
