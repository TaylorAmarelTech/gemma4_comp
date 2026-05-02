# The Duecare ecosystem — one harness, four user layers

> **The 30-second pitch.** A single content-safety harness, layered
> around Google Gemma 4, deployable from a worker's phone to a
> Big Tech enterprise. The same code spots a recruitment fraud the
> day a worker pays the fee, drafts the refund-claim packet a
> lawyer files three months later, surfaces the pattern a regulator
> investigates a year later, and feeds the regional report an ILO
> office publishes the year after that.

## The 4-layer ecosystem

```mermaid
graph TB
    subgraph L1["LAYER 1 — Individual / OFW"]
        OFW["Migrant worker<br/>Android app on phone"]
        OFW2["Worker's family<br/>Web chat embed"]
    end

    subgraph L2["LAYER 2 — NGO / Legal / Caseworker"]
        NGO["NGO office<br/>Mac mini on the LAN"]
        LAWYER["Legal aid clinic<br/>Same Mac mini"]
        CASEWORKER["Caseworker<br/>Browser → Mac mini"]
    end

    subgraph L3["LAYER 3 — Researcher / Journalist / Compliance"]
        RESEARCH["Academic / NGO researcher<br/>pip install + laptop"]
        JOURNO["Investigative journalist<br/>Local CLI"]
        COMPLIANCE["Recruitment-agency<br/>compliance officer"]
    end

    subgraph L4["LAYER 4 — Regulator / Enterprise / Supra-national"]
        REGULATOR["Government regulator<br/>Cloud server + per-unit tenancy"]
        EMBASSY["Embassy / consulate<br/>On-prem server"]
        ENTERPRISE["Enterprise platform<br/>k8s + Helm + thin clients"]
        ILO["ILO / IOM / OHCHR<br/>Federated aggregator"]
    end

    OFW -.shares intake doc.-> NGO
    OFW -.shares intake doc.-> LAWYER
    NGO -.referrals.-> LAWYER
    NGO -.aggregate counts only.-> ILO
    CASEWORKER -.intake packet.-> NGO
    LAWYER -.refund claim.-> REGULATOR
    LAWYER -.case data.-> JOURNO
    REGULATOR -.investigations.-> EMBASSY
    REGULATOR -.aggregate.-> ILO
    EMBASSY -.repatriation.-> NGO
    RESEARCH -.published rubrics.-> COMPLIANCE
    COMPLIANCE -.self-audit findings.-> REGULATOR
    JOURNO -.published stories.-> REGULATOR
    ENTERPRISE -.classifier API.-> NGO

    style L1 fill:#e8f4f8,stroke:#1976d2
    style L2 fill:#fff3e0,stroke:#f57c00
    style L3 fill:#f3e5f5,stroke:#8e24aa
    style L4 fill:#e8f5e9,stroke:#43a047
```

The same harness logic runs at every layer. What changes is the
**deployment shape** (Topology A, B, C, D, or E from
[deployment_topologies.md](deployment_topologies.md)) and the
**workflow** (per-persona walkthrough in
[scenarios/](scenarios/README.md)).

## The same harness, served differently

```mermaid
graph LR
    GEMMA["Gemma 4<br/>(E2B / E4B / 31B)"]
    HARNESS["Duecare harness<br/>GREP + RAG + Tools + Persona"]
    GEMMA --> HARNESS

    HARNESS --> A["Topology A<br/>Single-component local<br/>(developers, researchers)"]
    HARNESS --> B["Topology B<br/>NGO-office edge<br/>(NGOs, legal aid, regulators)"]
    HARNESS --> C["Topology C<br/>Server + thin clients<br/>(enterprises, multi-region orgs)"]
    HARNESS --> D["Topology D<br/>On-device only<br/>(migrant workers via Android)"]
    HARNESS --> E["Topology E<br/>Hybrid edge LLM + cloud knowledge<br/>(field workers + central updates)"]

    style GEMMA fill:#fff9c4,stroke:#fbc02d
    style HARNESS fill:#bbdefb,stroke:#1976d2
```

A NGO can run Topology B for their office + recommend Topology D
to the workers they serve + contribute aggregate counts to a
Topology C federation aggregator — all using the same source code.

## The data flow — Maria's case

```mermaid
sequenceDiagram
    participant W as Maria<br/>(worker)
    participant CW as Caseworker
    participant NGO as NGO office<br/>Mac mini
    participant L as Lawyer
    participant R as Regulator<br/>(POEA / DMW)
    participant ILO as ILO Bangkok<br/>(aggregate)

    Note over W,CW: Pre-departure
    W->>+W: Installs APK<br/>v0.9 on her phone
    W->>W: Guided intake →<br/>10 questions answered
    W->>W: Reports tab shows<br/>passport-withholding +<br/>fee-camouflage flags

    Note over W,L: After return to PHL
    W->>CW: Walks into NGO office
    CW->>NGO: Pastes intake into chat
    NGO->>NGO: Generates intake document<br/>(markdown + statute citations)
    NGO->>L: Forwards intake doc

    Note over L,R: Refund claim
    L->>L: Edits drafted refund-claim<br/>cover letter
    L->>R: Files claim with POEA<br/>(citing MC 14-2017 §3)
    R->>R: Investigates the recruiter

    Note over R,ILO: Pattern emerges
    R->>R: Logs to per-tenant audit log<br/>(via duecare-llm-server middleware)
    R-->>ILO: Weekly aggregate counts<br/>(noised, signed, no PII)
    ILO->>ILO: Cross-corridor rollup<br/>identifies regional pattern
    ILO->>R: Publishes regional advisory
    ILO->>NGO: Publishes regional advisory
    ILO->>W: Updated GREP pack<br/>via OTA extension
```

Every arrow in this diagram is enabled by code that ships today.
The privacy boundary holds at every step (worker's PII never
leaves her phone unless she shares the intake doc; NGO's
contributions to ILO are noised aggregate counts only).

## The 17 PyPI packages — what each layer needs

```mermaid
graph TB
    CORE["duecare-llm-core<br/>protocols + schemas"]

    subgraph L1P["Used by everyone"]
        MODELS["duecare-llm-models<br/>8 backends"]
        DOMAINS["duecare-llm-domains<br/>3 domain packs"]
        TASKS["duecare-llm-tasks<br/>9 capability tests"]
    end

    subgraph L2P["Layer 2-4 (server-side)"]
        AGENTS["duecare-llm-agents<br/>12-agent swarm"]
        WORKFLOWS["duecare-llm-workflows<br/>YAML DAG runner"]
        SERVER["duecare-llm-server<br/>FastAPI + middleware"]
        ENGINE["duecare-llm-engine<br/>pipeline runner"]
        EVIDB["duecare-llm-evidence-db<br/>audit + journal"]
        NL2SQL["duecare-llm-nl2sql<br/>natural-language queries"]
    end

    subgraph L3P["Layer 3+ (research / training)"]
        BENCHMARK["duecare-llm-benchmark<br/>207-prompt rubric"]
        TRAINING["duecare-llm-training<br/>Unsloth SFT + DPO"]
        RESEARCH_TOOLS["duecare-llm-research-tools<br/>Tavily/Brave/Serper/DDG"]
    end

    subgraph META["Meta / chat surface"]
        CHAT["duecare-llm-chat<br/>harness + UI"]
        PUB["duecare-llm-publishing<br/>HF Hub + Kaggle"]
        CLI["duecare-llm-cli<br/>command-line tool"]
        ALL["duecare-llm<br/>(meta package)"]
    end

    CORE --> L1P
    CORE --> L2P
    CORE --> L3P
    CORE --> META
    L1P --> CHAT
    L1P --> SERVER
    L2P --> SERVER
    L3P --> BENCHMARK
    META --> ALL

    style CORE fill:#fff9c4,stroke:#fbc02d
    style META fill:#c8e6c9,stroke:#388e3c
```

A migrant worker uses zero PyPI packages directly (the Android
app bundles its own Kotlin port of the harness). A researcher
uses 4-5 (`core` + `chat` + `tasks` + `domains` + sometimes
`benchmark`). An enterprise uses 12+ for a full deployment.
Everyone gets the same harness logic — just different surface
areas.

## Why this composition works

**Privacy travels with the user.** A worker's data lives on her
phone. An NGO's data lives on the office Mac mini. A regulator's
data lives in their VPC. The federation protocol shares only
noised aggregate counts. **No data leaves the layer that owns it
without an explicit user action.**

**Same primitives, different deployments.** A new GREP rule added
to detect a corridor-specific pattern lands once + propagates to
every layer through the extension-pack format. A new corridor
profile lands once + every persona's chat surface knows about it
the next session.

**Open source binds the trust chain.** Every layer can audit every
other layer's source code. The Android app's harness is a Kotlin
port of the Python harness; both are public. The federation
aggregator's source is public. There's no closed component
anywhere that an organization is asked to trust on faith.

**Open standards bind the data.** Every layer speaks OpenAPI 3
(REST), Prometheus (metrics), OpenTelemetry (traces), JSON
(audit). No proprietary protocols. An organization adopting
Duecare can swap any one component for an alternative that
speaks the same standard.

## The four-layer adoption path

A real-world adoption sequence — what we've seen work for similar
tools (Tella by Horizontal, Polaris's data architecture, Anti-
Slavery International's open-source initiatives):

| Phase | Months | Who adopts first | What unlocks next |
|---|---|---|---|
| Phase 1 | 1-3 | Individual researchers + journalists | Public reproducibility + press coverage |
| Phase 2 | 3-9 | NGOs (1-5 pilot deployments) | Real workflow validation + caseworker testimonials |
| Phase 3 | 9-18 | Government regulators (initial unit-level adoption) | Policy-level validation + budget allocation |
| Phase 4 | 18-36 | Enterprises (recruitment platforms, social media moderation) | Cross-cutting integration |
| Phase 5 | 36+ | ILO / IOM / supra-national federation | Regional pattern aggregation, multi-NGO coordination |

Duecare is currently at the **start of Phase 1**. The 6+5 Kaggle
notebooks + the published documentation are the Phase 1 adoption
surface. The Android app is the Phase 1.5 surface (workers can
adopt directly).

## What "max impact + max audience" looks like in practice

If everything works as designed:

- A migrant worker in Hong Kong installs the APK before her flight
  back to Manila. She hands her case to her local NGO with the
  intake doc pre-generated.
- The NGO's Mac mini handles 5-15 cases / day with no
  subscription cost.
- The NGO's caseworker recovers 2 hours of legal-research time
  per intake. They handle more cases.
- The NGO contributes aggregate counts to a regional federation
  aggregator. ILO Bangkok publishes a regional report identifying
  a new fee-camouflage pattern across 12 NGOs in PH-HK + ID-HK.
- POEA enforcement responds to the aggregate signal. The
  recruiter at the center of the pattern gets investigated.
- An enterprise platform adopting Duecare's classifier flags
  the same recruiter's job ads on their platform. The pattern
  gets cut off at the source.
- A journalist publishes the pattern story using the
  press kit + Duecare's reproducible methodology. Public pressure
  closes the corridor of the specific abuse.
- An ILO regional office documents the closure in its annual
  report. Other corridors learn from the pattern.

That's the loop. Every step uses the same harness, the same
domain pack, the same audit-log schema, the same observability
stack. Different topology, different persona, same code.

## Adoption mechanics — what advances each layer

| Layer | What advances it | What blocks it |
|---|---|---|
| Layer 1 (workers) | Translated UI + Play Store / F-Droid distribution + worker-community endorsements | Lack of awareness; recruiter retaliation if found |
| Layer 2 (NGOs) | First 3-5 reference deployments + their public testimonials | NGO IT capacity; budget for hardware ($250-800) |
| Layer 3 (researchers / journalists) | Reproducibility of headline numbers + press kit usage | Citation discipline; verification of claims |
| Layer 4 (regulators / enterprises / ILO) | Initial unit-level pilot + cross-NGO federation pilot | Procurement cycles; vendor-questionnaire reviews |

Right now (May 2026, hackathon submission window):
- Layer 3 has the most immediate traction (notebooks + writeup
  + press kit ship today)
- Layer 1 has the working app but needs distribution channels
- Layer 2 is unblocked technically; needs first NGO reference
- Layer 4 is design-complete; needs first organizational pilot

## Adjacent reads

- [Try in 2 minutes](try_in_2_minutes.md) — per-persona quickstart
- [Deployment topologies](deployment_topologies.md) — the 5 deployment shapes
- [Scenarios index](scenarios/README.md) — 14 persona walkthroughs
- [Cross-NGO trends federation](cross_ngo_trends_federation.md) — the privacy-preserving aggregation protocol
- [Press kit](press_kit.md) — facts + quotes + story angles
- [Comparison vs alternatives](comparison_to_alternatives.md) — when Duecare fits vs not
