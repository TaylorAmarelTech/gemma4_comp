# Appendices — deeper enclosures linked from the writeup

> The [writeup](../writeup_draft.md) stays tight at 1,500 words.
> This index is the entry point for everything that didn't fit but
> matters for readers who want to go deeper.
>
> **Reading order suggestion:** start with the writeup → bird's-eye
> [system map](../system_map.md) → [author's notes](../authors_notes.md)
> for the why → then dive into specific appendices below.

## How to use this index

Each appendix is a self-contained doc that elaborates one slice of
the writeup. None require reading the others; pick what's relevant.

Most appendices are existing docs the writeup links to indirectly.
A few are new documents created specifically as appendices for the
submission.

## A. Methodology + corpus

| # | Appendix | What it covers |
|---|---|---|
| A1 | [Harness lift report](../harness_lift_report.md) | Full +56.5pp / +87.5pp / +51.2pp / +34.1pp methodology + 4 appendices (refusal rate, layer ablation, fabrication detection) |
| A2 | [Prompt schema](../prompt_schema.md) | Full data shape + vocabulary for the 394 example prompts |
| A3 | [Corpus coverage matrix](../corpus_coverage.md) | 2D coverage heatmaps across category × sector × corridor × difficulty × ILO |
| A4 | [Contributing prompts guide](../contributing_prompts.md) | 5-step add-path + style guide for new evaluation prompts |
| A5 | [Quality rubrics](../quality_rubrics.md) | The 5-tier scoring system + the 6 required-rubric categories with 66 criteria |
| A6 | [Corpus stats](../corpus_stats.md) | Auto-generated statistics: difficulty distribution, ILO indicator coverage, etc. |

## B. The harness internals

| # | Appendix | What it covers |
|---|---|---|
| B1 | [Architecture](../architecture.md) | The 17-package PyPI workspace + 4-layer harness mechanics + 4-phase execution arc |
| B2 | [Embedding guide](../embedding_guide.md) | Embed the harness in your own product (OpenAPI + JS widget + AAR plan) |
| B3 | [Extension pack format](../extension_pack_format.md) | Build + sign your own GREP/RAG packs (Ed25519-signed) |
| B4 | [Notebook guide](../notebook_guide.md) | How the 6+5 notebook shape was decided + per-notebook context |

## C. Deployment + operations

| # | Appendix | What it covers |
|---|---|---|
| C1 | [Deployment topologies](../deployment_topologies.md) | Master selector across 5 topologies (on-device / NGO-edge / cloud single / cloud multi / hybrid) |
| C2 | [Cloud deployment](../cloud_deployment.md) | 13-platform cookbook (AWS / GCP / Azure / Render / HF / Fly / Railway / Modal / RunPod / Lambda / Vast / SaladCloud / Civo) |
| C3 | [Local install](../deployment_local.md) | One-command laptop bring-up via Docker compose |
| C4 | [Enterprise deployment](../deployment_enterprise.md) | Production-grade patterns (Helm + observability + multi-tenancy) |
| C5 | [Containers guide](../containers.md) | Surface-by-surface container patterns |
| C6 | [Operations](../operations.md) | Day-2 ops + alerting + scaling |

## D. Personas + user requirements

| # | Appendix | What it covers |
|---|---|---|
| D1 | [Persona scenarios index](../scenarios/README.md) | All 14 personas in one navigation page |
| D2 | [Persona readiness audit](../persona_readiness_audit.md) | Per-persona happy-path verification across 6 dimensions |
| D3 | [Maria's case end-to-end](../marias_case_end_to_end.md) | Composite case spanning 365 days through 8 personas |
| D4 | [Try in 2 minutes](../try_in_2_minutes.md) | Per-persona ultra-quickstart |
| D5 | [Scenario translations index](../scenarios/translations/) | Tagalog + Spanish drafts of worker-self-help (native review pending) |

## E. Governance + enterprise considerations

| # | Appendix | What it covers |
|---|---|---|
| E1 | [Enterprise readiness](../considerations/enterprise_readiness.md) | CTO gap analysis + remediation plan |
| E2 | [Threat model](../considerations/THREAT_MODEL.md) | STRIDE breakdown across 4 trust boundaries |
| E3 | [Compliance crosswalk](../considerations/COMPLIANCE.md) | GDPR / SOC2 / ISO 27001 mapping |
| E4 | [Multi-tenancy](../considerations/multi_tenancy.md) | Tenant isolation model + bypass tests |
| E5 | [SLO](../considerations/SLO.md) | Service-level objectives + error budgets |
| E6 | [Runbook](../considerations/runbook.md) | Incident → recovery → post-mortem |
| E7 | [Vendor questionnaire](../considerations/vendor_questionnaire.md) | Standard procurement Q&A |
| E8 | [Capacity planning](../considerations/capacity_planning.md) | Sizing per topology |

## F. Decision records (ADRs)

| # | Appendix | What it covers |
|---|---|---|
| F1 | [ADR index](../adr/README.md) | All 5 architecture decisions with rationale |
| F2 | [ADR-001 Multi-package PyPI split](../adr/001-multi-package-pypi-split.md) | Why 17 packages instead of 1 monolith |
| F3 | [ADR-002 Folder-per-module](../adr/002-folder-per-module-pattern.md) | Self-describing module convention |
| F4 | [ADR-003 On-device default](../adr/003-on-device-default-cloud-opt-in.md) | Privacy-first defaults |
| F5 | [ADR-004 6+5 notebook shape](../adr/004-six-plus-five-notebook-shape.md) | Submission surface design |
| F6 | [ADR-005 Tenant from edge proxy](../adr/005-tenant-id-from-edge-proxy.md) | Multi-tenant header strategy |

## G. Outreach + adoption

| # | Appendix | What it covers |
|---|---|---|
| G1 | [Press kit](../press_kit.md) | One-pager + facts + 6 story angles + founder bio |
| G2 | [Comparison vs alternatives](../comparison_to_alternatives.md) | Honest matrix vs Azure / OpenAI / Hive / Sift / Llama Guard / NeMo / in-house |
| G3 | [Educator resources](../educator_resources.md) | Drop-in lesson plans (1-hour to 2-week) for AI ethics / social work / migration / law / NGO capacity-building |
| G4 | [FAQ](../FAQ.md) | Common questions answered |
| G5 | [Prior art](../prior_art.md) | Adjacent projects + how Duecare differs |
| G6 | [First-deployer feedback intake](../first_deployer_feedback.md) | Structured template for early deployers |

## H. Submission + sustainability

| # | Appendix | What it covers |
|---|---|---|
| H1 | [For judges](../FOR_JUDGES.md) | The hackathon-judge entry point + 2-min and 5-min verification paths |
| H2 | [Readiness dashboard](../readiness_dashboard.md) | Single-screen status across every dimension |
| H3 | [Submission gate checklist](../submission_gate_checklist.md) | 13-phase pre-Submit verification |
| H4 | [Post-submission sustainability](../post_submission_sustainability.md) | T+7 → T+365 plan with 8 non-negotiable principles |
| H5 | [2-week submission plan](../two_week_submission_plan.md) | T-16 to T-0 day-by-day |
| H6 | [Notebook QA companion](../notebook_qa_companion.md) | Per-notebook test checklist for all 11 |
| H7 | [Bench-and-tune readiness](../bench_and_tune_readiness.md) | A2 fine-tune pre-flight + run-time monitoring + post-run verification |
| H8 | [Cross-NGO trends federation](../cross_ngo_trends_federation.md) | Privacy-preserving aggregation protocol design |
| H9 | [Smoke test report 2026-05-02](../smoke_test_report_2026-05-02.md) | 24 categories tested, all pass, 5 fixes applied |

## I. Author voice

| # | Appendix | What it covers |
|---|---|---|
| I1 | [Author's notes](../authors_notes.md) | Informal observations, what didn't work, design judgments, limitations, things I wanted to ship but didn't |
| I2 | [System map](../system_map.md) | Bird's-eye view of every component, user, deployment in Mermaid |
| I3 | [Interactive system map (HTML)](../system_map.html) | Same map but clickable + filterable |

---

## What's NOT in this appendix index

- Module-level meta files (PURPOSE.md / AGENTS.md / etc.) — these are
  per-module and not meant for end-readers; see [folder-per-module
  ADR](../adr/002-folder-per-module-pattern.md)
- Auto-generated current state (`docs/current_kaggle_notebook_state.md`)
  — this is operational, not narrative
- Internal `.claude/rules/*.md` — these guide AI assistant behavior
  and live outside the docs site

If something feels missing, file an issue at
[`github.com/TaylorAmarelTech/gemma4_comp/issues`](https://github.com/TaylorAmarelTech/gemma4_comp/issues)
with the `docs` label.
