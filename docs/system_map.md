# System map — bird's-eye view of everything

> Single-page navigation map across **users, surfaces, harness, notebooks,
> packages, and deployments**. Use this to orient yourself before
> diving into any specific doc.
>
> **Interactive version:** [`system_map.html`](system_map.html) — click
> any node, filter by type. Lives under the same docs site.

## At a glance

| Dimension | Count |
|---|---:|
| User personas served | 14 |
| Product surfaces | 5 |
| Kaggle notebooks | 11 (2 core + 9 appendix) |
| PyPI packages | 17 |
| Deployment topologies | 5 |
| GREP rules | 42 |
| RAG documents | 26 |
| Migration corridors | 20 |
| ILO C029 indicators | 11 |
| Mean harness lift | +56.5 pp |

## Layer 1 — Users → Surfaces

```mermaid
graph LR
  OFW[OFW / migrant worker]
  CW[Caseworker]
  ND[NGO director]
  L[Lawyer]
  R[Researcher]
  J[Journalist]
  REC[Recruitment compliance]
  REG[Government regulator]
  EMB[Embassy / consulate]
  ILO[ILO / IOM regional]
  IT[IT director]
  ARCH[Chief architect]
  VP[VP Engineering]
  CTO[Platform CTO]

  CHAT[Worker chat]
  CLASS[NGO classifier]
  ANDROID[Android v0.9 APK]
  DASH[Live demo dashboard]
  API[FastAPI server]

  OFW --> CHAT
  OFW --> ANDROID
  CW --> CLASS
  CW --> DASH
  ND --> ANDROID
  ND --> API
  L --> CLASS
  L --> ANDROID
  R --> API
  J --> CLASS
  REC --> CLASS
  REG --> DASH
  EMB --> CLASS
  ILO --> API
  IT --> API
  ARCH --> API
  VP --> API
  CTO --> API
```

## Layer 2 — The 4-layer harness (the technical core)

```mermaid
graph LR
  USER[User input] --> P[① Persona<br/>40-yr expert system prompt]
  P --> G[② GREP<br/>42 regex KB rules]
  G --> R[③ RAG<br/>BM25 over 26 docs]
  R --> T[④ Tools<br/>4 function calls<br/>via Gemma 4]
  T --> MERGE[⑥ FINAL MERGED PROMPT<br/>byte-for-byte]
  MERGE --> GEMMA[⑦ Gemma 4 response]

  GEMMA --> PIPE[Pipeline modal<br/>shows all 7 cards<br/>color-coded by layer]
```

Every response shows a **▸ View pipeline** link opening the 7-card
modal — every byte the model saw is visible. That visualization IS
the demo.

## Layer 3 — Notebooks (the submission surface)

```mermaid
graph TB
  subgraph CORE["6 core notebooks (walk in order)"]
    NB1[1. chat-playground<br/>Raw Gemma 4 baseline]
    NB2[2. chat-playground-with-grep-rag-tools<br/>⭐ Headline demo]
    NB3[3. content-classification-playground<br/>4-schema JSON sandbox]
    NB4[4. content-knowledge-builder-playground<br/>Add custom GREP/RAG]
    NB5[5. gemma-content-classification-evaluation<br/>NGO dashboard]
    NB6[6. live-demo<br/>⭐ Polished product]
    NB1 --> NB2 --> NB3 --> NB4 --> NB5 --> NB6
  end

  subgraph APPENDIX["5 appendix notebooks (extension + research)"]
    A1[A1. prompt-generation]
    A2[A2. bench-and-tune<br/>Unsloth SFT + DPO + GGUF]
    A3[A3. research-graphs<br/>6 Plotly charts]
    A4[A4. agentic-research<br/>5th toggle]
    A5[A5. jailbroken-models<br/>⭐ Real-not-faked proof]
  end

  CORE --> APPENDIX
```

## Layer 4 — PyPI packages (17 wheels under `duecare.*` namespace)

```mermaid
graph TB
  subgraph TIER1["Tier 1 — Foundation"]
    CORE[duecare-llm-core<br/>Pydantic + Protocol contracts]
  end

  subgraph TIER2["Tier 2 — Domain logic"]
    MODELS[duecare-llm-models<br/>8 adapters]
    DOMAINS[duecare-llm-domains<br/>3 packs]
    TASKS[duecare-llm-tasks<br/>9 capability tests]
    EVDB[duecare-llm-evidence-db]
    CHAT[duecare-llm-chat ⭐<br/>The harness]
    BENCH[duecare-llm-benchmark]
    TRAIN[duecare-llm-training]
    ENGINE[duecare-llm-engine<br/>+ OTel]
  end

  subgraph TIER3["Tier 3 — Orchestration"]
    AGENTS[duecare-llm-agents<br/>12 agents]
    WF[duecare-llm-workflows<br/>YAML DAG runner]
    PUB[duecare-llm-publishing<br/>HF Hub + Kaggle]
    NL2SQL[duecare-llm-nl2sql]
    RT[duecare-llm-research-tools]
  end

  subgraph TIER4["Tier 4 — Surfaces + meta"]
    SERVER[duecare-llm-server<br/>FastAPI 6.2 MB]
    CLI[duecare-llm-cli<br/>duecare CLI]
    META[duecare-llm meta<br/>installs all]
  end

  CORE --> MODELS & DOMAINS & TASKS & EVDB & CHAT & BENCH & TRAIN & ENGINE
  TIER2 --> AGENTS & WF & PUB & NL2SQL & RT
  TIER3 --> SERVER & CLI & META
```

Cross-layer imports flow **downward only** (per
[`.claude/rules/20_code_style.md`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/.claude/rules/20_code_style.md))
— Tier 4 may import from Tier 1, never the reverse.

## Layer 5 — Deployment topologies (5 shapes)

```mermaid
graph LR
  subgraph A["A. On-device only"]
    A1[Android v0.9 APK<br/>MediaPipe Gemma 4<br/>SQLCipher journal]
  end

  subgraph B["B. NGO-office edge"]
    B1[Mac mini / NUC<br/>Docker compose<br/>2-10 caseworkers]
  end

  subgraph C["C. Cloud single-tenant"]
    C1[Helm chart<br/>HPA + PDB<br/>+ NetworkPolicy]
  end

  subgraph D["D. Cloud multi-tenant"]
    D1[Helm + tenancy MW<br/>+ rate limit<br/>+ cost meter]
  end

  subgraph E["E. Hybrid"]
    E1[Cloud Gemma 4<br/>+ on-device journal]
  end
```

Pick a topology with [`docs/deployment_topologies.md`](deployment_topologies.md).

## Cross-cutting threads

These aren't a layer — they cut across every layer:

| Thread | Where it lives |
|---|---|
| **Privacy** (anonymizer hard gate, audit log of hashes) | [`.claude/rules/10_safety_gate.md`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/.claude/rules/10_safety_gate.md) · [`considerations/THREAT_MODEL.md`](considerations/THREAT_MODEL.md) |
| **Reproducibility** ((git_sha, dataset_version) provenance) | [`RESULTS.md`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/RESULTS.md) · [`harness_lift_report.md`](harness_lift_report.md) |
| **Observability** (OTel + Prometheus + Loki + Grafana) | [`considerations/SLO.md`](considerations/SLO.md) · [`considerations/runbook.md`](considerations/runbook.md) |
| **Governance** (ADRs + threat model + compliance crosswalk) | [`adr/`](adr/) · [`considerations/`](considerations/) |
| **Cross-NGO trends** (federation w/o PII) | [`cross_ngo_trends_federation.md`](cross_ngo_trends_federation.md) |

## How to use this map

| If you are... | Click in order |
|---|---|
| A judge in a hurry | Stat cards → Layer 3 (notebooks) → [`FOR_JUDGES.md`](FOR_JUDGES.md) |
| A first-time deployer | Layer 1 (find your persona) → Layer 5 (pick topology) → relevant scenario |
| A contributor | Layer 4 (packages) → [`adr/`](adr/) → [`CONTRIBUTING.md`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/CONTRIBUTING.md) |
| An academic | Layer 3 (notebooks A1–A3) → [`harness_lift_report.md`](harness_lift_report.md) → [`prompt_schema.md`](prompt_schema.md) |
| A journalist | Layer 1 (journalist node) → [`press_kit.md`](press_kit.md) → [`marias_case_end_to_end.md`](marias_case_end_to_end.md) |

## See also

- [`readiness_dashboard.md`](readiness_dashboard.md) — current submission readiness across every dimension
- [`authors_notes.md`](authors_notes.md) — informal observations + reflections from the author
- [`appendices/README.md`](appendices/README.md) — index of additional enclosures linked from the writeup
- [`writeup_draft.md`](writeup_draft.md) — the formal 1,500-word submission writeup
