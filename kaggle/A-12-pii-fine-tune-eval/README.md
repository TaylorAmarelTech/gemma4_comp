# A-12 — PrivacyRedactor LoRA fine-tune + eval

<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher

This is appendix slot **A-12** of the canonical 24-slot
experiment ladder defined in
[`docs/appendix_experiment_ladder.md`](../../docs/appendix_experiment_ladder.md).

The kernel trains a Gemma 4 LoRA adapter (PrivacyRedactor) on
A-10's synthetic composite intake + gold redaction plans, then
benchmarks stock vs fine-tuned redaction accuracy on a held-out
split.

## What it does

1. Installs DueCare from GitHub (no Kaggle wheel datasets — per
   the 2026-05-11 GitHub-only policy).
2. Installs the Unsloth stack (FastModel + peft + trl SFT).
3. Loads Gemma 4 base (default `e2b-it`; override via
   `DUECARE_GEMMA_VARIANT`).
4. Discovers A-10 gold JSONL files under `/kaggle/input` and
   splits 80/20 train/holdout (deterministic seed).
5. SFT trains a LoRA adapter (default 200 steps, override via
   `DUECARE_SFT_MAX_STEPS`).
6. Evaluates stock vs fine-tuned label F1 on the holdout set.
7. Saves the adapter to `/kaggle/working/pii-redactor-<variant>-v1/`.
8. Optional HF Hub push if `HF_TOKEN` Kaggle Secret is set.
9. Workbench shell prints the eval summary + download links.

## Inputs

- **Required Kaggle Dataset attachment:** the bundle produced by
  A-10 (folder `kaggle/A-09-chat-playground-with-agentic-research/`).
  Publish that bundle ZIP as a Kaggle Dataset, then use **Add Data**
  here so the trainer finds `*_pii_gold.jsonl` under `/kaggle/input`.
- **Internet:** ON (DueCare GitHub install + HF Hub model download
  + optional adapter push).
- **GPU:** T4 (e2b-it default fits in 16 GB 4-bit).
- **Optional secret:** `HF_TOKEN` (Kaggle Add-ons → Secrets) for
  adapter push to
  `TaylorScottAmarel/duecare-gemma-4-<variant>-pii-redactor-v1`.

## Outputs

To `/kaggle/working/`:

- `pii-redactor-<variant>-v1/` — LoRA adapter directory
- `<run_id>_eval.json` — per-row + aggregate eval payload (v1.0
  schema; consumed by A-08 alongside SafetyJudge bundles for cross-
  domain comparison)
- `<run_id>_metadata.json` — eval payload minus `results`
- `<run_id>_bundle.zip` — manifest + eval + metadata

## Cross-links

- **Adapter retraining policy:** [duecare-ai.com/evaluation](https://duecare-ai.com/evaluation) — the hub's `/evaluation` section 04 names the **PrivacyRedactor** adapter this kernel trains.
- **Full kernel roster:** [duecare-ai.com/kernels](https://duecare-ai.com/kernels).
- **Public website:** [duecare-ai.com](https://duecare-ai.com).

Run-ID format: `a11_pii_finetune_{variant}_{iso_ts}`.

## How the LoRA adapter plugs back in

Set the following env in any A-06 / A-07 baseline / harnessed
runner to use this PrivacyRedactor adapter:

- `DUECARE_LORA_ADAPTER_PATH=/kaggle/input/<a-11-bundle>/pii-redactor-<variant>-v1`
- or `DUECARE_LORA_ADAPTER_REPO=TaylorScottAmarel/duecare-gemma-4-<variant>-pii-redactor-v1`
- `DUECARE_LORA_ADAPTER_SLUG=pii-redactor-v1`

## Where this slot lives

- **Canonical role:** A-11 PII fine-tune + eval
- **Folder path:** `kaggle/A-12-pii-fine-tune-eval/` (a new
  folder; no legacy slot was available in the existing 13-folder
  layout)
- **Sibling reference implementations:**
  `kaggle/A-07-bench-and-tune/` (the SafetyJudge trainer), and
  `kaggle/A-09-chat-playground-with-agentic-research/` (A-10 PII
  synth data generator that feeds this kernel).

See `docs/appendix_experiment_ladder.md` for the full ladder spec
and `docs/appendix_artifact_schema.md` for the v1.0 cross-kernel
artifact contract.

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A12 appendix — PrivacyRedactor LoRA fine-tune + eval**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#03 core: Video pitch (in-app slides + presenter remote)](../03-duecare-video-pitch/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)
- [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md)
- **[#A12 appendix: PrivacyRedactor LoRA fine-tune + eval](../A-12-pii-fine-tune-eval/README.md)**
- [#A13 appendix: Multimodal document analyzer (Gemma 4 vision)](../A-13-multimodal-document-analyzer/README.md)
- [#A14 appendix: On-device export (LoRA merge -> GGUF + LiteRT)](../A-14-on-device-export/README.md)
- [#A15 appendix: UGC batch moderator (Lane 01 platform safety)](../A-15-ugc-batch-moderator/README.md)
- [#A16 appendix: NGO local-KB / case-file ingestion](../A-16-ngo-local-kb/README.md)
- [#A17 appendix: Knowledge-pack builder + verifier](../A-17-knowledge-pack-builder/README.md)
- [#A18 appendix: Sentinel / research monitor](../A-18-sentinel-research-monitor/README.md)
- [#A19 appendix: Multilingual demo (5-language playback)](../A-19-multilingual-demo/README.md)
- [#A20 appendix: Privacy boundary visualization](../A-20-privacy-boundary/README.md)
- [#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)
- [#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)
- [#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
