# Gemma 4 Model Loading Trace

This repo has one canonical local Gemma 4 inference path:
`duecare.chat.gemma4_runtime.Gemma4Runtime`.

The runtime intentionally follows the known-working Unsloth FastModel recipe used for the Kaggle Gemma 4 notebooks:

```python
from unsloth import FastModel

model, tokenizer = FastModel.from_pretrained(
    model_name=resolved_model_ref,
    dtype=None,
    max_seq_length=max_seq_length,
    load_in_4bit=True,
    full_finetuning=False,
    device_map="balanced",  # for 31B / 26B-A4B on 2x T4; otherwise auto
)
```

After load, the runtime applies `get_chat_template(tokenizer, chat_template="gemma-4-thinking")`.
Generation uses the Gemma 4 defaults from the Unsloth notebook: `temperature=1.0`, `top_p=0.95`, and `top_k=64`.

## Standard Model References

- `google/gemma-4-2b-it` and `e2b-it` resolve to `unsloth/gemma-4-E2B-it` unless a matching Kaggle-attached model folder is mounted.
- `google/gemma-4-4b-it` and `e4b-it` resolve to `unsloth/gemma-4-E4B-it`.
- `google/gemma-4-26b-a4b-it` and `26b-a4b-it` resolve to `unsloth/gemma-4-26B-A4B-it`.
- `google/gemma-4-31b-it` and `31b-it` resolve to `unsloth/gemma-4-31B-it`.
- `jailbroken-31b` resolves to `dealignai/Gemma-4-31B-JANG_4M-CRACK`.

Kaggle-attached models are preferred when `/kaggle/input/models/google/gemma-4/transformers/gemma-4-{variant}/{1,2,3}/config.json` exists. Otherwise the runtime downloads the Unsloth repo from Hugging Face.

## Runtime Path Trace

- Kernel 01 exploration workbench:
  `/api/load-model` -> `load_gemma()` -> `Gemma4Runtime.load()` -> `FastModel.from_pretrained(...)`.
- Kernel 02 live demo:
  `/api/live/model/load` and startup loading -> `load_gemma_shared()` -> `_LIVE_MODEL_RUNTIME.load()` -> `FastModel.from_pretrained(...)`.
- Kernel A-00 preconfigured experiment:
  `/api/a00/pipeline/run` -> `_create_pipeline_job()` -> `_run_pipeline_job()` -> `_prepare_base_model_for_pipeline()` / `_load_model_runtime()` -> `A00_MODEL_RUNTIME.load()` -> `FastModel.from_pretrained(...)`.
- Kernel A-00 final LLM grading:
  the same `A00_MODEL_RUNTIME` is reloaded with the selected Gemma 4 model before combined rule + LLM grading.
  A-00 loads inference at `DUECARE_A00_INFERENCE_MAX_SEQ_LENGTH` (default `16384`) so grading prompts can carry
  the prompt, response, harness trace, rubric, and JSON instructions without falling back to the shorter training
  context. The combined judge output budget is controlled by `DUECARE_A00_COMBINED_JUDGE_MAX_NEW_TOKENS`
  (default `1600`) so structured rubric JSON is not silently truncated.

## Fine-Tuning Path

A-00 fine-tuning uses the Unsloth training path because LoRA adapter creation is not the same operation as inference loading:

```python
from unsloth import FastModel
from trl import SFTTrainer, SFTConfig

model, tokenizer = FastModel.from_pretrained(
    model_name=base_model,
    dtype=None,
    max_seq_length=max_seq_length,
    load_in_4bit=True,
    full_finetuning=False,
)
model = FastModel.get_peft_model(
    model,
    finetune_vision_layers=False,
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
)
```

The tokenizer is standardized with `gemma-4-thinking`, training rows are rendered through `tokenizer.apply_chat_template(...)`, and `train_on_responses_only(...)` masks user turns before `SFTTrainer.train()`.

## Kaggle Bootstrap Contract

The copy/paste Kaggle kernels must install the Hanchen/Unsloth stack before loading Gemma 4:

```text
torch>=2.8.0
triton>=3.4.0
torchvision
bitsandbytes
unsloth
unsloth_zoo>=2026.4.6
transformers==5.5.0
torchcodec
timm
```

The kernels also install DueCare from GitHub source when release wheels are missing, then launch the server and a Cloudflare quick tunnel.
