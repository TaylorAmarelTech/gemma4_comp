# Duecare Quality Rubrics

Eleven dimensions, each with a 1-5 maturity scale and Duecare's
honest self-score as of 2026-05-01. The gap between current and
target is what the team works on. This doc is meant to be re-scored
quarterly post-hackathon and shared with NGO partners + contributors.

> **Self-scoring discipline.** Every score below is justified by a
> specific artifact (file, URL, or measurement). Where the score is
> below the target, the gap is named explicitly + the next concrete
> action is queued.

## Quick navigation

Each rubric is deep-linkable via anchor — share `docs/quality_rubrics.md#rubric-N-name` with a reviewer to jump straight to that section.

| # | Rubric | Anchor |
|---|---|---|
| 1 | Code quality | [#rubric-1-code-quality](#rubric-1-code-quality) |
| 2 | Repository quality | [#rubric-2-repository-quality](#rubric-2-repository-quality) |
| 3 | Writeup quality | [#rubric-3-writeup-quality](#rubric-3-writeup-quality) |
| 4 | Impact | [#rubric-4-impact-and-the-path-to-impact](#rubric-4-impact-and-the-path-to-impact) |
| 5 | Ease of use (per audience) | [#rubric-5-ease-of-use](#rubric-5-ease-of-use) |
| 6 | Ease of integration | [#rubric-6-ease-of-integration](#rubric-6-ease-of-integration) |
| 7 | UI / UX | [#rubric-7-ui--ux](#rubric-7-ui--ux) |
| 8 | Extensibility | [#rubric-8-extensibility](#rubric-8-extensibility) |
| 9 | Community + maintenance | [#rubric-9-community--maintenance--currency](#rubric-9-community--maintenance--currency) |
| 10 | Sharing + publishing | [#rubric-10-sharing--publishing](#rubric-10-sharing--publishing) |
| 11 | Audience-fit | [#rubric-11-audience-fit--accessibility-breadth](#rubric-11-audience-fit--accessibility-breadth) |
| ⊕ | Aggregate scorecard | [#aggregate-scorecard-snapshot-2026-05-01](#aggregate-scorecard-snapshot-2026-05-01) |

> **Splitting policy.** Any individual rubric that grows past ~500 words gets promoted to `docs/rubrics/<name>.md` and replaced inline with a one-paragraph summary + link. Today: all 11 fit comfortably in one file.

## Audience definitions (referenced throughout)

The rubrics scope expectations to who the surface is for. Five
audiences:

| Audience | Skill profile | Primary surface | Privacy posture |
|---|---|---|---|
| **Worker (W)** | First-language non-English, mobile-only, low-literacy possible, untrusted device environment | Android app + mobile web | Maximal — no account, no telemetry, on-device only |
| **NGO intake officer (N)** | Domain-expert, modest tech literacy, NGO-issued laptop | Classifier dashboard + chat | High — case data must stay on the NGO's infra |
| **Researcher / academic (R)** | High tech literacy, Python, willing to read code | Kaggle notebooks + writeup + GitHub | Open — public benchmarks |
| **Engineer / contributor (E)** | High tech literacy, Python + Kotlin + Docker + K8s | All of the above + the source code | Open |
| **Enterprise integrator (I)** | High tech literacy, prefers stable APIs + IaC | Helm chart + OpenAPI + Docker | High — own infra, own auth, own audit |

Throughout the rubrics, capabilities are tagged `[W]`, `[N]`, `[R]`, `[E]`, `[I]` to indicate which audience benefits.

---

## Rubric 1: Code quality

| Level | What it looks like | Evidence |
|---|---|---|
| **L1** Untested scripts | Runs on author's machine | — |
| **L2** Some tests, sporadic linting | Has a test suite, no CI gate | — |
| **L3** Typed, linted, CI-enforced | Type hints + ruff + mypy + pytest, all in CI | — |
| **L4** Property/mutation-tested, contract-validated | Hypothesis tests on hot paths, mutation testing >70% kill rate | — |
| **L5** Formally specified critical paths | Property tests + invariants documented + adversarial test corpus | — |

**Duecare current: L3** (target: L4 by hackathon end, L5 post-hackathon).

- 194 unit tests passing (across `packages/` + `tests/`).
- Type hints required (CLAUDE.md `.claude/rules/20_code_style.md`).
- `ruff check` + `mypy` enforced in `make lint`.
- **Gap:** no Hypothesis property tests, no mutation coverage measurement.
- **Next:** add `hypothesis` tests for `_grep_call`, `_rag_call`, `grade_response_required`; run `mutmut` on `duecare.chat.harness` and report kill rate.

## Rubric 2: Repository quality

| Level | What it looks like |
|---|---|
| **L1** No README | — |
| **L2** Basic README + LICENSE | — |
| **L3** README + LICENSE + CONTRIBUTING + SECURITY + CODE_OF_CONDUCT + CI + structured docs | — |
| **L4** L3 + automated dependency scanning + reproducible builds + release notes per version | — |
| **L5** L4 + signed commits + signed releases + SBOM + provenance attestation | — |

**Duecare current: L3** (target: L4).

- README, LICENSE (MIT), SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md all present.
- 17 PyPI packages with consistent structure under `packages/`.
- `.claude/rules/40_forge_module_contract.md` enforces folder-per-module pattern with auto-generated `PURPOSE.md` / `AGENTS.md` / `INPUTS_OUTPUTS.md` / `HIERARCHY.md` / `DIAGRAM.md` / `TESTS.md` / `STATUS.md` per module.
- **Gap:** no Dependabot / Renovate config; no SBOM publishing; no signed commits; no release-notes automation.
- **Next:** add `.github/dependabot.yml`; add SBOM generation step to `pypi-publish.yml`; enable signed commits via `git config commit.gpgsign true` + Sigstore for releases.

## Rubric 3: Writeup quality

| Level | What it looks like |
|---|---|
| **L1** Demo + a tweet | — |
| **L2** Single-page README explaining the project | — |
| **L3** Structured writeup with TL;DR + problem + solution + reproducibility | — |
| **L4** L3 + quantified claims with provenance + prior-art comparison + audience-specific pages | — |
| **L5** L4 + adversarial third-party review + replication study | — |

**Duecare current: L4** (target: L4 — sustained).

- `docs/writeup_draft.md` (~1450 words, Kaggle cap 1500) with 8 sections.
- `docs/FOR_JUDGES.md` audience-specific (Researcher / Engineer audiences).
- `docs/harness_lift_report.md` quantifies +87.5/+51.2/+34.1 pp lift across 3 dimensions on 207 prompts.
- `docs/prior_art.md` cites Just Good Work + Polaris + Tella + HarmBench/AILuminate + DoNotPay caveat.
- `RESULTS.md` pins every metric to `(git_sha, dataset_version, model_revision)`.
- **Gap:** no third-party review yet (a peer's read would catch our blind spots).
- **Next:** ask one NGO contact + one academic for an honest 30-min review pre-submission.

## Rubric 4: Impact (and the path to impact)

| Level | What it looks like |
|---|---|
| **L1** Hypothesized impact, no users | — |
| **L2** 1 user / NGO partner pilot | — |
| **L3** Multiple pilots, documented use cases, public health/safety org endorsement | — |
| **L4** Production deployment at 1+ NGO + measured outcome (refunds recovered, complaints filed, harm prevented) | — |
| **L5** L4 + cited in regulatory/policy work | — |

**Duecare current: L1** (target: L2 within 90 days, L3 within 12 months).

- The harness is built; the impact is hypothesized but unmeasured at scale.
- North star (inform AND document) maps to two measurable outcomes: (1) refund recovered per fee paid, (2) prevented payments per worker advised.
- **Gap:** no real-world pilot. Polaris, IJM, MfMW HK, BP2MI named in the writeup but not engaged as users.
- **Next:** post-hackathon, send the v1 APK + a one-pager to MfMW HK domestic-worker outreach team; offer to pilot for 30 days at zero cost; instrument the journal export count + refund-claim filing count as the only telemetry (opt-in, aggregate).

## Rubric 5: Ease of use

Per audience.

### 5.W — Worker

| Level | What it looks like |
|---|---|
| **L1** Install Android Studio + sideload APK | — |
| **L2** Sideload APK from a download link, no SDK install | — |
| **L3** Install via F-Droid or Play Store, single tap | — |
| **L4** L3 + first-launch onboarding in worker's language + zero-friction model download | — |
| **L5** L4 + offline install via NGO partner distribution (USB / SD card / Bluetooth share) | — |

**Duecare current: L2** (skeleton APK download from GitHub Releases). Target: **L4** by v1 MVP.

### 5.R — Researcher

| Level | What it looks like |
|---|---|
| **L1** Clone repo + figure out which scripts to run | — |
| **L2** README quick-start | — |
| **L3** `pip install` from PyPI + `python -m duecare.chat.run_server` | — |
| **L4** L3 + Kaggle notebook one-click "Run all" | — |
| **L5** L4 + hosted live demo URL judges/researchers can click without installing anything | — |

**Duecare current: L4** (Kaggle notebooks one-click; PyPI install pending publish). Target: **L5** when HF Spaces is live.

### 5.E — Engineer / contributor

| Level | What it looks like |
|---|---|
| **L1** Manual setup, multiple READMEs to read | — |
| **L2** `make install` works | — |
| **L3** L2 + devcontainer (Codespaces 90s onboarding) | — |
| **L4** L3 + one-line installer (`curl ... | bash`) + Docker Compose | — |
| **L5** L4 + Helm chart for cluster deploys + multi-arch images | — |

**Duecare current: L5** (as of this commit batch). All four artifacts ship.

### 5.I — Enterprise integrator

| Level | What it looks like |
|---|---|
| **L1** Source-only, build it yourself | — |
| **L2** Docker image | — |
| **L3** Helm chart with HPA + persistence | — |
| **L4** L3 + OpenAPI spec + auth (OIDC/SAML stub) + observability (Prometheus + OTel) | — |
| **L5** L4 + Terraform modules for AWS/GCP/Azure + signed images + SLSA provenance | — |

**Duecare current: L3**. Target: **L4** by v1.0.0.
- **Gap:** no OpenAPI spec, no auth integration, no observability instrumentation surfaced.
- **Next:** generate OpenAPI from the FastAPI app; add Hilt-style auth-strategy plug-point.

## Rubric 6: Ease of integration

| Level | What it looks like |
|---|---|
| **L1** Read the source, copy what you need | — |
| **L2** Documented Python API | — |
| **L3** Stable PyPI package + semver | — |
| **L4** L3 + REST API with OpenAPI + client SDKs | — |
| **L5** L4 + webhook subscriptions + event bus + plugin architecture | — |

**Duecare current: L3.5** (17 PyPI packages semver-tagged from v0.1.0; FastAPI server with OpenAPI 3 schema published at `docs/openapi.yaml`; thin clients in `examples/embedding/` for React, vanilla JS, Telegram, Messenger, WhatsApp Cloud API; reaching full L4 needs typed-client SDKs in pip + npm). Target: **L4** by hackathon submission (2026-05-18).

## Rubric 7: UI / UX

| Level | What it looks like |
|---|---|
| **L1** Functional, no design | — |
| **L2** Consistent design tokens, basic responsive | — |
| **L3** L2 + accessible (WCAG 2.1 AA) + keyboard-navigable + i18n-ready | — |
| **L4** L3 + user-tested with target audience + measured task-completion rate | — |
| **L5** L4 + offline-first PWA + screen-reader audited + multi-language ships | — |

**Duecare current chat playground: L2** (mobile-responsive + tap targets ≥44px). Target: **L3**.

**Duecare current Android app: L1** (4-tab placeholder skeleton). Target: **L3** by v1 MVP.

- **Gap:** no axe-core accessibility scan run; no user testing yet; only English ships.
- **Next:** run `axe-core-cli` against the chat HTML; add Tagalog + Indonesian + Nepali + Bengali strings to Android `res/values-*/strings.xml`.

## Rubric 8: Extensibility

| Level | What it looks like |
|---|---|
| **L1** Hard-coded values | — |
| **L2** Config files | — |
| **L3** Plugin architecture (load modules at runtime) | — |
| **L4** L3 + UI-driven extension (add rules/docs/tools without writing code) | — |
| **L5** L4 + community marketplace + signed extensions + auto-updates | — |

**Duecare current: L4**. The chat UI lets users add custom GREP rules, RAG docs, tool entries, fee labels, NGO entries via the Persona/GREP/RAG/Tools modals; extensions persist in `localStorage` and ship per-message via `toggles.custom_*`.

- **Gap:** no shareable bundle format yet — users can export/import their own JSON but there's no community-curated registry.
- **Next:** define a `duecare-extension-pack-v1` JSON schema; build a signing scheme so an NGO can publish a pack of corridor-specific GREP rules other workers can trust.

## Rubric 9: Community + maintenance + currency

| Level | What it looks like |
|---|---|
| **L1** Single maintainer, no process | — |
| **L2** Issue tracker + accepts PRs | — |
| **L3** L2 + Code of Conduct + Contributor's Guide + good-first-issue label | — |
| **L4** L3 + scheduled rule/RAG updates (laws change) + rule provenance audit + dataset version pinning | — |
| **L5** L4 + multiple maintainers + governance doc + paid stewardship | — |

**Duecare current: L3**. CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md present.

- **Gap:** no scheduled refresh process for the 26 RAG docs (laws change — kafala 2024 update, new POEA MCs every year). No process for verifying GREP citations stay accurate.
- **Next:** add a `docs/data_currency.md` listing each RAG doc with last-verified date + statute version + a recurring quarterly check task. Add a `scripts/data_currency_audit.py` that flags docs >12mo old.

## Rubric 10: Sharing + publishing

How easily can a contributor publish a new prompt test, GREP entry,
RAG doc, tool, persona, or rubric, and have other deployments
auto-update?

| Level | What it looks like |
|---|---|
| **L1** Edit source, rebuild, redeploy | — |
| **L2** Config files in the repo, contribute via PR | — |
| **L3** Per-user overrides + JSON export/import | — |
| **L4** L3 + community-curated published bundles + version pinning | — |
| **L5** L4 + signed bundles + auto-update channel + provenance chain | — |

**Duecare current: L3** (per-user JSON export/import via the Persona modal footer). Target: **L4** by Q3 2026.

- **Gap:** no published bundle registry. NGOs can author rules but other deployments don't auto-discover.
- **Next:** publish a `duecare-extension-packs` GitHub Pages registry with a signed `index.json`; clients can opt-in to a pack via URL.

## Rubric 11: Audience-fit / accessibility breadth

How well does the project meet each defined audience?

| Audience | Current fit | Target | Gap |
|---|---|---|---|
| Worker (W) | **L2** — sideloadable APK with placeholder screens | L4 | Real screens, multi-language, on-device LiteRT inference, NGO-distribution channel |
| NGO intake (N) | **L3** — classifier dashboard + risk-vector JSON | L4 | Multi-tenant deployment patterns, batch import, case-management integration |
| Researcher (R) | **L4** — Kaggle notebooks + harness lift report + corpus coverage | L5 | Hosted live demo + replication study |
| Engineer (E) | **L4** — Devcontainer + Compose + Helm + 17 packages + CI | L5 | Mutation testing + property tests + auto-generated SDKs |
| Enterprise (I) | **L3** — Helm chart + Docker + Dockerized API doc | L4 | OpenAPI + auth + observability + Terraform |

---

## Aggregate scorecard (snapshot 2026-05-01)

| Rubric | Current | Target | Gap |
|---|---|---|---|
| 1. Code quality | L3 | L4 | Hypothesis + mutation testing |
| 2. Repo quality | L3 | L4 | Dependabot + SBOM + signed commits |
| 3. Writeup quality | L4 | L4 | (sustain) |
| 4. Impact | L1 | L2-L3 | Real NGO pilot |
| 5.W Ease-of-use (Worker) | L2 | L4 | Real screens + i18n + NGO distribution |
| 5.N Ease-of-use (NGO) | L3 | L4 | Multi-tenant + case-mgmt integration |
| 5.R Ease-of-use (Researcher) | L4 | L5 | Hosted live demo |
| 5.E Ease-of-use (Engineer) | L5 | L5 | (sustain) |
| 5.I Ease-of-use (Enterprise) | L3 | L4 | OpenAPI + auth + obs |
| 6. Ease of integration | L3 | L4 | REST + SDKs |
| 7. UI/UX (chat) | L2 | L3 | Accessibility audit + i18n |
| 7. UI/UX (Android) | L1 | L3 | Real screens (v1 MVP) |
| 8. Extensibility | L4 | L4 | (sustain) |
| 9. Community / maintenance | L3 | L4 | Quarterly data-currency audit |
| 10. Sharing / publishing | L3 | L4 | Bundle registry |
| 11.W Audience fit (Worker) | L2 | L4 | (per 5.W + 7) |
| 11.N Audience fit (NGO) | L3 | L4 | (per 5.N) |
| 11.R Audience fit (Researcher) | L4 | L5 | (per 5.R) |
| 11.E Audience fit (Engineer) | L4 | L5 | (per 1 + 6) |
| 11.I Audience fit (Enterprise) | L3 | L4 | (per 5.I) |

**Mean current: 2.95** | **Mean target: 3.95** | **Gap-to-close: ~1.0 level across the board.**

---

## What this rubric is for

1. **Self-honest planning.** No "we're great at everything" — each row names the next concrete action.
2. **Sharing with NGO partners.** A pilot conversation goes faster when we can show "here's where we're strong, here's where we're weak, here's what we'd need to fix to deploy at your scale."
3. **Quarterly re-scoring.** This doc gets a `## Snapshot YYYY-QQ` section appended each quarter; the deltas tell us if we're moving forward.
4. **Hackathon judging differentiation.** Most submissions don't honestly self-score. A submission that does signals operational maturity.

## What this rubric is NOT for

- Marketing — these scores are for internal use; the writeup uses concrete claims, not maturity levels.
- Comparing to other projects — different scopes, different priorities. Levels are project-internal.
- Replacing user research. L3 on UI/UX is meaningless if no actual workers ever opened the app. L4 requires real testing.

---

## Reproduce / re-score

```bash
# Re-score by editing this doc directly. Each cell links to a
# concrete artifact — verify the artifact exists, then move the
# level up or down honestly. Treat any L4 claim as suspicious if
# you can't point at a measurement.
python scripts/quality_scorecard_diff.py docs/quality_rubrics.md  # planned
```

The diff script is on the v1.1 roadmap — it parses this doc and
produces a JSON delta against the previous snapshot, so contributors
can see at a glance what moved.
