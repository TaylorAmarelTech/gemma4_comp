# Frequently asked questions

> Quick answers to the questions that come up over and over.
> If your question isn't here, file an issue or check
> [`docs/scenarios/`](./scenarios/) for the persona-specific
> walkthrough that probably answers it in context.

## What this is

### Q: In one sentence, what does Duecare do?

It's an AI safety harness around Google Gemma 4 that helps migrant
workers, NGOs, and regulators recognize recruitment fraud and
trafficking patterns — running locally with no data sent anywhere.

### Q: Is this a chatbot? An app? A library? A platform?

Yes. It's all of those, packaged together:
- A chat playground (Kaggle notebook + a FastAPI server)
- A worker-facing Android app (Duecare Journey)
- 17 PyPI packages you can `pip install` independently
- A Helm chart + Docker images for deploying at scale
- A research benchmark (207 hand-graded prompts + a published rubric)

The shape you interact with depends on your role —
[`docs/scenarios/`](./scenarios/) has the persona-specific entry point.

### Q: Who is this for?

11 documented personas, from migrant workers using the Android app
to Big Tech CTOs running an enterprise pilot. The
[scenarios index](./scenarios/README.md) lists them all.

## Cost + licensing

### Q: How much does it cost?

Zero in license fees (MIT). Hardware/cloud costs depend on
deployment shape:
- Solo on a laptop: $0
- NGO on a Mac mini: $250-800 one-time
- Small cloud server: $25-100/mo
- National-scale regulator: $1,500-10k/mo

See [`docs/considerations/capacity_planning.md`](./considerations/capacity_planning.md)
for sizing tables.

### Q: Are there hidden costs?

Two:
1. **Optional cloud-LLM fallback** — if you point Duecare at a
   commercial Gemma endpoint (HF Inference, OpenAI-compatible
   service), you pay the provider's per-token rate. Cap with the
   per-tenant token budget in `metering.py`.
2. **Optional internet search** — Tavily/Brave/Serper free tiers
   give 1k-2.5k queries/mo; above that, paid plans apply.

Both are off by default.

### Q: What's the license?

MIT for the project. Apache 2.0 for the Gemma 4 model itself
(via the Google `litert-community` repos). Each of the 17 PyPI
packages declares MIT in its `pyproject.toml`.

### Q: Can I use it commercially?

Yes. MIT permits commercial use. Attribution is required only
when you redistribute the source.

## Privacy + security

### Q: Does my data leave my machine?

By default: only the one-time AI model download. No telemetry,
no analytics, no phone-home.

If you opt in (Settings → Cloud model in Android, or env vars on
the server), each chat goes to your configured cloud endpoint.
The maintainers don't operate any service the data passes through.

### Q: Can the maintainer see my prompts?

No. There's no Duecare cloud service. The maintainer has no
ability to see what you do with the software. (This is enforced
by the absence of any maintainer-operated infrastructure, not by
a privacy policy.)

### Q: Is the journal encrypted?

On Android: yes, SQLCipher with the key in Android Keystore. On
the server: encryption is your responsibility — Postgres TDE, RDS
encryption, GCP CMEK, Azure Key Vault, etc.

### Q: What happens if my phone is stolen?

The journal is encrypted at rest. To read it, an attacker needs:
1. To unlock the phone (or bypass the lock screen)
2. To retrieve the SQLCipher key from Android Keystore (requires
   a rooted phone + significant skill)

For a higher threat model, set up a quick-launch shortcut to the
**Settings → Panic wipe** action (one tap erases everything).

### Q: What if the recruiter forces me to unlock my phone?

Use the panic wipe primitive. The recruiter sees you tap one
button; the data is gone. Re-install the APK later when safe.

The app's icon is intentionally generic ("Duecare Journey" with a
blue book) — it doesn't say "anti-trafficking" anywhere on the
home screen.

### Q: Are you SOC 2 / GDPR / HIPAA / FedRAMP certified?

No. The *deployment can support* such certifications — see
[`docs/considerations/COMPLIANCE.md`](./considerations/COMPLIANCE.md) —
but the open-source project itself isn't certified. Your
auditor's review is on you.

## Comparison + alternatives

### Q: Why not just use Azure Content Safety / OpenAI Moderation / Hive / Sift?

[`docs/comparison_to_alternatives.md`](./comparison_to_alternatives.md)
is the honest matrix. Short answer:
- For generic content moderation (CSAM / hate speech / spam),
  use a commercial API
- For trafficking-specific use cases with on-prem requirements,
  Duecare is purpose-built
- For everything in between, run your own benchmark on YOUR
  domain before deciding

### Q: How does it compare to Llama Guard 3 / ShieldGemma?

Those are content-classifier models. Duecare is a content-classifier
model + a domain-grounded harness (42 GREP rules + 26 RAG docs +
20 corridor lookups + a chat surface). Use Llama Guard if you
want just a model; use Duecare if you want the full domain stack.

### Q: How does it compare to building in-house?

3-month adoption + 1.5 FTE for Duecare vs 6-18 months + 3 FTE
for in-house. See [`docs/scenarios/vp-engineering.md`](./scenarios/vp-engineering.md)
for the detailed math.

## Deployment

### Q: What's the fastest way to try it?

Open the Kaggle notebook
[duecare-chat-playground-with-grep-rag-tools](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-chat-playground-grep-rag-tools).
"Run All". Type a question. Two-minute time investment.

For the Docker stack: `git clone` + `make demo`. Five minutes.

### Q: Can I run it without Docker?

Yes — `pip install duecare-llm` installs the meta package
(all 17 wheels). See [`docs/deployment_local.md`](./deployment_local.md).

### Q: Does it need a GPU?

No. The default `gemma4:e2b` model runs on CPU. GPU helps
throughput (5x-15x RPS per pod) but isn't required.

### Q: Which cloud platforms work?

13 documented:
- Hugging Face Spaces, Render, Fly.io, Railway (quickest)
- AWS EKS / Lightsail, GCP GKE / Cloud Run, Azure AKS / Container Apps
- Self-hosted k8s, k3s, air-gapped

[`docs/cloud_deployment.md`](./cloud_deployment.md) has the per-platform recipes.

### Q: How big is the AI model?

| Variant | Size | RAM needed |
|---|---:|---:|
| gemma3:1b | 600 MB | 4 GB |
| gemma4:e2b INT4 | 750 MB | 4 GB |
| gemma4:e2b INT8 (default) | 1.5 GB | 8 GB |
| gemma4:e4b INT4 | 2 GB | 8 GB |
| gemma4:e4b INT8 | 3.5 GB | 16 GB |
| gemma4:31b | 18 GB | 32 GB + GPU |

[`docs/gemma4_model_guide.md`](./gemma4_model_guide.md) has the
detailed picker.

## What it does + doesn't do

### Q: Does it predict trafficking?

It detects exploitation patterns associated with trafficking. The
patterns map to ILO C029 indicators 1-11. Conversion to a confirmed
trafficking case requires investigation — the harness produces
evidence + draft documents, not verdicts.

### Q: Does it cover my country / corridor?

Bundled corridors as of v0.8: PH-HK, ID-HK, PH-SA, NP-SA, BD-SA,
ID-SG, MX-US, VE-CO, GH-LB, NG-LB, SY-DE, UA-PL.

For other corridors, you can add an extension pack per
[`docs/extension_pack_format.md`](./extension_pack_format.md) —
roughly 1-2 days of work per corridor for someone who knows the
local recruitment regulations.

### Q: Does it speak my language?

Chat surface: any language Gemma 4 understands (which is most
major migrant-corridor languages — Tagalog, Bahasa, Nepali, Bangla,
Arabic, Spanish, French, etc.).

UI labels: English-only as of v0.8. Translation is on the v0.9
roadmap.

### Q: Can it read photos?

The Android app v0.7+ accepts photo attachments and stores them.
**Photo OCR** (extracting text from contract / receipt photos) is
v0.9 — currently the photo is stored as evidence but not analyzed.

The harness's `Scout` agent supports multimodal input via Gemma 4's
image encoder; full integration into the chat surface is in flight.

### Q: Can it draft legal documents?

It drafts a refund-claim cover letter (the bundled refund-claim
template, populated with the controlling statute + amount + recipient).
For other document types — affidavits, complaint forms,
representation letters — your legal team customizes.

### Q: Can it represent me / my client in court?

No. It's a research + drafting tool, not a lawyer. See
[`docs/scenarios/lawyer-evidence-prep.md`](./scenarios/lawyer-evidence-prep.md)
for how legal-aid lawyers use it appropriately.

## Updates + maintenance

### Q: Who maintains this?

Single maintainer (Taylor Amarel) as of 2026. No Big Tech behind
it — the project is fully open source MIT.

### Q: What's the release cadence?

Roughly weekly during the hackathon (2026-Q2); ~monthly after.
Current versions (2026-05-02):
- Android app: v0.8.0
- Python packages: v0.1.0
- Docker image: latest = git SHA on master

### Q: How do I get notified of new releases?

Watch the GitHub repo
(https://github.com/TaylorAmarelTech/gemma4_comp). For the
Android app, watch
(https://github.com/TaylorAmarelTech/duecare-journey-android).

### Q: What if the maintainer disappears?

The image you've already pulled keeps working forever. The repo
is forkable. Your data lives on the hardware you control. No
license activation, no SaaS dependency.

### Q: How do I report a bug / contribute?

GitHub issues at https://github.com/TaylorAmarelTech/gemma4_comp/issues
for the harness; same path on the Android sibling repo for app-specific
issues. Security issues: see `SECURITY.md` for private disclosure.

## For specific use cases

### Q: I'm a researcher — can I cite this?

Yes. See [`CITATION.cff`](../CITATION.cff) or
[`docs/scenarios/researcher-analysis.md`](./scenarios/researcher-analysis.md)
for the full bibtex + reproduction instructions.

### Q: I'm a journalist — can I write about it?

Yes. [`docs/press_kit.md`](./press_kit.md) has the one-pager,
quotes, suggested story angles, and what NOT to claim.

### Q: I'm an educator — can I use it in class?

Yes. [`docs/educator_resources.md`](./educator_resources.md) has
drop-in lesson plans (1-hour to 2-week), discussion prompts, and
suggested external readings.

### Q: I'm at an NGO and want to deploy it — what's the path?

Read [`docs/scenarios/ngo-office-deployment.md`](./scenarios/ngo-office-deployment.md).
90-minute setup + day-2 / day-30 / when-broken sections. Or jump
straight to `make demo` if you're comfortable with Docker.

After you deploy, fill out
[`docs/first_deployer_feedback.md`](./first_deployer_feedback.md) —
your real-world experience shapes the next release.

### Q: I'm a migrant worker — is this safe to install?

The honest answer:
- The app icon doesn't say "anti-trafficking"
- The app doesn't ask for an account, email, or phone number
- Nothing leaves your phone unless you tap Share
- Panic-wipe erases everything in one tap
- The AI model + journal stay encrypted on your phone

[`docs/scenarios/worker-self-help.md`](./scenarios/worker-self-help.md)
has the full plain-language explanation, including "what to do if
your recruiter sees the app on your phone."

## Other

### Q: Is this affiliated with Google?

No. It's an independent open-source project that uses Google's
Gemma 4 model (which is open-weights Apache 2.0). Submitted to
Google's 2026 Gemma 4 Good Hackathon under the Safety & Trust track.

### Q: Why "Duecare"?

Named for California Civil Code §1714(a) — the duty-of-care
standard a CA jury applied in March 2026 to find Meta and Google
negligent for defective platform design. The name signals: does
the model exercise *due care* on prompts about trafficking and
exploitation?

### Q: I have a question that isn't here.

File an issue at
https://github.com/TaylorAmarelTech/gemma4_comp/issues, or email
`amarel.taylor.s [at] gmail.com` (subject: `[duecare question]`).

If the question recurs, it lands in this FAQ on the next pass.
