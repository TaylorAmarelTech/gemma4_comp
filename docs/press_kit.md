# Press Kit

Materials for journalists, NGO communications staff, researchers, and
reviewers writing about DueCare. Attribution: "DueCare project,
MIT-licensed, github.com/TaylorAmarelTech/gemma4_comp".

## One-Paragraph Summary

DueCare is an open-source Gemma 4 safety ecosystem for migrant-worker
protection. It helps platform teams, NGOs, regulators, worker-support
deployments, researchers, anonymized knowledge-sharing workflows, and
developers review recruitment-risk evidence with clearer trust boundaries.
Sensitive material can be processed in a local, Kaggle, tenant-owned, or
trusted deployment. Shared intelligence should be limited to reviewed,
redacted fact objects, aggregate signals, benchmark rows, pack metadata, and
hash receipts rather than raw worker chats, private case files, IDs, phone
numbers, or personal narratives.

## One-Line Summary

DueCare uses Gemma 4, deterministic safety layers, knowledge packs,
anonymization gates, and reproducible benchmarks to support anti-trafficking
work without centralizing raw case data.

## Key Facts

| | |
|---|---|
| Project name | DueCare |
| License | MIT |
| Maintainer | Taylor Amarel ([github.com/TaylorAmarelTech](https://github.com/TaylorAmarelTech)) |
| Submitted to | Google Gemma 4 Good Hackathon, Safety & Trust track |
| Built on | Gemma 4 plus deterministic harness layers, retrieval, tools, redaction, and validation scripts |
| Main public hub | [duecare-ai.com](https://duecare-ai.com/) |
| GitHub Pages docs | [tayloramareltech.github.io/gemma4_comp](https://tayloramareltech.github.io/gemma4_comp/) |
| Source code | [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp) |
| Kaggle path | 01 workbench, 02 live demo, A-00 proof path; optional 03/04 benchmark surfaces |

## Six Public Lanes

| Lane | What DueCare supports |
|---|---|
| Platform safety | Screening risky recruitment posts, ads, profiles, and messages before harm spreads. |
| NGO & regulator | Case review, cited drafts, routing, document review, and regulator pattern analysis. |
| Individual worker / mobile | Private worker-support guidance and worker-controlled next steps. |
| Researcher | Reproducible prompts, benchmarks, model comparisons, and evidence review. |
| Anonymized knowledge sharing | Reviewed redacted fact objects, evidence edges, aggregate risk signals, and pack proposals. |
| Developer / integration partner | Packages, APIs, schemas, examples, and deployment patterns for embedding DueCare elsewhere. |

## What The Project Demonstrates

DueCare is not a single chatbot. It is a component ecosystem:

- workbench pages for chat, Bulk File Review, Knowledge Extraction, Search,
  Templates, and Anonymization & Sharing;
- deterministic safety layers for GREP rules, retrieval, tools, citations,
  imports, online-search checks, and evaluation;
- hierarchy-aware document review that can create evidence at folder,
  document, page, paragraph/chunk, table-row, media, person, case, and
  cross-case levels;
- redaction and labeling workflows that separate local evidence from
  shareable intelligence;
- A-00 and optional benchmark surfaces for reproducible evaluation and model
  improvement.

## Evidence And Metrics

Use dated, reproducible artifacts for metrics. Do not copy old benchmark,
rubric, corpus, or test-count numbers into public copy unless the command,
git SHA, dataset/export, and model revision are cited beside the number.

Recommended verification sources:

- [`docs/reproducibility.md`](./reproducibility.md)
- [`docs/harness_lift_report.md`](./harness_lift_report.md)
- [`docs/FOR_PEER_REVIEW.md`](./FOR_PEER_REVIEW.md)
- `python scripts/validate_public_surface.py`
- `python scripts/validate_main_kaggle_kernels.py`
- `python scripts/validate_kaggle_page_sources.py`
- `python -m pytest packages --collect-only -q`

Current public wording should say "smoke/proxy evaluation", "dated artifact",
or "runtime self-audit" when a result has not been proven by weeks-long local
Gemma operation, production traffic, or field deployment.

## Quotable Framing

> "The point is not to centralize vulnerable workers' records. The point is to
> let many trusted local nodes learn from reviewed, anonymized intelligence
> while raw evidence stays under local control."

> "Gemma 4 is valuable here because it can help local deployments reason,
> extract, summarize, and evaluate evidence. The safety comes from the
> ecosystem around the model: rules, retrieval, provenance, redaction, human
> review, and reproducible checks."

## What Not To Claim

- Do not claim DueCare prevents trafficking by itself. It supports people and
  institutions that do prevention, assistance, investigation, and research.
- Do not claim DueCare detects trafficking with high accuracy. It surfaces
  risk patterns; confirmed cases require investigation.
- Do not claim DueCare replaces lawyers, caseworkers, NGOs, regulators, or
  emergency services.
- Do not claim government endorsement, certification, SOC 2/HIPAA/GDPR
  certification, production reliability, or weeks-long local Gemma reliability
  unless a current artifact proves it.
- Do not imply raw worker files, private chats, IDs, phone numbers, passports,
  or personal narratives should be uploaded to the public hub.
- Do not reuse exact historical counts as current facts unless they are
  remeasured from the current repo and cited with the verification command.

## Links

| | |
|---|---|
| Main server website / public hub | https://duecare-ai.com/ |
| GitHub Pages docs | https://tayloramareltech.github.io/gemma4_comp/ |
| Source code | https://github.com/TaylorAmarelTech/gemma4_comp |
| Kaggle workbench | https://www.kaggle.com/code/taylorsamarel/duecare-app |
| Kaggle live demo | https://www.kaggle.com/code/taylorsamarel/duecare-live-demo |
| Kaggle proof path | https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation |
| Hackathon | https://www.kaggle.com/competitions/gemma-4-good-hackathon |

## Press Contact

amarel.taylor.s [at] gmail.com

Subject line: `[duecare press]`
