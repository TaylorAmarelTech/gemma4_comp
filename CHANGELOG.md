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
- **NEW (2026-05-04 PM):** v3.5 R2 hardening — second-round
  adversarial review (4 parallel agents on PII, kernel.py,
  concurrency, det-grader edges) found 3 critical bugs the first
  round missed:
  - **🚨 GAMING ATTACK defense.** A response that consisted only of
    rubric pass_indicators glued together — `"ILO C029 §1 ILO
    C181 Art. 7 POEA MC 14-2017 BP2MI Reg debt bondage withholding
    of wages substance over form regardless of label"` — scored
    93–100% on the universal grader (exactly the failure mode the
    rubric is supposed to defend against). Now capped at 60% with
    `gaming_flagged=true` and `gaming_penalty_pp` surfaced when
    response is < 200 chars OR lacks sentence-break / markdown
    structure.
  - **🚨 PERF: 50KB response took 11 minutes to grade.**
    `_normalized_edit_distance` was the dominant hot path (56K
    calls per grade, pure-Python DP). Fix: short-string Levenshtein
    DP (≤32 chars, fast) + `difflib.SequenceMatcher` for longer
    strings + length-delta fast-fail (skip DP if `abs(la-lb)/max
    > 20%`) + trigram-Jaccard pre-filter on fuzzy (skip when tri <
    0.10) + cap `response_text` at 32KB at grader entry + cap
    haystack passed to fuzzy/trigram at 8KB. Result: 50KB in 17s
    (73× faster), 1.6KB in 3.3s, 32 chars in 43 ms.
  - **🚨 Empty needle silent free-pass.** `_multi_signal_match("",
    "anything")` returned `matched=True` because `"" in any_string`
    is always `True`. Any caller passing an empty pass_indicator
    got a free PASS. Fix: reject needles < 2 chars up front.
  - Concurrency: `gemma_call` wrapped in module-level
    `_GEMMA_LOCK` (HF `model.generate` not thread-safe; concurrent
    `/api/chat/send` + `/api/grade-deep` would corrupt CUDA state).
    `_IMAGE_STORE` LRU eviction now atomic under
    `_IMAGE_STORE_LOCK` (was TOCTOU race + iteration-during-
    mutation potential).
  - Sector inference: word-boundary regex (was naive substring →
    fired on "domestic dispute", "domestic flight").
  - PII audit: clean (no real names/addresses/phones in PII-
    sensitive scope; 3 minor labelling polish items for composite
    characters in classifier examples).
  - Kernel.py audit: 3 HIGH (unauth `/api/shutdown`, cloudflared
    process leak in 2 kernels, shutdown-race) + 10 MEDIUM noted
    for follow-up; not blocking submission since live demo runs as
    single-user. Tests 76 → 87 (11 new).
- **NEW (2026-05-04 PM):** v3.4 hardening — adversarial code review
  by 3 parallel agents (UI/XSS, regex/ReDoS, API/parser). UI + GREP
  came back clean (one minor verdict-fallback escapeHtml fix). API/
  parser had 4 HIGH + 4 MEDIUM findings, all addressed:
  - H1: NaN/Inf `judge_weight` bypassed `min/max` clamp → now
    rejected via `math.isfinite` check; defaults to 0.5
  - H2: malformed dimension dicts in `_judge_deterministic_agreement`
    raised KeyError → now uses `.get()` with isinstance guards;
    skips rows missing id/status
  - H4: `/api/grade-deep` had no payload caps → Pydantic Field
    constraints (response_text max 20k, dimensions max 20,
    judge_weight 0..1, max_new_tokens 16..2048, temperature 0..2)
  - M1: judge could hallucinate evidence quotes that didn't appear
    in the response → new `_evidence_substring_check` validates;
    `yes` verdicts with ungrounded evidence demoted to `partial`
    and flagged in UI with red banner
  - M2: parser silently coerced non-string verdicts (numbers, lists,
    null) to `uncertain` → now sets `parse_ok=False` so caller can
    flag
  - M3: parse fallback picked verdict by enum order (yes/no/partial),
    causing "no, partial citation" to return `partial` → now picks
    first verdict by character position
  - M4: unknown dimension ids in `dimensions=[...]` parameter
    silently returned `pct_score=0` → now 400 with valid id list
  - L1: judge response > 64KB caused regex slowdown → input capped
    at 64KB; evidence_quote + rationale truncated to 500 chars
  - XSS-L1 (UI): verdict fallback `${verdictLabels[d.verdict] ||
    d.verdict}` was unescaped → now `escapeHtml(d.verdict)` on
    fallback
  - 11 new tests; total 76 → 87. All pass.
- **NEW (2026-05-04 PM):** v3.3 harness expansion — 7 new GREP rules
  + 7 new RAG docs + 9 fee-camouflage labels + 9 corridor caps + 7
  NGO contacts + new `lookup_ilo_convention` tool + 2 new universal
  rubric dimensions. Diagnosed via 6 escalating-difficulty tricky
  prompts (kafala, novation, multi-convention reasoning) and closed
  every gap.
  - GREP additions (49 total, was 42): kafala safekeeping passport
    fee · Lebanon kafala domestic worker · loan transferred to
    lender/employer · ILO convention specific query · novation no-
    keyword loan transfer · fishing-or-domestic-work convention
    comparison · Gulf employer + payday lender loan
  - RAG additions (33 total, was 26): Lebanon Cabinet Decree
    13166/2021 (kafala reform) · Kuwait Decree 19/2018 (DW
    protections) · ILO C188 (Work in Fishing 2007) · ILO C181 (no
    fees from workers) · POEA complaint procedure RA 8042 §10 +
    §11 · ILO Forced Labour Protocol P029 (2014) · UN Smuggling-
    of-Migrants Protocol
  - Fee camouflage (25 total, was 16): safekeeping fee · guarantee
    fee · passport fee · loan transfer fee · loan novation fee ·
    documentation fee · skills test fee · orientation fee ·
    stamping fee
  - Corridor caps (16 total, was 7): PH→Saudi · PH→Kuwait ·
    PH→Lebanon · PH→UAE · ID→Saudi · ID→Lebanon · LK→Lebanon ·
    BD→Saudi · BD→Kuwait
  - NGO intake (12 total, was 4): PH+Saudi · PH+Kuwait · PH+Lebanon
    · ID+Saudi · ID+Lebanon · LK+Lebanon · BD+Saudi · BD+Kuwait
  - New tool: `lookup_ilo_convention(number)` — returns year,
    title, key articles, focus, ratification context. Auto-fires
    when prompt mentions "C0XX" / "Convention 0XX" / "ILO 189".
  - Dispatcher: now fires `lookup_corridor_fee_cap` +
    `lookup_ngo_intake` when EITHER side of a corridor is named
    (was: required both)
  - Universal rubric: 17 dimensions now (was 15). New:
    `procedural_pathway` (concrete file-at-X-under-§Y vs vague
    "consult an authority") and `convention_specific_article`
    (cites Art. 9, not just C189). Tightened
    `multi_jurisdiction_coverage` applicability — fires on country
    names + cross-border verbs, not generic "from/to" noise.
  - 22 new tests; total 54 → 76. All pass.
- **NEW (2026-05-04):** LLM-as-judge grader (v1.0) — sends the
  response back to the loaded Gemma with one focused yes/no
  question per rubric dimension. Complements the deterministic
  multi-signal v3.1 grader for cases where keyword/cluster/fuzzy/
  trigram all fall short — paraphrased citations, implicit
  refusals, semantic substance the lexical grader can't see.
  - Two new endpoints: `/api/grade-deep` (LLM judge only) and
    `/api/grade-combined` (50/50 blend of deterministic + judge,
    with disagreement panel highlighting dimensions where the two
    graders see different evidence)
  - 15 dimension-specific yes/no questions in `JUDGE_QUESTIONS`,
    each requiring an evidence quote pulled from the response —
    no hallucinated support
  - Strict JSON envelope parsing with three fallback layers
    (fenced JSON, embedded JSON, scanned-keyword) so a model that
    drifts from the format still produces a verdict
  - Skips `NOT_APPLICABLE` dimensions to save model calls
  - 11 new unit tests (all pass with mock model_call)
  - UI: 4 grader modes now (Universal / Expert / Deep / Combined)
- **FIXED (2026-05-04):** GREP rules `usury_pattern_high_apr` and
  `fishing_vessel_debt_confinement` had regex bugs that made
  their primary test cases not fire. Usury now matches `68% APR`
  (was requiring `year/annum/annual` after the percentage);
  fishing-vessel matches `cannot leave to go ashore` and `keep us
  at sea` (was requiring literal `cannot to leave`). Tests pass
  54/54.
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
