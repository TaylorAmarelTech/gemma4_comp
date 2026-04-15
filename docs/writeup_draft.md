# Kaggle Writeup Draft — DueCare

> **Title:** DueCare — Exercising Due Care in LLM Safety Design
>
> **Subtitle:** 74,567 trafficking prompts. 5 weighted rubrics. Native function
> calling + multimodal document analysis. One command, on your laptop.
>
> **Track:** Main Track (parallel eligibility: Unsloth, llama.cpp,
> Ollama, LiteRT Special Technology tracks)
>
> **Named for:** Cal. Civ. Code § 1714(a) — the duty of care standard
> that a California jury applied to find Meta and Google negligent for
> defective platform design (March 2026).
>
> **Target word count:** 1,350 words (within the 1,500-word limit)

---

## TL;DR (80 words)

DueCare is an agentic safety harness for LLMs — named for the
Cal. Civ. Code sect. 1714(a) duty of care standard. Stock Gemma 4 E4B
scores **0.61 mean / 20% pass / 0% harmful** on trafficking prompts
from a 74,567-prompt corpus (Kaggle T4). RAG context lifts scores 28%.
Cross-domain to tax evasion and financial crime with zero code changes.
**15 adversarial generators, 7 evaluation frameworks, 19 Kaggle
notebooks, 194 tests, 8 pip-installable packages, one CLI command.**
Runs on a laptop.

## 1. The problem (230 words)

**Scale.** 281 million international migrants globally (IOM 2024).
**28 million people in forced labor.** Trafficking is a $236B criminal
industry (ILO 2022). Every day, migrant workers message AI assistants
for legal help — and get generic answers that miss exploitation
indicators that would trigger a referral in a trained human caseworker.

Frontier LLMs fail predictably on migrant-worker trafficking scenarios
— documented in my prior OpenAI gpt-oss-20b Red-Teaming Challenge
writeup, *"LLM Complicity in Modern Slavery: Native Blind Spots to
Amplified Exploitation."* Five categories of failure recur across
providers: moral/religious framing of exploitation, regulatory
evasion, coercion math, financial obfuscation, and systematic
combinatorial variations.

The organizations that most need to evaluate LLMs for this use case —
frontline NGOs (Polaris Project, IJM, ECPAT), Gulf and Southeast-Asia
recruitment regulators (POEA, BP2MI, HRD Nepal), ILO/IOM field offices,
labor ministries — **cannot send sensitive case data to frontier APIs.**
Legal, regulatory, and operational constraints require a local
evaluator.

The hackathon's own problem statement names this gap: *"a community
where privacy is non-negotiable."*

And the gap isn't trafficking-specific. Tax evasion investigators at
the IRS, FATF-aligned AML teams, medical misinformation researchers —
every safety-critical domain has the same shape (taxonomy + evidence +
rubric + graded examples) and the same blocker (cloud APIs are
unavailable). A one-off trafficking-only fine-tune doesn't help them.

What's missing is **infrastructure** — an evaluator and training
harness that's domain-agnostic, model-agnostic, reproducible, and runs
locally. That's DueCare.

## 2. The approach (280 words)

DueCare ships as **8 PyPI packages** sharing the `duecare` Python namespace
via implicit namespace packages (Python 3.3+). Each package has a single
layer of the architecture:

| Package | Layer |
|---|---|
| `duecare-llm-core` | Contracts (Protocol-based), schemas (Pydantic v2), registry, provenance, observability |
| `duecare-llm-models` | 8 model adapters (HF Transformers, llama.cpp, Unsloth, Ollama, OpenAI-compatible, Anthropic, Google Gemini, HF Inference Endpoints) |
| `duecare-llm-domains` | `FileDomainPack` + pack loader + 3 shipped domain packs |
| `duecare-llm-tasks` | 9 capability tests (guardrails, anonymization, classification, fact extraction, grounding, multimodal classification, adversarial multi-turn, tool use, cross-lingual) |
| `duecare-llm-agents` | 12 autonomous agents + `AgentSupervisor` |
| `duecare-llm-workflows` | YAML DAG loader + topological runner |
| `duecare-llm-publishing` | HF Hub + Kaggle publisher, markdown reports, HF model cards |
| `duecare-llm` (meta) | `duecare` CLI + re-exports from all siblings |

Kaggle notebooks `!pip install` only the packages they need — minutes,
not gigabytes. A Phase 1 baseline notebook pulls
`duecare-llm-core duecare-llm-domains duecare-llm-tasks duecare-llm-agents`;
a Phase 3 fine-tune notebook adds `duecare-llm-models[unsloth]`.

**Gemma 4 plays two roles.** Subject of evaluation (E2B and E4B tested
against Llama, Mistral, Qwen, DeepSeek, Claude, GPT-4o) and
orchestration substrate (the Coordinator agent uses Gemma 4 E4B native
function calling to schedule the 11 other agents). Multimodal powers
the Scout's document-image path (recruitment-contract photo in,
structured findings out). Unsloth + Trainer handles post-training.
Judge's `retrieve_from_evidence` is agentic retrieval. Every Gemma 4
hackathon keyword is load-bearing, not decorative.

## 3. Technical architecture (300 words)

**Protocols over inheritance.** Every cross-layer contract is a
runtime-checkable `typing.Protocol`. Adapters for HF Transformers,
llama.cpp, Unsloth, Ollama, OpenAI, Anthropic, Gemini, and HF Inference
Endpoints all satisfy the same `Model` protocol without any forced
base class. Adding a new backend is a new folder, not a refactor.

**Pydantic v2 schemas.** Every data flow between layers is a validated
Pydantic model with automatic JSON round-trip. `Provenance` stamps
every record with `(run_id, git_sha, config_hash)` so results are
reproducible to the byte. The `TaskResult`, `AgentOutput`, and
`WorkflowRun` models flow unchanged from the lowest-level Task through
the Coordinator and out to the Kaggle submission notebook.

**Folder-per-module structure.** All 58 modules live in their own
folders with 7 auto-generated meta files (PURPOSE, AGENTS, INPUTS_OUTPUTS,
HIERARCHY, DIAGRAM, TESTS, STATUS) plus source files and a `tests/`
subfolder. The `AGENTS.md` files comply with the Linux Foundation's
emerging [agents.md](https://agents.md/) standard — the same file works
across Claude Code, Cursor, GitHub Copilot, Gemini CLI, Windsurf,
Aider, Zed, Warp, and RooCode. An AI reviewer walking into any folder
immediately understands that folder's purpose, contract, and tests.

**`AgentSupervisor` meta-agent.** Every agent call is wrapped by a
supervisor that enforces retry policies, hard budget caps, and
abort-on-harm. The Validator agent's red-team check can signal
`harm_detected=True` on the shared context, which causes the supervisor
to raise `HarmDetected` and abort the workflow before any artifact
gets published.

**Domain packs are content, not code.** `configs/duecare/domains/<id>/`
holds `taxonomy.yaml`, `rubric.yaml`, `pii_spec.yaml`, and
`seed_prompts.jsonl`. Adding `medical_misinformation` is a directory
copy and an edit — zero code change.

## 4. Results (180 words)

**Stock Gemma 4 E4B on Kaggle T4 (50 graded prompts).** Keyword score
(0.610 mean, 20% pass, 0% explicit-harmful-phrase) understates the
safety gap. A refined six-band classifier (negation-context + victim-
prompt aware) reveals **28% HARD_VIOLATION** (model gave exploitative
implementation help, e.g. disguising illegal placement fees as salary
deductions), **46% DETECTION_FAIL** (treated exploitation as legit
business), **22% refused**, **0% FULL_SUCCESS**. Phase 3 closes this gap.

| Metric | Value |
|---|---|
| Mean keyword score (NB 00) | 0.610 |
| Pass rate by keyword (NB 00) | 20% |
| Explicit-harmful-phrase rate (NB 00) | 0.0% |
| **HARD_VIOLATION rate (V3 reclassification)** | **28%** |
| **DETECTION_FAIL rate (V3)** | **46%** |
| FULL_SUCCESS rate (V3) | 0% |
| RAG context lift over plain | +23% |
| Guided prompt lift over plain | +28% |
| Trafficking corpus | 74,567 prompts |
| Adversarial generators | 15 |
| Tests passing | 194 |
| Kaggle notebooks completed | 21 of 25 |

Context injection alone lifts scores 23–28% without training — proof
Gemma 4 has the capability but needs domain knowledge, which Phase 3
Unsloth fine-tuning supplies permanently. Cross-domain proof: same
`duecare run` command on `--domain tax_evasion` or `financial_crime`
produces structurally-identical reports with zero code changes.

## 5. Impact and who benefits (260 words)

DueCare ships on two axes at the same time.

**Consumer side — individual workers and their families.** A Filipino
domestic worker in Jeddah pastes a suspicious recruiter message into
the browser extension (`deployment/browser_extension/`) or into the
public web demo and gets back, in Tagalog or English: the detected
violation, the ILO convention it breaks, the local hotline number
(POEA 1343 / BP2MI / HRD Nepal / IOM), and the embassy contact. No
login. No account. Nothing leaves the device. The browser extension
runs against `localhost` by default; the mobile-friendly web UI is
identical. This is the path that reaches the tens of thousands of
people actually at risk.

**Enterprise side — institutions that process cases.** Three user
classes, none of whom can call a frontier API with their data:
**recruitment regulators** (POEA, BP2MI, HRD Nepal) auditing their
licensing workflows; **frontline NGOs and legal aid clinics** (IJM,
Polaris, ECPAT, ILO/IOM field offices) doing intake triage; and
**platform trust & safety teams** under discovery obligations after
the 2026 Meta/YouTube trafficking verdict. They run the same `duecare`
CLI against batches of cases, use the `AgentSupervisor` to enforce
budget + abort-on-harm policies, and deploy the FastAPI dashboard
internally.

**Concrete before/after.** An NGO intake officer reads
*"My employer holds my passport and charges me ₱60,000 for food."*
Without DueCare: generic refusal, no next step. With DueCare: the
6-dimension judge flags the missing ILO C181 Article 7 citation, the
POEA hotline (1343), the POLO Riyadh referral. The survivor gets the
right referral. Cross-domain is free: one YAML directory adds medical
misinformation or AML.

**DueCare runs on a laptop — blast radius zero. Zero data leaks. Zero
vendor dependency.** Same binary reaches both audiences; the UI wraps
it differently for each.

## 6. Reproducibility (80 words)

- **Code:** [GitHub](https://github.com/TaylorAmarelTech/gemma4_comp) — MIT
- **Packages:** `pip install duecare-llm` (meta) or any of the 7 sibling
  packages individually
- **Weights:** [Kaggle Models — DueCare Safety Harness](https://www.kaggle.com/models/taylorsamarel/duecare-safety-harness) (pending Phase 3 fine-tune)
- **Notebooks:** [Kaggle notebooks](https://www.kaggle.com/taylorsamarel/code)
- **Live demo:** HF Spaces (URL pinned after week-5 deploy)
- **Tests:** `python -m pytest packages tests` → 194 passed

Every metric in this writeup is reproducible from
`(git_sha, config_hash, dataset_version)`.

## 7. Acknowledgements (80 words)

Built on top of my existing *LLM Safety Testing Ecosystem* for
migrant-worker protection: 21K-test benchmark, 26 migration corridors,
174 scraper seed modules, 20,460+ verified facts, 126 attack chains,
631 prompt-injection mutators. Grounded in ILO C029, C097, C181, C189,
the UN Palermo Protocol, the TVPA, 18 years of POEA enforcement data,
and the FATF 40 Recommendations.

Privacy is non-negotiable. The lab runs on your machine.

---
