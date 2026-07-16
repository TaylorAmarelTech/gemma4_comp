#!/usr/bin/env python3
"""Build a public from-scratch TPU language-model training notebook."""

# Embedded notebook cells favor readable, copyable statements over builder
# line wrapping. Each generated code cell is compiled below.
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
DEFAULT_OUTPUT = (
    ROOT / "reports" / "kaggle_publish" / "grounded_scratch_tpu_notebook_v1"
)
KERNEL_ID = "taylorsamarel/duecare-grounded-byte-model-training-lab"
DATASET_ID = "taylorsamarel/duecare-measured-review-curriculum-200k"
RELEASE_SHA256 = "1b062ce12fe43494f7d63659a53017c857e0ac0103759d8f71b3340f63bdc2b7"
REGISTRY_PATH = ROOT / "configs" / "duecare" / "model_fallbacks.json"
REGISTRY = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
POLICY = REGISTRY["policies"]["kaggle_tpu_from_scratch_training"]
ARCHITECTURES = POLICY["candidates"]


def _markdown(identifier: str, source: str) -> Any:
    cell = nbformat.v4.new_markdown_cell(source.strip())
    cell["id"] = identifier
    return cell


def _code(identifier: str, source: str) -> Any:
    cell = nbformat.v4.new_code_cell(source.strip())
    cell["id"] = identifier
    return cell


def _notebook() -> Any:
    architecture_literal = repr(ARCHITECTURES)
    cells = [
        _markdown(
            "title",
            """
# DueCare · grounded byte transformer from scratch

<div style="padding:25px 30px;border-radius:18px;background:linear-gradient(120deg,#102a43,#136f63,#f2b134);color:white">
<b style="letter-spacing:.12em;text-transform:uppercase">Kaggle TPU learning laboratory</b>
<h2 style="margin:.4em 0">No pretrained checkpoint and no borrowed tokenizer</h2>
<p style="font-size:16px;line-height:1.5">This notebook initializes every
model parameter at random, learns a byte-level tokenizer contract, performs
real optimization on grounded DueCare remixes, and publishes the complete
training receipt.</p></div>

This is an educational mechanism baseline. It does **not** claim that a small
model trained for a few steps is useful for legal analysis, worker support,
trafficking classification, or production deployment.
""",
        ),
        _markdown(
            "terms",
            """
## Start here: plain-language terms

- **Training from scratch** means the model begins with random weights rather
  than loading a pretrained checkpoint.
- A **byte tokenizer** represents text with the 256 possible byte values plus
  start, end, and padding symbols. It needs no external vocabulary model.
- A **decoder-only transformer** predicts the next byte using causal
  self-attention, so it cannot look ahead at future target bytes.
- A **Tensor Processing Unit (TPU)** is Google's tensor accelerator.
- **JAX** is the numerical computing framework used here to compile the model
  to the TPU.
- **Unicode Transformation Format, 8-bit (UTF-8)** is the standard text
  encoding converted into byte identifiers by this notebook.
- **JavaScript Object Notation (JSON)** stores readable configuration and run
  receipts; a NumPy `.npz` archive stores the complete numeric parameter tree.
- **Cross-entropy loss** measures next-byte prediction error. Falling training
  loss proves fit to the sampled stream, not general reasoning or safety.
- A **held-out parent** is a source lineage excluded from optimization.

The 207,680-row public supervised curriculum is the source pool. The primary
Tensor Processing Unit profile selects 96 unique training parents, 8 held-out
parents, and 24 optimizer steps per architecture. If a Tensor Processing Unit
is unavailable, a clearly labeled central-processing-unit compatibility
profile uses 16/4 parents and 2 steps. Every selected row retains its source
and parent hashes; no free-standing fictional examples are generated.
""",
        ),
        _code(
            "setup",
            rf'''
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from pathlib import Path

import jax
import jax.numpy as jnp
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import HTML, Markdown, display

DATASET_ID = {DATASET_ID!r}
EXPECTED_RELEASE_SHA256 = {RELEASE_SHA256!r}
ARCHITECTURES = {architecture_literal}
OUT = Path(os.environ.get("DUECARE_SCRATCH_OUTPUT_DIR", "/kaggle/working/from-scratch-tpu"))
OUT.mkdir(parents=True, exist_ok=True)
COLORS = ["#136f63", "#f2b134", "#d1495b", "#247ba0", "#6d597a", "#4f772d"]
plt.style.use("seaborn-v0_8-whitegrid")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


manifest_candidates = []
dataset_override = os.environ.get("DUECARE_SCRATCH_DATASET_ROOT")
if dataset_override:
    manifest_candidates.append(Path(dataset_override) / "release-manifest.json")
if Path("/kaggle/input").exists():
    manifest_candidates.extend(Path("/kaggle/input").rglob("release-manifest.json"))
manifest_matches = []
for path in manifest_candidates:
    if sha256_file(path) == EXPECTED_RELEASE_SHA256:
        manifest_matches.append(path)
if len(manifest_matches) != 1:
    raise RuntimeError(f"Expected one attached release manifest, found {{len(manifest_matches)}}")
dataset_root = manifest_matches[0].parent
release = json.loads(manifest_matches[0].read_text(encoding="utf-8"))

devices = jax.devices()
if not devices:
    raise RuntimeError("JAX reported no compute devices")
backend = jax.default_backend()
tpu_devices = [device for device in devices if device.platform == "tpu"]
if backend == "tpu":
    runtime_profile = {{
        "name": "tpu_primary",
        "training_parent_limit": 96,
        "heldout_parent_limit": 8,
        "optimizer_steps": 24,
        "batch_size": 4,
    }}
else:
    runtime_profile = {{
        "name": "cpu_compatibility_fallback",
        "training_parent_limit": 16,
        "heldout_parent_limit": 4,
        "optimizer_steps": 2,
        "batch_size": 2,
    }}
    display(Markdown(
        "**Compatibility fallback active:** no Tensor Processing Unit was "
        "visible. This run is recorded as a central-processing-unit mechanism "
        "smoke test and cannot support a Tensor Processing Unit claim."
    ))

identity = pd.DataFrame([
    ("Dataset", DATASET_ID),
    ("Release manifest SHA-256", EXPECTED_RELEASE_SHA256),
    ("JAX backend", backend),
    ("Runtime profile", runtime_profile["name"]),
    ("Visible compute devices", len(devices)),
    ("Visible TPU devices", len(tpu_devices)),
    ("Pretrained model loaded", False),
    ("External tokenizer loaded", False),
], columns=["Field", "Verified value"])
display(identity.style.hide(axis="index"))
''',
        ),
        _markdown(
            "data-heading",
            """
## 1. Select grounded rows and preserve lineage

The selection is deterministic. It uses distinct parent hashes and keeps train
and test lineages separate. The model sees only approved public curriculum
rows. Row count is scale; unique parent count is the more honest diversity
measure.
""",
        ),
        _code(
            "data",
            r'''
def iter_jsonl(paths):
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)


def compact(text, limit=540):
    value = " ".join(str(text).split())
    if len(value) <= limit:
        return value
    head = limit * 3 // 5
    return value[:head] + " [...] " + value[-(limit - head - 7):]


def training_text(row):
    messages = row["messages"]
    user = next(str(item["content"]) for item in messages if item["role"] == "user")
    answer = next(str(item["content"]) for item in reversed(messages) if item["role"] == "assistant")
    return compact(user, 430) + "\n<ANSWER>\n" + compact(answer, 430)


def select_unique(paths, count):
    rows, parents = [], set()
    for row in iter_jsonl(paths):
        parent = row["parent_row_sha256"]
        if parent in parents:
            continue
        rows.append({
            "id": row["id"],
            "parent": parent,
            "family": row["parent_lineage_family_id"],
            "task": row["curriculum_task"],
            "audience": row["audience"],
            "format": row["presentation_format"],
            "sha256": row["sha256"],
            "text": training_text(row),
        })
        parents.add(parent)
        if len(rows) == count:
            return rows
    raise RuntimeError(f"Expected {count} unique parents, found {len(rows)}")


train_rows = select_unique(
    sorted(dataset_root.rglob("supervised_train-*.jsonl")),
    runtime_profile["training_parent_limit"],
)
heldout_rows = select_unique(
    sorted(dataset_root.rglob("supervised_test-*.jsonl")),
    runtime_profile["heldout_parent_limit"],
)
train_parents = {row["parent"] for row in train_rows}
heldout_parents = {row["parent"] for row in heldout_rows}
if train_parents & heldout_parents:
    raise RuntimeError("Training and held-out parent lineages overlap")

lineage = pd.DataFrame([
    ("Public source rows", 207680),
    ("Pilot training rows", len(train_rows)),
    ("Pilot unique training parents", len(train_parents)),
    ("Held-out rows", len(heldout_rows)),
    ("Held-out parent overlap", len(train_parents & heldout_parents)),
], columns=["Measure", "Rows or parents"])
display(lineage.style.hide(axis="index"))

fig, axes = plt.subplots(1, 3, figsize=(17, 5))
for axis, field, title, color in zip(
    axes,
    ["task", "audience", "format"],
    ["Review-task coverage", "Audience coverage", "Presentation coverage"],
    COLORS[:3],
):
    pd.Series([row[field] for row in train_rows]).value_counts().sort_values().plot.barh(ax=axis, color=color)
    axis.set(title=title, xlabel="Unique parent rows", ylabel="")
fig.tight_layout()
fig.savefig(OUT / "grounded_training_coverage.png", dpi=150, bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "tokenizer-heading",
            """
## 2. Build a tokenizer without an external model

UTF-8 text becomes bytes 0 through 255. Three additional symbols mean padding,
beginning of sequence, and end of sequence. This is simple and language-agnostic,
but byte sequences are longer than modern subword tokenization.
""",
        ),
        _code(
            "tokenizer",
            r'''
PAD, BOS, EOS = 256, 257, 258
VOCAB_SIZE = 259


def encode(text, context_length):
    values = [BOS, *text.encode("utf-8")[: context_length - 2], EOS]
    return np.asarray(values + [PAD] * (context_length - len(values)), dtype=np.int32)


def decode(values):
    raw = bytes(int(value) for value in values if 0 <= int(value) < 256)
    return raw.decode("utf-8", errors="replace")


byte_counts = np.zeros(256, dtype=np.int64)
for row in train_rows:
    for value in row["text"].encode("utf-8"):
        byte_counts[value] += 1
top_bytes = pd.DataFrame({
    "byte": np.argsort(byte_counts)[-24:][::-1],
    "count": np.sort(byte_counts)[-24:][::-1],
})
top_bytes["visible character"] = top_bytes["byte"].map(lambda value: repr(bytes([value]).decode("utf-8", errors="replace")))
display(top_bytes)
fig, ax = plt.subplots(figsize=(12, 5))
ax.bar(top_bytes["visible character"], top_bytes["count"], color=COLORS[0])
ax.set(title="Most frequent training bytes", xlabel="Decoded byte", ylabel="Occurrences")
ax.tick_params(axis="x", rotation=55)
fig.tight_layout()
fig.savefig(OUT / "byte_token_distribution.png", dpi=150, bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "model-heading",
            """
## 3. Define two from-scratch model options

Both candidates use causal multi-head attention, residual connections, layer
normalization, and a feed-forward network. They differ in width, depth, and
context length. Each candidate gets an independent random initialization and a
complete attempt receipt. This is an architecture comparison, not a hidden
fallback to a pretrained model.
""",
        ),
        _code(
            "model",
            r'''
def layer_norm(x, scale, bias, eps=1e-5):
    mean = x.mean(axis=-1, keepdims=True)
    variance = jnp.square(x - mean).mean(axis=-1, keepdims=True)
    return (x - mean) * jax.lax.rsqrt(variance + eps) * scale + bias


def init_matrix(key, rows, columns):
    return jax.random.normal(key, (rows, columns), dtype=jnp.float32) / math.sqrt(rows)


def init_params(key, config):
    width = config["hidden_size"]
    keys = iter(jax.random.split(key, 4 + config["layers"] * 8))
    params = {
        "token_embedding": jax.random.normal(next(keys), (VOCAB_SIZE, width)) * 0.02,
        "position_embedding": jax.random.normal(next(keys), (config["context_length"], width)) * 0.02,
        "layers": [],
        "final_scale": jnp.ones((width,)),
        "final_bias": jnp.zeros((width,)),
    }
    for _ in range(config["layers"]):
        params["layers"].append({
            "attention_scale": jnp.ones((width,)),
            "attention_bias": jnp.zeros((width,)),
            "wq": init_matrix(next(keys), width, width),
            "wk": init_matrix(next(keys), width, width),
            "wv": init_matrix(next(keys), width, width),
            "wo": init_matrix(next(keys), width, width),
            "feed_scale": jnp.ones((width,)),
            "feed_bias": jnp.zeros((width,)),
            "w1": init_matrix(next(keys), width, width * 4),
            "w2": init_matrix(next(keys), width * 4, width),
        })
    return params


def forward(params, tokens, config):
    batch, length = tokens.shape
    width = config["hidden_size"]
    heads = config["attention_heads"]
    head_width = width // heads
    x = params["token_embedding"][tokens] + params["position_embedding"][:length]
    causal = jnp.tril(jnp.ones((length, length), dtype=bool))
    for layer in params["layers"]:
        normalized = layer_norm(x, layer["attention_scale"], layer["attention_bias"])
        projections = []
        for name in ("wq", "wk", "wv"):
            value = normalized @ layer[name]
            projections.append(value.reshape(batch, length, heads, head_width).transpose(0, 2, 1, 3))
        query, key, value = projections
        scores = jnp.einsum("bhid,bhjd->bhij", query, key) / math.sqrt(head_width)
        scores = jnp.where(causal[None, None, :, :], scores, -1e30)
        attention = jax.nn.softmax(scores, axis=-1)
        context = jnp.einsum("bhij,bhjd->bhid", attention, value)
        context = context.transpose(0, 2, 1, 3).reshape(batch, length, width)
        x = x + context @ layer["wo"]
        normalized = layer_norm(x, layer["feed_scale"], layer["feed_bias"])
        hidden = jax.nn.gelu(normalized @ layer["w1"])
        x = x + hidden @ layer["w2"]
    x = layer_norm(x, params["final_scale"], params["final_bias"])
    return x @ params["token_embedding"].T


def parameter_count(params):
    return sum(int(value.size) for value in jax.tree_util.tree_leaves(params))


architecture_table = []
for index, config in enumerate(ARCHITECTURES):
    params = init_params(jax.random.PRNGKey(100 + index), config)
    architecture_table.append({**config, "parameters": parameter_count(params)})
architecture_table = pd.DataFrame(architecture_table)
display(architecture_table)
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.bar(architecture_table["label"], architecture_table["parameters"], color=COLORS[:len(architecture_table)])
ax.set(title="Trainable parameters initialized from scratch", ylabel="Parameters", xlabel="")
ax.tick_params(axis="x", rotation=12)
fig.tight_layout()
fig.savefig(OUT / "scratch_parameter_scale.png", dpi=150, bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "train-heading",
            """
## 4. Train both candidates on the TPU

The loop uses Adam updates, gradient clipping, learning-rate warm-up followed
by cosine decay, and a locked held-out set. Initial and final held-out loss are
reported separately from training loss. The runtime profile controls the
number of optimizer steps; even the 24-step Tensor Processing Unit profile is
a mechanism test, not sufficient pretraining.
""",
        ),
        _code(
            "train",
            r'''
STEPS = runtime_profile["optimizer_steps"]
BATCH_SIZE = runtime_profile["batch_size"]
BASE_LEARNING_RATE = 3e-3


def loss_and_accuracy(params, batch, config):
    inputs, labels = batch[:, :-1], batch[:, 1:]
    logits = forward(params, inputs, config)
    mask = labels != PAD
    safe_labels = jnp.where(mask, labels, 0)
    token_loss = -jax.nn.log_softmax(logits, axis=-1)[
        jnp.arange(labels.shape[0])[:, None], jnp.arange(labels.shape[1])[None, :], safe_labels
    ]
    loss = (token_loss * mask).sum() / mask.sum().clip(1)
    accuracy = ((logits.argmax(axis=-1) == labels) * mask).sum() / mask.sum().clip(1)
    return loss, accuracy


def learning_rate(step):
    if step < 3:
        return BASE_LEARNING_RATE * (step + 1) / 3
    progress = (step - 3) / max(1, STEPS - 4)
    return 2e-4 + 0.5 * (BASE_LEARNING_RATE - 2e-4) * (1 + math.cos(math.pi * progress))


def make_train_step(config):
    @jax.jit
    def step_fn(params, first, second, count, batch, rate):
        (loss, accuracy), gradients = jax.value_and_grad(loss_and_accuracy, has_aux=True)(params, batch, config)
        grad_norm = jnp.sqrt(sum(jnp.square(value).sum() for value in jax.tree_util.tree_leaves(gradients)))
        clip = jnp.minimum(1.0, 1.0 / (grad_norm + 1e-6))
        gradients = jax.tree_util.tree_map(lambda value: value * clip, gradients)
        first = jax.tree_util.tree_map(lambda old, grad: 0.9 * old + 0.1 * grad, first, gradients)
        second = jax.tree_util.tree_map(lambda old, grad: 0.999 * old + 0.001 * jnp.square(grad), second, gradients)
        first_hat = jax.tree_util.tree_map(lambda value: value / (1 - 0.9 ** count), first)
        second_hat = jax.tree_util.tree_map(lambda value: value / (1 - 0.999 ** count), second)
        params = jax.tree_util.tree_map(
            lambda value, mean, variance: value - rate * mean / (jnp.sqrt(variance) + 1e-8),
            params,
            first_hat,
            second_hat,
        )
        return params, first, second, loss, accuracy, grad_norm
    return step_fn


def generate(params, prompt, config, inference_fn, limit=90):
    context = config["context_length"]
    values = [BOS, *prompt.encode("utf-8")[: max(1, context - limit - 2)]]
    for _ in range(limit):
        position = min(len(values), context - 1)
        padded = values[-position:] + [PAD] * (context - position)
        logits = inference_fn(params, jnp.asarray([padded], dtype=jnp.int32))
        next_value = int(jax.device_get(logits[0, position - 1].argmax()))
        if next_value in (EOS, PAD, BOS):
            break
        values.append(next_value)
    return decode(values[1:])


attempts, curves, comparisons, trained_models = [], [], [], {}
rng = np.random.default_rng(20260715)
for architecture_index, config in enumerate(ARCHITECTURES):
    started = time.perf_counter()
    try:
        context = config["context_length"]
        train_tokens = np.stack([encode(row["text"], context + 1) for row in train_rows])
        heldout_tokens = jnp.asarray(np.stack([encode(row["text"], context + 1) for row in heldout_rows]))
        params = init_params(jax.random.PRNGKey(1000 + architecture_index), config)
        evaluate = jax.jit(lambda model, batch: loss_and_accuracy(model, batch, config))
        inference = jax.jit(lambda model, tokens: forward(model, tokens, config))
        initial_loss, initial_accuracy = evaluate(params, heldout_tokens)
        first = jax.tree_util.tree_map(jnp.zeros_like, params)
        second = jax.tree_util.tree_map(jnp.zeros_like, params)
        train_step = make_train_step(config)
        initial_outputs = [generate(params, row["text"].split("<ANSWER>", 1)[0] + "<ANSWER>", config, inference) for row in heldout_rows[:3]]
        for step_index in range(STEPS):
            indices = rng.choice(len(train_tokens), size=BATCH_SIZE, replace=False)
            batch = jnp.asarray(train_tokens[indices])
            rate = learning_rate(step_index)
            step_started = time.perf_counter()
            params, first, second, loss, accuracy, grad_norm = train_step(
                params, first, second, jnp.asarray(step_index + 1, dtype=jnp.float32), batch, rate
            )
            jax.block_until_ready(loss)
            curves.append({
                "model": config["label"],
                "step": step_index + 1,
                "loss": float(loss),
                "token_accuracy": float(accuracy),
                "gradient_norm": float(grad_norm),
                "learning_rate": rate,
                "step_seconds": time.perf_counter() - step_started,
            })
        final_loss, final_accuracy = evaluate(params, heldout_tokens)
        final_outputs = [generate(params, row["text"].split("<ANSWER>", 1)[0] + "<ANSWER>", config, inference) for row in heldout_rows[:3]]
        for row_index, row in enumerate(heldout_rows[:3]):
            comparisons.append({
                "model": config["label"],
                "source_row_id": row["id"],
                "source_row_sha256": row["sha256"],
                "parent_row_sha256": row["parent"],
                "random_initialization_output": initial_outputs[row_index],
                "trained_output": final_outputs[row_index],
                "training_eligible": False,
            })
        trained_models[config["label"]] = params
        attempts.append({
            "label": config["label"],
            "completed": True,
            "parameters": parameter_count(params),
            "initial_heldout_loss": float(initial_loss),
            "final_heldout_loss": float(final_loss),
            "initial_heldout_accuracy": float(initial_accuracy),
            "final_heldout_accuracy": float(final_accuracy),
            "elapsed_seconds": time.perf_counter() - started,
            "error": None,
        })
    except Exception as exc:
        attempts.append({
            "label": config["label"],
            "completed": False,
            "elapsed_seconds": time.perf_counter() - started,
            "error": f"{type(exc).__name__}: {str(exc)[:500]}",
        })

if not trained_models:
    raise RuntimeError(f"Every from-scratch architecture attempt failed: {attempts}")

curve_frame = pd.DataFrame(curves)
attempt_frame = pd.DataFrame(attempts)
display(attempt_frame)
display(curve_frame.tail(10))
''',
        ),
        _markdown(
            "visual-heading",
            """
## 5. Read optimization and held-out evidence together

The learning-rate curve explains update size; gradient norm shows optimizer
pressure; token accuracy and loss show training-stream fit. Held-out loss is the
only transfer signal here, and it is still based on eight source-grounded rows.
""",
        ),
        _code(
            "visuals",
            r'''
fig, axes = plt.subplots(2, 2, figsize=(14, 9))
for index, (label, group) in enumerate(curve_frame.groupby("model")):
    color = COLORS[index]
    axes[0, 0].plot(group["step"], group["loss"], marker="o", color=color, label=label)
    axes[0, 1].plot(group["step"], group["token_accuracy"], marker="o", color=color, label=label)
    axes[1, 0].plot(group["step"], group["learning_rate"], color=color, label=label)
    axes[1, 1].plot(group["step"], group["gradient_norm"], color=color, label=label)
axes[0, 0].set(title="From-scratch training loss", ylabel="Cross-entropy loss")
axes[0, 1].set(title="Next-byte training accuracy", ylabel="Accuracy")
axes[1, 0].set(title="Learning-rate schedule", ylabel="Learning rate")
axes[1, 1].set(title="Gradient norm before clipping", ylabel="Gradient norm")
for axis in axes.flat:
    axis.set_xlabel("Optimizer step")
    axis.legend(frameon=False)
fig.tight_layout()
fig.savefig(OUT / "scratch_optimization_dashboard.png", dpi=150, bbox_inches="tight")
plt.show()

completed = attempt_frame[attempt_frame["completed"]].copy()
heldout_plot = completed.set_index("label")[["initial_heldout_loss", "final_heldout_loss"]]
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
heldout_plot.plot.bar(ax=axes[0], color=COLORS[:2])
axes[0].set(title=f"Held-out loss before and after {STEPS} steps", xlabel="", ylabel="Cross-entropy loss")
axes[0].tick_params(axis="x", rotation=12)
curve_frame.groupby("model")["step_seconds"].median().plot.bar(ax=axes[1], color=COLORS[2:4])
axes[1].set(title="Median compiled optimizer-step time", xlabel="", ylabel="Seconds")
axes[1].tick_params(axis="x", rotation=12)
fig.tight_layout()
fig.savefig(OUT / "scratch_transfer_and_timing.png", dpi=150, bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "outputs-heading",
            """
## 6. Random initialization versus trained completions

These text samples are intentionally shown because they prevent a falling loss
curve from being mistaken for useful language behavior. A few dozen optimizer
steps can teach byte patterns without creating a capable language model.
Neither the random nor trained output is fed back into the training dataset.
""",
        ),
        _code(
            "outputs",
            r'''
comparison_frame = pd.DataFrame(comparisons)
display(HTML(comparison_frame.to_html(index=False, escape=True)))
lengths = comparison_frame.assign(
    random_bytes=comparison_frame["random_initialization_output"].map(lambda value: len(value.encode("utf-8"))),
    trained_bytes=comparison_frame["trained_output"].map(lambda value: len(value.encode("utf-8"))),
)
fig, ax = plt.subplots(figsize=(11, 5))
lengths.groupby("model")[["random_bytes", "trained_bytes"]].mean().plot.bar(ax=ax, color=COLORS[:2])
ax.set(title="Visible completion length before and after training", xlabel="", ylabel="Mean UTF-8 bytes")
ax.tick_params(axis="x", rotation=12)
fig.tight_layout()
fig.savefig(OUT / "scratch_before_after_lengths.png", dpi=150, bbox_inches="tight")
plt.show()
''',
        ),
        _markdown(
            "save-heading",
            """
## 7. Save full models and the training receipt

Because these models started from scratch, the outputs are complete parameter
trees—not adapters. Each NumPy archive is paired with architecture JSON,
lineage counts, attempt status, curves, and claim boundaries.
""",
        ),
        _code(
            "save",
            r'''
def flatten_params(params):
    leaves, structure = jax.tree_util.tree_flatten(params)
    arrays = {
        f"leaf_{index:04d}": np.asarray(jax.device_get(value))
        for index, value in enumerate(leaves)
    }
    leaf_manifest = [
        {
            "name": name,
            "shape": list(value.shape),
            "dtype": str(value.dtype),
        }
        for name, value in arrays.items()
    ]
    return arrays, structure, leaf_manifest


def load_full_model(model_path, config):
    """Rebuild the parameter tree and replace every leaf from an NPZ archive."""
    template = init_params(jax.random.PRNGKey(0), config)
    _, tree_definition = jax.tree_util.tree_flatten(template)
    with np.load(model_path, allow_pickle=False) as archive:
        names = sorted(archive.files)
        leaves = [jnp.asarray(archive[name]) for name in names]
    return jax.tree_util.tree_unflatten(tree_definition, leaves)


saved_models = []
for config in ARCHITECTURES:
    label = config["label"]
    if label not in trained_models:
        continue
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    arrays, structure, leaf_manifest = flatten_params(trained_models[label])
    model_path = OUT / f"{slug}.npz"
    np.savez_compressed(model_path, **arrays)
    config_path = OUT / f"{slug}.config.json"
    config_path.write_text(json.dumps({
        **config,
        "vocabulary_size": VOCAB_SIZE,
        "tokenizer": "UTF-8 bytes plus PAD/BOS/EOS",
        "parameter_tree": str(structure),
        "parameter_leaves": leaf_manifest,
        "initialized_from_scratch": True,
    }, indent=2), encoding="utf-8")
    reloaded = load_full_model(model_path, config)
    original_leaves = jax.tree_util.tree_leaves(trained_models[label])
    reloaded_leaves = jax.tree_util.tree_leaves(reloaded)
    reload_verified = len(original_leaves) == len(reloaded_leaves) and all(
        np.array_equal(np.asarray(jax.device_get(original)), np.asarray(jax.device_get(restored)))
        for original, restored in zip(original_leaves, reloaded_leaves, strict=True)
    )
    if not reload_verified:
        raise RuntimeError(f"Saved model reload verification failed for {label}")
    saved_models.append({
        "label": label,
        "model_file": model_path.name,
        "model_sha256": sha256_file(model_path),
        "config_file": config_path.name,
        "config_sha256": sha256_file(config_path),
        "parameter_leaves": len(leaf_manifest),
        "reload_verified": reload_verified,
    })

curve_frame.to_csv(OUT / "scratch-training-curves.csv", index=False)
with (OUT / "scratch-before-after.jsonl").open("w", encoding="utf-8") as handle:
    for row in comparisons:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")

summary = {
    "schema_version": "duecare.grounded_scratch_training.v1",
    "dataset_id": DATASET_ID,
    "release_manifest_sha256": EXPECTED_RELEASE_SHA256,
    "accelerator": f"JAX on {backend}",
    "runtime_profile": runtime_profile,
    "visible_compute_devices": len(devices),
    "visible_tpu_devices": len(tpu_devices),
    "pretrained_checkpoint_loaded": False,
    "external_tokenizer_loaded": False,
    "initialized_from_scratch": True,
    "source_supervised_rows": 207680,
    "pilot_training_rows": len(train_rows),
    "unique_training_parents": len(train_parents),
    "heldout_rows": len(heldout_rows),
    "heldout_parent_overlap": len(train_parents & heldout_parents),
    "free_standing_fictional_generation": False,
    "optimizer_steps_per_model": STEPS,
    "architecture_attempts": attempts,
    "saved_models": saved_models,
    "training_completed": bool(saved_models),
    "tpu_training_completed": bool(saved_models) and backend == "tpu",
    "cpu_fallback_training_completed": bool(saved_models) and backend == "cpu",
    "adapter_produced": False,
    "full_model_produced": bool(saved_models),
    "real_world_model_lift_demonstrated": False,
    "production_ready": False,
    "claim_scope": f"From-scratch {backend} mechanism and small held-out byte-loss study only; no domain effectiveness claim.",
    "charts": sorted(path.name for path in OUT.glob("*.png")),
}
(OUT / "scratch-training-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
display(pd.DataFrame([
    ("Training completed", summary["training_completed"]),
    ("TPU training completed", summary["tpu_training_completed"]),
    ("CPU fallback training completed", summary["cpu_fallback_training_completed"]),
    ("Full model produced", summary["full_model_produced"]),
    ("Adapter produced", summary["adapter_produced"]),
    ("Real-world model lift demonstrated", summary["real_world_model_lift_demonstrated"]),
    ("Production ready", summary["production_ready"]),
], columns=["Claim", "Evidence"]).style.hide(axis="index"))
print(json.dumps(summary, indent=2))
''',
        ),
        _markdown(
            "close",
            """
## What this adds to the training portfolio

1. A checkpoint-free fallback when pretrained model loading is unavailable.
2. A tokenizer-free loading path with an explicit, reversible byte contract.
3. Two architecture receipts instead of one hard-coded model.
4. Real accelerator optimization with the actual backend recorded, plus
   learning curves, held-out loss, and before/after text.
5. A negative-control lesson: optimization success is not the same as useful
   language-model capability.

For a serious from-scratch language model, the next study would require vastly
more tokens, optimizer steps, architecture sweeps, validation blocks, and
compute. The grounded 200K curriculum is appropriate for post-training
experiments; it is not by itself a broad pretraining corpus.
""",
        ),
    ]
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    return notebook


def _validate(notebook: Any, output: Path) -> None:
    target = output / ".validation"
    target.mkdir(parents=True, exist_ok=True)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        path = target / f"cell-{index:02d}.py"
        path.write_text(cell.source, encoding="utf-8")
        py_compile.compile(str(path), doraise=True)
        tree = ast.parse(cell.source, filename=str(path))
        bad = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} & {
            "null",
            "true",
            "false",
        }
        if bad:
            raise ValueError(f"JSON literal names embedded in cell {index}: {sorted(bad)}")


def build(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    notebook = _notebook()
    nbformat.write(notebook, output / "notebook.ipynb")
    _validate(notebook, output)
    metadata = {
        "id": KERNEL_ID,
        "title": "DueCare Grounded Byte Model Training Lab",
        "code_file": "notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": True,
        "enable_internet": False,
        "dataset_sources": [DATASET_ID],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    (output / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "schema_version": "duecare.grounded_scratch_tpu_notebook.v1",
        "kernel_id": KERNEL_ID,
        "dataset_id": DATASET_ID,
        "release_manifest_sha256": RELEASE_SHA256,
        "architecture_candidates": ARCHITECTURES,
        "pretrained_model_sources": [],
        "code_cells_compiled": True,
        "remote_training_completed": False,
    }
    (output / "build-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.output.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
