# Frequently Asked Questions

Quick answers for reviewers, Kaggle users, NGOs, platform teams, researchers,
and developers. For exact metrics, use a dated artifact and verification
command from [Reproducibility](reproducibility.md).

## What This Is

### Q: In one sentence, what does DueCare do?

DueCare is an open-source Gemma 4 safety ecosystem that helps local or
tenant-controlled deployments review recruitment-risk evidence, draft grounded
next steps, and share only reviewed anonymized intelligence.

### Q: Is this a chatbot, an app, a library, or a platform?

It is a component ecosystem:

- Kaggle workbench and live-demo kernels for judges and reviewers.
- Workbench pages for chat, Bulk File Review, Knowledge Extraction, Search,
  Templates, and Anonymization & Sharing.
- Python package surfaces for embedding the harness in other systems.
- Public hub and GitHub Pages docs for onboarding, APIs, and knowledge-sharing
  architecture.
- A-00 and optional benchmark surfaces for reproducible evaluation.

### Q: Who is it for?

The public lanes are exactly:

1. Platform safety
2. NGO & regulator
3. Individual worker / mobile
4. Researcher
5. Anonymized knowledge sharing
6. Developer / integration partner

Start with [User Paths](user_paths.md) to choose the right route.

## Privacy And Safety

### Q: Does my data leave my machine?

Raw worker chats, private case files, IDs, phone numbers, passports, and
personal narratives should stay in the local Kaggle session, worker device,
trusted NGO machine, or tenant-owned deployment. Sharing is a separate step:
only reviewed, redacted fact objects, aggregate signals, pack proposals,
benchmark rows, or hash receipts should move to the public hub.

If an operator configures a cloud model or hosted integration, that deployment
must document its own data path and consent boundary.

### Q: Can the maintainer see my prompts?

Not from a local, Kaggle, or tenant-controlled deployment. The maintainer can
only see material that someone submits to a public DueCare service, GitHub,
Kaggle, email, or another hosted endpoint. Do not submit raw private case data
to the public hub.

### Q: Is DueCare certified for SOC 2, HIPAA, GDPR, or FedRAMP?

No. DueCare is open-source software and documentation. A specific deployment
may be designed to support an organization's audit or compliance process, but
the project itself is not certified.

### Q: Is DueCare an emergency service?

No. DueCare can organize information and surface relevant public resources,
but emergency support, legal advice, investigation, and enforcement require
qualified people and institutions.

## Trying It

### Q: What is the fastest way to try it?

Use the active Kaggle kernels:

- [DueCare App](https://www.kaggle.com/code/taylorsamarel/duecare-app)
- [DueCare Live Demo](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)
- [A-00 proof path](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation)

Copy the active `kernel.py`, use **GPU T4 x2** and **Internet: On**, attach
`google/gemma-4`, then run the notebook. Startup time varies by Kaggle worker,
package install path, model cache state, model variant, and Cloudflare quick
tunnel availability.

### Q: Can it run without a model attached?

Yes for many demo and inspection paths. Heuristic-only mode can serve the start
page, slides, deterministic GREP/RAG/tools paths, sample flows, and cached
recording slots. Live chat and optional Gemma graph/edge passes need a model.

### Q: Can I install it locally?

Use [Install](install.md), [Local Deployment](deployment_local.md), and the
[Embedding Guide](embedding_guide.md). Treat the Kaggle kernels as the primary
judge-safe path during active judging.

## What It Does And Does Not Do

### Q: Does DueCare detect trafficking?

It surfaces exploitation and recruitment-risk patterns associated with
trafficking. It does not confirm a trafficking case. Confirmation requires
investigation, context, and qualified human judgment.

### Q: Does DueCare replace lawyers, NGOs, caseworkers, or regulators?

No. It drafts, explains, extracts, checks, and organizes. A trusted person or
institution decides what to do.

### Q: Does it cover every country or corridor?

No. Corridor and policy coverage is versioned knowledge, not a blanket claim.
Use the current corpus manifest or runtime self-audit before naming exact
coverage.

### Q: Can it read documents and images?

The workbench can organize document bundles and queue/extract text or media
evidence depending on the runtime path. Public claims should distinguish
deterministic extraction, queued OCR/vision work, and optional Gemma passes.

## Research And Claims

### Q: Can I cite DueCare?

Yes. Use [Researcher Analysis](scenarios/researcher-analysis.md),
[Reproducibility](reproducibility.md), and the repository citation metadata.
When citing metrics, include the git SHA, dataset/export, model revision, and
verification command.

### Q: Are the headline lift numbers production guarantees?

No. Treat them as dated smoke/proxy evaluation artifacts unless a current
weeks-long or field deployment artifact proves otherwise.

### Q: How do I audit public claims?

Run:

```bash
python scripts/validate_public_surface.py
python scripts/validate_main_kaggle_kernels.py
python scripts/validate_kaggle_page_sources.py
python -m pytest packages --collect-only -q
```

Then read [Reproducibility](reproducibility.md) for the artifact policy.

## Deployment And Integration

### Q: I am an NGO or regulator. Where should I start?

Read [Caseworker Workflow](scenarios/caseworker_workflow.md),
[NGO Office Deployment](scenarios/ngo-office-deployment.md), and
[Regulator Pattern Analysis](scenarios/regulator-pattern-analysis.md).

### Q: I am a platform team. Where should I start?

Read [Enterprise Pilot](scenarios/enterprise_pilot.md) and
[Platform / On-Prem Deployment](deployment_enterprise.md).

### Q: I am a developer or integrator. Where should I start?

Read [Install](install.md), [Embedding Guide](embedding_guide.md), and the
[OpenAPI spec](openapi.yaml).

### Q: I am interested in anonymized knowledge sharing. Where should I start?

Read [Information Sharing Architecture](information_sharing_architecture.md),
[Anonymization Policy](anonymization_policy.md), and
[Submission Labeling Policy](submission_labeling_policy.md).

## Other

### Q: Is this affiliated with Google?

No. It is an independent open-source project built for the Google Gemma 4 Good
Hackathon and uses Gemma 4 as a model layer.

### Q: Where are the public URLs?

- Main server website / public hub: <https://duecare-ai.com/>
- GitHub Pages docs: <https://tayloramareltech.github.io/gemma4_comp/>
- Source code: <https://github.com/TaylorAmarelTech/gemma4_comp>

### Q: I have a question that is not here.

File an issue at <https://github.com/TaylorAmarelTech/gemma4_comp/issues> or
email `amarel.taylor.s [at] gmail.com` with subject `[duecare question]`.
