# Publishing plan — Jailbreak notebook family (181-189)

Nine notebooks built across this conversation. All four per-model
producers (186-189) write to a uniform artifact contract under
`/kaggle/working/jailbreak_out/{slot}/`; the CPU comparator (185) and
the four playgrounds / generators (181-184) read and extend that
corpus. This document is the command sequence to publish — Claude
does not push automatically (per `feedback_kaggle_pushes.md`); you
execute these commands when ready.

## Family summary

| # | Dir | GPU | Reads | Writes |
|---|---|---|---|---|
| 181 | `kaggle/kernels/duecare_181_jailbreak_response_viewer` | none | `jailbreak_out/*` | — |
| 182 | `kaggle/kernels/duecare_182_refusal_direction_visualizer` | T4 | stock weights | `refusal_direction_from_182.pt` |
| 183 | `kaggle/kernels/duecare_183_redteam_prompt_amplifier` | T4 | `jailbreak_out/*/generations.jsonl` + optional `refusal_direction_from_182.pt` | `amplified_redteam_prompts.jsonl` |
| 184 | `kaggle/kernels/duecare_184_frontier_consultation_playground` | T4 | stock weights + `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` secret | `frontier_consultation_log.jsonl` |
| 185 | `kaggle/kernels/duecare_185_jailbroken_gemma_comparison` | none | `jailbreak_out/*` | — |
| 186 | `kaggle/kernels/duecare_186_jailbreak_stock_gemma` | T4 | stock weights | `jailbreak_out/stock_e4b`, `stock_dan`, `stock_roleplay` |
| 187 | `kaggle/kernels/duecare_187_jailbreak_abliterated_e4b` | T4x2 / L4 | stock weights | `jailbreak_out/abliterated_e4b/` + `refusal_direction.pt` |
| 188 | `kaggle/kernels/duecare_188_jailbreak_uncensored_community` | T4 | HF community weights (probed) | `jailbreak_out/uncensored_community/` |
| 189 | `kaggle/kernels/duecare_189_jailbreak_cracked_31b` | L4x4 / A100 | `dealignai/Gemma-4-31B-JANG_4M-CRACK` | `jailbreak_out/cracked_31b/` |

## Publish order (recommended)

Run this once top-to-bottom the first time; on subsequent rounds only
push the notebooks whose build script changed.

### Phase 1 — push the notebooks (all Kaggle kernels, public)

Run from the repo root. Each command publishes one kernel; `kaggle
kernels push` is idempotent and versions on re-push.

```bash
cd C:/Users/amare/OneDrive/Documents/gemma4_comp

kaggle kernels push -p kaggle/kernels/duecare_186_jailbreak_stock_gemma
kaggle kernels push -p kaggle/kernels/duecare_187_jailbreak_abliterated_e4b
kaggle kernels push -p kaggle/kernels/duecare_188_jailbreak_uncensored_community
kaggle kernels push -p kaggle/kernels/duecare_189_jailbreak_cracked_31b

# Playgrounds and comparator
kaggle kernels push -p kaggle/kernels/duecare_181_jailbreak_response_viewer
kaggle kernels push -p kaggle/kernels/duecare_182_refusal_direction_visualizer
kaggle kernels push -p kaggle/kernels/duecare_183_redteam_prompt_amplifier
kaggle kernels push -p kaggle/kernels/duecare_184_frontier_consultation_playground
kaggle kernels push -p kaggle/kernels/duecare_185_jailbroken_gemma_comparison
```

### Phase 2 — run the per-model producers on Kaggle

These are the only notebooks that generate artifacts. Open each kernel
on Kaggle.com and run it manually (or via `kaggle kernels status` to
check which have completed a recent run). They should run in this
order on these accelerators:

- **186** on T4 (4-7 min)
- **187** on T4 x 2 or L4 (8-12 min; T4 x 1 is too small for bf16)
- **188** on T4 (5-10 min; may skip if no candidate resolves)
- **189** on L4 x 4 or A100 (12-20 min; skips gracefully on T4)

### Phase 3 — bundle the artifacts into a Kaggle dataset

After the four producers have each completed at least once, the
`/kaggle/working/jailbreak_out/` folders contain everything the
comparator and playgrounds need. Bundle them into one dataset so 181 /
183 / 184 / 185 can consume them.

From a local clone of the kernel outputs (use `kaggle kernels output -p
<local-dir>` to pull each producer's `/kaggle/working/` to disk):

```bash
# Pull outputs locally
mkdir -p /tmp/jailbreak_artifacts/jailbreak_out
kaggle kernels output taylorsamarel/duecare-186-jailbreak-stock-gemma       -p /tmp/jailbreak_artifacts/
kaggle kernels output taylorsamarel/duecare-187-jailbreak-abliterated-e4b   -p /tmp/jailbreak_artifacts/
kaggle kernels output taylorsamarel/duecare-188-jailbreak-uncensored-community -p /tmp/jailbreak_artifacts/
kaggle kernels output taylorsamarel/duecare-189-jailbreak-cracked-31b       -p /tmp/jailbreak_artifacts/

# Create (first time) or version (subsequent) the dataset.
# Dataset metadata file: jailbreak-artifacts-metadata.json
cat > /tmp/jailbreak_artifacts/dataset-metadata.json <<'JSON'
{
  "title": "DueCare Jailbreak Artifacts",
  "id": "taylorsamarel/duecare-jailbreak-artifacts",
  "licenses": [{"name": "CC0-1.0"}]
}
JSON

# First time:
kaggle datasets create -p /tmp/jailbreak_artifacts -r zip

# Subsequent versions:
# kaggle datasets version -p /tmp/jailbreak_artifacts -m "round N: <which producers re-ran>" -r zip
```

### Phase 4 — re-run the comparator / playgrounds now that the dataset exists

After the dataset is published, open 181 / 183 / 184 / 185 on Kaggle
and add `taylorsamarel/duecare-jailbreak-artifacts` to each kernel's
attached datasets (or edit `kernel-metadata.json` → `dataset_sources`
and re-push). Trigger a new run on each; they will now read real
artifacts instead of the embedded sample bundles.

## Optional: required Kaggle secrets

- **184 frontier consultation** uses either of these if set, otherwise
  falls back to cached expert answers:
  - `ANTHROPIC_API_KEY` — live Claude consults (preferred per the
    rubric's "Gemma 4 unique features" angle)
  - `OPENROUTER_API_KEY` — OpenRouter Claude proxy

  Set under `Settings → Add-ons → Secrets` on the Kaggle notebook.

- **188 uncensored community** uses `HF_TOKEN` if the HF repo it
  resolves is gated. Set it if candidate loads fail with 401 errors.

## Which kernels need re-push after the next build round

If you edit a build script and re-run it, the kernel directory is
overwritten and you need to re-push that kernel. No dataset re-version
is needed unless a producer notebook's output contract changes.

```bash
# Example: after editing build_notebook_187_jailbreak_abliterated_e4b.py
python scripts/build_notebook_187_jailbreak_abliterated_e4b.py
kaggle kernels push -p kaggle/kernels/duecare_187_jailbreak_abliterated_e4b
```

## One-shot publish-all helper

If you want a single command, use the existing helper:

```bash
python scripts/publish_kaggle.py push-notebooks
```

It iterates every kernel directory under `kaggle/kernels/` and pushes
them in order. Slower than the targeted commands but fire-and-forget.
