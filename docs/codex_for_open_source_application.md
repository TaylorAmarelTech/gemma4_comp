# Codex for Open Source - application answers (DueCare)

Draft answers for the OpenAI *Codex for Open Source* application. Every claim
here is reproducible from the public repository. Character counts are noted for
the fields that cap at 500.

## Pre-filled context

| Field | Value |
|---|---|
| First name | Taylor |
| Last name | Amarel |
| Email | amarel.taylor.s@gmail.com |
| GitHub username | TaylorAmarelTech |
| GitHub repository URL | https://github.com/TaylorAmarelTech/gemma4_comp |
| OpenAI Organization ID | *(fill from https://platform.openai.com/account/organization)* |

## Licensing & open-source status (verified)

Fully open source under the **MIT License** - the standard, maximally
permissive OSI-approved license. Confirmed:

- Root `LICENSE`: MIT, (c) 2026 Taylor Amarel.
- All **18** package `pyproject.toml` files declare `license = {text = "MIT"}`.
- Public repository, MIT throughout; public datasets on Kaggle carry their own
  open licenses (CC for grades/scores). No proprietary or "source-available"
  restrictions.

---

## Describe your role: are you a primary or core maintainer?

I am the **sole author and primary maintainer**. I wrote and maintain the
entire DueCare codebase: the 17-package `duecare-llm-*` workspace, the
cross-model harness-lift safety benchmark, the ILO forced-labour indicator
engine, the deterministic verifier, and all public datasets, notebooks, and the
FastAPI evaluation app. Every commit, release, test, and architectural decision
is mine.

## Why does this repository qualify? (<=500 chars)

> Open-source (MIT) LLM safety harness and benchmark that *measurably* improves
> model behaviour on a high-stakes, under-served domain: migrant-worker
> trafficking. A reproducible **+40.7/100** safety lift holds across **8 models
> from 6 providers** (Gemma, GPT-OSS, GLM, DeepSeek, Qwen, Mistral), backed by
> **85,417** public graded rows, an un-gameable deterministic verifier, and open
> datasets. Stars are low; the problem -- LLMs giving unsafe or unhelpful advice
> to vulnerable workers -- is not.

*(~470 chars)*

## I'm interested in...

Select **all** offered benefits -- each maps to a concrete need below:

- **ChatGPT Pro (with Codex)** -- day-to-day maintenance, PR review, refactoring.
- **Codex Security** -- continuous review of the safety-critical surface.
- **API credits** -- broader, independently-verifiable evaluation compute.

## Why does your project need Codex Security? (<=500 chars)

> DueCare processes sensitive material (worker chats, IDs, case details) and is
> meant for NGOs and regulators to run locally. Security is load-bearing: a hard
> PII-anonymization gate, a federation peer allowlist that already closed an
> SSRF hole in the knowledge-sync endpoint, and trust-boundary disclosures on
> every surface. Codex Security would give continuous review of the anonymizer,
> the outbound allowlist, and the FastAPI endpoints before NGOs deploy them.

*(~480 chars)*

## OpenAI Organization ID

*(Taylor: paste from https://platform.openai.com/account/organization -- I can't
retrieve this.)*

## How will you use API credits for your project? (<=500 chars)

> Grade the full **78,719-prompt** safety registry across every major model (the
> current sweep is bottlenecked by a self-hosted judge quota), expand the
> cross-provider leaderboard, and automate maintainer workflows: PR triage and
> review, release checks, the evals-as-CI regression gate, and regenerating
> public datasets, reports, and reproducibility notebooks. Credits convert
> directly into more, broader, independently-verifiable safety evidence.

*(~460 chars)*

## Anything else we should know? (<=500 chars)

> Though built for the Gemma 4 hackathon, the harness is **provider-neutral** --
> it drives local Gemma, Ollama, OpenAI-compatible, Anthropic, and Gemini targets
> through one interface, and the +40.7 lift reproduces across all of them. It
> targets a shortcoming *every* LLM shares: confident but unsafe or unhelpful
> answers in high-stakes human-rights situations. It isn't popular by stars or
> downloads yet -- but closing that gap is exactly the kind of safety work that
> should be.

*(~490 chars)*

---

## Supporting facts (all reproducible from the repo)

- **Provider-neutral by design.** The harness `model_targets` include local
  Gemma, Ollama, OpenAI-compatible, Anthropic, Gemini, HF endpoints, and
  frontier APIs (`packages/duecare-llm-chat/.../harnesses/base.py`). Originally a
  Gemma 4 competition entry; the abstraction applies to **all** LLMs.
- **Measured, not asserted.** Baseline vs. harnessed, judged 0-100 by a
  three-model panel (each judge from a different family, never grading its own)
  across five reasoned safety dimensions; +40.7 mean on gemma4:31b over 7,953
  paired prompts, ~99.8% improved, Cohen's d ~1.73, holds on every model tested.
- **Un-gameable corroboration.** `duecare.kit.verify` -- a deterministic,
  model-free checker -- independently confirms the lift (+1.03/5), so the result
  does not depend on any single judge model.
- **Real engineering hygiene.** 17 MIT packages, PEP 420 namespace, typed
  (Pydantic v2 / Protocols), ~1,490 tests, evals-as-CI regression gate, public
  Kaggle datasets + reproducibility notebooks, an installable `duecare-llm-kit`.
- **Serious real-world problem.** Migrant-worker trafficking: LLMs routinely
  give unsafe or unhelpful answers to people in danger. DueCare grounds
  responses in the 11 ILO Forced-Labour Indicators and the controlling
  conventions, keeps sensitive data local, and routes to real help.
