# Rubric evaluation — per-component grade card

> **Generated:** 2026-05-01 (T-17 days from the 2026-05-18 hackathon
> deadline). This doc grades every load-bearing component of the
> Duecare submission against the Gemma 4 Good Hackathon's three
> rubric axes: **Impact & Vision (40 pts)**, **Video Pitch &
> Storytelling (30 pts)**, and **Technical Depth & Execution (30 pts)**.
> 70 of 100 points live in the video.
>
> Source: comprehensive audit run 2026-05-01 against the live tree.
> Honest grades. Where the work is shipped but invisible to judges,
> the rating reflects "what the rubric will see," not "what we built."

## TL;DR

| Category | Today | Reachable in 17 days | What's blocking |
|---|---|---|---|
| **Impact & Vision (40)** | 32 / 40 (B+) | 36 / 40 (A–) | Video file existing |
| **Video Pitch (30)** | 5 / 30 (F) | 25 / 30 (A–) | Recording the 2:50 cut |
| **Technical Depth (30)** | 28 / 30 (A–) | 30 / 30 (A) | Publishing 5 notebooks + bench-and-tune fine-tune run |
| **Total** | **65 / 100 (D+)** | **91 / 100 (A–)** | Three actions in section "Top 5 next 17 days" |

The fall-off from "what we built" to "what scores" is **the missing
video** (-25 points if absent, -5 points if mediocre). All other gaps
are fixable within the deadline.

---

## Per-component grade table

### Core Kaggle notebooks (6) — the submission surface

| # | Notebook | State | Impact | Video | Tech | Risk |
|---|---|---|:-:|:-:|:-:|---|
| 1 | chat-playground (raw Gemma 4 baseline) | Complete | B | B | A | None — baseline by design |
| 2 | chat-playground-with-grep-rag-tools | Complete | **A** | **A+** | **A** | THE headline demo. Verify wheels dataset on Kaggle before video shoot. |
| 3 | content-classification-playground | Complete (publish pending) | A | A | A | Push to Kaggle by 2026-05-15 |
| 4 | content-knowledge-builder-playground | Complete (publish pending) | A | A | A | Push to Kaggle by 2026-05-15 |
| 5 | gemma-content-classification-evaluation (NGO dashboard) | Complete | A | A | A | Live |
| 6 | live-demo (1,951-line polished product + 22-slide deck) | Complete | **A** | **A+** | **A** | Verify wheels dataset on Kaggle |

### Appendix Kaggle notebooks (5) — extension + research

| # | Notebook | State | Impact | Video | Tech | Risk |
|---|---|---|:-:|:-:|:-:|---|
| A1 | prompt-generation | Complete (publish pending) | B | n/a | B | Push to Kaggle |
| A2 | bench-and-tune (Unsloth SFT + DPO + GGUF + HF push) | Complete; T4×2 run pending | B | n/a | **A** | Run on Kaggle T4×2 + push weights |
| A3 | research-graphs (6 Plotly charts) | Folder exists, kernel build status unclear | B | n/a | B | Verify kernel.py is built |
| A4 | chat-playground-with-agentic-research | Complete (publish pending) | B | n/a | A | Push to Kaggle |
| A5 | chat-playground-jailbroken-models | Complete (publish pending) | **A** | n/a | **A+** | Strongest "real not faked" proof; push priority |

### PyPI packages (17) — the reusability story

All 17 wheels are built (`packages/*/dist/*.whl` + `kaggle/*/wheels/`).
None are stubs.

| Package | Wheel | Used by | Grade |
|---|---|---|:-:|
| duecare-llm | ✓ | meta — `pip install duecare-llm` | A |
| duecare-llm-core | ✓ | every other package | A |
| duecare-llm-models | ✓ | adapters across 8 backends | A |
| duecare-llm-chat | ✓ | live-demo, chat playgrounds | A |
| duecare-llm-domains | ✓ | trafficking + tax-evasion + financial-crime packs | A |
| duecare-llm-tasks | ✓ | 9 capability tests | A |
| duecare-llm-benchmark | ✓ | bench-and-tune | A |
| duecare-llm-training | ✓ | Unsloth SFT + DPO | A |
| duecare-llm-agents | ✓ | 12-agent swarm | A |
| duecare-llm-workflows | ✓ | YAML DAG runner | A |
| duecare-llm-publishing | ✓ | HF Hub + Kaggle CLI wrappers | A |
| duecare-llm-cli | ✓ | `duecare` CLI entry point | A |
| duecare-llm-engine | ✓ | inference orchestrator | A |
| duecare-llm-evidence-db | ✓ | structured journal store | A |
| duecare-llm-nl2sql | ✓ | natural-language queries over evidence-db | B+ (less polished) |
| duecare-llm-research-tools | ✓ | Tavily/Brave/Serper/DuckDuckGo/Wikipedia + browser | A |
| duecare-llm-server | ✓ (6.2 MB — FastAPI + static assets) | the FastAPI surface | A |

### Submission documents

| Doc | State | Impact | Tech | Notes |
|---|---|:-:|:-:|---|
| writeup_draft.md (1,486 words; <1,500 cap) | Complete + refreshed for v0.6 / v0.7 Android | A | A | Ready to lock |
| FOR_JUDGES.md | Complete; TBD markers reworded as "publish pending" 2026-05-01 | A | A | Five-min path tested |
| video_script.md (2:50 beat sheet) | Complete; v0.6 Android beat updated 2026-05-01 | A+ | n/a | **Need actual MP4** |
| RESULTS.md | Refreshed 2026-05-01 with real harness-lift numbers | A | A | Fine-tune row still pending Kaggle T4×2 run |
| harness_lift_report.md (207 prompts, +56.5 pp mean lift) | Complete | A+ | A+ | The headline evidence |
| project_status.md | Refreshed 2026-05-01 | A | A | Current |
| deployment_topologies.md | New 2026-05-01 (5 topologies, decision tree, hardware sizing) | A | A | New today |
| android_app_architecture.md | Reflects v0.6 + v0.7 | A | A | Current |
| cloud_deployment.md | 13 platforms; cross-references topology selector | A | A | Current |

### Embedding examples (5 client examples)

| Path | State | Notes |
|---|---|---|
| examples/embedding/web-widget/ | ✓ working (vanilla JS) | Demo-ready |
| examples/embedding/react-component/ | ✓ working (React 18+) | Demo-ready |
| examples/embedding/telegram-bot/ | ✓ working | Demo-ready |
| examples/embedding/messenger-bot/ | ✓ working | Demo-ready |
| examples/embedding/whatsapp-cloud-api/ | ✓ working (Meta Cloud API) | Demo-ready |
| (planned: wordpress-plugin, browser-extension, ios-swift-package, android-aar, whatsapp-twilio) | listed in embedding_guide.md as planned | Honest "planned" framing — not blocking |

**Audit note:** the audit found "stub" content because the
embedding-example READMEs are short by design. Re-checked: each
contains a working bot.py / index.html / .tsx and a runnable env
example. **They are not stubs; they are minimal-but-working samples.**

### Deployment-topology examples (5, added today)

| Path | State |
|---|---|
| examples/deployment/local-all-in-one/ | ✓ Docker Compose (ollama + duecare + caddy) |
| examples/deployment/local-cli/ | ✓ single Python CLI w/ REPL |
| examples/deployment/ngo-office-edge/ | ✓ Mac mini / NUC + mDNS |
| examples/deployment/server-and-clients/ | ✓ deploy + 8 client patterns |
| examples/deployment/hybrid-edge-llm-cloud-rag/ | ✓ privacy contract + extension-pack OTA |

### Infrastructure (10+ cloud platforms)

| Platform | Status | Visibility |
|---|---|---|
| infra/render/render.yaml | ready | Used in cloud_deployment.md |
| infra/fly/fly.toml | ready | Used in cloud_deployment.md |
| infra/railway/railway.json | ready | Used in cloud_deployment.md |
| infra/aws/lightsail-deploy.sh | ready | Used in cloud_deployment.md |
| infra/eks/eksctl-cluster.yaml + helm/duecare/ | ready | Used in cloud_deployment.md |
| infra/gcp/cloudrun-deploy.sh | ready | Used in cloud_deployment.md |
| infra/gke/gke-autopilot-deploy.sh | ready | Used in cloud_deployment.md |
| infra/azure/containerapp-deploy.sh + aks/ | ready | Used in cloud_deployment.md |

**Honest note:** the writeup says "Dockerized API at `docs/deployment_enterprise.md`"
but doesn't enumerate the 10 cloud configs. **Judges score what they
see in the video + writeup.** The infra is real and well-built but not
a scoring component.

### Android sibling repo (`duecare-journey-android`)

| Layer | State | Grade |
|---|---|:-:|
| v0.6.0 APK released | ✓ on GitHub | A |
| v0.7.0 APK in CI | building (commit 47a17be) | A |
| MediaPipe Gemma 4 E2B on-device | ✓ working (six selectable variants, mirror fallbacks) | A |
| Cloud Gemma routing fallback (Ollama / OpenAI / HF) | ✓ working | A |
| Encrypted SQLCipher journal | ✓ working | A |
| Reports tab + ILO histogram + fee-table + intake doc | ✓ working | A |
| Auto-risk-tagging at write time | ✓ working | A |
| Guided intake wizard (10-question) | ✓ working | A |
| Structured Add-Fee + auto-LegalAssessment + Refund-claim drafting (v0.7) | ✓ working | A |
| Image picker for journal attachments (v0.7) | ✓ working | B+ (file encryption is v0.8) |
| Clear chat history (v0.7) | ✓ working | A |
| JVM unit tests for intel/ layer (v0.7) | ✓ ~30 cases | A |
| Real per-token streaming from MediaPipe | client-side chunking only | C (planned v0.8) |
| Tink AES-GCM encryption for attachments | not yet | C (planned v0.8) |

---

## Where the score actually comes from

### Impact & Vision (40 pts) — what judges look for

> "How clearly and compellingly does the project address a significant
> real-world problem? Is the vision inspiring and does the solution
> have tangible potential for positive change?"

**Today: 32 / 40.** Strengths:
- Quantified harness lift (+56.5 pp mean across 207 prompts; +87.5 pp
  on jurisdiction-specific citations) is real, deep evidence.
- 11 ILO indicators + 6 corridor profiles = recognized international
  taxonomy, not invented categories.
- Three deployment surfaces (NGO dashboard, worker chat, encrypted
  journal app) shows the technology meets workers where they are.
- Privacy posture (no telemetry, no account, panic wipe, on-device
  default, opt-in cloud) is non-negotiable for the threat model.
- Composite-character framing (Maria) labelled honestly; named NGOs
  (Polaris, IJM, POEA, BP2MI, Mission for Migrant Workers HK,
  PathFinders, HOME, TWC2) carry the impact story.

**Gaps that cost points:**
- Without the video, the rubric's "as demonstrated in the video" clause
  binds; -8 points.
- Android is shipping but isn't yet visible in any video frame; -2.

**To reach 36 / 40:**
- Record the Android-tab demo into the video (1 day work).
- Add one named NGO endorsement in the writeup (cold-email can be sent
  today; 5-day reply window is tight but possible).

### Video Pitch & Storytelling (30 pts)

> "How exciting, engaging, and well-produced is the video?"

**Today: 5 / 30.** Why so low: the video file does not exist yet.
Script is A+ (script-only ≈ 5 / 30 for "judges read it but can't
score it as video").

**To reach 25 / 30:**
- Hire a $50-100 narrator on Fiverr (1 day).
- Screen-record live-demo, chat-playground-with-grep-rag-tools, and
  classification notebooks (1 day).
- Capture v0.6 / v0.7 APK on a real phone showing Reports tab + intake
  doc (half a day).
- Edit + sound design (3 days).
- Caption + final pass (1 day).
- **Total: 6.5 days. Recommended start date: 2026-05-04.**

### Technical Depth & Execution (30 pts)

> "Is the technology real, functional, well-engineered, and not just
> faked for the demo?"

**Today: 28 / 30.** Strengths:
- 17 typed-Protocol-driven PyPI packages with auto-generated meta
  files, semver tagged, all wheels built.
- 6 polished Kaggle notebooks (Core), 5 appendix (Advanced).
- The Pipeline modal in chat-playground-with-grep-rag-tools is
  load-bearing explainability — judges can see exactly which GREP
  rule + which RAG doc + which tool fired for any response.
- The harness-lift report has 207 hand-graded prompts across 12
  criteria — not vibes-based.
- Native Gemma 4 features (function calling for agent orchestration,
  multimodal for Scout) are substrate, not decoration.
- Android repo has CI building APKs on every commit, with JVM unit
  tests for the intel/ layer (v0.7).

**Gaps that cost points:**
- 5 of 11 notebooks pending Kaggle publication (-1).
- Bench-and-tune T4×2 run + HF Hub push not yet completed (-1).

**To reach 30 / 30:**
- Push notebooks 3, 4, A1, A3, A4, A5 to Kaggle by 2026-05-15.
- Run bench-and-tune on Kaggle T4×2 and push the resulting weights to
  HF Hub at `taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0`.

---

## Top 5 actions in the next 17 days (in priority order)

1. **Record + submit the video** (covers 25 of the missing 35 points).
   Owner: Taylor + narrator. Deadline: 2026-05-12 (6 days editing
   buffer before the 2026-05-18 deadline).
2. **Push notebooks 3, 4, A1, A3, A4, A5 to Kaggle** with attached
   wheels datasets. Verify each runs end-to-end on Kaggle T4×2.
   Deadline: 2026-05-15.
3. **Run bench-and-tune notebook (A2) on Kaggle T4×2.** Push fine-tuned
   weights to HF Hub. Update RESULTS.md fine-tune row with real numbers.
   Deadline: 2026-05-15.
4. **Cold-email 1-2 NGOs** for an attributed endorsement to embed in
   the writeup. Polaris, Mission for Migrant Workers HK, IJM, POEA,
   BP2MI are the highest-leverage targets. Deadline: 2026-05-04 (so
   reply lands by 2026-05-14).
5. **Lock writeup, FOR_JUDGES, RESULTS, video_script** by 2026-05-16.
   No further edits past that — proof-read only. Submit on 2026-05-17
   for the one-day buffer.

---

## What this doc commits to

If we hit all five actions: **91 / 100 (A–)** is the realistic landing
zone. That's competitive for the Safety & Trust track ($10K) and
within striking distance of the Main track ($10K-50K).

If we ship only the video and skip everything else: **85 / 100 (B+)**.
Still likely in-the-money for Safety & Trust.

If we skip the video: **65 / 100 (D+)**. Outside the money.

The video is the highest-leverage single deliverable left.
