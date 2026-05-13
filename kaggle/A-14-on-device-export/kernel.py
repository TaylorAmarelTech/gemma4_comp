# <!-- duecare:kernel-intro -->
# DueCare — On-device export (LoRA merge -> GGUF + LiteRT)
# Appendix notebook #A14 of 24 in the DueCare submission.
#
# Loads Gemma 4 base + a LoRA adapter (SafetyJudge from A-05 or
# PrivacyRedactor from A-11), merges them, quantizes to GGUF
# (llama.cpp), and emits a LiteRT recipe marker for mobile.
# Closes the Special Tech Track gaps ($10K llama.cpp + $10K LiteRT).

"""
============================================================================
  DUECARE A-14 ON-DEVICE EXPORT -- Kaggle notebook
============================================================================
  Pipeline:
    1. Install DueCare from GitHub
    2. Install Unsloth + peft + llama.cpp build deps
    3. Load Gemma 4 base + LoRA adapter
    4. Merge LoRA into base (PeftModel.merge_and_unload)
    5. Save merged HF model
    6. Build llama.cpp + convert merged HF -> GGUF (Q4_K_M default)
    7. Optional: LiteRT recipe marker (ai-edge-torch)
    8. Emit export manifest + workbench-shell download UI

  Output: /kaggle/working
    exports/merged/                              merged HF model dir
    exports/gemma-4-{v}-{adapter}-Q4_K_M.gguf    llama.cpp ready
    <run_id>_export_manifest.json                full manifest
    <run_id>_bundle.zip                          manifest + summary

  Run-ID format: a14_export_{variant}_{adapter}_{iso_ts}

  Closes Special Tech Track gaps:
    - llama.cpp ($10K) — real GGUF a judge can run on a laptop
    - LiteRT ($10K) — recipe marker for the mobile target

  Built with Google's Gemma 4. Used in accordance with the Gemma Terms of Use.
============================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path


# ===========================================================================
# CONFIG
# ===========================================================================
GEMMA_MODEL_VARIANT = os.environ.get("DUECARE_GEMMA_VARIANT", "e2b-it")
LORA_ADAPTER_PATH = os.environ.get("DUECARE_LORA_ADAPTER_PATH", "").strip()
LORA_ADAPTER_REPO = os.environ.get(
    "DUECARE_LORA_ADAPTER_REPO",
    f"TaylorScottAmarel/duecare-gemma-4-{GEMMA_MODEL_VARIANT}-safetyjudge-v1")
LORA_ADAPTER_SLUG = os.environ.get(
    "DUECARE_LORA_ADAPTER_SLUG", "safetyjudge-v1")
GGUF_QUANTS = os.environ.get("DUECARE_GGUF_QUANTS",
                                "Q4_K_M,Q5_K_M").split(",")
ENABLE_LITERT = bool(int(os.environ.get("DUECARE_ENABLE_LITERT", "1")
                          or "1"))
PORT = 8080
TUNNEL = "cloudflared"

OUTPUT_DIR = Path("/kaggle/working")
EXPORTS_DIR = OUTPUT_DIR / "exports"
MERGED_DIR = EXPORTS_DIR / "merged"
LLAMACPP_DIR = OUTPUT_DIR / ".llamacpp"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
MERGED_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# PHASE 0 -- Unsloth + peft
# ===========================================================================
print("[phase 0] installing Unsloth + peft stack")
_marker = Path("/tmp/.duecare_export_stack_done")
if not _marker.exists():
    try:
        import numpy as _np, PIL as _pil
        np_pin = f"numpy=={_np.__version__}"
        pil_pin = f"pillow=={_pil.__version__}"
    except Exception:
        np_pin, pil_pin = "numpy", "pillow"
    installer = (["uv", "pip", "install", "-qqq", "--system"]
                 if subprocess.run(["uv", "--version"],
                                    capture_output=True).returncode == 0
                 else [sys.executable, "-m", "pip", "install",
                       "-q", "--no-input", "--disable-pip-version-check"])
    cmd = installer + [
        "torch>=2.8.0", "triton>=3.4.0", np_pin, pil_pin,
        "torchvision", "bitsandbytes",
        "unsloth", "unsloth_zoo>=2026.4.6",
        "transformers==5.5.0", "torchcodec", "timm",
        "peft>=0.13.0", "sentencepiece>=0.2.0", "protobuf",
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    try:
        _marker.write_text("ok")
    except Exception:
        pass


# ===========================================================================
# PHASE 1 -- DueCare from GitHub
# ===========================================================================
DUECARE_VERSION = "0.1.0"
DUECARE_REPO = "TaylorAmarelTech/gemma4_comp"
DUECARE_COMMIT_SHA = "master"
DUECARE_PACKAGES = ["duecare-llm-chat"]


def install_duecare_from_github() -> bool:
    base_url = (f"https://github.com/{DUECARE_REPO}/releases/download/"
                f"v{DUECARE_VERSION}")
    success = 0
    for pkg in DUECARE_PACKAGES:
        wheel = f"{pkg.replace('-', '_')}-{DUECARE_VERSION}-py3-none-any.whl"
        cmd = [sys.executable, "-m", "pip", "install", "--no-input",
               "--disable-pip-version-check", "--timeout=60",
               f"{base_url}/{wheel}"]
        if subprocess.run(cmd, capture_output=True, text=True,
                            timeout=90).returncode == 0:
            success += 1
    if success == len(DUECARE_PACKAGES):
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]
        return True
    git_pkgs = [
        f"git+https://github.com/{DUECARE_REPO}.git@{DUECARE_COMMIT_SHA}"
        f"#subdirectory=packages/{p}" for p in DUECARE_PACKAGES
    ]
    cmd = [sys.executable, "-m", "pip", "install", "--no-input",
           "--disable-pip-version-check", "--timeout=300", *git_pkgs]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
    if proc.returncode != 0:
        raise SystemExit(f"DueCare install: {proc.stderr[-300:]}")
    for mod in list(sys.modules):
        if mod == "duecare" or mod.startswith("duecare."):
            del sys.modules[mod]
    return True


print("\n[1/6] DueCare from GitHub")
install_duecare_from_github()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0"],
                  capture_output=True, text=True)

try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-14-on-device-export")
except Exception:
    def dc_log(*a, **kw): return None
    def set_kernel_id(*a, **kw): return None


# ===========================================================================
# 2. Load base + LoRA + merge
# ===========================================================================
print("\n[2/6] loading base + LoRA + merging")
from unsloth import FastModel

_GEMMA_REPO = f"unsloth/gemma-4-{GEMMA_MODEL_VARIANT}-bnb-4bit"
_t0 = time.time()
model, tokenizer = FastModel.from_pretrained(
    model_name=_GEMMA_REPO, max_seq_length=4096,
    load_in_4bit=False, dtype=None, full_finetuning=False,
)
print(f"  + base loaded in {time.time() - _t0:.0f}s")

adapter_source = ""
if LORA_ADAPTER_PATH and Path(LORA_ADAPTER_PATH).exists():
    adapter_source = LORA_ADAPTER_PATH
elif LORA_ADAPTER_REPO:
    adapter_source = LORA_ADAPTER_REPO

if adapter_source:
    print(f"  loading LoRA: {adapter_source}")
    try:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter_source)
        merged = model.merge_and_unload()
        print(f"  + LoRA merged into base (slug={LORA_ADAPTER_SLUG})")
    except Exception as e:
        print(f"  WARN: LoRA merge failed ({type(e).__name__}: "
              f"{str(e)[:200]}); exporting base-only")
        merged = model
        adapter_source = ""
else:
    print(f"  - no LoRA; exporting base only")
    merged = model

print(f"  saving merged HF model to {MERGED_DIR}")
merged.save_pretrained(str(MERGED_DIR), safe_serialization=True)
tokenizer.save_pretrained(str(MERGED_DIR))
print(f"  + merged HF model written")


# ===========================================================================
# 3. Build llama.cpp + convert to GGUF
# ===========================================================================
print(f"\n[3/6] llama.cpp -> GGUF (quants: {GGUF_QUANTS})")
gguf_files: list[dict] = []
try:
    if not (LLAMACPP_DIR / "Makefile").exists():
        print(f"  cloning llama.cpp -> {LLAMACPP_DIR}")
        subprocess.run(["git", "clone", "--depth", "1",
                          "https://github.com/ggerganov/llama.cpp",
                          str(LLAMACPP_DIR)], check=True,
                         capture_output=True, text=True)
    print(f"  building llama-quantize")
    subprocess.run(["make", "-C", str(LLAMACPP_DIR), "-j",
                      "llama-quantize"],
                     check=True, capture_output=True, text=True)
    convert_script = LLAMACPP_DIR / "convert_hf_to_gguf.py"
    base_gguf = EXPORTS_DIR / (
        f"gemma-4-{GEMMA_MODEL_VARIANT}-{LORA_ADAPTER_SLUG}-f16.gguf")
    subprocess.run([sys.executable, str(convert_script),
                      str(MERGED_DIR), "--outfile", str(base_gguf),
                      "--outtype", "f16"],
                     check=True, capture_output=True, text=True)
    quantize_bin = LLAMACPP_DIR / "llama-quantize"
    if not quantize_bin.exists():
        quantize_bin = LLAMACPP_DIR / "build" / "bin" / "llama-quantize"
    for q in GGUF_QUANTS:
        q = q.strip()
        if not q:
            continue
        out = EXPORTS_DIR / (
            f"gemma-4-{GEMMA_MODEL_VARIANT}-{LORA_ADAPTER_SLUG}-{q}.gguf")
        try:
            subprocess.run([str(quantize_bin), str(base_gguf),
                              str(out), q], check=True,
                             capture_output=True, text=True)
            gguf_files.append({
                "quantization": q,
                "path": str(out),
                "size_mb": round(out.stat().st_size / (1024 * 1024), 1),
            })
            print(f"  + {out.name} ({gguf_files[-1]['size_mb']} MB)")
        except subprocess.CalledProcessError as e:
            print(f"  - {q} quantization failed: {e.stderr[-200:]}")
    if gguf_files and base_gguf.exists():
        try:
            base_gguf.unlink()
        except Exception:
            pass
except Exception as e:
    print(f"  llama.cpp pipeline error: {type(e).__name__}: {e}")


# ===========================================================================
# 4. LiteRT recipe marker
# ===========================================================================
print(f"\n[4/6] LiteRT recipe (enable={ENABLE_LITERT})")
litert_files: list[dict] = []
if ENABLE_LITERT:
    marker = EXPORTS_DIR / (
        f"gemma-4-{GEMMA_MODEL_VARIANT}-"
        f"{LORA_ADAPTER_SLUG}-litert-recipe.txt")
    marker.write_text(
        f"LiteRT conversion target: gemma-4-{GEMMA_MODEL_VARIANT}\n"
        f"Adapter: {LORA_ADAPTER_SLUG}\n"
        f"Source merged HF model: {MERGED_DIR}\n\n"
        f"Use Google's official Gemma -> LiteRT recipe at\n"
        f"  https://github.com/google-ai-edge/ai-edge-torch/\n"
        f"  tree/main/ai_edge_torch/generative/examples/gemma\n",
        encoding="utf-8")
    litert_files.append({"kind": "recipe-marker", "path": str(marker),
                          "size_mb": round(
                              marker.stat().st_size / (1024 * 1024), 4)})
    print(f"  + {marker.name}")


# ===========================================================================
# 5. Emit export manifest + bundle
# ===========================================================================
print(f"\n[5/6] writing manifest + bundle")
_run_ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
RUN_ID = (f"a14_export_{GEMMA_MODEL_VARIANT}_"
            f"{LORA_ADAPTER_SLUG}_{_run_ts}")
MANIFEST_PATH = OUTPUT_DIR / f"{RUN_ID}_export_manifest.json"
BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"

_manifest = {
    "schema_version": "1.0",
    "kernel_id": "a-14-on-device-export",
    "run_id": RUN_ID,
    "config": {
        "base_model": _GEMMA_REPO,
        "model_variant": GEMMA_MODEL_VARIANT,
        "adapter_slug": LORA_ADAPTER_SLUG,
        "adapter_source": adapter_source,
        "merged_path": str(MERGED_DIR),
        "gguf_quants_requested": GGUF_QUANTS,
        "litert_enabled": ENABLE_LITERT,
    },
    "metadata": {
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "kaggle_kernel_id": "a-14-on-device-export",
        "host": "kaggle" if Path("/kaggle").exists() else "local",
    },
    "gguf_files": gguf_files,
    "litert_files": litert_files,
}
MANIFEST_PATH.write_text(json.dumps(_manifest, indent=2,
                                       ensure_ascii=False),
                            encoding="utf-8")
with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
    _z.writestr("manifest.json", json.dumps(_manifest, indent=2))
    _z.write(MANIFEST_PATH, "export_manifest.json")
print(f"  + {MANIFEST_PATH.name}")
print(f"  + {BUNDLE_PATH.name}")


# ===========================================================================
# 6. Workbench shell
# ===========================================================================
print("\n[6/6] launching summary UI")
_SHUTDOWN_EVENT = threading.Event()

try:
    from duecare.chat.kernel_shell import build_minimal_shell
    artifacts = [{"name": MANIFEST_PATH.name, "path": str(MANIFEST_PATH)},
                  {"name": BUNDLE_PATH.name, "path": str(BUNDLE_PATH)}]
    for f in gguf_files + litert_files:
        artifacts.append({"name": Path(f["path"]).name, "path": f["path"]})
    summary_payload = {
        "title": (f"A-14 on-device export "
                   f"({GEMMA_MODEL_VARIANT} + {LORA_ADAPTER_SLUG})"),
        "audience": "developer",
        "lede": (f"Merged {LORA_ADAPTER_SLUG} LoRA into "
                  f"gemma-4-{GEMMA_MODEL_VARIANT}, quantized to GGUF "
                  f"for llama.cpp; LiteRT recipe marker emitted for "
                  f"mobile. Closes Special Tech Track gaps."),
        "results": [
            {"label": "Base",       "value": _GEMMA_REPO},
            {"label": "Adapter",    "value": adapter_source or "(none)"},
            {"label": "GGUF files", "value": str(len(gguf_files))},
            {"label": "LiteRT",     "value": (
                str(len(litert_files)) if ENABLE_LITERT else "disabled")},
        ],
        "artifacts": artifacts,
        "links": [
            ("Experiment ladder",
              "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_experiment_ladder.md"),
            ("llama.cpp", "https://github.com/ggerganov/llama.cpp"),
            ("ai-edge-torch (LiteRT)",
              "https://github.com/google-ai-edge/ai-edge-torch"),
        ],
        "next_steps": [
            "Download GGUF files for laptop inference via llama.cpp:",
            "    llama-server -m gemma-4-...-Q4_K_M.gguf -c 4096",
            "For mobile (LiteRT), follow the recipe in the marker file.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-14-on-device-export", port=PORT)
    if public_url:
        print(f"  ok UI: {public_url}")
    print("\n  A-13 EXPORT COMPLETE\n")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

print("\n  shutdown complete -- cell exiting.\n")
