# Credits and attributions

DueCare is built on a stack of open-source software, public legal
sources, and prior research. This file enumerates the dependencies,
data sources, and influences a judge or contributor should be aware
of, with attribution.

## Model and inference

- **Gemma 4** — Google DeepMind. Open-weight base model used as the
  local runtime across all three Kaggle kernels and the sibling
  Android app. Subject to the Gemma Terms of Use. We use the E2B,
  E4B, 26B-A4B, and 31B-IT variants from
  [`google/gemma-4`](https://www.kaggle.com/models/google/gemma-4) on
  Kaggle.
- **Unsloth** — [unsloth.ai](https://unsloth.ai) /
  [github.com/unslothai/unsloth](https://github.com/unslothai/unsloth).
  Used for LoRA fine-tuning of Gemma 4 in the A-00 control plane
  (`DueCare Fine-tuning and Evaluation`). Apache-2.0.
- **MediaPipe LiteRT** — Google AI Edge. Powers Gemma 4 E2B inference
  fully on-device in the sibling Android app
  ([`duecare-journey-android`](https://github.com/TaylorAmarelTech/duecare-journey-android)
  v0.9.0). Apache-2.0.
- **llama.cpp** — [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp).
  Reference deployment target for the GGUF export path. MIT.

## Runtime libraries

- **FastAPI** — the live-demo server is a FastAPI app
  (`packages/duecare-llm-server`). MIT.
- **Pydantic v2** — data-model layer across every harness contract.
  MIT.
- **Uvicorn** — ASGI server for the kernel-embedded live demo. BSD.
- **DuckDB** — local storage for the live demo. MIT.
- **Cloudflare quick tunnel** — every Kaggle kernel prints a public
  `https://*.trycloudflare.com` URL for the reviewer-facing demo.
- **Hugging Face Transformers + PEFT + TRL** — used through Unsloth's
  fine-tune path. Apache-2.0.

## Kaggle community

- **@bwandowando** — [kaggle.com/bwandowando](https://www.kaggle.com/bwandowando).
  The install-marker-then-restart sequencing that lets a heavy,
  C-extension-bearing stack (torch + triton + Unsloth) be installed inside a
  running Kaggle session comes from his published recipe. We follow the
  ordering faithfully in `kaggle/02-live-demo/kernel.py` and
  `kaggle/_archive/notebooks/A-07-bench-and-tune/kernel.py`, because the
  ordering is the part that actually works. Without it the Gemma 4 kernels
  would not boot on Kaggle.
- **Daniel Han and the Unsloth team** — the pinned Gemma 4 + Unsloth version
  set installed by those kernels is theirs.

## Models evaluated in the benchmark

The DueCare Harness-Lift Benchmark measures *paired lift* — the same prompt,
with and without the harness, graded identically. That design means other
organisations' models are run as measurement subjects, and several are also
used as judges. All of them deserve naming. Nothing here is a claim about a
vendor's product quality in general; the metric is how much a prompt-level
harness changes a response on one migrant-worker safety rubric.

**Evaluated as subjects** (7 on the public board):

- **Google DeepMind** — Gemma 4 (`gemma4:31b` plus the E2B / E4B / 26B-A4B
  variants). Gemma Terms of Use.
- **OpenAI** — `gpt-oss:20b`, `gpt-oss:120b` (open-weight release), and
  `gpt-4o` / `gpt-4o-mini` in the wider frontier study.
- **Zhipu AI / Z.ai** — `glm-5.1`, `glm-5.2`.
- **DeepSeek** — `deepseek-v4-pro` and earlier v3.x releases.
- **Alibaba Qwen** — `qwen3.5:397b`, `qwen3-coder:480b`, `qwen3-next:80b`.
- **MiniMax** — `minimax-m2.7`.
- **Moonshot AI** — Kimi K2 / K3 lanes.
- **Anthropic** — Claude models in the frontier comparison lanes.
- **Mistral AI** — `mistral-large` in earlier generation runs.

**Used as judges** — `deepseek-v4-pro`, `glm-5.2`, `gpt-oss:120b`: a
three-model panel with self-family exclusion, so no model grades its own
family. Judge disagreement is reported rather than hidden.

## Serving and routing

- **Ollama** — [ollama.com](https://ollama.com) /
  [github.com/ollama/ollama](https://github.com/ollama/ollama). Local and
  cloud serving for the open-weight models in the benchmark engine. MIT.
- **OpenRouter** — [openrouter.ai](https://openrouter.ai). Routing layer for
  closed frontier models in the comparison lanes.
- **Hugging Face Hub** — model distribution and the `huggingface_hub` client.
  Apache-2.0.

## Typography

The workbench, hub, and slide surfaces load these via Google Fonts. All three
families are **SIL Open Font License 1.1**:

- **Inter** — Rasmus Andersson.
  [github.com/rsms/inter](https://github.com/rsms/inter)
- **JetBrains Mono** — JetBrains.
  [github.com/JetBrains/JetBrainsMono](https://github.com/JetBrains/JetBrainsMono)
- **IBM Plex Sans / IBM Plex Mono** — IBM.
  [github.com/IBM/plex](https://github.com/IBM/plex)

## Research tooling with citation requests

Some libraries are permissively licensed but their authors ask to be cited
academically. Honouring that:

- **VADER** (`vaderSentiment`) — Hutto, C.J. & Gilbert, E.E. (2014).
  *VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social
  Media Text.* Eighth International Conference on Weblogs and Social Media
  (ICWSM-14). Used for tone analysis in the prompt/response NLP notebooks.
  MIT.
- **textstat** — readability metrics in the prompt/response NLP notebook. MIT.
- **sentence-transformers** — Reimers, N. & Gurevych, I. (2019).
  *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.* EMNLP
  2019. Apache-2.0. The specific checkpoints used are listed in
  `LICENSES.md`.

## Legal and policy sources (cited in the knowledge packs)

These are public sources. The knowledge-pack RAG corpus quotes
section numbers, captions, and citation strings verbatim with full
attribution to the issuing authority. The list below is illustrative,
not exhaustive — the full inventory lives in
`packages/duecare-llm-chat/src/duecare/chat/harness/_citations.json`.

- **International Labour Organization (ILO)** — Conventions C029
  (Forced Labour), C181 (Private Employment Agencies), C189 (Domestic
  Workers); Forced Labour Indicators; Global Estimates of Modern
  Slavery 2022; Profits and Poverty: The Economics of Forced Labour
  2024.
- **United Nations** — Palermo Protocol (Protocol to Prevent, Suppress
  and Punish Trafficking in Persons).
- **Philippines** — RA 8042 (Migrant Workers and Overseas Filipinos
  Act); RA 10022 (amendment); RA 10361 (Batas Kasambahay); RA 9208
  (Anti-Trafficking); RA 11862 (recent amendment); POEA Memorandum
  Circular 14-2017 / 02-2007 (now DMW policy); DMW model contract.
- **Indonesia** — BP2MI Regulation 9/2020.
- **Nepal** — Foreign Employment Act 2007 §11(2); 2015 Free-Visa-
  Free-Ticket Cabinet Decision.
- **Bangladesh** — Overseas Employment Act 2013.
- **Hong Kong** — Employment Ordinance Cap. 57; Money Lenders
  Ordinance Cap. 163; Employment Agency Regulations Cap. 57A.
- **Singapore** — Employment of Foreign Manpower Act Cap. 91A §22A.
- **United Arab Emirates** — MoHRE Decree 765/2015.
- **California (US)** — Civil Code §1714(a), the general duty-of-care
  doctrine that gave the project its name.

## Influences and prior art

- **Taylor Amarel's 2025 Kaggle red-teaming research** — *LLM complicity in modern slavery:
  from native-blind...*
  ([Kaggle write-up](https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming/writeups/llm-complicity-in-modern-slavery-from-native-blind)).
  The empirical evidence that frontier LLMs consistently fail on
  migrant-worker safety prompts. Motivates the harness design.
- **Sister synthetic-evidence harness** — a fully synthetic test-data
  generator (`synthetic_test_evidence/`) with closed-set indicator
  vocabulary, prompt packs (v1 lenient, v2 chain-of-thought + strict
  thresholds), reproducible release zip, deterministic CI smoke
  runner, and per-lane sample cases. Maintained alongside DueCare;
  outputs are watermarked and safe for any public-cloud test
  environment.
- **DueCare Journey for Android (sibling app)** —
  [github.com/TaylorAmarelTech/duecare-journey-android](https://github.com/TaylorAmarelTech/duecare-journey-android)
  v0.9.0. On-device worker-facing app demonstrating the LiteRT path
  for Special Technology Track eligibility.
- **Partner NGOs** — Polaris Project, International Justice Mission
  (IJM), ECPAT, the Philippine Overseas Employment Administration
  (POEA, now DMW), BP2MI (Indonesia), HRD Nepal. Their published
  guidance, statutes, contact pathways, and case archetypes shaped
  the GREP rule library and RAG knowledge packs.
- **Cal. Civ. Code §1714(a) doctrine** — March 2026 California jury
  verdict against Meta and Google for defective platform design. We
  apply the same duty-of-care standard to language models.

## Directory data (organisations that help workers)

`configs/duecare/research_monitor/migrant_support_orgs.yaml` compiles contact
routes for migrant-support organisations — helplines, shelters, legal aid,
unions, resource centres, labour attachés, and intergovernmental bodies — so
the harness can point a worker or caseworker at real help instead of inventing
a number.

- **Every entry is published organisational contact information.** No
  individual's personal details are included, and the catalog header states
  that constraint.
- **Per-entry provenance is recorded** in each row's `notes` field, naming the
  official directory or publication the contact came from (for example a
  ministry labour-wing directory or an agency's own published hotline page).
- **The organisations are credited by name in the data itself** and are the
  authors of their own contact information; DueCare claims no ownership over
  it and asserts no endorsement by them.
- `url_verified` marks whether a link has been re-checked. Contact details go
  stale, which is exactly why they live in a versioned knowledge object rather
  than being trained into model weights.

If you represent an organisation listed here and want an entry corrected or
removed, open an issue on the repository and it will be changed.

## AI-assisted development

Stated plainly because the repository makes it visible anyway, and because a
project whose thesis is "real, not faked" should not be coy about its own
tooling.

DueCare was built with substantial AI coding assistance — principally
Anthropic's Claude (via Claude Code) and OpenAI's Codex, whose working notes,
review prompts, and handoffs are committed under `docs/` and `.claude/` rather
than scrubbed. Architecture, research direction, domain expertise, the
benchmark design, and every published claim are the author's. AI assistance
does not extend to the results: benchmark numbers come from recorded runs that
regenerate from `(git_sha, dataset_version)`, and where a result did not
support a claim it is published as a negative result instead.

## Synthetic content disclaimers

Every shipped sample bundle (`packages/duecare-llm-chat/src/duecare/chat/static/samples/*`)
is fully synthetic and carries a `SYNTHETIC TEST DATA - NOT REAL`
watermark or banner. Composite agency names ("Sunburst Manpower
Services", "HK Domestic Jobs", "MetroMed Diagnostic Center") are
labelled `(composite)` in any judge-visible surface. No real
worker PII, no real recruiter PII, no real case data is included in
this repository or any of its samples.

## License

The DueCare project code is **MIT-licensed**. The Gemma 4 model
weights are subject to the Gemma Terms of Use. Library dependencies
retain their respective licenses (see each library's repository).
Knowledge-pack content quotes from public statutes and circulars is
used under fair-use citation; redistribution of those quoted
fragments inside the knowledge packs is permissible because the
underlying texts are public-record government and IGO publications.

## How to add a citation

If a knowledge pack, GREP rule, or response template adds a new
statutory or organizational citation, add it to:

1. The relevant pack JSON
   (`packages/duecare-llm-chat/src/duecare/chat/harness/_citations.json`
   or the equivalent for the specific harness).
2. The "Legal and policy sources" section of this file.
3. The relevant test fixture if a contract test pins it (e.g.
   `packages/duecare-llm-server/tests/test_slides_surface.py`
   asserts `RA 8042` is the migrant-workers statute, not RA 11227).
