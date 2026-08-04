from __future__ import annotations

import gc
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


DEFAULT_SMALL_VARIANT = "e2b-it"
DEFAULT_SMALL_MODEL_REF = "google/gemma-4-E2B-it"
DEFAULT_MAX_SEQ_LENGTH = 4096
PINNED_MODEL_REVISIONS = {
    "e2b-it": "4abfca14e6c6bfb5888b80288185b1243fb8d539",
    "google/gemma-4-E2B-it": "4abfca14e6c6bfb5888b80288185b1243fb8d539",
    "unsloth/gemma-4-E2B-it": "4abfca14e6c6bfb5888b80288185b1243fb8d539",
    "e4b-it": "0d5a7f9ba73eda1616e58344f7025fae44914675",
    "google/gemma-4-E4B-it": "0d5a7f9ba73eda1616e58344f7025fae44914675",
    "unsloth/gemma-4-E4B-it": "0d5a7f9ba73eda1616e58344f7025fae44914675",
}
_IMMUTABLE_REVISION = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


@dataclass
class Gemma4LoadSpec:
    source: str = "hf"
    model_ref: str = DEFAULT_SMALL_MODEL_REF
    revision: str = ""
    adapter_ref: str = ""
    quantization: str = "4bit"
    trust_remote_code: bool = True
    max_seq_length: int = DEFAULT_MAX_SEQ_LENGTH


@dataclass
class Gemma4LoadedModel:
    model: Any
    tokenizer: Any
    backend: Callable[..., str]
    info: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)


def variant_from_ref(model_ref: str) -> str:
    ref = (model_ref or "").strip()
    low = ref.lower()
    if low in {"e2b-it", "e4b-it", "26b-a4b-it", "31b-it", "jailbroken-e4b", "jailbroken-31b"}:
        return low
    if "gemma-4-2b" in low or "gemma-4-e2b" in low:
        return "e2b-it"
    if "gemma-4-4b" in low or "gemma-4-e4b" in low:
        return "e4b-it"
    if "gemma-4-26b" in low or "26b-a4b" in low:
        return "26b-a4b-it"
    if "gemma-4-31b" in low:
        return "31b-it"
    return ""


def _is_official_gemma4_alias(model_ref: str) -> bool:
    low = (model_ref or "").strip().lower()
    return (
        low in {"e2b-it", "e4b-it", "26b-a4b-it", "31b-it"}
        or low.startswith("google/gemma-4-")
        or low.startswith("unsloth/gemma-4-")
    )


def resolve_model_ref(source: str, model_ref: str) -> tuple[str, str, str]:
    source = (source or "hf").strip()
    model_ref = (model_ref or DEFAULT_SMALL_MODEL_REF).strip()
    if source in {"kaggle_path", "local_path", "github"}:
        return model_ref, variant_from_ref(model_ref), source

    variant = variant_from_ref(model_ref)
    if not variant:
        return model_ref, "", source

    if "/" in model_ref and not _is_official_gemma4_alias(model_ref):
        return model_ref, variant, "hf"

    for version in ("1", "2", "3"):
        candidate = (
            Path("/kaggle/input/models/google/gemma-4/transformers")
            / f"gemma-4-{variant}"
            / version
        )
        if (candidate / "config.json").exists():
            return str(candidate), variant, "kaggle_attached"

    if variant.startswith("jailbroken-"):
        # Research-only variants. DueCare ships no safety-stripped model and
        # names none: the operator supplies their own checkpoint. When unset we
        # fall back to ``model_ref`` rather than inventing a repo id, so an
        # unconfigured request fails on a missing model instead of silently
        # resolving to one.
        repos = {
            "jailbroken-e4b": os.environ.get("DUECARE_STRIPPED_MODEL_E4B", ""),
            "jailbroken-31b": os.environ.get("DUECARE_STRIPPED_MODEL_31B", ""),
        }
        return repos.get(variant) or model_ref, variant, "hf"

    repo_variant = (
        variant.replace("e2b-it", "E2B-it")
        .replace("e4b-it", "E4B-it")
        .replace("26b-a4b-it", "26B-A4B-it")
        .replace("31b-it", "31B-it")
    )
    return f"unsloth/gemma-4-{repo_variant}", variant, "hf"


def resolve_model_revision(model_ref: str, resolved_model_ref: str = "", revision: str = "") -> str:
    """Return an immutable Hub revision for a requested/resolved model pair."""

    explicit = (revision or "").strip().lower()
    if explicit and _IMMUTABLE_REVISION.fullmatch(explicit):
        return explicit
    requested = (model_ref or "").strip()
    resolved = (resolved_model_ref or "").strip()
    variant = variant_from_ref(requested) or variant_from_ref(resolved)
    keys = [resolved, requested]
    if _is_official_gemma4_alias(requested) or _is_official_gemma4_alias(resolved):
        keys.append(variant)
    for key in keys:
        pinned = PINNED_MODEL_REVISIONS.get(key)
        if pinned:
            return pinned
    return ""


class Gemma4Runtime:
    def __init__(self, log: Callable[[str, str], None] | None = None) -> None:
        self.loaded: Gemma4LoadedModel | None = None
        self.log = log or (lambda _phase, _msg: None)

    def unload(self, reason: str = "manual") -> dict[str, Any]:
        self.log("unload", reason)
        self.loaded = None
        try:
            gc.collect()
        except Exception:
            pass
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except Exception:
            pass
        return {
            "loaded": False,
            "source": "unloaded",
            "model_ref": DEFAULT_SMALL_MODEL_REF,
            "adapter_ref": "",
            "quantization": "",
            "loaded_at": "",
            "notes": f"Model unloaded: {reason}. Load Gemma 4 before running inference.",
        }

    def load(self, spec: Gemma4LoadSpec) -> Gemma4LoadedModel:
        try:
            self.log("importing", "importing torch")
            import torch
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"PyTorch is not available: {exc}") from exc

        cuda_version = getattr(torch.version, "cuda", "unknown")
        cuda_available = bool(torch.cuda.is_available())
        device_count = int(torch.cuda.device_count()) if cuda_available else 0
        self.log(
            "imported",
            f"torch={torch.__version__}; cuda={cuda_version}; "
            f"cuda_available={cuda_available}; device_count={device_count}",
        )
        if not cuda_available or device_count < 1:
            message = (
                "CUDA accelerator is not visible to PyTorch. Local Gemma 4 loading uses "
                "Unsloth FastModel and requires a Kaggle GPU runtime. In Kaggle, stop this "
                "session, set Accelerator to GPU T4 x2, enable Internet, then rerun the "
                "kernel from the top. If the status strip still shows GPU=none, the notebook "
                "is running on CPU and FastModel will not load."
            )
            self.log("gpu-missing", message)
            raise RuntimeError(message)

        try:
            self.log("importing", "importing Unsloth FastModel")
            from unsloth import FastModel
        except Exception as exc:  # noqa: BLE001
            message = (
                "Unsloth FastModel stack not available after CUDA preflight passed: "
                f"{exc}. Restart the Kaggle session after package installation; if it "
                "persists, verify the attached image has torch, transformers, and unsloth "
                "installed for the active Python environment."
            )
            self.log("error", message)
            raise RuntimeError(message) from exc

        self.unload("loading replacement model")
        self.log("gpu-check", self._gpu_inventory(torch))
        resolved_ref, variant, resolved_source = resolve_model_ref(spec.source, spec.model_ref)
        resolved_revision = (
            resolve_model_revision(spec.model_ref, resolved_ref, spec.revision)
            if resolved_source == "hf"
            else (spec.revision or "").strip().lower()
        )
        device_map = "balanced" if variant in {"26b-a4b-it", "31b-it"} and device_count >= 2 else "auto"

        self.log("resolve-repo", f"{spec.model_ref} -> {resolved_ref}")
        if resolved_source == "hf":
            self.log("resolve-repo", f"no local Kaggle model attachment found; will download from HF Hub: {resolved_ref}")
            if resolved_revision:
                self.log("resolve-revision", f"pinned HF revision: {resolved_revision}")
            else:
                self.log("resolve-revision", "no immutable HF revision configured for this model")
        else:
            self.log("resolve-repo", f"using local attached model: {resolved_ref}")
        if variant in {"26b-a4b-it", "31b-it", "jailbroken-31b"}:
            self.log(
                "preload",
                "large-model path: first run can take 15-25 min; cached runs are faster. "
                "weights download, shard-map, quantization, and CUDA memory planning happen inside FastModel.from_pretrained.",
            )
        self.log(
            "from_pretrained",
            "FastModel.from_pretrained("
            f"model={resolved_ref}, max_seq={int(spec.max_seq_length or DEFAULT_MAX_SEQ_LENGTH)}, "
            f"4bit={spec.quantization.lower() in {'4bit', 'nf4'}}, device_map={device_map})",
        )

        heartbeat_stop = threading.Event()

        def _heartbeat_loop() -> None:
            last_alloc: list[float] = []
            tick = 0
            while not heartbeat_stop.wait(15.0):
                tick += 1
                try:
                    alloc_per_dev = [
                        torch.cuda.memory_allocated(idx) / 1_073_741_824
                        for idx in range(torch.cuda.device_count())
                    ]
                    delta = sum(alloc_per_dev) - sum(last_alloc[: len(alloc_per_dev)])
                    last_alloc = alloc_per_dev
                    phase_hint = "loading_to_gpu" if sum(alloc_per_dev) > 0.1 else "downloading_or_cpu_init"
                    msg = (
                        f"heartbeat #{tick} (still alive after {tick * 15}s): VRAM "
                        + " | ".join(f"cuda:{i}={gb:.2f}GB" for i, gb in enumerate(alloc_per_dev))
                        + (f" - +{delta:.2f}GB since last tick" if abs(delta) > 0.01 else " - no change since last tick")
                    )
                    self.log(phase_hint, msg)
                except Exception as exc:  # noqa: BLE001
                    self.log("heartbeat_error", f"heartbeat #{tick} probe failed: {type(exc).__name__}: {exc}")

        threading.Thread(target=_heartbeat_loop, daemon=True, name="duecare-gemma4-loader-heartbeat").start()
        t0 = time.time()
        load_kwargs = {
            "model_name": resolved_ref,
            "dtype": None,
            "max_seq_length": int(spec.max_seq_length or DEFAULT_MAX_SEQ_LENGTH),
            "load_in_4bit": spec.quantization.lower() in {"4bit", "nf4"},
            "full_finetuning": False,
            "device_map": device_map,
        }
        if resolved_source == "hf" and resolved_revision:
            load_kwargs["revision"] = resolved_revision
        try:
            model, tokenizer = FastModel.from_pretrained(**load_kwargs)
        except Exception as exc:  # noqa: BLE001
            self.log("error", f"FastModel FAILED: {type(exc).__name__}: {str(exc)[:500]}")
            raise
        finally:
            heartbeat_stop.set()
        self.log("loaded", f"FastModel returned in {time.time() - t0:.1f}s")
        self._log_gpu_memory(torch)

        try:
            self.log("chat-template", "applying gemma-4-thinking chat template")
            from unsloth.chat_templates import get_chat_template

            tokenizer = get_chat_template(tokenizer, chat_template="gemma-4-thinking")
            self.log("chat-template", "chat template ready")
        except Exception as exc:  # noqa: BLE001
            self.log("chat-template", f"skipped: {type(exc).__name__}: {exc}")

        if spec.adapter_ref:
            try:
                from peft import PeftModel

                model = PeftModel.from_pretrained(model, spec.adapter_ref)
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(f"adapter load failed: {exc}") from exc

        input_device = "cuda:0" if device_map == "balanced" else self._infer_input_device(model, torch)
        self.log("ready", f"model input device resolved: {input_device}")

        def _normalise_messages(prompt_or_messages) -> list[dict]:
            if isinstance(prompt_or_messages, list):
                messages_in = prompt_or_messages
            else:
                messages_in = [{"role": "user", "content": str(prompt_or_messages)}]
            messages_out: list[dict] = []
            for msg in messages_in:
                item = dict(msg)
                content = item.get("content")
                if isinstance(content, str):
                    item["content"] = [{"type": "text", "text": content}]
                elif isinstance(content, list):
                    normalised_content: list[dict[str, Any]] = []
                    for part in content:
                        if isinstance(part, str):
                            normalised_content.append({"type": "text", "text": part})
                        elif isinstance(part, dict):
                            normalised_content.append(part)
                        else:
                            normalised_content.append({"type": "text", "text": str(part)})
                    item["content"] = normalised_content
                messages_out.append(item)
            return messages_out

        def backend(
            prompt,
            *,
            max_new_tokens: int = 512,
            temperature: float = 1.0,
            top_p: float = 0.95,
            top_k: int = 64,
        ) -> str:
            messages = _normalise_messages(prompt)
            if hasattr(tokenizer, "apply_chat_template"):
                inputs = tokenizer.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    tokenize=True,
                    return_dict=True,
                    return_tensors="pt",
                ).to(input_device)
            else:
                inputs = tokenizer(prompt, return_tensors="pt")
                inputs = {k: v.to(input_device) for k, v in inputs.items()}
            out = None
            text = ""
            try:
                out = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    use_cache=True,
                    do_sample=temperature > 0,
                    temperature=max(float(temperature or 0.0), 0.01),
                    top_p=top_p,
                    top_k=top_k,
                )
                try:
                    text = tokenizer.batch_decode(out)[0]
                except Exception:
                    text = tokenizer.decode(out[0], skip_special_tokens=True)
            finally:
                # Free per-call intermediate tensors (input ids, attention
                # mask, model outputs, and the KV cache from this generate
                # call) so back-to-back model invocations on a large
                # variant (26B-A4B / 31B) don't accumulate VRAM and OOM
                # the second / third call. Observed in the live tunnel:
                # case-brief succeeded, then knowledge-draft batch OOM'd
                # because the prior generation's KV cache stayed pinned.
                #
                # Two-step cleanup: (1) drop Python references to the
                # generated tensor + the input tensors so the garbage
                # collector can release them; (2) ask PyTorch's caching
                # allocator to return free blocks to the CUDA driver.
                try:
                    inputs = None
                    out = None
                    import gc as _gc_local
                    _gc_local.collect()
                    if hasattr(torch, "cuda") and torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        # synchronize so empty_cache actually reclaims
                        # before the next call's allocation starts.
                        torch.cuda.synchronize()
                except Exception:
                    # Memory cleanup is best-effort — if it fails (e.g.
                    # torch.cuda unavailable), don't break the call.
                    pass
            from duecare.chat._model_output import sanitize_model_output

            return sanitize_model_output(text)

        info = {
            "loaded": True,
            "source": resolved_source,
            "model_ref": spec.model_ref,
            "resolved_model_ref": resolved_ref,
            "revision": resolved_revision,
            "revision_repo": resolved_ref if resolved_revision else "",
            "variant": variant,
            "adapter_ref": spec.adapter_ref,
            "quantization": spec.quantization,
            "loaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "device": input_device,
            "device_map": device_map,
            "loader": "unsloth.FastModel",
            "max_seq_length": int(spec.max_seq_length or DEFAULT_MAX_SEQ_LENGTH),
            "notes": "Model loaded through shared DueCare Gemma 4 Unsloth/FastModel runtime.",
        }
        self.loaded = Gemma4LoadedModel(
            model=model,
            tokenizer=tokenizer,
            backend=backend,
            info=info,
            raw={"torch": torch},
        )
        return self.loaded

    def _gpu_inventory(self, torch: Any) -> str:
        try:
            devices = []
            for idx in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(idx)
                devices.append(f"{props.name} cuda:{idx} ({props.total_memory / 1_073_741_824:.1f} GB)")
            return "GPU: " + " | ".join(devices) if devices else "GPU: none"
        except Exception as exc:  # noqa: BLE001
            return f"GPU inventory unavailable: {type(exc).__name__}: {exc}"

    def _log_gpu_memory(self, torch: Any) -> None:
        try:
            for idx in range(torch.cuda.device_count()):
                alloc = torch.cuda.memory_allocated(idx) / 1_073_741_824
                reserved = torch.cuda.memory_reserved(idx) / 1_073_741_824
                name = torch.cuda.get_device_name(idx)
                self.log("gpu-memory", f"cuda:{idx} {name}: allocated={alloc:.2f} GB; reserved={reserved:.2f} GB")
        except Exception as exc:  # noqa: BLE001
            self.log("gpu-memory", f"GPU memory summary unavailable: {type(exc).__name__}: {exc}")

    @staticmethod
    def _infer_input_device(model: Any, torch: Any) -> str:
        try:
            dev = getattr(model, "device", None)
            if dev is not None and str(dev) not in {"meta", "None"}:
                return str(dev)
        except Exception:
            pass
        try:
            dev = next(model.parameters()).device
            if dev is not None and str(dev) not in {"meta", "None"}:
                return str(dev)
        except Exception:
            pass
        try:
            alloc = [
                (torch.cuda.memory_allocated(idx), idx)
                for idx in range(torch.cuda.device_count())
            ]
            if alloc:
                return f"cuda:{max(alloc)[1]}"
        except Exception:
            pass
        return "cuda:0"
