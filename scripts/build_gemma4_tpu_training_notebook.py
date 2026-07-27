#!/usr/bin/env python3
"""Build the public Gemma 4 TPU training-and-diagnostics Kaggle notebook."""

# Embedded notebook cells preserve readable, copyable statements; their line
# length is validated as notebook code rather than as this builder's layout.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import ast
import json
import py_compile
from pathlib import Path
from typing import Any

import nbformat

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "gemma4_tpu_training_lab_v1"
KERNEL_ID = "taylorsamarel/duecare-gemma-4-tpu-lora-training-lab"
DATASET_ID = "taylorsamarel/duecare-measured-review-curriculum-200k"
FALLBACK_REGISTRY_PATH = ROOT / "configs" / "duecare" / "model_fallbacks.json"
FALLBACK_REGISTRY = json.loads(FALLBACK_REGISTRY_PATH.read_text(encoding="utf-8"))
TPU_POLICY = FALLBACK_REGISTRY["policies"]["kaggle_tpu_adapter_training"]
TPU_MODEL_CANDIDATES = TPU_POLICY["candidates"]
TPU_ACCELERATOR_CANDIDATES = TPU_POLICY["accelerator_candidates"]
MODEL_SOURCES = [candidate["model_source"] for candidate in TPU_MODEL_CANDIDATES]
RELEASE_SHA256 = "1b062ce12fe43494f7d63659a53017c857e0ac0103759d8f71b3340f63bdc2b7"
TRANSFORMERS_VERSION = "5.5.0"
PEFT_VERSION = "0.19.1"


def _markdown(cell_id: str, source: str) -> Any:
    cell = nbformat.v4.new_markdown_cell(source.strip())
    cell["id"] = cell_id
    return cell


def _code(cell_id: str, source: str) -> Any:
    cell = nbformat.v4.new_code_cell(source.strip())
    cell["id"] = cell_id
    return cell


def _notebook() -> Any:
    candidate_json = json.dumps(
        [
            {
                "label": candidate["label"],
                "handle": candidate["download_handle"],
            }
            for candidate in TPU_MODEL_CANDIDATES
        ],
        indent=4,
    )
    accelerator_json = repr(
        [
            {"label": candidate["label"], "strategy": candidate["strategy"]}
            for candidate in TPU_ACCELERATOR_CANDIDATES
        ]
    )
    cells = [
        _markdown(
            "title",
            """
# DueCare · Gemma 4 Tensor Processing Unit Training Lab

This public Kaggle learning notebook performs a **real, deliberately small**
parameter-efficient training run on Gemma 4 E2B. It uses Google's official
Transformers checkpoint on a Kaggle **Tensor Processing Unit (TPU)** and
**Low-Rank Adaptation (LoRA)**, which
freezes the base model and trains compact update matrices.

The run is designed to answer a narrow engineering question: can the attached
Gemma 4 checkpoint complete a reproducible adapter-training loop against
parent-diverse, public DueCare curriculum views and emit inspectable artifacts?

It does **not** establish legal accuracy, trafficking status, worker outcomes,
real-world safety improvement, or production readiness.
""",
        ),
        _markdown(
            "glossary",
            """
## Plain-language glossary

- **Supervised fine-tuning:** showing a model an input and a desired output,
  then updating parameters so the desired output becomes more likely.
- **Low-Rank Adaptation (LoRA):** a parameter-efficient method that trains
  small matrices while the original model weights remain frozen.
- **Tensor Processing Unit (TPU):** Google's accelerator for large tensor
  computations. This notebook records the number of devices that actually
  participate; it can use a one-device compatibility route when the runtime's
  multi-device process addresses are unavailable.
- **PyTorch/XLA:** the PyTorch integration that compiles tensor operations for
  accelerators such as a Tensor Processing Unit. XLA is the compiler/runtime
  name used by the project.
- **Parameter-Efficient Fine-Tuning (PEFT):** the broader family of methods
  that update a small share of a model; Low-Rank Adaptation is one example.
- **JavaScript Object Notation (JSON):** the machine-readable text format used
  for run receipts and summaries.
- **Training loss:** the model's error on examples it is currently learning.
  Falling loss shows fit, not necessarily useful transfer.
- **Learning rate:** the size of each parameter update.
- **Held-out prompt:** an evaluation prompt excluded from the training sample.
- **Harness:** deterministic checks applied outside the model. A separate
  four-arm notebook compares base/trained Gemma with and without that harness.
""",
        ),
        _markdown(
            "study-design",
            """
## Study design and stopping boundary

1. Verify the public dataset's exact release-manifest hash.
2. Select 32 training views with distinct parent hashes.
3. Convert each view into a compact prompt/response remix without adding facts.
4. capture base-model responses to two source-grounded held-out remixes;
5. train a rank-2 LoRA adapter for two epochs (eight optimizer steps);
6. capture adapted responses using the same prompts and decoding settings;
7. save loss, learning-rate, accuracy, timing, topology, parameter, and
   before/after graphics plus machine-readable JSON artifacts.

This is a quota-conscious pilot. Scaling to all 207,680 supervised rows should
follow only after the pilot is stable and a locked evaluation plan exists.
""",
        ),
        _code(
            "install",
            rf"""
import os
import subprocess
import sys

os.environ["PJRT_DEVICE"] = "TPU"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Keep Kaggle's matching torch and torch_xla pair intact. Only the model and
# adapter libraries are pinned here; upgrading torch independently can break
# the TPU runtime.
subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--quiet",
        "--upgrade",
        "transformers=={TRANSFORMERS_VERSION}",
        "peft=={PEFT_VERSION}",
        "accelerate",
        "sentencepiece",
    ],
    check=True,
)
print("Environment prepared for the PyTorch/XLA TPU backend.")
""",
        ),
        _code(
            "imports-style",
            r"""
import hashlib
import json
import math
import platform
import re
import time
from pathlib import Path

import importlib.metadata
import kagglehub
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import HTML, Markdown, display

plt.style.use("seaborn-v0_8-whitegrid")
COLORS = ["#1957A6", "#00A896", "#F4A261", "#C44536", "#6C5CE7", "#374151"]
OUT = Path("/kaggle/working/tpu-training-lab")
OUT.mkdir(parents=True, exist_ok=True)

print({
    "python": platform.python_version(),
    "transformers": importlib.metadata.version("transformers"),
    "peft": importlib.metadata.version("peft"),
    "torch": importlib.metadata.version("torch"),
    "torch_xla": importlib.metadata.version("torch-xla"),
})
""",
        ),
        _markdown(
            "identity-heading",
            """
## 1. Verify the release before reading rows

The manifest hash binds this run to one immutable public package. A different
hash stops the notebook instead of silently training on a different release.
""",
        ),
        _code(
            "verify-release",
            rf'''
EXPECTED_RELEASE_SHA256 = "{RELEASE_SHA256}"
input_root = Path("/kaggle/input")
manifest_paths = list(input_root.rglob("release-manifest.json"))
matches = []
for path in manifest_paths:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest == EXPECTED_RELEASE_SHA256:
        matches.append(path)

if len(matches) != 1:
    raise RuntimeError(
        f"Expected exactly one release manifest with SHA-256 {{EXPECTED_RELEASE_SHA256}}, found {{len(matches)}}."
    )

release_manifest_path = matches[0]
dataset_root = release_manifest_path.parent
release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
identity = pd.DataFrame([
    ("Public dataset", "{DATASET_ID}"),
    ("Release manifest SHA-256", EXPECTED_RELEASE_SHA256),
    ("Supervised training rows", "207,680"),
    ("Preference training pairs", "207,680"),
    ("Training mode here", "32 parent-diverse supervised views; 8 optimizer steps"),
    ("Publication state", "public learning artifact"),
], columns=["Field", "Value"])
display(identity.style.hide(axis="index").set_properties(**{{"text-align": "left"}}))
''',
        ),
        _markdown(
            "sample-heading",
            """
## 2. Select parent-diverse compact training views

The source rows can be long. For this small systems test, each prompt contains
exact excerpts from the approved DueCare prompt and selected response. Each
target recomposes exact sentences from the source review into three fields.
The transformation adds no case facts, retains the parent hash, and inherits
the parent's split.
""",
        ),
        _code(
            "load-sample",
            r"""
def iter_jsonl(paths):
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)


def section(text, start, end=None):
    if start not in text:
        return text
    value = text.split(start, 1)[1]
    if end and end in value:
        value = value.split(end, 1)[0]
    return value.strip()


def exact_excerpt(text, limit):
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    head = max(1, limit * 3 // 5)
    tail = max(1, limit - head - 5)
    return f"{compact[:head]} [...] {compact[-tail:]}"


def grounded_pair(row):
    messages = row.get("messages", [])
    user = next((str(m.get("content") or "") for m in messages if m.get("role") == "user"), "")
    source_target = next((str(m.get("content") or "") for m in reversed(messages) if m.get("role") == "assistant"), "")
    if not user or not source_target:
        raise RuntimeError(f"Grounded source row has an empty prompt or response: {row.get('id')}")
    original_prompt = section(user, "Original prompt:\n", "\n\nSelected response:\n")
    selected_response = section(user, "Selected response:\n", "\n\nReview task:")
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", " ".join(source_target.split()))
        if sentence.strip()
    ]
    observed = sentences[0]
    unknown = next(
        (sentence for sentence in sentences if "not " in sentence.lower() or "claim" in sentence.lower()),
        sentences[min(1, len(sentences) - 1)],
    )
    next_step = next(
        (sentence for sentence in sentences if "preserve" in sentence.lower() or "review" in sentence.lower()),
        sentences[-1],
    )
    prompt = (
        "Recompose only the supplied grounded excerpts into exactly three fields: "
        "Observed, Unknown, and Next. Do not add a fact, legal conclusion, or contact.\n\n"
        f"Grounded prompt excerpt: {exact_excerpt(original_prompt, 320)}\n\n"
        f"Grounded response excerpt: {exact_excerpt(selected_response, 480)}\n\n"
        f"Declared review task: {row['curriculum_task']}; audience: {row['audience']}; "
        f"format: {row['presentation_format']}."
    )
    response = (
        f"Observed: {exact_excerpt(observed, 180)} "
        f"Unknown: {exact_excerpt(unknown, 180)} "
        f"Next: {exact_excerpt(next_step, 180)}"
    )
    return {
        "prompt": prompt,
        "response": response,
        "parent": row["parent_row_sha256"],
        "source_row": row["id"],
        "source_row_sha256": row["sha256"],
        "source_prompt_sha256": hashlib.sha256(original_prompt.encode()).hexdigest(),
        "source_response_sha256": hashlib.sha256(selected_response.encode()).hexdigest(),
        "task": row["curriculum_task"],
        "audience": row["audience"],
        "format": row["presentation_format"],
        "split": row["split"],
        "transformation": "deterministic_source_grounded_remix",
    }


train_paths = sorted(dataset_root.rglob("supervised_train-*.jsonl"))
if not train_paths:
    raise FileNotFoundError("No supervised training shards were attached.")

selected = []
seen_parents = set()
for row in iter_jsonl(train_paths):
    parent = row["parent_row_sha256"]
    if parent in seen_parents:
        continue
    selected.append(grounded_pair(row))
    seen_parents.add(parent)
    if len(selected) == 32:
        break

if len(selected) != 32:
    raise RuntimeError(f"Expected 32 distinct parent rows, found {len(selected)}.")

sample_table = pd.DataFrame(selected)
sample_table["prompt_chars"] = sample_table["prompt"].str.len()
sample_table["response_chars"] = sample_table["response"].str.len()
display(HTML(sample_table[["parent", "task", "audience", "format", "prompt_chars", "response_chars"]].head(12).to_html(index=False, escape=True)))

if not all(row["transformation"] == "deterministic_source_grounded_remix" for row in selected):
    raise RuntimeError("Training sample contains a non-grounded transformation.")
""",
        ),
        _code(
            "sample-chart",
            r"""
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
sample_table["task"].str.replace("_", " ").value_counts().plot.barh(ax=axes[0], color=COLORS[0])
axes[0].set(title="Parent-diverse sample by review task", xlabel="Rows", ylabel="")
sample_table[["prompt_chars", "response_chars"]].plot.hist(ax=axes[1], bins=12, alpha=.72, color=COLORS[:2])
axes[1].set(title="Compact prompt and target lengths", xlabel="Characters", ylabel="Rows")
fig.tight_layout()
fig.savefig(OUT / "training_sample_profile.png", dpi=150, bbox_inches="tight")
plt.show()
""",
        ),
        _markdown(
            "tpu-heading",
            """
## 3. Resolve accelerator and model fallbacks

Gemma 4 E2B has about 2.3 billion effective parameters and 5.1 billion total
parameters when per-layer embeddings are counted. The preferred compatibility
route uses one real TPU device because this Kaggle runtime can advertise eight
devices while exposing only one process address. An all-device route remains a
recorded fallback for runtimes with a complete topology.

The loader is not tied to one brittle identifier. It tries operator-supplied
compatible paths, then attached official Google Gemma 4, Gemma 3, and Gemma 2
instruction checkpoints. A full failed training attempt advances to the next
candidate. The receipt records every resolution and attempt, and all claims
name the model that actually completed training. Each model/accelerator attempt
has a 30-minute default wall-clock budget so one incompatible compilation
cannot consume the entire TPU session. Operators can set
`DUECARE_TPU_ATTEMPT_TIMEOUT_SECONDS` between 300 and 2,700 seconds.
""",
        ),
        _code(
            "tpu-model",
            rf'''
MODEL_CANDIDATES = {candidate_json}
ACCELERATOR_CANDIDATES = {accelerator_json}

# Operators can prepend compatible local paths without editing the notebook.
# Every failed resolution is retained in the run receipt.
override_paths = [value for value in os.environ.get("DUECARE_TPU_MODEL_PATHS", "").split(os.pathsep) if value]
resolved_models = []
resolution_attempts = []
for path_value in override_paths:
    path = Path(path_value)
    valid = path.is_dir() and (path / "config.json").is_file()
    resolution_attempts.append({{"source": "operator_path", "value": path_value, "resolved": valid}})
    if valid:
        resolved_models.append({{"label": f"operator path: {{path.name}}", "handle": None, "path": str(path)}})

for candidate in MODEL_CANDIDATES:
    try:
        path = Path(kagglehub.model_download(candidate["handle"]))
        valid = path.is_dir() and (path / "config.json").is_file()
        resolution_attempts.append({{**candidate, "path": str(path), "resolved": valid}})
        if valid:
            resolved_models.append({{**candidate, "path": str(path)}})
    except Exception as exc:
        resolution_attempts.append({{**candidate, "resolved": False, "error": f"{{type(exc).__name__}}: {{str(exc)[:240]}}"}})

deduplicated = {{}}
for candidate in resolved_models:
    deduplicated.setdefault(str(Path(candidate["path"]).resolve()), candidate)
resolved_models = list(deduplicated.values())
if not resolved_models:
    raise RuntimeError("None of the configured Gemma checkpoints resolved. See resolution_attempts.")

display(pd.DataFrame(resolution_attempts))
display(pd.DataFrame(ACCELERATOR_CANDIDATES))
print(
    f"Resolved {{len(resolved_models)}} compatible model option(s) and "
    f"{{len(ACCELERATOR_CANDIDATES)}} accelerator route(s); complete attempts run in order."
)

''',
        ),
        _markdown(
            "baseline-heading",
            """
## 4. Capture the base model on held-out grounded remixes

These prompts descend from the dataset's test split, not the selected training
parents. They retain parent and source hashes and use the same deterministic
remix function. They test format discipline and uncertainty language, not
whether any person or event meets a legal definition.
""",
        ),
        _code(
            "baseline-generation",
            r"""
test_paths = sorted(dataset_root.rglob("supervised_test-*.jsonl"))
if not test_paths:
    raise FileNotFoundError("No supervised test shards were attached.")

held_out = []
heldout_parents = set()
for row in iter_jsonl(test_paths):
    parent = row["parent_row_sha256"]
    if parent in heldout_parents or parent in seen_parents:
        continue
    held_out.append(grounded_pair(row))
    heldout_parents.add(parent)
    if len(held_out) == 2:
        break
if len(held_out) != 2:
    raise RuntimeError(f"Expected two lineage-separated grounded test rows, found {len(held_out)}.")

HELD_OUT_PROMPTS = [row["prompt"] for row in held_out]
display(pd.DataFrame({
    "source parent": [row["parent"][:16] for row in held_out],
    "review task": [row["task"] for row in held_out],
    "prompt characters": [len(row["prompt"]) for row in held_out],
}))
print("The worker captures base responses before its first optimizer step.")
""",
        ),
        _markdown(
            "train-heading",
            """
## 5. Run eight real optimizer steps

The learning rate warms up for one step and then follows cosine decay. The
callback records batch loss, response-token accuracy, learning rate, and wall
time. Eight steps are enough to test the mechanism, not enough to justify a
quality claim.
""",
        ),
        _code(
            "train",
            r"""
import shutil

EPOCHS = 2
TOTAL_STEPS = 8
SEQUENCE_LENGTH = 256

training_input = OUT / "training-input.json"
heldout_input = OUT / "heldout-input.json"
training_input.write_text(json.dumps(selected, ensure_ascii=False), encoding="utf-8")
heldout_input.write_text(json.dumps(held_out, ensure_ascii=False), encoding="utf-8")

TRAINER_SCRIPT = r'''
import gc
import json
import math
import os
import time
from pathlib import Path

os.environ["PJRT_DEVICE"] = "TPU"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
ACCELERATOR_STRATEGY = os.environ["DUECARE_TPU_STRATEGY"]
if ACCELERATOR_STRATEGY == "pjrt_single_device":
    os.environ["TPU_NUM_DEVICES"] = "1"

import torch
import torch_xla
import torch_xla.core.xla_model as xm
import torch_xla.distributed.xla_multiprocessing as xmp
import torch_xla.runtime as xr
from peft import LoraConfig, get_peft_model, get_peft_model_state_dict
from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer

OUT = Path(os.environ["DUECARE_OUT"])
MODEL_PATH = os.environ["DUECARE_MODEL_PATH"]
MODEL_LABEL = os.environ["DUECARE_MODEL_LABEL"]
MODEL_HANDLE = os.environ.get("DUECARE_MODEL_HANDLE") or None
TRAINING = json.loads(Path(os.environ["DUECARE_TRAINING_INPUT"]).read_text(encoding="utf-8"))
HELDOUT = json.loads(Path(os.environ["DUECARE_HELDOUT_INPUT"]).read_text(encoding="utf-8"))
MAX_LENGTH = 256
MAX_NEW_TOKENS = 96
STEPS = 8


def chat_text(tokenizer, prompt, response=None):
    messages = [{"role": "user", "content": prompt}]
    if response is not None:
        messages.append({"role": "assistant", "content": response})
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=response is None,
    )


def encoded_example(tokenizer, row, device):
    prompt_text = chat_text(tokenizer, row["prompt"])
    full_text = chat_text(tokenizer, row["prompt"], row["response"])
    encoded = tokenizer(
        full_text,
        add_special_tokens=False,
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
        return_tensors="pt",
    )
    prompt_ids = tokenizer(
        prompt_text,
        add_special_tokens=False,
        truncation=True,
        max_length=MAX_LENGTH,
    )["input_ids"]
    labels = encoded["input_ids"].clone()
    labels[:, : min(len(prompt_ids), MAX_LENGTH)] = -100
    labels[encoded["attention_mask"] == 0] = -100
    return {
        "input_ids": encoded["input_ids"].to(device),
        "attention_mask": encoded["attention_mask"].to(device),
        "labels": labels.to(device),
    }


def generate(model, tokenizer, prompts, device):
    outputs = []
    model.eval()
    with torch.no_grad():
        for prompt in prompts:
            text = chat_text(tokenizer, prompt)
            batch = tokenizer(
                text,
                add_special_tokens=False,
                return_tensors="pt",
                truncation=True,
                max_length=MAX_LENGTH,
            )
            input_length = batch["input_ids"].shape[-1]
            batch = {key: value.to(device) for key, value in batch.items()}
            generated = model.generate(
                **batch,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                use_cache=False,
            )
            outputs.append(tokenizer.decode(generated[0, input_length:].cpu(), skip_special_tokens=True))
            xm.mark_step()
    return outputs


def learning_rate(step):
    if step == 0:
        return 1e-4
    progress = (step - 1) / max(1, STEPS - 2)
    return 1e-5 + 0.5 * (2e-4 - 1e-5) * (1 + math.cos(math.pi * progress))


def worker(_index):
    rank = xr.global_ordinal()
    world_size = xr.world_size()
    if world_size < 1:
        raise RuntimeError(f"Expected at least one TPU worker, found {world_size}")
    device = torch_xla.device()
    load_started = time.perf_counter()
    try:
        processor = AutoProcessor.from_pretrained(MODEL_PATH, local_files_only=True)
        tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor
    except Exception:
        processor = None
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        dtype=torch.bfloat16,
        attn_implementation="eager",
        low_cpu_mem_usage=True,
        local_files_only=True,
    )
    model.config.use_cache = False
    projection_names = {"q_proj", "k_proj", "v_proj", "o_proj"}
    target_modules = []
    for module_name, module in model.named_modules():
        pieces = module_name.split(".")
        is_projection = bool(pieces) and pieces[-1] in projection_names
        is_wrapped_projection = (
            len(pieces) > 1
            and pieces[-1] == "linear"
            and pieces[-2] in projection_names
        )
        is_text_path = not any(part in {"audio_tower", "vision_tower"} for part in pieces)
        if isinstance(module, torch.nn.Linear) and is_text_path and (is_projection or is_wrapped_projection):
            target_modules.append(module_name)
    if not target_modules:
        raise RuntimeError("No compatible text projection modules were found for Low-Rank Adaptation")
    model = get_peft_model(
        model,
        LoraConfig(
            r=2,
            lora_alpha=4,
            lora_dropout=0.0,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=target_modules,
        ),
    )
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    model.to(device)
    xm.mark_step()
    model_load_seconds = time.perf_counter() - load_started
    total_parameters = sum(parameter.numel() for parameter in model.parameters())
    trainable_parameters = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)

    base_outputs = []
    base_generation_seconds = 0.0
    if rank == 0:
        started = time.perf_counter()
        base_outputs = generate(model, tokenizer, [row["prompt"] for row in HELDOUT], device)
        base_generation_seconds = time.perf_counter() - started
    xm.rendezvous("base-generation-complete")

    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=2e-4,
        weight_decay=0.01,
    )
    model.train()
    records = []
    train_started = time.perf_counter()
    for step in range(STEPS):
        step_started = time.perf_counter()
        row = TRAINING[(step * world_size + rank) % len(TRAINING)]
        batch = encoded_example(tokenizer, row, device)
        lr_value = learning_rate(step)
        for group in optimizer.param_groups:
            group["lr"] = lr_value
        optimizer.zero_grad(set_to_none=True)
        result = model(**batch)
        loss = result.loss
        with torch.no_grad():
            shifted_logits = result.logits[:, :-1].argmax(dim=-1)
            shifted_labels = batch["labels"][:, 1:]
            mask = shifted_labels.ne(-100)
            correct = shifted_logits.eq(shifted_labels).logical_and(mask).sum()
            accuracy = correct.float() / mask.sum().clamp_min(1)
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(
            [parameter for parameter in model.parameters() if parameter.requires_grad],
            max_norm=1.0,
        )
        xm.optimizer_step(optimizer, barrier=True)
        xm.mark_step()
        records.append({
            "rank": rank,
            "step": step + 1,
            "loss": float(loss.detach().cpu()),
            "response_token_accuracy": float(accuracy.detach().cpu()),
            "grad_norm": float(torch.as_tensor(grad_norm).detach().cpu()),
            "learning_rate": lr_value,
            "step_seconds": time.perf_counter() - step_started,
            "source_row_id": row["source_row"],
            "parent_row_sha256": row["parent"],
        })
        del result, loss, batch
    training_seconds = time.perf_counter() - train_started
    (OUT / f"rank-{rank}-metrics.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    xm.rendezvous("training-complete")

    adapted_outputs = []
    adapted_generation_seconds = 0.0
    if rank == 0:
        started = time.perf_counter()
        adapted_outputs = generate(model, tokenizer, [row["prompt"] for row in HELDOUT], device)
        adapted_generation_seconds = time.perf_counter() - started
        adapter_dir = OUT / "adapter"
        adapter_dir.mkdir(parents=True, exist_ok=True)
        state = {key: value.detach().cpu() for key, value in get_peft_model_state_dict(model).items()}
        model.save_pretrained(adapter_dir, state_dict=state, safe_serialization=True)
        tokenizer.save_pretrained(adapter_dir)
        with (OUT / "heldout-before-after.jsonl").open("w", encoding="utf-8") as handle:
            for index, row in enumerate(HELDOUT):
                handle.write(json.dumps({
                    "case": row["source_row"],
                    "prompt": row["prompt"],
                    "source_row_id": row["source_row"],
                    "source_row_sha256": row["source_row_sha256"],
                    "parent_row_sha256": row["parent"],
                    "base_response": base_outputs[index],
                    "adapted_response": adapted_outputs[index],
                    "grounded_remix": True,
                    "transformation": "deterministic_source_grounded_remix",
                }, ensure_ascii=False) + "\n")
        summary = {
            "selected_model_label": MODEL_LABEL,
            "selected_model_handle": MODEL_HANDLE,
            "selected_model_path": MODEL_PATH,
            "accelerator_strategy": ACCELERATOR_STRATEGY,
            "world_size": world_size,
            "device": str(device),
            "model_load_seconds": model_load_seconds,
            "training_seconds": training_seconds,
            "base_generation_seconds": base_generation_seconds,
            "adapted_generation_seconds": adapted_generation_seconds,
            "total_parameters": total_parameters,
            "trainable_parameters": trainable_parameters,
            "trainable_share": trainable_parameters / total_parameters,
            "adapter_target_modules": target_modules,
            "sequence_length": MAX_LENGTH,
            "max_new_tokens": MAX_NEW_TOKENS,
            "optimizer_steps": STEPS,
            "packages": {
                "torch": torch.__version__,
                "torch_xla": __import__("torch_xla").__version__,
                "transformers": __import__("transformers").__version__,
                "peft": __import__("peft").__version__,
            },
        }
        (OUT / "worker-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    xm.rendezvous("artifacts-saved")
    del model
    gc.collect()


if __name__ == "__main__":
    process_count = 1 if ACCELERATOR_STRATEGY == "pjrt_single_device" else None
    xmp.spawn(worker, args=(), nprocs=process_count, start_method="fork")
'''

compile(TRAINER_SCRIPT, "duecare_tpu_worker.py", "exec")
trainer_script = OUT / "duecare_tpu_worker.py"
trainer_script.write_text(TRAINER_SCRIPT, encoding="utf-8")

model_attempts = []
selected_model = None
selected_accelerator = None
attempt_timeout_seconds = int(
    os.environ.get("DUECARE_TPU_ATTEMPT_TIMEOUT_SECONDS", "1800")
)
if not 300 <= attempt_timeout_seconds <= 2700:
    raise ValueError(
        "DUECARE_TPU_ATTEMPT_TIMEOUT_SECONDS must be between 300 and 2700"
    )
for candidate in resolved_models:
    for accelerator in ACCELERATOR_CANDIDATES:
        for path in list(OUT.glob("rank-*-metrics.json")) + [
            OUT / "worker-summary.json",
            OUT / "heldout-before-after.jsonl",
        ]:
            path.unlink(missing_ok=True)
        shutil.rmtree(OUT / "adapter", ignore_errors=True)
        environment = dict(os.environ)
        environment.pop("TPU_NUM_DEVICES", None)
        environment.update({
            "PJRT_DEVICE": "TPU",
            "DUECARE_TPU_STRATEGY": accelerator["strategy"],
            "DUECARE_OUT": str(OUT),
            "DUECARE_MODEL_PATH": candidate["path"],
            "DUECARE_MODEL_LABEL": candidate["label"],
            "DUECARE_MODEL_HANDLE": candidate.get("handle") or "",
            "DUECARE_TRAINING_INPUT": str(training_input),
            "DUECARE_HELDOUT_INPUT": str(heldout_input),
        })
        started = time.perf_counter()
        timed_out = False
        try:
            completed = subprocess.run(
                [sys.executable, str(trainer_script)],
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=attempt_timeout_seconds,
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = 124
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            stderr += (
                f"\nDueCare stopped this fallback attempt after "
                f"{attempt_timeout_seconds} seconds so the next compatible "
                "model/accelerator route could run.\n"
            )
        attempt_number = len(model_attempts) + 1
        stdout_path = OUT / f"attempt-{attempt_number:02d}.stdout.log"
        stderr_path = OUT / f"attempt-{attempt_number:02d}.stderr.log"
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        attempt = {
            "label": candidate["label"],
            "handle": candidate.get("handle"),
            "path": candidate["path"],
            "accelerator_label": accelerator["label"],
            "accelerator_strategy": accelerator["strategy"],
            "returncode": returncode,
            "timed_out": timed_out,
            "attempt_timeout_seconds": attempt_timeout_seconds,
            "elapsed_seconds": time.perf_counter() - started,
            "stdout_log": stdout_path.name,
            "stderr_log": stderr_path.name,
            "stderr_tail": stderr[-1000:],
        }
        model_attempts.append(attempt)
        if returncode == 0 and (OUT / "worker-summary.json").is_file():
            selected_model = candidate
            selected_accelerator = accelerator
            break
    if selected_model is not None:
        break

(OUT / "model-resolution-receipt.json").write_text(
    json.dumps({"resolution_attempts": resolution_attempts, "training_attempts": model_attempts}, indent=2),
    encoding="utf-8",
)
if selected_model is None or selected_accelerator is None:
    raise RuntimeError("Every configured TPU model training attempt failed. See model-resolution-receipt.json.")

worker_summary = json.loads((OUT / "worker-summary.json").read_text(encoding="utf-8"))
rank_metrics = pd.concat(
    [pd.DataFrame(json.loads(path.read_text(encoding="utf-8"))) for path in sorted(OUT.glob("rank-*-metrics.json"))],
    ignore_index=True,
)
metrics = rank_metrics.groupby("step", as_index=False).agg(
    loss=("loss", "mean"),
    loss_std=("loss", "std"),
    response_token_accuracy=("response_token_accuracy", "mean"),
    grad_norm=("grad_norm", "mean"),
    learning_rate=("learning_rate", "first"),
    step_seconds=("step_seconds", "max"),
)
metrics["loss_std"] = metrics["loss_std"].fillna(0.0)
if len(metrics) != TOTAL_STEPS or metrics["loss"].isna().any():
    raise RuntimeError("The TPU loop did not produce eight complete optimizer-step summaries.")
metrics.to_json(OUT / "tpu-training-metrics.json", orient="records", indent=2)

total_parameters = int(worker_summary["total_parameters"])
trainable_parameters = int(worker_summary["trainable_parameters"])
training_seconds = float(worker_summary["training_seconds"])
base_generation_seconds = float(worker_summary["base_generation_seconds"])
adapted_generation_seconds = float(worker_summary["adapted_generation_seconds"])
tpu_devices = [f"TPU:{index}" for index in range(int(worker_summary["world_size"]))]

topology = pd.DataFrame({
    "worker": range(len(tpu_devices)),
    "device": tpu_devices,
    "accelerator strategy": [worker_summary["accelerator_strategy"]] * len(tpu_devices),
})
display(topology)
fig, ax = plt.subplots(figsize=(max(6, len(tpu_devices) * 1.6), 2.8))
for index, device in enumerate(tpu_devices):
    ax.add_patch(plt.Rectangle((index, 0), .86, .8, color=COLORS[index % len(COLORS)], alpha=.9))
    ax.text(index + .43, .4, f"Worker {index}\n{device}", ha="center", va="center", color="white", fontsize=9, weight="bold")
ax.set(xlim=(-.1, max(1, len(tpu_devices))), ylim=(-.1, 1), title="Worker-reported TPU topology")
ax.axis("off")
fig.tight_layout()
fig.savefig(OUT / "tpu_topology.png", dpi=150, bbox_inches="tight")
plt.show()

display(pd.DataFrame(model_attempts))
display(metrics.style.format({
    "loss": "{:.5f}",
    "loss_std": "{:.5f}",
    "response_token_accuracy": "{:.4f}",
    "grad_norm": "{:.4f}",
    "learning_rate": "{:.7f}",
    "step_seconds": "{:.2f}",
}))

parameter_table = pd.DataFrame([
    ("Selected model", worker_summary["selected_model_label"]),
    ("Total parameters", total_parameters),
    ("Trainable LoRA parameters", trainable_parameters),
    ("Trainable share", trainable_parameters / total_parameters),
    ("Accelerator strategy", worker_summary["accelerator_strategy"]),
    ("TPU workers", worker_summary["world_size"]),
], columns=["Metric", "Value"])
display(parameter_table)

fig, ax = plt.subplots(figsize=(8, 4.5))
values = [total_parameters - trainable_parameters, trainable_parameters]
ax.bar(["Frozen/base", "Trainable LoRA"], values, color=[COLORS[0], COLORS[2]])
ax.set_yscale("log")
ax.set(title="Parameter-efficient training allocation", ylabel="Parameters · logarithmic scale")
for index, value in enumerate(values):
    ax.text(index, value, f"{value:,}", ha="center", va="bottom", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "parameter_allocation.png", dpi=150, bbox_inches="tight")
plt.show()
""",
        ),
        _markdown(
            "curves-heading",
            """
## 6. Learning curves and optimization diagnostics

Read these together. Lower training loss is encouraging only if held-out
behavior also improves without introducing unsupported certainty.
""",
        ),
        _code(
            "curves",
            r"""
fig, axes = plt.subplots(2, 2, figsize=(14, 9))
metrics.plot(x="step", y="loss", marker="o", color=COLORS[0], ax=axes[0, 0], legend=False)
metrics.assign(smoothed_loss=metrics["loss"].rolling(3, min_periods=1).mean()).plot(
    x="step", y="smoothed_loss", marker="o", color=COLORS[1], ax=axes[0, 1], legend=False
)
metrics.plot(x="step", y="learning_rate", marker="o", color=COLORS[2], ax=axes[1, 0], legend=False)
metrics.plot(x="step", y="response_token_accuracy", marker="o", color=COLORS[4], ax=axes[1, 1], legend=False)
axes[0, 0].set(title="Per-step training loss", ylabel="Cross-entropy loss")
axes[0, 1].set(title="Three-step smoothed training loss", ylabel="Smoothed loss")
axes[1, 0].set(title="Learning-rate warm-up and cosine decay", ylabel="Learning rate")
axes[1, 1].set(title="Response-token accuracy", ylabel="Weighted accuracy")
for ax in axes.flat:
    ax.set_xlabel("Optimizer step")
fig.tight_layout()
fig.savefig(OUT / "tpu_learning_curves.png", dpi=150, bbox_inches="tight")
plt.show()

fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
metrics.plot(x="step", y="step_seconds", marker="o", color=COLORS[3], ax=axes[0], legend=False)
axes[0].axhline(metrics["step_seconds"].median(), color=COLORS[5], ls="--", label=f"median {metrics['step_seconds'].median():.1f}s")
axes[0].set(title="TPU optimizer-step duration", xlabel="Optimizer step", ylabel="Seconds")
axes[0].legend()
metrics.plot(x="step", y="grad_norm", marker="o", color=COLORS[4], ax=axes[1], legend=False)
axes[1].axhline(1.0, color=COLORS[3], ls="--", label="clip threshold")
axes[1].set(title="Mean pre-clipping gradient norm", xlabel="Optimizer step", ylabel="Gradient norm")
axes[1].legend()
metrics.plot(x="step", y="loss_std", marker="o", color=COLORS[1], ax=axes[2], legend=False)
axes[2].set(title="Loss dispersion across active TPU workers", xlabel="Optimizer step", ylabel="Standard deviation")
fig.tight_layout()
fig.savefig(OUT / "tpu_optimization_diagnostics.png", dpi=150, bbox_inches="tight")
plt.show()
""",
        ),
        _markdown(
            "after-heading",
            """
## 7. Re-run the same held-out prompts after training

Side-by-side text is evidence of what this exact run emitted. It is not an
independent quality judgment. The lightweight marker audit below measures only
whether visible boundary concepts appear; it does not grade factual or legal
correctness.
""",
        ),
        _code(
            "after-generation",
            r"""
comparison_records = list(iter_jsonl([OUT / "heldout-before-after.jsonl"]))
if len(comparison_records) != len(held_out):
    raise RuntimeError("The TPU worker did not emit the complete held-out before/after set.")
comparisons = pd.DataFrame({
    "case": [row["case"] for row in comparison_records],
    "parent": [row["parent_row_sha256"] for row in comparison_records],
    "base response": [row["base_response"] for row in comparison_records],
    "adapted response": [row["adapted_response"] for row in comparison_records],
})
base_outputs = comparisons["base response"].tolist()
adapted_outputs = comparisons["adapted response"].tolist()
display(HTML(comparisons.to_html(index=False, escape=True)))

MARKERS = {
    "observation language": ("observ", "record", "document"),
    "uncertainty language": ("unknown", "missing", "insufficient", "uncertain"),
    "conflict language": ("conflict", "contradict", "disagree"),
    "claim boundary": ("not a legal", "no legal finding", "does not establish", "do not infer"),
    "human review": ("human review", "reviewer", "corrobor"),
}


def marker_score(text):
    lowered = text.lower()
    return {name: int(any(token in lowered for token in tokens)) for name, tokens in MARKERS.items()}


marker_rows = []
for case_index, case_name in enumerate(comparisons["case"]):
    for arm, outputs in (("base", base_outputs), ("adapted", adapted_outputs)):
        marker_rows.append({"case": case_name, "arm": arm, **marker_score(outputs[case_index])})
marker_frame = pd.DataFrame(marker_rows)
display(marker_frame)

marker_totals = marker_frame.groupby("arm")[list(MARKERS)].sum().T
fig, ax = plt.subplots(figsize=(10, 5))
marker_totals.plot.bar(ax=ax, color=COLORS[:2])
ax.set(title="Visible boundary-marker coverage on two held-out prompts", xlabel="Marker", ylabel="Cases containing marker")
ax.tick_params(axis="x", rotation=25)
fig.tight_layout()
fig.savefig(OUT / "heldout_marker_coverage.png", dpi=150, bbox_inches="tight")
plt.show()
""",
        ),
        _markdown(
            "save-heading",
            """
## 8. Save the adapter and a manifest-bound run record

The output is the compact LoRA delta, not a merged production model. Loading
it later requires the exact selected base checkpoint plus compatible
Transformers and Parameter-Efficient Fine-Tuning (PEFT) versions.
""",
        ),
        _code(
            "save",
            rf'''
adapter_path = OUT / "adapter" / "adapter_model.safetensors"
if not adapter_path.is_file():
    raise FileNotFoundError("The TPU worker did not save adapter_model.safetensors.")
adapter_sha256 = hashlib.sha256(adapter_path.read_bytes()).hexdigest()
summary = {{
    "schema_version": "duecare.gemma_family.tpu_lora_pilot.v2",
    "dataset_id": "{DATASET_ID}",
    "release_manifest_sha256": EXPECTED_RELEASE_SHA256,
    "selected_model_label": worker_summary["selected_model_label"],
    "selected_model_handle": worker_summary["selected_model_handle"],
    "model_fallbacks_configured": len(MODEL_CANDIDATES) + len(override_paths),
    "model_resolution_receipt": "model-resolution-receipt.json",
    "packages": worker_summary["packages"],
    "accelerator": "Kaggle TPU via PyTorch/XLA",
    "accelerator_strategy": worker_summary["accelerator_strategy"],
    "tpu_cores": worker_summary["world_size"],
    "training_completed": True,
    "training_rows": len(selected),
    "unique_parent_rows": len(seen_parents),
    "training_data_policy": "deterministic remixes of approved DueCare prompts and responses only",
    "free_standing_fictional_generation": False,
    "heldout_grounded_rows": len(held_out),
    "heldout_parent_overlap_with_training": len(heldout_parents & seen_parents),
    "optimizer_steps": len(metrics),
    "epochs": EPOCHS,
    "global_batch_size": worker_summary["world_size"],
    "sequence_length": worker_summary["sequence_length"],
    "lora_rank": 2,
    "total_parameters": total_parameters,
    "trainable_parameters": trainable_parameters,
    "trainable_share": trainable_parameters / total_parameters,
    "initial_loss": float(metrics.iloc[0]["loss"]),
    "final_loss": float(metrics.iloc[-1]["loss"]),
    "training_seconds": training_seconds,
    "base_generation_seconds": base_generation_seconds,
    "adapted_generation_seconds": adapted_generation_seconds,
    "adapter_path": str(adapter_path),
    "adapter_sha256": adapter_sha256,
    "adapter_produced": True,
    "victim_identification_improvement_demonstrated": False,
    "field_detection_improvement_demonstrated": False,
    "real_world_model_lift_demonstrated": False,
    "production_ready": False,
    "claim_scope": "Real TPU LoRA mechanism pilot on the selected fallback-registry model; before/after text and marker coverage on two lineage-separated grounded-remix holdout prompts only.",
    "charts": sorted(path.name for path in OUT.glob("*.png")),
}}
(OUT / "tpu-training-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
display(pd.DataFrame([
    ("TPU training completed", summary["training_completed"]),
    ("Adapter produced", summary["adapter_produced"]),
    ("Initial training loss", summary["initial_loss"]),
    ("Final training loss", summary["final_loss"]),
    ("Victim-identification improvement demonstrated", summary["victim_identification_improvement_demonstrated"]),
    ("Field-detection improvement demonstrated", summary["field_detection_improvement_demonstrated"]),
    ("Real-world model lift demonstrated", summary["real_world_model_lift_demonstrated"]),
    ("Production ready", summary["production_ready"]),
], columns=["Claim", "Evidence"]).style.hide(axis="index"))
print(json.dumps(summary, indent=2))
''',
        ),
        _markdown(
            "interpretation",
            """
## How to interpret the run

- A completed loop and saved adapter prove the training mechanism worked.
- Falling loss proves fit to these 32 compact views; it does not prove transfer.
- This pilot does not measure victim-identification accuracy, field-detection
  effectiveness, prevalence, legal findings, or worker outcomes.
- The before/after texts show observable behavior on two held-out grounded
  remixes. They are too few and too dependent on their source families for a
  general improvement claim.
- The separate four-arm notebook tests the base model and trained model both
  with and without the deterministic harness. Its harness gains are structural
  because the harness enforces required fields; they are not evidence that the
  model learned those safeguards internally.
- A promotion study needs larger parent-diverse training samples, locked
  lineage-separated evaluation, blinded human review, safety slices, and
  uncertainty intervals.
""",
        ),
    ]

    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    return notebook


def _validate_python_cells(notebook: Any, output_dir: Path) -> None:
    validation_dir = output_dir / ".validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        path = validation_dir / f"cell-{index:02d}.py"
        path.write_text(cell.source, encoding="utf-8")
        py_compile.compile(str(path), doraise=True)
        tree = ast.parse(cell.source, filename=str(path))
        json_literal_names = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        } & {"null", "true", "false"}
        if json_literal_names:
            raise ValueError(
                f"JSON literals embedded as Python names in cell {index}: "
                f"{sorted(json_literal_names)}"
            )


def build(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    notebook = _notebook()
    notebook_path = output_dir / "notebook.ipynb"
    nbformat.write(notebook, notebook_path)
    _validate_python_cells(notebook, output_dir)

    metadata = {
        "id": KERNEL_ID,
        "title": "DueCare Gemma 4 TPU LoRA Training Lab",
        "code_file": notebook_path.name,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": True,
        "enable_internet": True,
        "dataset_sources": [DATASET_ID],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": MODEL_SOURCES,
        "docker_image_pinning_type": "original",
        "keywords": ["nlp"],
    }
    (output_dir / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "schema_version": "duecare.gemma4.tpu_training_notebook.v1",
        "kernel_id": KERNEL_ID,
        "dataset_id": DATASET_ID,
        "release_manifest_sha256": RELEASE_SHA256,
        "model_sources": MODEL_SOURCES,
        "model_fallback_registry": str(FALLBACK_REGISTRY_PATH.relative_to(ROOT)),
        "model_fallback_registry_schema": FALLBACK_REGISTRY["schema_version"],
        "model_resolution_order": [
            "operator-supplied compatible local paths",
            *[candidate["label"] for candidate in TPU_MODEL_CANDIDATES],
        ],
        "accelerator_resolution_order": [
            candidate["label"] for candidate in TPU_ACCELERATOR_CANDIDATES
        ],
        "fallback_attempt_timeout_seconds": 1800,
        "fallback_attempt_timeout_override": (
            "DUECARE_TPU_ATTEMPT_TIMEOUT_SECONDS (300 to 2700 seconds)"
        ),
        "transformers_version": TRANSFORMERS_VERSION,
        "peft_version": PEFT_VERSION,
        "accelerator": "Kaggle TPU with recorded compatibility fallbacks",
        "code_cells_compiled": True,
        "remote_training_completed": False,
    }
    (output_dir / "build-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build(args.output_dir.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
