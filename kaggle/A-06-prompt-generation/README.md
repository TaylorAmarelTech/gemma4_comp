# DueCare — Two-track synthetic data generator (#A06 appendix)
<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Research pipeline notebook for growing two synthetic Gemma 4 training tracks: anti-exploitation safety reasoning and privacy redaction. |
| **What it does** | Turns seed rubrics into prompt candidates, graded response ladders, composite anonymization cases, and exportable training/evaluation data. |
| **Demo path** | Run the generator on a small sample, open the printed Cloudflare workbench URL, filter prompts, inspect Worst/Bad/Neutral/Good/Best graded responses, and download the A7 bundle ZIP. |
| **Audience** | Researcher. |
| **Outputs** | Safety prompt JSONL, graded-response JSONL, anonymization case/gold JSONLs, downloadable CSV, and corpus-browser dashboard. |
| **Cross-links** | Use the quick links at the bottom for the full workbench, live demo, fine-tune pipeline, and public website. |

Appendix-style notebook. **Not** part of the core deployment flow —
this is the data-pipeline tool advanced users invoke when they want
to grow training/evaluation material beyond the bundled 587 prompts and
25-row smoke set. It deliberately produces **two tracks**: SafetyJudge
data for anti-human-exploitation response quality, and PrivacyRedactor
data for anonymization/redaction behavior. Both tracks are synthetic or
composite only; no raw worker PII belongs in these artifacts.

Kaggle memory rule: this notebook should load **one model per run**.
Run it once with the stock/harness teacher profile, run it again with an
abliterated/uncensored Gemma profile if you want adversarial diversity, and
optionally run a human-curated review profile. Each run writes a manifest
and ZIP bundle that A7 can consume through Kaggle Add Data or the A7
workbench upload panel.

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-prompt-generation *(manual Kaggle publication target)* |
| **Title on Kaggle** | "DueCare Prompt Generation" |
| **Slug** | `taylorsamarel/duecare-prompt-generation` |
| **Wheels dataset** | `taylorsamarel/duecare-prompt-generation-wheels` *(local wheels present; create/update dataset during manual Kaggle publish)* |
| **Trafficking-prompts dataset** | `taylorsamarel/duecare-trafficking-prompts` (5 YAML rubrics — seed material) |
| **Models attached** | `google/gemma-4/Transformers/{e2b,e4b}-it/1` |
| **GPU** | T4 ×1 minimum (E4B-it default) |
| **Internet** | ON |
| **Secrets** | `HF_TOKEN` |
| **Expected runtime** | ~50-75 min for 50 prompts × 5 grades = 250 graded responses |

Built with Google's Gemma 4 (base model:
[google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)).
Used in accordance with the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms).

## Why "appendix"

Three of the five core notebooks (chat-playground, chat-playground-with-grep-rag-tools,
gemma-content-classification-evaluation) are everything an end user
needs for deployment. The live-demo notebook is the user-facing live
URL judges click. **Bench-and-tune and prompt-generation are tools
for the people who want to *extend* the system** — they are
optional, not required.

This kernel sits in the appendix because:

1. Most DueCare deployments will use the bundled 587 prompts +
   smoke_25 benchmark; they won't need to generate new ones.
2. Generating prompts requires GPU + ~1 hour; the core notebooks
   load in 30 seconds.
3. The safety outputs (`generated_prompts.jsonl`,
   `graded_responses.jsonl`) feed *into* the bench-and-tune
   notebook's SFT/DPO pipelines. The privacy outputs
   (`anonymization_cases.jsonl`, `anonymization_gold.jsonl`) feed a
   separate PrivacyRedactor adapter/eval track rather than being blended
   into the SafetyJudge adapter.

## What it does

End-to-end:

1. **Step 1 — Load source material.** Reads the 5 trafficking-prompts
   YAML rubrics (`business_framed_exploitation`,
   `financial_crime_blindness`, `jurisdictional_hierarchy`,
   `prompt_injection_amplification`, `victim_revictimization`).
   Falls back to a 3-scenario hardcoded list if the dataset isn't
   attached.
2. **Step 2 — Generate SafetyJudge prompts.** For each seed scenario, prompts
   Gemma 4 to write a realistic 80-150 word adversarial test prompt
   in the voice of a perpetrator or confused intermediary. Writes
   the result in the same row shape as `smoke_25.jsonl` so the
   prompt plugs directly into the existing benchmark runner.
3. **Step 3 — Grade SafetyJudge responses.** For each generated prompt, asks
   Gemma 4 to write five demonstration responses on a 0-4 scale. The
   compatibility labels remain `HARMFUL`, `INCOMPLETE`, `ADEQUATE`,
   `GOOD`, `BEST`; the screen and artifacts also include the old review
   labels `WORST`, `BAD`, `NEUTRAL`, `GOOD`, `BEST`. Used as SFT/DPO
   training data downstream.
4. **Step 4 — Build PrivacyRedactor cases.** Emits composite intake
   notes with placeholder PII tokens, expected redacted text, and gold
   structured redaction plans. These rows are for anonymizer training or
   evaluation behind deterministic regex/NER gates.

## Output

- `/kaggle/working/generated_prompts.jsonl` — N rows in the
  smoke_25 shape: `{id, category, locale, text, expected_verdict,
  expected_severity_min, expected_signals}`
- `/kaggle/working/graded_responses.jsonl` — N×5 rows:
  `{prompt_id, prompt_text, category, grade, grade_label,
   rating_label, response}`
- `/kaggle/working/anonymization_cases.jsonl` — synthetic/composite
   intake rows with expected redacted text and PII span labels
- `/kaggle/working/anonymization_gold.jsonl` — chat-format gold
   responses for PrivacyRedactor SFT/evaluation
- `/kaggle/working/duecare_a06_to_a07_manifest.json` — provenance and
   handoff instructions for A7, including the generation profile
- `/kaggle/working/duecare_a06_to_a07_bundle.zip` — all A6 handoff files
   zipped for download, Kaggle Dataset upload, or Add Data attachment
- `/kaggle/working/generation_log.json` — run summary

Export these JSONLs back to a Kaggle Dataset (`duecare-eval-results` or
a new `duecare-generated-prompts`) and attach that dataset to A7.
Without the attachment, A7 falls back to its bundled harness-distilled
examples.

## Cloudflare handoff workflow

After Run All, Kaggle prints a line like
`[workbench] https://...trycloudflare.com`. Open that URL to inspect the
generated corpus and download artifacts.

1. Download `duecare_a06_to_a07_bundle.zip` from the A6 dashboard.
2. For the most reproducible A7 run, publish that ZIP as a Kaggle Dataset
   and attach it to A7 with **Add Data** before Run All.
3. For quick staging, open A7's Cloudflare dashboard after Run All and upload
   multiple A6 ZIPs or JSONL artifacts in the **A-06 bundle handoff** panel,
   then rerun A7 so dataset build/training consumes them.
4. Repeat A6 once per generation profile if you want diversity. A7 can merge
   stock/harness, abliterated-adversary, and human-reviewed bundles.

Only move synthetic/composite rows through this path. Do not put raw worker
chats, IDs, phone numbers, emails, addresses, or private documents in an A6
bundle.

## Handoff artifact format

The A7 SafetyJudge path expects `graded_responses.jsonl` rows with these
fields:

| Field | Meaning |
|---|---|
| `prompt_id` | Stable prompt identifier. |
| `prompt_text` | The full generated evaluation prompt. |
| `category` | Rubric or trafficking-pattern category. |
| `grade` | Integer `0` through `4`. |
| `grade_label` | Compatibility label: `HARMFUL`, `INCOMPLETE`, `ADEQUATE`, `GOOD`, or `BEST`. |
| `rating_label` | Screen-facing review label: `WORST`, `BAD`, `NEUTRAL`, `GOOD`, or `BEST`. |
| `response` | Full demonstration response text for that quality tier. |
| `generation_profile` | `stock_harness_teacher`, `abliterated_adversary`, or `human_curated_review`. |
| `generator_model_variant` | Gemma 4 variant used to generate the row. |

A7 uses `BEST` rows from trusted profiles for SFT examples and keeps
`WORST`/`BAD` rows for DPO rejected examples and stress testing.

Recommended generation profiles:

- `stock_harness_teacher` — default. Use for trusted **Best** examples and
   the main SafetyJudge SFT target.
- `abliterated_adversary` — use abliterated Gemma for diverse adversarial
   prompts, harmful/incomplete responses, and evaluator stress tests. Do not
   use as **Best** labels unless reviewed.
- `human_curated_review` — optional highest-trust run after manual review.

## Files in this folder

```
prompt-generation/
├── kernel.py            ← source-of-truth (paste into Kaggle)
├── kernel-metadata.json ← Kaggle kernel config
├── README.md            ← this file
└── wheels/              ← local wheels for Kaggle dataset upload
```

## Status

**Prototype appendix (2026-05-10).** The Phase 0 install + wheel
install + Gemma load paths are real and follow the same pattern as
`bench-and-tune` and `live-demo`. The two LLM-driven steps
(generation, grading) use deliberately simple starter templates —
research users should replace `PROMPT_GENERATION_TEMPLATE` and
`_grading_template` with patterns optimized for their domain.

The local wheels are present in this folder for the manual Kaggle
dataset publication step. Do not auto-push them; Taylor publishes the
kernel and wheel dataset manually.

---

<!-- duecare:quick-cross-links -->

### Quick cross-links

- **Core workbench:** [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md).
- **Focused live demo:** [#02 core: Live demo](../02-live-demo/README.md).
- **Natural next appendix:** [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md).
- **Public website:** [duecare-ai.com](https://duecare-ai.com).

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A06 appendix — Two-track synthetic data generator**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- **[#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)**
- [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).

---

## Cross-links

- **[DueCare Exploration Workbench (#01)](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench)** -- the full chat playground with all 6 harness layers, 9-variant model picker, 4 grading modes, A/B compare, and every visualization in one place.
- **[Live demo (#02)](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)** -- focused public-hub walkthrough demonstrating the +56.5pp lift on a curated set of compound-indicator prompts.
- **[Next step -> A-07 bench-and-tune](https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune)** -- attach the generated JSONLs, train the SafetyJudge adapter, and benchmark stock versus fine-tuned Gemma 4.
- **[Public hub: duecare-ai.com](https://duecare-ai.com)** -- knowledge-pack registry, anonymized signal intake, public-source proposal intake, and the 5-lane audience showcase.
