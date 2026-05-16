from __future__ import annotations

import gc
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


DEFAULT_SMALL_VARIANT = "e2b-it"
DEFAULT_SMALL_MODEL_REF = "google/gemma-4-2b-it"
DEFAULT_MAX_SEQ_LENGTH = 4096


@dataclass
class Gemma4LoadSpec:
    source: str = "hf"
    model_ref: str = DEFAULT_SMALL_MODEL_REF
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


def resolve_model_ref(source: str, model_ref: str) -> tuple[str, str, str]:
    source = (source or "hf").strip()
    model_ref = (model_ref or DEFAULT_SMALL_MODEL_REF).strip()
    if source in {"kaggle_path", "local_path", "github"}:
        return model_ref, variant_from_ref(model_ref), source

    variant = variant_from_ref(model_ref)
    if not variant:
        return model_ref, "", source

    for version in ("1", "2", "3"):
        candidate = (
            Path("/kaggle/input/models/google/gemma-4/transformers")
            / f"gemma-4-{variant}"
            / version
        )
        if (candidate / "config.json").exists():
            return str(candidate), variant, "kaggle_attached"

    if variant.startswith("jailbroken-"):
        repos = {
            "jailbroken-e4b": "mlabonne/Gemma-4-E4B-it-abliterated",
            "jailbroken-31b": "mlabonne/Gemma-4-31B-it-abliterated",
        }
        return repos.get(variant, model_ref), variant, "hf"

    repo_variant = (
        variant.replace("e2b-it", "E2B-it")
        .replace("e4b-it", "E4B-it")
        .replace("26b-a4b-it", "26B-A4B-it")
        .replace("31b-it", "31B-it")
    )
    return f"unsloth/gemma-4-{repo_variant}", variant, "hf"


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
            import torch
            from unsloth import FastModel
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Unsloth FastModel stack not available: {exc}") from exc

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. Gemma 4 local runtime requires Kaggle GPU.")

        self.unload("loading replacement model")
        resolved_ref, variant, resolved_source = resolve_model_ref(spec.source, spec.model_ref)
        device_count = max(1, torch.cuda.device_count())
        device_map = "balanced" if variant in {"26b-a4b-it", "31b-it"} and device_count >= 2 else "auto"

        self.log("resolve", f"{spec.model_ref} -> {resolved_ref}")
        t0 = time.time()
        model, tokenizer = FastModel.from_pretrained(
            model_name=resolved_ref,
            dtype=None,
            max_seq_length=int(spec.max_seq_length or DEFAULT_MAX_SEQ_LENGTH),
            load_in_4bit=spec.quantization.lower() in {"4bit", "nf4"},
            full_finetuning=False,
            device_map=device_map,
        )
        self.log("loaded", f"FastModel returned in {time.time() - t0:.1f}s")

        try:
            from unsloth.chat_templates import get_chat_template

            tokenizer = get_chat_template(tokenizer, chat_template="gemma-4-thinking")
        except Exception as exc:  # noqa: BLE001
            self.log("chat-template", f"skipped: {type(exc).__name__}: {exc}")

        if spec.adapter_ref:
            try:
                from peft import PeftModel

                model = PeftModel.from_pretrained(model, spec.adapter_ref)
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(f"adapter load failed: {exc}") from exc

        input_device = self._infer_input_device(model, torch)

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
                messages_out.append(item)
            return messages_out

        def backend(prompt, *, max_new_tokens: int = 512, temperature: float = 0.2) -> str:
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
            out = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                use_cache=True,
                do_sample=temperature > 0,
                temperature=max(float(temperature or 0.0), 0.01),
                top_p=0.95,
            )
            try:
                text = tokenizer.batch_decode(out)[0]
            except Exception:
                text = tokenizer.decode(out[0], skip_special_tokens=True)
            from duecare.chat._model_output import sanitize_model_output

            return sanitize_model_output(text)

        info = {
            "loaded": True,
            "source": resolved_source,
            "model_ref": spec.model_ref,
            "resolved_model_ref": resolved_ref,
            "variant": variant,
            "adapter_ref": spec.adapter_ref,
            "quantization": spec.quantization,
            "loaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "device": input_device,
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
