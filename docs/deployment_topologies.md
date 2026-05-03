# Deployment topologies — pick the right shape

Duecare is composed of five things that can live in different places:

1. **Gemma 4** — the language model itself
2. **GREP layer** — deterministic regex rules (37 trafficking patterns)
3. **RAG layer** — 26-doc legal corpus + BM25 retrieval
4. **Tools layer** — corridor fee caps, ILO indicator lookup, NGO directory
5. **Internet search** — `duecare-llm-research-tools` (Tavily / Brave /
   Serper / DuckDuckGo / Wikipedia / arbitrary URL fetch)

This doc explains the four topologies you can compose those into, when
to pick each, and links to a runnable example for every one. If you
came here wondering "where does Gemma live in production?", read the
2-minute decision tree first.

---

## 2-minute decision tree

```
Are you a single user on a laptop?
 └── Yes → Topology A (single-component local)        ← examples/deployment/local-all-in-one/
 └── No
     │
     Do field workers need to use this on phones?
      └── Yes
          │
          Is privacy paramount (data must NEVER leave the worker's device)?
           └── Yes → Topology D (on-device LLM only)  ← duecare-journey-android, no cloud
           └── No  → Topology C (server + thin clients) ← examples/deployment/server-and-clients/
                       │
                       Or → Topology E (hybrid: on-device LLM + cloud knowledge)
                            ← examples/deployment/hybrid-edge-llm-cloud-rag/
      └── No
          │
          Are workers all on the same LAN (one NGO office)?
           └── Yes → Topology B (NGO-office edge box)  ← examples/deployment/ngo-office-edge/
           └── No  → Topology C (server + thin clients) ← examples/deployment/server-and-clients/
```

---

## Comparison matrix

| Topology | Where Gemma lives | Where harness lives | Where data lives | Internet required at runtime? | Best for | Setup time |
|---|---|---|---|---|---|---|
| **A. Single-component local** | Same machine | Same machine | Same machine | No (after first launch) | Solo user / developer | 5 min |
| **B. NGO-office edge** | Office Mac mini / NUC | Same box | Same box | No | NGO with 1-20 caseworkers on LAN | 30 min |
| **C. Server + thin clients** | Cloud server | Same server | Server DB | Yes | Multi-NGO, multi-region, hosted SaaS | 15 min |
| **D. On-device LLM only** | Worker's phone | Phone (Kotlin port) | Phone | No | Worker who must avoid all telemetry | n/a (just install the APK) |
| **E. Hybrid edge LLM + cloud knowledge** | Worker's phone | Phone GREP + cloud RAG/search | Mixed (chat private; lookups go to cloud) | Yes (lookups only) | Worker who wants Gemma local but needs current legal info | install APK + point at cloud RAG endpoint |

Notes on "data lives":
- **A / B / D**: Worker's chat history, journal entries, fee records all
  stay on the box that runs the model. Disk encryption is the worker's
  responsibility (or the NGO sysadmin's).
- **C**: All worker data lives on the cloud server. NGO is responsible
  for privacy posture, GDPR, audit logs, and breach notification. The
  hosted server should run inside the NGO's VPC, not as a public SaaS.
- **E**: The worker's chat + journal are local; only knowledge lookups
  (RAG queries, web searches, ILO statute lookups) cross the network.
  The lookups themselves don't carry the worker's identity.

---

## Topology A — Single-component local (everything in one process)

**One Docker Compose stack, one URL, no internet needed at runtime.**
Gemma runs via Ollama. The Duecare server bundles GREP + RAG + tools.
A Caddy reverse proxy makes the whole thing reachable at
`http://localhost`.

```
┌─────────────────── docker-compose stack ───────────────────┐
│                                                            │
│   ┌──────────────┐  ┌──────────────────┐  ┌────────────┐   │
│   │  ollama      │← │  duecare server  │← │   caddy    │   │
│   │ (gemma4:e2b) │  │ (FastAPI + GREP  │  │ (reverse   │   │
│   │              │  │  + RAG + tools)  │  │  proxy)    │   │
│   └──────────────┘  └──────────────────┘  └────────────┘   │
│         │                    │                  │          │
│         └─── localhost ──────┴──────────────────┘          │
│                                                            │
└────────────────────────────────────────────────────────────┘
                          ↑
              http://localhost
```

**Best for:** developer evaluating the harness; solo NGO advocate; a
laptop in the field with no signal; air-gapped reproduction of a
hackathon submission.

**Cost:** $0 (bring your own laptop).

**Privacy:** ★★★★★ — nothing leaves the box.

**Internet at runtime:** none required after the model is pulled.

**Try it:** `cd examples/deployment/local-all-in-one && docker compose up`

---

## Topology B — NGO-office edge (Mac mini / NUC on the LAN)

**Same Docker Compose as Topology A, plus mDNS so caseworkers' phones
and laptops can reach it via `duecare.local`.**

Run on a Mac mini, an Intel NUC, an old gaming PC, or a Synology with
Docker. Caseworkers connect from their phones / laptops over the
office Wi-Fi. No internet, no SaaS, no cloud bill.

```
┌────────────── NGO office LAN ──────────────┐
│                                            │
│   ┌──────────────────┐                     │
│   │  Mac mini / NUC  │ ← caseworker phone  │
│   │ docker-compose:  │ ← caseworker laptop │
│   │ ollama + duecare │ ← intern's tablet   │
│   │ + caddy + mdns   │                     │
│   └──────────────────┘                     │
│           │                                │
│        duecare.local (mDNS)                │
│           or 192.168.x.y                   │
└────────────────────────────────────────────┘
```

**Best for:** NGO with 1-20 caseworkers in one office, strong privacy
requirements, intermittent or expensive internet.

**Cost:** $400-800 one-time hardware + $0/mo. Mac mini M2 8GB ≈ $599
new, ≈ $300 refurbished.

**Privacy:** ★★★★★ — never leaves the LAN.

**Internet at runtime:** none for chat / GREP / RAG / fee lookups;
Topology B + cloud search bridge if you want web research too (rare).

**Try it:** `cd examples/deployment/ngo-office-edge && docker compose up`

---

## Topology C — Server + thin clients (the hosted-SaaS shape)

**Duecare server runs once on Render / Fly / Cloud Run / GKE / EKS /
your own VPS.** Multiple thin clients (Android app pointed at the
cloud URL, Telegram bot, Messenger bot, WhatsApp Cloud API webhook,
React widget on an NGO website, CLI) all talk to the same backend.

```
                    ┌──────────────────────────────────┐
                    │        cloud server              │
                    │  (Render / GCR / GKE / EKS /     │
                    │   Fly / Lightsail / your VPS)    │
                    │                                  │
                    │   FastAPI + GREP + RAG + tools   │
                    │     + Gemma 4 via Ollama         │
                    │     + research-tools             │
                    │     + evidence-db (Postgres)     │
                    └──────────────┬───────────────────┘
                                   │
        ┌──────┬──────┬─────┬──────┼──────┬──────┬──────┐
        │      │      │     │      │      │      │      │
   Android  React  WhatsApp Tele  Web    iOS    CLI    NGO
   app     widget   cloud   gram  embed         tool  website
                    API     bot
```

**Best for:** multi-NGO hosted service, multi-region, want one place
to update rules + corpus + model and have all clients pick it up.

**Cost:** $0 idle on Cloud Run / Render free tier; $7-25/mo for an
always-on small instance; $75/mo+ for managed K8s.

**Privacy:** ★★★ — operator of the server can see prompts. Pair with a
zero-knowledge auth proxy if you need stronger guarantees.

**Internet at runtime:** required (clients reach the server).

**Try it:** `cd examples/deployment/server-and-clients` — has the
deploy command for the server + 3 client configs.

---

## Topology D — On-device LLM only (Android app, no network)

**Everything runs on the worker's phone.** Gemma 4 E2B INT8 via
MediaPipe. The Android app's `intel/` package is a Kotlin port of the
GREP rules + ILO indicators + corridor knowledge. The journal is
SQLCipher-encrypted at rest.

This is the mode the `duecare-journey-android` app v0.9.0 ships in by
default. The Settings → Cloud model section is opt-in.

**Best for:** worker who's been told never to install anything that
sends data anywhere; humanitarian context where the worker would be
endangered by a trafficking detection signal arriving on a recruiter's
infrastructure.

**Cost:** $0.

**Privacy:** ★★★★★ — by design.

**Internet at runtime:** only for the one-time ~1.5 GB model download.
After that, none.

**Try it:** install
[the latest APK](https://github.com/TaylorAmarelTech/duecare-journey-android/releases).

---

## Topology E — Hybrid edge LLM + cloud knowledge

**The worker runs Gemma locally on their phone but wants real-time
knowledge updates** (a new POEA Memo Circular dropped yesterday; a
recruitment scheme in the news this morning). The model stays local;
only knowledge lookups cross the network.

```
   Worker's phone (Gemma 4 + GREP + journal)
          │
          │  knowledge query: "is there a new POEA MC about training fees?"
          ▼
   ┌────────────────────────────────────┐
   │  cloud knowledge endpoint           │
   │  (your Render server or HF Space)   │
   │                                     │
   │  - latest GREP rule pack            │
   │  - latest RAG corpus                │
   │  - duecare-llm-research-tools       │
   │    (Tavily / Brave / Serper)        │
   └────────────────────────────────────┘
```

The lookup carries no worker identity — it's just `{ query: "POEA MC
training fee", corridor: "PH-HK" }`. The model + chat history stay on
the device.

**Best for:** worker who wants Gemma's privacy AND current information;
NGO that pushes weekly knowledge updates to the field.

**Cost:** $5-25/mo for the knowledge endpoint + $0 for the phone.

**Privacy:** ★★★★ — chat private; only de-identified lookups leave.

**Internet at runtime:** required for lookups (most operations are
fully local).

**Try it:** `cd examples/deployment/hybrid-edge-llm-cloud-rag`

---

## Composability — how topologies stack

You can combine topologies in one organization:

- **A + C**: developers run Topology A locally; users hit Topology C
  in production. The server's container is the same image either way.
- **B + C**: NGO HQ runs Topology B for the office; field caseworkers
  on the road use Topology C against the same backend.
- **C + D + E**: NGO has a hosted Topology C server; some workers use
  Topology D (pure on-device) for max privacy; others use Topology E
  to get current knowledge from the same Topology C server.

The Duecare image is the same in all cases. Only the deployment shape
and the privacy posture differ.

---

## Picking a topology — common questions

**"What if I have a few hundred users a day?"** — Topology C on
Render or Cloud Run. Scale-to-zero handles burst, the model warm-up
penalty is acceptable for a chat surface.

**"What if I need GDPR / SOC 2 / HIPAA-style compliance?"** — Topology
B (no data ever leaves your premises) is the only one that lets you
honestly tell an auditor "the worker's data did not leave our control."
Topology C inside your own VPC also works if your VPC itself is in
scope of your compliance attestation.

**"What if my country bans cloud egress?"** — Topology B or D. (China,
Russia, Saudi Arabia, Iran, parts of India and Indonesia have
restrictions on certain LLM endpoints.)

**"What if the model upgrade is the priority?"** — Topology C. You
push a new image once and every client (Android, web, Telegram, etc.)
picks it up immediately. Topology B and D require an APK / Docker
image push to each device, which can be days for a field rollout.

**"What if cost is the priority?"** — Topology A and D are free.
Topology B is one-time $400-800. Topology C is $5-25/mo for small
NGOs, scaling with traffic.

---

## What's bundled where

| Component | Topology A | Topology B | Topology C | Topology D | Topology E |
|---|:-:|:-:|:-:|:-:|:-:|
| Gemma 4 | Local Ollama | Edge Ollama | Cloud Ollama | On-device MediaPipe | On-device MediaPipe |
| GREP rules | Local Python | Edge Python | Cloud Python | On-device Kotlin | On-device Kotlin |
| RAG (BM25 + corpus) | Local | Edge | Cloud | On-device (subset) | Cloud (full) |
| Tools (corridor / ILO / NGO) | Local | Edge | Cloud | On-device (subset) | Cloud (full) |
| Internet search | Local (DuckDuckGo) | Edge (DuckDuckGo) | Cloud (Tavily/Brave/Serper) | Not available | Cloud (Tavily/Brave/Serper) |
| Journal (encrypted) | Local SQLite | Edge SQLite per worker | Cloud Postgres per worker | On-device SQLCipher | On-device SQLCipher |

---

## Hardware sizing

| Topology | Min RAM | Recommended RAM | Storage | GPU |
|---|---:|---:|---:|---|
| A (laptop) | 8 GB | 16 GB | 10 GB | optional (CPU works for E2B) |
| B (Mac mini / NUC) | 16 GB | 32 GB | 100 GB | optional but improves latency |
| C (cloud server) | 4 GB CPU-only / 16 GB w/ GPU | 8 GB / 24 GB | 50 GB | optional (T4 is cheapest) |
| D (Android phone) | 6 GB | 8 GB+ | 4 GB free | n/a — uses NPU when present |
| E (phone + cloud) | same as D + cloud sizing for C | — | — | — |

---

## Reference examples in this repo

- [`examples/deployment/local-all-in-one/`](../examples/deployment/local-all-in-one/) — Topology A
- [`examples/deployment/local-cli/`](../examples/deployment/local-cli/) — Topology A, no Docker
- [`examples/deployment/ngo-office-edge/`](../examples/deployment/ngo-office-edge/) — Topology B
- [`examples/deployment/server-and-clients/`](../examples/deployment/server-and-clients/) — Topology C
- [`examples/deployment/hybrid-edge-llm-cloud-rag/`](../examples/deployment/hybrid-edge-llm-cloud-rag/) — Topology E

For Topology D, see the
[`duecare-journey-android`](https://github.com/TaylorAmarelTech/duecare-journey-android)
sibling repo.

---

## See also

- [`docs/cloud_deployment.md`](./cloud_deployment.md) — 13-platform
  cloud cookbook (the "how to deploy on each cloud" companion to
  Topology C above).
- [`docs/deployment_local.md`](./deployment_local.md) — three local
  paths (Ollama / Kaggle kernel / pip install) — alternatives to the
  Docker Compose example for Topology A.
- [`docs/deployment_enterprise.md`](./deployment_enterprise.md) —
  enterprise-specific concerns (SSO, audit log, RBAC) — companion to
  Topology C in regulated environments.
- [`docs/deployment_modes.md`](./deployment_modes.md) — three
  *application-level* deployment patterns (waterfall detection / worker
  tool / agency dashboard) — orthogonal to topology; you can combine
  any application mode with any of the five topologies above.
- [`docs/embedding_guide.md`](./embedding_guide.md) — how to embed the
  Duecare safety harness into other apps; pairs with Topology C.
