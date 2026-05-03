# Changelog

> All notable changes to the Duecare project. Pairs with the
> Android sibling repo's CHANGELOG at
> [`duecare-journey-android/docs/release_notes_v0.X.md`](https://github.com/TaylorAmarelTech/duecare-journey-android/blob/main/docs/).

The format follows [Keep a Changelog](https://keepachangelog.com/);
versioning follows [SemVer](https://semver.org/) per package, with
the meta `duecare-llm` package tracking the workspace lockstep.

## Unreleased

- Pending: bench-and-tune (A2) Kaggle T4×2 fine-tune run + HF Hub
  push of `Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0`
- Pending: notebook publish for #3, #4, A1, A3, A4, A5, A6 (built
  locally; gated by Kaggle daily push rate-limit)
- **NEW (2026-05-03):** Universal Grader v3.0 — replaces
  prompt-shape-coupled categories (business_framed / victim / etc.)
  with 15 cross-prompt dimensions. Multi-signal scoring beyond
  keyword matching:
  - Intent detection: 5 categories (refusal / education / referral
    / analytical / evasion) auto-derived from response text;
    dimension weights reweighted by primary intent
  - Citation cross-reference: 106-source reference corpus
    (was 26 RAG docs only) — adds 42 GREP rule citations + 7
    corridor caps + 11 ILO indicators + 4 NGO names + 16 fee labels
  - Section-number verification: catches hallucinated section
    references (e.g., `ILO C029 §99` flagged because convention
    only has 33 articles); 19 known statutes mapped
  - Semantic phrase clusters: each indicator expands to
    paraphrases/synonyms (e.g., `cannot provide` → 18 variants);
    catches semantic equivalents that pure keyword matching misses
  - Structural detection: well-organized responses (sections,
    lists, emphasis) get up to +5pp score boost
  - Per-citation source attribution (`grounded_via`)
- **NEW (2026-05-03):** A6 `duecare-grading-evaluation` notebook —
  dedicated lift regenerator. Runs N prompts × 2 conditions through
  Gemma 4, grades both with v3 grader, emits MD + JSON reports with
  provenance tuple `(model, git_sha, dataset_version)`. The
  falsifiable +56.5pp number, regenerated live from a git SHA.
- **NEW (2026-05-03):** Copy Pipeline button (Markdown / JSON) in
  the chat package's Pipeline modal — copies the full 7-card trace
  for any response into the clipboard. Useful for bug reports,
  GitHub issues, downstream tooling.
- **NEW (2026-05-03):** 13 unit tests for v3 grader functions
  (semantic clusters, section verification, citation expansion,
  structural detection, response profile, lift evaluator,
  aggregator). Test count: 23 → 36 in test_harness_behavior.py.
- Added: readiness rubric suite consolidating ~10 scattered
  status / rubric docs into 4 canonical views —
  `docs/readiness_dashboard.md` (single-screen status across every
  dimension), `docs/persona_readiness_audit.md` (happy path verified
  per persona, 13/14 ready), `docs/submission_gate_checklist.md`
  (13-phase pre-Submit verification), and
  `docs/post_submission_sustainability.md` (T+7 → T+365 plan with 8
  non-negotiable principles + decision triggers)
- Added: Android v0.9.0 (2026-05-02) doubles bundled corridors
  6 → 12 → 20; adds 5 new GREP rules (kafala-huroob-absconder,
  H2A-H2B-fee-violation, fishing-vessel-debt-confinement,
  smuggler-fee-and-coercion, domestic-work-locked-in-residence)

## v0.1.0 — Hackathon submission target (2026-05-18)

The submission window. Items below ship between commits; this is
the rolling list of what's landed as of 2026-05-02.

### Added

#### Android sibling repo
- **v0.8.0** (2026-05-02, `749fc0f`): expanded from 6 to 12
  migration corridors — added MX-US, VE-CO, GH-LB, NG-LB, SY-DE,
  UA-PL with full regulator + NGO contact data
- **v0.7.0** (2026-05-02, `b0af568`): structured Add-Fee dialog +
  auto-LegalAssessment + RefundClaim drafting + image picker for
  attachments + Clear Chat affordance + JVM unit tests for
  intel/ layer
- **v0.6.0** (2026-04-30, `e90ed51`): cloud Gemma 4 routing
  (Ollama / OpenAI-compat / HF Inference) + 6 on-device variants
  with mirror-fallback URLs + intel domain knowledge layer
  (11 GREP rules + 11 ILO indicators + 6 corridor profiles) +
  Reports tab with NGO intake doc generator + guided intake
  wizard + risk auto-tagging
- **v0.5.0** (2026-04-30): Gemma 4 default + SHA-256 verify +
  custom URL + Wi-Fi awareness
- **v0.4.0** (2026-04-30): full audit pass + sideload model option
- **v0.3.x** (2026-04-30): onboarding + working chat + MediaPipe
  on-device Gemma + BETWEEN_EMPLOYERS stage
- **v0.2.0** (2026-04-30): flagship Journal screen + harm-reduction flow

#### Python harness + server
- Per-tenant token + cost meter (`metering.py`) with overridable
  cost-per-1k lookup; emits Prometheus counters
- Per-tenant rate-limit (`ratelimit.py`) — token bucket + concurrency
  cap; 429 + Retry-After
- Tenancy middleware (`tenancy.py`) — extracts tenant id from
  X-Tenant-ID / X-Forwarded-User / X-Auth-Request-User / env var
- `/metrics` endpoint with Prometheus exposition
- OpenTelemetry SDK auto-instrumentation in `duecare-llm-engine`
- Feature-flags layer (`feature_flags.py`) — YAML/JSON-driven
  with stable per-tenant bucketing
- Carbon-cost estimator (`carbon.py`) — per-inference kg CO2eq
  using energy-per-token + region grid intensity
- All new modules covered by JUnit / pytest tests

#### Containerization
- Multi-stage `Dockerfile` (multi-arch amd64+arm64, builds all
  17 wheels); cosign-signed published to ghcr.io
- `Dockerfile.dev` + `docker-compose.dev.yml` for hot-reload
  development
- `docker-compose.auth.yml` overlay with oauth2-proxy SSO
- One-command `make demo` / `make doctor` / `make backup`
- NGO-office-edge example with `setup.sh` + `add-caseworker.sh`

#### Observability
- `infra/observability/` Docker Compose stack: Prometheus + Grafana
  + Loki + OpenTelemetry Collector
- 6 SLO-anchored alert rules in `prometheus/rules.yml`
- Auto-provisioned "Duecare overview" Grafana dashboard

#### Helm chart
- HPA + PodDisruptionBudget + NetworkPolicy + ServiceMonitor templates

#### Documentation
- 12 persona walkthroughs in `docs/scenarios/` (OFW / caseworker /
  NGO director / lawyer / regulator / compliance officer /
  researcher / IT director / chief architect / VP engineering /
  enterprise pilot CTO + scenarios index)
- 5 ADRs in `docs/adr/` (multi-package PyPI split / folder-per-module
  / on-device default / 6+5 notebook shape / tenant id from edge proxy)
- `docs/considerations/` enterprise governance set: enterprise
  readiness gap analysis + runbook + SLO + multi-tenancy + threat
  model + compliance crosswalk + vendor questionnaire + capacity
  planning
- `docs/comparison_to_alternatives.md` — honest matrix vs
  Big Tech APIs / T&S vendors / Llama Guard / NeMo / in-house
- `docs/press_kit.md` — one-pager + quotes + story angles for
  journalists
- `docs/educator_resources.md` — drop-in lesson plans for AI
  ethics / social work / migration studies / law school / NGO
  capacity-building
- `docs/try_in_2_minutes.md` — per-persona ultra-quickstart
- `docs/first_deployer_feedback.md` — structured intake template
- `docs/FAQ.md` — common questions
- `docs/gemma4_model_guide.md` — variant picker
- `docs/deployment_topologies.md` — 5-topology selector
- `docs/containers.md` — surface-by-surface guide
- `docs/cloud_deployment.md` — 13-platform cookbook
- `docs/scenarios/caseworker_workflow.md` — 45-min intake
  walkthrough
- `docs/scenarios/ngo-office-deployment.md` — 90-min office setup

#### Submission
- Six core + five appendix Kaggle notebooks (`kaggle/`); index in
  `kaggle/_INDEX.md`
- Writeup at `docs/writeup_draft.md`
- Video script at `docs/video_script.md`
- Reproducibility provenance in `RESULTS.md` + `docs/harness_lift_report.md`
  (207 prompts, +56.5 pp mean lift, 100% of prompts helped)
- Rubric evaluation per component in `docs/rubric_evaluation_v07.md`

### Changed

- Default model everywhere is now `gemma4:e2b` (was `gemma2:2b`
  in early Docker compose / Android v0.5)
- Notebook table TBD markers replaced with "publish pending"
  wording across `docs/FOR_JUDGES.md` + `kaggle/README.md`
- Top-level README leads with `make demo` + persona-table
  navigation
- Enterprise governance docs moved to `docs/considerations/`
  subdirectory to keep top-level `docs/` focused

### Removed

- Android: `LiteRTGemmaEngine.kt` (unused stub) and
  `ComplaintPacketExporter.kt` (superseded by NgoReportBuilder)
- The "Complaint" placeholder Android tab (replaced by Reports)

### Fixed

- ReportsViewModel race: re-reads DAOs at generate time instead of
  using lagging StateFlow snapshot
- AdviceViewModel race: synchronous append instead of viewModelScope.launch
- Onboarding scroll bug (v0.3.1): rebuilt with LazyColumn + sticky
  footer
- Compile errors in v0.7 first push: ExposedDropdownMenu vs
  DropdownMenu in Material3 1.2

## v0.0.1 (early — pre-versioned)

The 21K-test LLM Safety Testing Ecosystem benchmark that became the
basis for Duecare. Pre-2026; lives in `_reference/` and is not
part of the public submission.

---

## How to read this changelog

- **Hackathon submission**: everything under "v0.1.0" + "Unreleased"
- **Production stability**: when v1.0.0 ships post-hackathon, the
  changelog will switch to per-package versioning per SemVer
- **Reproducibility**: each entry references a SHA you can `git
  checkout` to reproduce the exact state described
