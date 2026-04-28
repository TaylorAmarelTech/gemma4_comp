"""
============================================================================
  DUECARE LIVE DEMO -- Kaggle notebook (paste into a single code cell)
============================================================================

  Self-bootstrapping. Auto-detects environment, installs only what's
  missing, picks the best Gemma 4 config for the available VRAM, falls
  back to heuristic mode if anything goes wrong.

  Requires:
    - GPU (T4 x2 recommended; works with any T4 / P100 / A100 too)
    - Internet ON
    - The duecare-llm-wheels Kaggle Dataset attached (auto-detected)
    - HF_TOKEN OPTIONAL (only if you want to download Gemma from HF
      Hub instead of an attached Kaggle Models entry)
============================================================================
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# CONFIG -- edit these for your run
# ---------------------------------------------------------------------------
DATASET_SLUG = "duecare-llm-wheels"

# ===== Model selection =====================================================
# Pick which Gemma 4 to serve. The kernel will fall back to heuristic-only
# mode if the chosen model can't be loaded (no GPU / no weights / OOM).
#
# Recommended pairings (based on Daniel Hanchen / Unsloth's notebooks):
#   gemma-4-e2b-it    : ~2 GB  4-bit ; runs on a single T4 or even CPU
#   gemma-4-e4b-it    : ~5.5 GB 4-bit; runs on a single T4 (default)
#   gemma-4-26b-a4b-it: ~14 GB 4-bit; needs P100/A100 or 2xT4
#   gemma-4-31b-it    : ~18 GB 4-bit; needs 2xT4 (device_map="balanced") or A100
#
# Setting LOADER="unsloth" uses Unsloth's FastModel which gives the cleanest
# 31B-on-2xT4 path. LOADER="transformers" is the legacy path (E4B / E2B).
GEMMA_MODEL_VARIANT = "e4b-it"   # "e2b-it" | "e4b-it" | "26b-a4b-it" | "31b-it"
GEMMA_LOADER        = "auto"     # "auto" | "transformers" | "unsloth"
                                  # "auto" = legacy transformers for E2B/E4B
                                  #          (~30s start, server runs in same
                                  #           cell, no restart needed)
                                  #        + Unsloth FastModel for 31B/26B-A4B
                                  #          (Phase 0 install + restart dance
                                  #           required; only path that fits
                                  #           on T4 x2 for those variants).
                                  # "unsloth"      = force Unsloth on any variant
                                  # "transformers" = force legacy on any variant
GEMMA_LOAD_IN_4BIT  = True       # 4-bit quantization on small GPUs
GEMMA_DEVICE_MAP    = "auto"     # "auto" | "balanced" (2xT4 for 31B) | {"":0}
GEMMA_MAX_SEQ_LEN   = 8192       # context window
USE_GEMMA           = "auto"     # "auto" | True | False; False = heuristic only

# Unsloth FastModel supports all 8 Gemma 4 variants (per Hanchen's
# notebook https://www.kaggle.com/code/danielhanchen/gemma4-31b-unsloth):
#   Instruct (recommended for serving):
#     unsloth/gemma-4-E2B-it    unsloth/gemma-4-E4B-it
#     unsloth/gemma-4-31B-it    unsloth/gemma-4-26B-A4B-it
#   Base (for fine-tuning):
#     unsloth/gemma-4-E2B       unsloth/gemma-4-E4B
#     unsloth/gemma-4-31B       unsloth/gemma-4-26B-A4B
GEMMA4_FASTMODEL_VARIANTS = [
    "e2b-it", "e4b-it", "26b-a4b-it", "31b-it",
    "e2b",    "e4b",    "26b-a4b",    "31b",
]

# Legacy aliases kept for back-compat with older bootstrap code below
GEMMA_MODEL = f"google/gemma-4-{GEMMA_MODEL_VARIANT}"

# ===== Server / runtime =====================================================
PORT = 8080
TUNNEL = "cloudflared"        # "cloudflared" | "ngrok" | "none"
DUECARE_API_TOKEN = ""        # non-empty -> require auth on /api/*
DUECARE_DB = "/kaggle/working/duecare.duckdb"
PIPELINE_OUT = "/kaggle/working/multimodal_v1_output"

# ===== Benchmark =============================================================
# If True, runs the bundled smoke benchmark (~25 prompts) on startup
# right after the server is healthy, prints the aggregate score, and
# saves the per-row JSON to PIPELINE_OUT. Useful for proving "Backend
# X scored Y on the same test set" in the writeup. The Workbench
# Benchmark tab can still be used interactively after.
BENCHMARK_AUTORUN = False
BENCHMARK_AUTORUN_SET = "smoke_25"

# ===== GGUF export (llama.cpp / Ollama distribution) =========================
# If True, after the model loads cleanly (Phase 3), Unsloth's
# save_pretrained_gguf() writes a GGUF artifact to GGUF_OUTPUT_DIR.
# Required for the llama.cpp Special Tech track: a single .gguf
# file is the canonical desktop / on-device format.
#
# Only works with the Unsloth FastModel loader path (GEMMA_LOADER
# in {auto, unsloth}). Does NOT work with GEMMA_LOADER="transformers".
#
# Per Hanchen's notebook, currently-supported quantization methods
# are: "Q8_0", "BF16", "F16". Q4_K_M is on the Unsloth roadmap.
# Recommended default: "Q8_0" (best compression of the supported set,
# ~50% smaller than F16, lossless for most uses).
GGUF_EXPORT          = False
GGUF_QUANTIZATION    = "Q8_0"        # "Q8_0" | "BF16" | "F16"
GGUF_OUTPUT_DIR      = "/kaggle/working/duecare_gguf"

# Optional: push the GGUF to your HuggingFace account after export.
# Requires HF_TOKEN (set as a Kaggle secret named HF_TOKEN, OR set
# directly here as an env var). Repo will be created if it doesn't
# exist. Naming convention follows the Gemma attribution rules:
#   <user>/Duecare-Gemma-4-<size>-<purpose>-v<version>-GGUF
GGUF_PUSH_TO_HUB     = False
GGUF_HF_REPO         = ""            # e.g. "taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0-GGUF"


# ============================================================================
# HF Hub naming convention for any fine-tuned variants you publish:
#   Pattern: <user>/Duecare-Gemma-4-<size>-<purpose>-v<version>
#   Examples:
#     taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0
#     taylorscottamarel/Duecare-Gemma-4-31B-it-SafetyJudge-v0.1.0
#     taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-DPO-v0.1.0
#
# Model card MUST include a "Built with Google's Gemma 4" attribution
# and link to https://huggingface.co/google/gemma-4-e4b-it (or the
# variant you fine-tuned). Used under Apache 2.0.
# ============================================================================

# Surface the model name to the FastAPI app so the UI can show a
# "Backend: <model>" badge on every page.
os.environ["DUECARE_MODEL_NAME"] = (
    GEMMA_MODEL.replace("google/", "").replace("unsloth/", "")
    if USE_GEMMA else "heuristic-only")


# ===========================================================================
# PHASE 0 -- Pre-install Hanchen's Unsloth stack BEFORE anything imports
# torch / transformers. Required for big variants (31B, 26B-A4B) since the
# default Kaggle env ships an older transformers + torch that conflict
# with Unsloth's compiled extensions. Once installed, Python must be
# restarted before the new torch C-extensions can be imported -- you
# CANNOT swap a running torch in-process. So:
#   1. Check marker file.
#   2. If marker missing AND we need the Unsloth stack: install it via
#      subprocess, write marker, print restart instructions, sys.exit(0).
#   3. If marker present: skip and proceed.
# This pattern is from feedback_bwandowando_recipe_verbatim memory -- the
# restarted run picks up exactly where the cell would have if Unsloth had
# already been installed.
# ===========================================================================
def _need_unsloth_stack() -> bool:
    """Phase 0 install triggers ONLY when the user picks a variant
    that REQUIRES Unsloth (31B / 26B-A4B), or explicitly opts in.
    E4B / E2B keep the fast 30-second legacy transformers path that
    has been working for weeks -- no install + restart dance needed.

      - GEMMA_LOADER == "unsloth"                                : always
      - GEMMA_LOADER == "auto" + variant in {31b-it, 26b-a4b-it} : install
      - GEMMA_LOADER == "auto" + variant in {e2b-it, e4b-it}     : SKIP
      - GEMMA_LOADER == "transformers"                            : SKIP
    """
    if not USE_GEMMA:
        return False
    if GEMMA_LOADER == "unsloth":
        return True
    big = ("31b-it", "26b-a4b-it")
    if GEMMA_LOADER == "auto" and GEMMA_MODEL_VARIANT in big:
        return True
    return False


_UNSLOTH_MARKER = Path("/tmp/.duecare_unsloth_stack_v1_done")


def _install_unsloth_stack_inline() -> bool:
    """Install Daniel Hanchen's pinned Gemma 4 stack via subprocess.

    THIS MUST RUN BEFORE ANY OTHER CODE THAT IMPORTS torch / transformers
    so that the upcoming `from unsloth import FastModel` is the FIRST
    Python torch import in the process -- the freshly installed torch
    2.8+ then loads cleanly with no C-extension conflict.

    Mirrors Hanchen's notebook pattern (cell 1 = install, cell 2 = load).
    We do it all in one cell by being strict about import order:
      stdlib only at top of file
      -> Phase 0 install via subprocess (no Python imports)
      -> install_duecare_wheels (subprocess, no torch import)
      -> SKIP force_upgrade_hf_stack (it imports transformers)
      -> load_gemma_unsloth -> first torch import = clean

    Returns True on success, False on failure.
    """
    print("=" * 76)
    print("[phase 0] installing Hanchen's Unsloth Gemma 4 stack")
    print("=" * 76)
    print(f"  variant: {GEMMA_MODEL_VARIANT}  (~30 sec, single-cell run -- "
          f"no restart needed)")

    # Hanchen's exact command. We use uv if present (Kaggle has it),
    # otherwise fall back to pip.
    try:
        import numpy as _np_for_ver, PIL as _pil_for_ver
        np_pin = f"numpy=={_np_for_ver.__version__}"
        pil_pin = f"pillow=={_pil_for_ver.__version__}"
    except Exception:
        np_pin, pil_pin = "numpy", "pillow"

    uv_check = subprocess.run(["uv", "--version"],
                                capture_output=True, text=True)
    if uv_check.returncode == 0:
        installer = ["uv", "pip", "install", "-qqq", "--system"]
    else:
        installer = [sys.executable, "-m", "pip", "install",
                       "-q", "--no-input", "--disable-pip-version-check"]

    cmd = installer + [
        "torch>=2.8.0", "triton>=3.4.0", np_pin, pil_pin,
        "torchvision", "bitsandbytes",
        "unsloth", "unsloth_zoo>=2026.4.6",
        "transformers==5.5.0", "torchcodec", "timm",
    ]
    print(f"  $ {' '.join(cmd)}")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  INSTALL FAILED ({proc.returncode}):")
        print(f"    stderr tail: {proc.stderr[-800:]}")
        return False
    elapsed = time.time() - t0
    print(f"  ✓ Hanchen stack installed in {elapsed:.0f}s "
          f"(transformers==5.5.0, torch>=2.8.0, unsloth, unsloth_zoo>=2026.4.6)")

    # Mark success so subsequent runs in the SAME session skip the install
    try:
        _UNSLOTH_MARKER.parent.mkdir(parents=True, exist_ok=True)
        _UNSLOTH_MARKER.write_text(
            json.dumps({"variant": GEMMA_MODEL_VARIANT,
                        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
                        indent=2))
    except Exception:
        pass
    return True


# Tracks whether we ran Phase 0 inline this session. When True, the
# bootstrap below will SKIP force_upgrade_hf_stack because (a) Hanchen's
# install pinned transformers==5.5.0 already and (b) running it again
# would import transformers and load the old torch into the process,
# triggering the "_has_torch_function already has a docstring" crash.
_HANCHEN_STACK_INSTALLED = False
if _need_unsloth_stack():
    if _UNSLOTH_MARKER.exists():
        print(f"[phase 0] Unsloth stack marker present ({_UNSLOTH_MARKER}); "
              f"skipping install")
        _HANCHEN_STACK_INSTALLED = True
    else:
        _HANCHEN_STACK_INSTALLED = _install_unsloth_stack_inline()


# ===========================================================================
# SMART BOOTSTRAP -- environment-aware install + model load
# ===========================================================================
@dataclass
class GPUInfo:
    available: bool = False
    name: str = ""
    vram_gb: float = 0.0
    count: int = 0


@dataclass
class PackageInfo:
    name: str
    installed: bool = False
    version: str = ""
    required: str = ""
    satisfies: bool = True


@dataclass
class Env:
    platform: str = ""
    python_version: str = ""
    in_kaggle: bool = False
    has_internet: bool = True
    gpu: GPUInfo = field(default_factory=GPUInfo)
    has_hf_token: bool = False
    has_kaggle_secret: bool = False
    attached_model_path: Optional[str] = None
    pip_executable: str = ""

    def summary(self) -> str:
        lines = [
            f"  platform:       {self.platform}",
            f"  python:         {self.python_version}",
            f"  in_kaggle:      {self.in_kaggle}",
            f"  internet:       {self.has_internet}",
        ]
        if self.gpu.available:
            lines.append(f"  GPU:            {self.gpu.name} x{self.gpu.count}"
                          f"  ({self.gpu.vram_gb:.1f} GB VRAM)")
        else:
            lines.append(f"  GPU:            (none -- CPU mode)")
        lines.append(f"  HF_TOKEN:       {'yes' if self.has_hf_token else 'no'}")
        lines.append(f"  Kaggle secret:  "
                      f"{'yes' if self.has_kaggle_secret else 'no'}")
        lines.append(f"  attached model: {self.attached_model_path or '(none)'}")
        return "\n".join(lines)


def detect_environment() -> Env:
    """Detect everything about the Kaggle / local runtime."""
    env = Env(
        platform=f"{sys.platform}",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}."
                          f"{sys.version_info.micro}",
        in_kaggle=Path("/kaggle/working").exists(),
        pip_executable=sys.executable,
    )

    # Internet check (best-effort, 3-second timeout)
    try:
        import urllib.request as _ur
        _ur.urlopen("https://www.google.com", timeout=3).close()
    except Exception:
        env.has_internet = False

    # GPU detection (without importing torch yet)
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            lines = [l.strip() for l in out.stdout.strip().split("\n") if l.strip()]
            if lines:
                first = lines[0].split(",")
                env.gpu = GPUInfo(
                    available=True,
                    name=first[0].strip(),
                    vram_gb=float(first[1].strip()) / 1024.0,
                    count=len(lines),
                )
    except Exception:
        pass

    # Credentials
    env.has_hf_token = bool(any(os.environ.get(k) for k in (
        "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN")))
    if env.in_kaggle and not env.has_hf_token:
        try:
            from kaggle_secrets import UserSecretsClient   # type: ignore
            for label in ("HF_TOKEN", "HUGGINGFACE_TOKEN",
                            "HUGGING_FACE_TOKEN"):
                try:
                    tok = UserSecretsClient().get_secret(label)
                    if tok:
                        os.environ["HF_TOKEN"] = tok.strip()
                        env.has_hf_token = True
                        env.has_kaggle_secret = True
                        break
                except Exception:
                    continue
        except Exception:
            pass

    # Local Gemma model search -- mirrors the baseline pipeline's
    # 3-tier resolution: explicit MM_MODEL_PATH > narrow Kaggle patterns
    # > broad fallback walk of /kaggle/input/** for any config.json
    # whose path matches the variant or "gemma" substring.
    explicit = os.environ.get("MM_MODEL_PATH", "").strip()
    if (explicit and Path(explicit).is_dir()
            and Path(explicit, "config.json").exists()):
        env.attached_model_path = explicit
        return env

    # Aggressive diagnostic: list /kaggle/input contents so we can see
    # WHERE Kaggle mounted any attached models, and find every
    # config.json in the input tree.
    if env.in_kaggle and Path("/kaggle/input").is_dir():
        print("  [diag] /kaggle/input top-level contents:")
        try:
            for entry in sorted(Path("/kaggle/input").iterdir()):
                kind = "DIR " if entry.is_dir() else "FILE"
                print(f"    {kind}  {entry}")
        except Exception as _e:
            print(f"    (iterdir failed: {_e})")
        print("  [diag] all config.json files under /kaggle/input:")
        n_configs = 0
        for root, _dirs, files in os.walk("/kaggle/input"):
            if "config.json" in files:
                n_configs += 1
                print(f"    config.json -> {root}")
                if n_configs >= 20:
                    print(f"    ... (capped at 20)")
                    break
        if n_configs == 0:
            print(f"    (no config.json found anywhere -- model NOT "
                    f"mounted; metadata-attach may need UI accept)")

    import glob as _glob
    variant = (GEMMA_MODEL.split("/", 1)[-1] or "").lower()
    namespace = (GEMMA_MODEL.split("/", 1)[0] or "").lower()
    narrow_patterns = [
        f"/kaggle/input/models/{namespace}/gemma-4/transformers/{variant}/*",
        f"/kaggle/input/models/{namespace}/*/transformers/{variant}/*",
        f"/kaggle/input/models/**/{variant}/*",
        f"/kaggle/input/**/{variant}/*",
        "/kaggle/input/**/gemma-4*/*",
        "/kaggle/input/**/gemma-3-4b*/*",
        # Kaggle commonly mounts attached Models at these paths too:
        f"/kaggle/input/{variant}/*",
        f"/kaggle/input/gemma-4/transformers/{variant}/*",
        "/kaggle/input/gemma-4/transformers/*/*",
    ]
    for pat in narrow_patterns:
        for c in _glob.glob(pat, recursive=True):
            if Path(c).is_dir() and Path(c, "config.json").exists():
                env.attached_model_path = c
                return env

    # Broad fallback: walk /kaggle/input for ANY config.json whose path
    # contains "gemma" or the variant string. Matches what the baseline
    # working pipeline does in its main() resolver.
    if Path("/kaggle/input").is_dir():
        needles = {variant,
                    variant.replace("gemma-4-", ""),
                    "gemma"}
        needles = {n for n in needles if n}
        for root, _dirs, files in os.walk("/kaggle/input"):
            if "config.json" not in files:
                continue
            low = root.lower()
            if any(n in low for n in needles):
                env.attached_model_path = root
                return env

    # LAST RESORT: any config.json under /kaggle/input that looks like
    # a transformers checkpoint (has tokenizer.json or model.safetensors).
    # This is how we find a model even when path doesn't say "gemma".
    if Path("/kaggle/input").is_dir():
        for root, _dirs, files in os.walk("/kaggle/input"):
            if ("config.json" in files
                    and ("tokenizer.json" in files
                         or "model.safetensors" in files
                         or "model.safetensors.index.json" in files
                         or "pytorch_model.bin" in files)):
                env.attached_model_path = root
                return env

    return env


def force_upgrade_hf_stack(verbose: bool = True) -> dict[str, str]:
    """Install a transformers version that supports Gemma 4
    (model_type='gemma4').

    Diagnosed 2026-04-26 from Kaggle's actual Gemma 4 model files:
      config.json -> transformers_version: '5.5.0.dev0'
    Kaggle's preinstalled stable transformers (5.0.0) DROPPED gemma4
    recognition. PyPI's latest stable also doesn't have it. The model
    requires transformers >= 5.5.0.dev0, which is only available from
    git main or as a pre-release.

    Strategy:
      [attempt 1] pip install --pre --upgrade transformers>=5.5.0.dev
                  (gets the latest dev/rc with gemma4 support)
      [attempt 2] pip install git+https://github.com/huggingface/transformers
                  (installs absolute latest from main branch)
      [attempt 3] last resort: --force-reinstall the older pin so at
                  least text-only on other models works"""

    def _drop_cached_modules() -> None:
        for mod in list(sys.modules):
            base = mod.split(".")[0]
            if base in ("transformers", "huggingface_hub", "tokenizers",
                        "accelerate", "bitsandbytes", "safetensors",
                        "sentencepiece"):
                del sys.modules[mod]

    def _versions() -> dict[str, str]:
        from importlib.metadata import version as _v
        out = {}
        for pkg in ("transformers", "huggingface-hub", "tokenizers",
                    "accelerate", "bitsandbytes"):
            try:
                out[pkg] = _v(pkg)
            except Exception:
                out[pkg] = "(missing)"
        return out

    def _supports_gemma4() -> bool:
        """Check if installed transformers recognizes model_type=gemma4."""
        _drop_cached_modules()
        try:
            from transformers import CONFIG_MAPPING
            return "gemma4" in CONFIG_MAPPING
        except Exception:
            try:
                from transformers.models.auto.configuration_auto import (
                    CONFIG_MAPPING_NAMES)
                return "gemma4" in CONFIG_MAPPING_NAMES
            except Exception:
                return False

    # ---- Attempt 1: --pre to allow dev/rc releases
    if verbose:
        print(f"  [attempt 1] pip install --pre --upgrade transformers "
              f"+ supporting libs (Gemma 4 needs >= 5.5.0.dev0) ...")
    cmd = [sys.executable, "-m", "pip", "install", "--quiet",
           "--upgrade", "--pre",
           "--disable-pip-version-check", "--no-input",
           "transformers>=5.5.0.dev0",
           "accelerate>=1.0", "sentencepiece", "safetensors",
           "bitsandbytes>=0.43.0"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 and verbose:
        print(f"    [attempt 1] pip FAILED: {proc.stderr[-400:]}")

    _drop_cached_modules()
    if _supports_gemma4():
        v = _versions()
        if verbose:
            print(f"  ✓ transformers supports Gemma 4 via --pre install")
            for k, val in v.items():
                print(f"    {k:24s} {val}")
        return {"hf_stack": "ok-pre", **v}

    # ---- Attempt 2: install from git main
    if verbose:
        print(f"  [attempt 2] pip install transformers from git main "
              f"(latest dev with gemma4 support) ...")
    cmd2 = [sys.executable, "-m", "pip", "install", "--quiet",
            "--upgrade", "--disable-pip-version-check", "--no-input",
            "git+https://github.com/huggingface/transformers.git",
            "accelerate>=1.0", "sentencepiece", "safetensors",
            "bitsandbytes>=0.43.0"]
    proc2 = subprocess.run(cmd2, capture_output=True, text=True,
                            timeout=600)
    if proc2.returncode != 0 and verbose:
        print(f"    [attempt 2] git install FAILED: {proc2.stderr[-400:]}")

    _drop_cached_modules()
    if _supports_gemma4():
        v = _versions()
        if verbose:
            print(f"  ✓ transformers supports Gemma 4 via git main install")
            for k, val in v.items():
                print(f"    {k:24s} {val}")
        return {"hf_stack": "ok-git", **v}

    # ---- Attempt 3: fall back to the older 4.57 pin (won't load Gemma 4
    # but the kernel can still run in heuristic mode)
    if verbose:
        print(f"  [attempt 3] FALLBACK: pin to 4.57 (HEURISTIC mode "
              f"only -- Gemma 4 won't load)")
    cmd3 = [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
            "--force-reinstall", "--disable-pip-version-check",
            "--no-input",
            "transformers>=4.56,<5.0",
            "huggingface_hub<1.0",
            "accelerate>=1.0", "sentencepiece", "safetensors",
            "bitsandbytes>=0.43.0"]
    subprocess.run(cmd3, capture_output=True, text=True)
    _drop_cached_modules()
    v = _versions()
    if verbose:
        print(f"  HF stack pinned (no gemma4 support). resulting versions:")
        for k, val in v.items():
            print(f"    {k:24s} {val}")
    return {"hf_stack": "fallback-no-gemma4", **v}


def install_optional_deps(verbose: bool = True) -> dict[str, str]:
    """Install non-critical server deps in --upgrade mode (no
    force-reinstall). Failures here are non-fatal."""
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--quiet", "--upgrade",
        "--disable-pip-version-check", "--no-input",
        "fastapi>=0.115.0", "uvicorn>=0.30.0",
        "duckdb>=1.0.0", "click>=8.1.0",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        if verbose:
            print(f"  ✓ optional server deps OK")
        return {"optional": "installed"}
    if verbose:
        print(f"  ✗ optional deps install failed: "
              f"{proc.stderr[-200:]}")
    return {"optional": f"FAILED: {proc.stderr[-200:]}"}


def install_duecare_wheels(verbose: bool = True) -> tuple[list[Path], dict]:
    """Find duecare wheels in /kaggle/input/** and pip-install them.
    Returns (wheel_paths, install_status_per_wheel)."""
    if not Path("/kaggle/input").exists():
        return [], {}
    found = sorted(p for p in Path("/kaggle/input").rglob("*.whl")
                    if "duecare" in p.name.lower())
    if verbose:
        print(f"  found {len(found)} duecare wheel(s)")
    if not found:
        return found, {}
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--no-input",
           "--disable-pip-version-check", *[str(p) for p in found]]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    status = {}
    if proc.returncode == 0:
        for w in found:
            status[w.name] = "installed"
        if verbose:
            print(f"  ✓ installed {len(found)} duecare wheels")
    else:
        if verbose:
            print(f"  bulk install failed; trying one at a time")
        for w in found:
            single = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet",
                 "--no-input", "--disable-pip-version-check", str(w)],
                capture_output=True, text=True)
            status[w.name] = ("installed (retry)"
                                if single.returncode == 0
                                else f"FAILED: {single.stderr[:120]}")
            if verbose:
                sym = "✓" if single.returncode == 0 else "✗"
                print(f"  {sym} {w.name}")
    # Drop already-imported duecare/transformers from sys.modules so the
    # newly-installed versions take effect.
    for mod in list(sys.modules):
        if (mod == "duecare" or mod.startswith("duecare.")
                or mod == "transformers" or mod.startswith("transformers.")):
            del sys.modules[mod]
    return found, status


@dataclass
class LoadedModel:
    backend: Any
    processor: Any
    mode: str
    vram_used_gb: float = 0.0
    # Surfaced via /api/model-info to the UI badge.
    model_name: str = ""              # e.g. "gemma-4-31b-it"
    model_size_b: float = 0.0         # parameter count in billions
    quantization: str = ""            # "4-bit nf4" | "bf16" | etc
    device: str = ""                  # "cuda:0" | "balanced (2x T4)" | "cpu"
    loader: str = "transformers"      # "transformers" | "unsloth"
    # Raw model handle. Required for downstream operations like
    # save_pretrained_gguf() / push_to_hub_gguf() / get_peft_model().
    # Only populated when loader == "unsloth".
    raw_model: Any = None


def _gemma_diag_dump(model_path: str) -> None:
    """Print everything we can learn about the model files BEFORE
    trying to load. Lets us see config_class / tokenizer_class / chat
    template structure so failure causes are diagnosable from logs."""
    print(f"  ── DIAGNOSTIC DUMP ──")
    p = Path(model_path)
    print(f"  model dir: {p}")
    if p.is_dir():
        print(f"  directory contents:")
        try:
            for child in sorted(p.iterdir()):
                size = (child.stat().st_size
                        if child.is_file() else "(dir)")
                print(f"    {str(size):>14}  {child.name}")
        except Exception as _e:
            print(f"    (listdir failed: {_e})")

    # config.json
    try:
        cfg = json.loads((p / "config.json").read_text())
        print(f"  config.json:")
        for k in ("model_type", "architectures", "torch_dtype",
                  "transformers_version", "vocab_size",
                  "hidden_size", "num_hidden_layers"):
            if k in cfg:
                print(f"    {k:24s} {cfg[k]}")
    except Exception as _e:
        print(f"  (config.json read FAILED: {_e})")

    # tokenizer_config.json - especially the chat_template TYPE
    try:
        tcfg = json.loads((p / "tokenizer_config.json").read_text())
        print(f"  tokenizer_config.json:")
        for k in ("tokenizer_class", "model_max_length",
                  "padding_side", "use_fast"):
            if k in tcfg:
                print(f"    {k:24s} {tcfg[k]}")
        ct = tcfg.get("chat_template")
        if ct is None:
            print(f"    chat_template            (not in tcfg)")
        elif isinstance(ct, str):
            print(f"    chat_template            string ({len(ct)} chars)")
        elif isinstance(ct, list):
            print(f"    chat_template            list with {len(ct)} item(s)"
                  f"  <-- THIS is what trips 4.57.x")
            for i, item in enumerate(ct[:3]):
                if isinstance(item, dict):
                    print(f"      [{i}] keys: {list(item.keys())}")
                else:
                    print(f"      [{i}] {type(item).__name__}")
        else:
            print(f"    chat_template            {type(ct).__name__}")
    except Exception as _e:
        print(f"  (tokenizer_config.json read FAILED: {_e})")

    # processor_config.json - tells us what processor class is needed
    pp = p / "processor_config.json"
    if pp.exists():
        try:
            pcfg = json.loads(pp.read_text())
            print(f"  processor_config.json:")
            print(f"    processor_class          {pcfg.get('processor_class')}")
            print(f"    image_processor_type     "
                  f"{pcfg.get('image_processor_type')}")
        except Exception as _e:
            print(f"  (processor_config.json read FAILED: {_e})")

    # chat_template.jinja
    ctj = p / "chat_template.jinja"
    if ctj.exists():
        try:
            txt = ctj.read_text(encoding="utf-8")
            print(f"  chat_template.jinja      {len(txt)} chars, "
                  f"head: {txt[:80]!r}...")
        except Exception as _e:
            print(f"  (chat_template.jinja read FAILED: {_e})")

    # transformers / torch / bnb versions
    print(f"  package versions:")
    from importlib.metadata import version as _v
    for pkg in ("transformers", "tokenizers", "huggingface-hub",
                "accelerate", "bitsandbytes", "torch", "safetensors"):
        try:
            print(f"    {pkg:24s} {_v(pkg)}")
        except Exception:
            print(f"    {pkg:24s} (not installed)")
    print(f"  ── END DIAGNOSTIC DUMP ──")


def _try_strategy(name: str, fn: Callable, verbose: bool = True) -> Any:
    """Run a load strategy. Returns the loaded object or None.
    Prints full traceback on failure so we can debug."""
    if verbose:
        print(f"    [{name}] trying...")
    try:
        result = fn()
        if verbose:
            print(f"    [{name}] ✓ SUCCESS")
        return result
    except Exception as e:
        if verbose:
            tb = traceback.format_exc(limit=2)
            short = " | ".join(
                line.strip() for line in tb.strip().split("\n")[-3:])
            print(f"    [{name}] ✗ {type(e).__name__}: "
                  f"{str(e)[:200]}")
            print(f"        tb: {short[:280]}")
        return None


def _model_size_b_for(variant: str) -> float:
    """Approximate parameter count in billions, for the UI badge."""
    return {
        "e2b-it":     2.0,
        "e4b-it":     4.0,
        "26b-a4b-it": 26.0,
        "31b-it":     31.0,
    }.get(variant.lower(), 0.0)


def load_gemma_unsloth(env: Env, verbose: bool = True) -> Optional[LoadedModel]:
    """Unsloth FastModel loader -- the cleanest path for 31B on 2x T4.

    Per the official Unsloth Gemma-4 31B notebook (Daniel Hanchen,
    https://www.kaggle.com/code/danielhanchen/gemma4-31b-unsloth):
        from unsloth import FastModel
        model, tok = FastModel.from_pretrained(
            "unsloth/gemma-4-31B-it",
            max_seq_length=8192,
            load_in_4bit=True,
            full_finetuning=False,
            device_map="balanced",   # <-- splits across 2 T4
        )
    """
    if not env.gpu.available:
        if verbose: print("  no GPU; skipping Unsloth load")
        return None

    # ===================================================================
    # The Hanchen Unsloth stack is installed by Phase 0 BEFORE any torch
    # import (see top of file). By the time we get here, either:
    #   - the stack is already in place (marker file existed at start)
    #   - OR Phase 0 just installed it and exited; this is the second run
    # In both cases the import below should succeed cleanly.
    # ===================================================================
    try:
        import torch
        import transformers
        from unsloth import FastModel
        if verbose:
            print(f"  versions: torch={torch.__version__}  "
                  f"transformers={transformers.__version__}  "
                  f"unsloth=OK")
    except Exception as e:
        if verbose:
            print(f"  unsloth import FAILED: {type(e).__name__}: {e}")
            print(f"  if you see '_has_torch_function already has a "
                  f"docstring', the install ran but Python wasn't "
                  f"restarted -- Run > Restart & Run All in Kaggle.")
        return None

    variant = GEMMA_MODEL_VARIANT
    # Unsloth's HF Hub repo naming uses CapitalCase for E2B/E4B
    repo_variant = (variant.replace("e2b-it", "E2B-it")
                          .replace("e4b-it", "E4B-it")
                          .replace("26b-a4b-it", "26B-A4B-it")
                          .replace("31b-it", "31B-it"))
    hf_repo = f"unsloth/gemma-4-{repo_variant}"

    # Prefer the locally-attached Kaggle Gemma model if present -- saves
    # the 5-8 min HF Hub download. FastModel.from_pretrained accepts
    # either a HF Hub repo id or a local path; load_in_4bit=True
    # quantizes either way.
    local_candidates = []
    if env.in_kaggle:
        for v in ("1", "2", "3"):
            p = (f"/kaggle/input/models/google/gemma-4/transformers/"
                 f"gemma-4-{variant}/{v}")
            if Path(p, "config.json").exists():
                local_candidates.append(p)
    if local_candidates:
        repo = local_candidates[0]
        if verbose:
            print(f"  using LOCAL attached model: {repo}")
            print(f"  (skipping HF Hub download of {hf_repo})")
    else:
        repo = hf_repo
        if verbose:
            print(f"  no attached gemma-4-{variant} found at "
                  f"/kaggle/input/models/google/gemma-4/transformers/...")
            print(f"  downloading from HF Hub: {repo}")

    # Auto-upgrade device_map to "balanced" for big variants so the
    # model splits across 2x T4 (per Hanchen's notebook). Without
    # this, 31B 4-bit (~18GB) blows past a single T4's 15GB.
    effective_device_map = GEMMA_DEVICE_MAP
    big_variants = ("31b-it", "26b-a4b-it")
    if effective_device_map == "auto" and variant in big_variants:
        if env.gpu.count >= 2:
            effective_device_map = "balanced"
            if verbose:
                print(f"  variant={variant} + {env.gpu.count}xGPU detected: "
                      f"upgrading device_map auto -> balanced")
        else:
            if verbose:
                print(f"  WARN: variant={variant} typically needs 2x GPUs "
                      f"with device_map=balanced. You have {env.gpu.count}. "
                      f"Load may OOM.")
    if verbose: print(f"  Unsloth load: {repo} (max_seq={GEMMA_MAX_SEQ_LEN}, "
                      f"4bit={GEMMA_LOAD_IN_4BIT}, device_map={effective_device_map})")

    # EXACT call from Daniel Hanchen's notebook (the 2-T4 31B path):
    #   model, tokenizer = FastModel.from_pretrained(
    #       model_name="unsloth/gemma-4-31B-it",
    #       max_seq_length=8192,
    #       load_in_4bit=True,
    #       full_finetuning=False,
    #       device_map="balanced",
    #   )
    try:
        model, tokenizer = FastModel.from_pretrained(
            model_name=repo,
            dtype=None,                         # auto-detect (Hanchen)
            max_seq_length=GEMMA_MAX_SEQ_LEN,   # 8192 (Hanchen)
            load_in_4bit=GEMMA_LOAD_IN_4BIT,    # True (Hanchen)
            full_finetuning=False,              # False (Hanchen)
            device_map=effective_device_map,    # "balanced" for 31B on 2xT4
        )
    except Exception as e:
        if verbose:
            print(f"  Unsloth FastModel.from_pretrained FAILED: "
                  f"{type(e).__name__}: {str(e)[:300]}")
        return None

    # Apply Hanchen's recommended chat template post-load
    try:
        from unsloth.chat_templates import get_chat_template
        tokenizer = get_chat_template(tokenizer,
                                        chat_template="gemma-4-thinking")
        if verbose: print("  applied chat_template=gemma-4-thinking")
    except Exception as e:
        if verbose:
            print(f"  WARN: get_chat_template failed: {type(e).__name__}: {e}")

    def _gemma_call(prompt: str, max_new_tokens: int = 350) -> str:
        # Match Hanchen's apply_chat_template / model.generate pattern
        # verbatim. Inputs go to "cuda" (the first device); when
        # device_map="balanced" the model layers are split but the
        # input embedding layer always lives on cuda:0.
        messages = [{"role": "user",
                     "content": [{"type": "text", "text": prompt}]}]
        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,   # Must add for generation (Hanchen)
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to("cuda")
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            use_cache=True,
            # Recommended Gemma 4 settings (Hanchen)
            temperature=1.0, top_p=0.95, top_k=64,
        )
        text = tokenizer.batch_decode(out)[0]
        # Strip the conversation prefix
        if "<|turn>model" in text:
            text = text.split("<|turn>model", 1)[1]
        # Strip the thinking-mode chain-of-thought wrapper. Format:
        #   <|channel>thought\n<channel|>actual answer<turn|>
        if "<channel|>" in text:
            text = text.split("<channel|>", 1)[1]
        # Strip end-of-turn marker
        text = text.split("<turn|>", 1)[0]
        return text.replace("<bos>", "").replace("<eos>", "").strip()

    vram = round(torch.cuda.memory_allocated() / 1024**3, 2)
    return LoadedModel(
        backend=_gemma_call,
        processor=tokenizer,
        mode="unsloth",
        vram_used_gb=vram,
        model_name=f"gemma-4-{variant}",
        model_size_b=_model_size_b_for(variant),
        quantization="4-bit nf4" if GEMMA_LOAD_IN_4BIT else "bf16",
        device=(f"balanced ({env.gpu.count}x {env.gpu.name or 'GPU'})"
                if effective_device_map == "balanced"
                else effective_device_map
                if isinstance(effective_device_map, str)
                else "cuda:0"),
        raw_model=model,                # for save_pretrained_gguf etc.
        loader="unsloth",
    )


def maybe_export_gguf(loaded: Optional["LoadedModel"], env: "Env",
                       verbose: bool = True) -> Optional[Path]:
    """Optional Phase 3.5: export the loaded model to GGUF for the
    llama.cpp / Ollama distribution path. Toggled via GGUF_EXPORT.

    Per Hanchen's notebook (the reference Unsloth recipe), the call is:
        model.save_pretrained_gguf(
            "gemma_4_finetune", tokenizer,
            quantization_method="Q8_0",   # or "BF16" or "F16"
        )
    Optionally push to HF Hub via:
        model.push_to_hub_gguf(
            "<user>/<repo>", tokenizer,
            quantization_method="Q8_0",
            token="HF_TOKEN",
        )
    Only the Unsloth FastModel path supports this. The legacy
    transformers loader returns raw_model=None and we skip gracefully.
    """
    if not GGUF_EXPORT:
        return None
    if loaded is None or loaded.raw_model is None:
        if verbose:
            print(f"  GGUF_EXPORT requested but no Unsloth model loaded "
                  f"(loader={loaded.loader if loaded else 'none'}); "
                  f"skipping. Set GEMMA_LOADER=auto or unsloth.")
        return None
    if GGUF_QUANTIZATION not in ("Q8_0", "BF16", "F16"):
        if verbose:
            print(f"  GGUF_QUANTIZATION={GGUF_QUANTIZATION!r} unsupported; "
                  f"Hanchen's notebook says only Q8_0 / BF16 / F16 work "
                  f"today (Q4_K_M is on the roadmap). Skipping export.")
        return None

    out_dir = Path(GGUF_OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"  exporting GGUF: dir={out_dir}  q={GGUF_QUANTIZATION}")
        print(f"  this may take several minutes for large variants")

    try:
        loaded.raw_model.save_pretrained_gguf(
            str(out_dir),
            loaded.processor,
            quantization_method=GGUF_QUANTIZATION,
        )
    except Exception as e:
        if verbose:
            print(f"  save_pretrained_gguf FAILED: "
                  f"{type(e).__name__}: {str(e)[:300]}")
        return None

    # Locate the resulting .gguf file
    gguf_files = sorted(out_dir.rglob("*.gguf"))
    if not gguf_files:
        if verbose:
            print(f"  WARN: save_pretrained_gguf returned 0 .gguf files "
                  f"in {out_dir}")
        return None
    gguf_path = gguf_files[-1]   # most recent
    sz_mb = gguf_path.stat().st_size / 1024 / 1024
    if verbose:
        print(f"  GGUF written: {gguf_path}  ({sz_mb:.1f} MB)")

    # Optional HF Hub push
    if GGUF_PUSH_TO_HUB and GGUF_HF_REPO:
        hf_token = (os.environ.get("HF_TOKEN") or
                     os.environ.get("HUGGING_FACE_HUB_TOKEN") or "")
        if not hf_token:
            if verbose:
                print(f"  GGUF_PUSH_TO_HUB requested but no HF_TOKEN "
                      f"in env; skipping upload.")
        else:
            if verbose:
                print(f"  pushing GGUF to HuggingFace: {GGUF_HF_REPO}")
            try:
                loaded.raw_model.push_to_hub_gguf(
                    GGUF_HF_REPO,
                    loaded.processor,
                    quantization_method=GGUF_QUANTIZATION,
                    token=hf_token,
                )
                if verbose:
                    print(f"  GGUF pushed: huggingface.co/{GGUF_HF_REPO}")
            except Exception as e:
                if verbose:
                    print(f"  push_to_hub_gguf FAILED: "
                          f"{type(e).__name__}: {str(e)[:300]}")

    return gguf_path


def load_gemma_smart(env: Env, model_id: str = GEMMA_MODEL,
                       verbose: bool = True) -> Optional[LoadedModel]:
    """EXHAUSTIVE Gemma 4 loader. Tries multimodal first, then
    text-only with 12+ tokenizer strategies and 8+ model strategies.
    Falls back through e4b-it -> e2b-it variants if e4b-it can't load.
    As a last resort, attempts to install transformers==4.56.0 (a
    known-good version for Gemma 4) and retries.

    Demo's gemma_call only needs text generation (moderate /
    worker_check / query). Multimodal is a bonus."""
    # ---- Loader dispatch ------------------------------------------------
    # FastModel (Unsloth) only fires for variants that REQUIRE it:
    #   - 31b-it, 26b-a4b-it: Unsloth is the only path that fits on T4 x2
    #   - GEMMA_LOADER == "unsloth": user opt-in
    # E2B / E4B stay on the legacy transformers path (30-sec startup,
    # no Phase 0 install + restart needed). This preserves the working
    # E4B flow that has been running for weeks.
    big_variants = ("31b-it", "26b-a4b-it")
    use_unsloth = (
        GEMMA_LOADER == "unsloth"
        or (GEMMA_LOADER == "auto" and GEMMA_MODEL_VARIANT in big_variants)
    )
    if use_unsloth:
        if verbose:
            print(f"  routing through Unsloth FastModel "
                  f"(variant={GEMMA_MODEL_VARIANT}, "
                  f"loader_pref={GEMMA_LOADER})")
        out = load_gemma_unsloth(env, verbose=verbose)
        if out is not None:
            return out
        if verbose:
            print(f"  Unsloth path failed; falling back to legacy "
                  f"transformers path")

    if not env.gpu.available:
        if verbose:
            print(f"  no GPU -- skipping Gemma load")
        return None
    if not env.attached_model_path and not env.has_hf_token:
        if verbose:
            print(f"  no attached model AND no HF token -- "
                  f"skipping Gemma load")
        return None
    try:
        import torch
        from transformers import (AutoProcessor, AutoTokenizer,
                                    AutoModelForImageTextToText,
                                    AutoModelForCausalLM,
                                    BitsAndBytesConfig)
    except Exception as e:
        if verbose:
            print(f"  transformers / torch import FAILED: "
                  f"{type(e).__name__}: {e}")
        return None

    model_path = env.attached_model_path or model_id
    if verbose:
        print(f"  initial model path: {model_path}")

    # Build the candidate model paths. Try the detected variant first;
    # fall through to other variants if e4b-it can't load.
    candidate_paths = [model_path]
    if env.in_kaggle:
        for variant in ("gemma-4-e4b-it", "gemma-4-e2b-it",
                        "gemma-4-26b-a4b-it", "gemma-4-31b-it"):
            for v in ("1", "2", "3"):
                p = (f"/kaggle/input/models/google/gemma-4/transformers/"
                     f"{variant}/{v}")
                if Path(p, "config.json").exists() and p not in candidate_paths:
                    candidate_paths.append(p)
    if verbose:
        print(f"  candidate paths to try (in order):")
        for cp in candidate_paths:
            print(f"    {cp}")

    # Print the full diagnostic dump for the primary path.
    _gemma_diag_dump(model_path)

    # Pick the load mode: 4-bit on T4/P100 (<20 GB VRAM), bf16 otherwise.
    vram = env.gpu.vram_gb
    use_4bit = vram < 20.0

    def _qconfig() -> Any:
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )

    def _base_kwargs(quant: bool, dmap: Any = None) -> dict:
        kw: dict = dict(
            device_map=dmap if dmap is not None else {"": 0},
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
        if quant:
            kw["quantization_config"] = _qconfig()
        else:
            kw["dtype"] = torch.bfloat16
        return kw

    quant_label = "4bit" if use_4bit else "bf16"

    # =====================================================================
    # Per-path loading attempt. Returns LoadedModel or None.
    # =====================================================================
    def _try_path(path: str) -> Optional[LoadedModel]:
        if verbose:
            print(f"  ╔══ trying model path: {path}")

        # ---- STAGE A: Multimodal (AutoProcessor + AutoModelForImageTextToText)
        if verbose:
            print(f"  ║  STAGE A: multimodal (AutoProcessor + "
                  f"AutoModelForImageTextToText)")
        proc_strategies = [
            ("AutoProcessor.standard",
             lambda: AutoProcessor.from_pretrained(
                 path, trust_remote_code=True)),
            ("AutoProcessor.fast",
             lambda: AutoProcessor.from_pretrained(
                 path, trust_remote_code=True, use_fast=True)),
            ("AutoProcessor.slow",
             lambda: AutoProcessor.from_pretrained(
                 path, trust_remote_code=True, use_fast=False)),
            ("AutoProcessor.no-trust",
             lambda: AutoProcessor.from_pretrained(path)),
        ]
        processor = None
        for name, fn in proc_strategies:
            processor = _try_strategy(name, fn, verbose=verbose)
            if processor is not None:
                break

        if processor is not None:
            mm_model_strategies = [
                ("ImageTextToText.4bit-sdpa", True, "sdpa"),
                ("ImageTextToText.4bit-eager", True, "eager"),
                ("ImageTextToText.bf16-sdpa", False, "sdpa"),
                ("ImageTextToText.bf16-eager", False, "eager"),
            ]
            for name, want_4bit, attn in mm_model_strategies:
                # Skip 4-bit configs if VRAM is sufficient for bf16.
                if want_4bit and not use_4bit:
                    continue
                if not want_4bit and use_4bit and vram < 16:
                    # Skip bf16 if we don't have enough VRAM.
                    continue
                model = _try_strategy(name, lambda a=attn, q=want_4bit:
                    AutoModelForImageTextToText.from_pretrained(
                        path, attn_implementation=a, **_base_kwargs(q)),
                    verbose=verbose)
                if model is not None:
                    model.eval()
                    try:
                        vram_used = torch.cuda.memory_allocated(0) / 1024**3
                    except Exception:
                        vram_used = 0.0
                    if verbose:
                        print(f"  ║  ✓✓ multimodal loaded ({name}, "
                              f"{vram_used:.2f} GB VRAM)")

                    @torch.inference_mode()
                    def gemma_call_mm(prompt: str,
                                        max_new_tokens: int = 300) -> str:
                        msgs = [{"role": "user",
                                 "content": [{"type": "text", "text": prompt}]}]
                        try:
                            inputs = processor.apply_chat_template(
                                msgs, add_generation_prompt=True,
                                tokenize=True, return_dict=True,
                                return_tensors="pt")
                        except Exception:
                            raw = (f"<start_of_turn>user\n{prompt}"
                                   f"<end_of_turn>\n<start_of_turn>model\n")
                            inputs = processor.tokenizer(
                                raw, return_tensors="pt")
                        inputs = {k: (v.to(model.device)
                                       if hasattr(v, "to") else v)
                                   for k, v in inputs.items()}
                        pl = inputs["input_ids"].shape[-1]
                        out = model.generate(
                            **inputs, max_new_tokens=max_new_tokens,
                            do_sample=False,
                            pad_token_id=(processor.tokenizer.pad_token_id
                                or processor.tokenizer.eos_token_id))
                        text = processor.tokenizer.decode(
                            out[0, pl:], skip_special_tokens=True).strip()
                        del out, inputs
                        try: torch.cuda.empty_cache()
                        except Exception: pass
                        return text
                    return LoadedModel(
                        backend=gemma_call_mm, processor=processor,
                        mode=f"mm-{name}", vram_used_gb=vram_used,
                        model_name=f"gemma-4-{GEMMA_MODEL_VARIANT}",
                        model_size_b=_model_size_b_for(GEMMA_MODEL_VARIANT),
                        quantization=quant_label,
                        device="cuda:0",
                        loader="transformers")
                try: torch.cuda.empty_cache()
                except Exception: pass

        # ---- STAGE B: Text-only (AutoTokenizer + AutoModelForCausalLM)
        if verbose:
            print(f"  ║  STAGE B: text-only (AutoTokenizer + "
                  f"AutoModelForCausalLM)")

        chat_template_text = ""
        ctj = Path(path) / "chat_template.jinja"
        if ctj.exists():
            try:
                chat_template_text = ctj.read_text(encoding="utf-8")
            except Exception:
                pass

        tk_strategies = [
            ("AutoTokenizer.standard",
             lambda: AutoTokenizer.from_pretrained(
                 path, trust_remote_code=True)),
            ("AutoTokenizer.fast",
             lambda: AutoTokenizer.from_pretrained(
                 path, trust_remote_code=True, use_fast=True)),
            ("AutoTokenizer.slow",
             lambda: AutoTokenizer.from_pretrained(
                 path, trust_remote_code=True, use_fast=False)),
            ("AutoTokenizer.no-trust",
             lambda: AutoTokenizer.from_pretrained(path)),
            ("AutoTokenizer.bypass-template",
             lambda: AutoTokenizer.from_pretrained(
                 path, trust_remote_code=True, chat_template="")),
            ("AutoTokenizer.bypass-template-slow",
             lambda: AutoTokenizer.from_pretrained(
                 path, trust_remote_code=True, chat_template="",
                 use_fast=False)),
            ("AutoTokenizer.legacy-true",
             lambda: AutoTokenizer.from_pretrained(
                 path, trust_remote_code=True, legacy=True,
                 chat_template="")),
            ("AutoTokenizer.legacy-false",
             lambda: AutoTokenizer.from_pretrained(
                 path, trust_remote_code=True, legacy=False,
                 chat_template="")),
        ]

        # Also try direct class imports if AutoTokenizer fails entirely.
        for cls_name in ("Gemma3TokenizerFast", "GemmaTokenizerFast",
                         "Gemma3Tokenizer", "GemmaTokenizer",
                         "LlamaTokenizerFast", "LlamaTokenizer"):
            def _direct(cn=cls_name):
                import transformers as _tx
                cls = getattr(_tx, cn, None)
                if cls is None:
                    raise ImportError(f"transformers has no {cn}")
                return cls.from_pretrained(path, trust_remote_code=True)
            tk_strategies.append((f"direct.{cls_name}", _direct))

        # Last resort: parse tokenizer.json directly via tokenizers lib +
        # build a PreTrainedTokenizerFast wrapper around it.
        def _raw_tokenizers_json():
            from transformers import PreTrainedTokenizerFast
            return PreTrainedTokenizerFast(
                tokenizer_file=str(Path(path) / "tokenizer.json"),
                bos_token="<bos>", eos_token="<eos>",
                pad_token="<pad>", unk_token="<unk>")
        tk_strategies.append(("raw-tokenizers-json", _raw_tokenizers_json))

        tokenizer = None
        tk_used = None
        for name, fn in tk_strategies:
            tokenizer = _try_strategy(name, fn, verbose=verbose)
            if tokenizer is not None:
                tk_used = name
                if "bypass" in name and chat_template_text:
                    try:
                        tokenizer.chat_template = chat_template_text
                        if verbose:
                            print(f"        + attached chat_template "
                                  f"({len(chat_template_text)} chars)")
                    except Exception as _e:
                        if verbose:
                            print(f"        chat_template attach failed: {_e}")
                break

        if tokenizer is None:
            if verbose:
                print(f"  ║  ALL tokenizer strategies failed for {path}")
            return None

        # ---- Now load the causal-LM model
        causal_strategies = [
            ("CausalLM.4bit-eager", True, "eager", {"": 0}),
            ("CausalLM.4bit-sdpa", True, "sdpa", {"": 0}),
            ("CausalLM.bf16-eager", False, "eager", {"": 0}),
            ("CausalLM.bf16-sdpa", False, "sdpa", {"": 0}),
            ("CausalLM.4bit-eager-auto", True, "eager", "auto"),
            ("CausalLM.bf16-eager-auto", False, "eager", "auto"),
        ]
        for name, want_4bit, attn, dmap in causal_strategies:
            if want_4bit and not use_4bit and vram >= 32:
                continue  # Skip 4-bit if huge VRAM
            model = _try_strategy(name, lambda a=attn, q=want_4bit, d=dmap:
                AutoModelForCausalLM.from_pretrained(
                    path, attn_implementation=a, **_base_kwargs(q, d)),
                verbose=verbose)
            if model is not None:
                model.eval()
                try:
                    vram_used = torch.cuda.memory_allocated(0) / 1024**3
                except Exception:
                    vram_used = 0.0
                if verbose:
                    print(f"  ║  ✓✓ text-only loaded ({name}, "
                          f"{vram_used:.2f} GB VRAM, tk={tk_used})")

                @torch.inference_mode()
                def gemma_call_text(prompt: str,
                                      max_new_tokens: int = 300) -> str:
                    inputs = None
                    try:
                        msgs = [{"role": "user", "content": prompt}]
                        inputs = tokenizer.apply_chat_template(
                            msgs, add_generation_prompt=True,
                            return_tensors="pt", return_dict=True)
                    except Exception:
                        raw = (f"<start_of_turn>user\n{prompt}"
                               f"<end_of_turn>\n<start_of_turn>model\n")
                        inputs = tokenizer(raw, return_tensors="pt")
                    inputs = {k: (v.to(model.device)
                                   if hasattr(v, "to") else v)
                               for k, v in inputs.items()}
                    pl = inputs["input_ids"].shape[-1]
                    out = model.generate(
                        **inputs, max_new_tokens=max_new_tokens,
                        do_sample=False,
                        pad_token_id=(tokenizer.pad_token_id
                                       or tokenizer.eos_token_id))
                    text = tokenizer.decode(
                        out[0, pl:], skip_special_tokens=True).strip()
                    del out, inputs
                    try: torch.cuda.empty_cache()
                    except Exception: pass
                    return text

                return LoadedModel(
                    backend=gemma_call_text, processor=tokenizer,
                    mode=f"text-{name}-tk={tk_used}",
                    vram_used_gb=vram_used,
                    model_name=f"gemma-4-{GEMMA_MODEL_VARIANT}",
                    model_size_b=_model_size_b_for(GEMMA_MODEL_VARIANT),
                    quantization=quant_label,
                    device="cuda:0",
                    loader="transformers")
            try: torch.cuda.empty_cache()
            except Exception: pass

        if verbose:
            print(f"  ║  ALL model strategies failed for {path}")
        return None

    # =====================================================================
    # Try each candidate path in order
    # =====================================================================
    for cp in candidate_paths:
        result = _try_path(cp)
        if result is not None:
            return result
        if verbose:
            print(f"  ╚══ path failed: {cp}; trying next...\n")

    # =====================================================================
    # LAST RESORT: try a different transformers version
    # =====================================================================
    if verbose:
        print(f"  ╔══ LAST RESORT: trying transformers==4.56.1")
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
         "--force-reinstall", "--disable-pip-version-check", "--no-input",
         "transformers==4.56.1", "huggingface_hub<1.0", "accelerate>=1.0",
         "sentencepiece", "safetensors", "bitsandbytes>=0.43.0"],
        capture_output=True, text=True)
    if proc.returncode == 0:
        if verbose:
            print(f"  ║  installed transformers==4.56.1; re-trying loaders")
        for mod in list(sys.modules):
            base = mod.split(".")[0]
            if base in ("transformers", "huggingface_hub", "tokenizers",
                        "accelerate", "bitsandbytes"):
                del sys.modules[mod]
        # Re-import (triggers cache miss)
        try:
            from transformers import (
                AutoProcessor as _AP2, AutoTokenizer as _AT2,
                AutoModelForImageTextToText as _AM2,
                AutoModelForCausalLM as _AC2,
                BitsAndBytesConfig as _BNB2)
        except Exception as e:
            if verbose:
                print(f"  ║  re-import after downgrade FAILED: {e}")
            return None
        # Just try once with the primary path under new transformers
        for cp in candidate_paths:
            result = _try_path(cp)
            if result is not None:
                if verbose:
                    print(f"  ║  ✓✓✓ loaded under transformers==4.56.1")
                return result
    else:
        if verbose:
            print(f"  ║  transformers==4.56.1 install FAILED: "
                  f"{proc.stderr[-200:]}")

    if verbose:
        print(f"  ╚══ ALL Gemma load attempts exhausted; HEURISTIC mode")
    return None


# ===========================================================================
# 1. Detect + install
# ===========================================================================
print("=" * 76)
print("[1/8] detecting environment + installing dependencies")
print("=" * 76)
env = detect_environment()
print(env.summary())
print()
print("=== installing duecare wheels ===")
wheels, wheel_status = install_duecare_wheels()
if not wheels:
    raise SystemExit(
        "No duecare *.whl files in /kaggle/input. "
        "Add Data -> Datasets -> taylorsamarel/duecare-llm-wheels.")

print()
if _HANCHEN_STACK_INSTALLED:
    # CRITICAL: when the Unsloth path is in use, Phase 0 already pinned
    # transformers==5.5.0 + torch>=2.8.0. Running force_upgrade_hf_stack
    # here would (a) overwrite that pin with a different transformers
    # and (b) import transformers into the running process, loading
    # the OLD torch C-extensions. That triggers the
    # "_has_torch_function already has a docstring" crash on the next
    # `from unsloth import FastModel`. Skip entirely.
    print("=== HF stack pinned by Phase 0 (Hanchen recipe); skipping ===")
    hf_status = {"hf_stack": "ok-hanchen-phase0"}
else:
    print("=== pinning HF stack (transformers + hub + tokenizers + bnb) ===")
    # Always force-reinstall the HF stack as ONE pip command so pip's
    # resolver picks the consistent gemma4-compatible chain. This mirrors
    # the baseline pipeline's proven bootstrap (raw_python/gemma4_*_v1.py).
    hf_status = force_upgrade_hf_stack()
print()
print("=== installing optional server deps ===")
opt_status = install_optional_deps()


# ===========================================================================
# 2. Stage env vars + sample corpus
# ===========================================================================
print("\n" + "=" * 76)
print("[2/8] env + sample corpus")
print("=" * 76)
os.environ["DUECARE_DB"] = DUECARE_DB
os.environ["DUECARE_PIPELINE_OUT"] = PIPELINE_OUT
if DUECARE_API_TOKEN:
    os.environ["DUECARE_API_TOKEN"] = DUECARE_API_TOKEN
Path(PIPELINE_OUT).mkdir(parents=True, exist_ok=True)

from duecare.cli import sample_data
sample_dir = sample_data.copy_to("/kaggle/working/sample_corpus")
n_files = sum(1 for _ in sample_dir.rglob('*') if _.is_file())
print(f"  sample corpus at {sample_dir} ({n_files} files)")


# ===========================================================================
# 3. Load Gemma 4 (smart -- auto-picks config)
# ===========================================================================
print("\n" + "=" * 76)
print("[3/8] Gemma 4 backend (smart loader)")
print("=" * 76)
gemma_call = None
if USE_GEMMA == "no" or USE_GEMMA is False:
    print("  USE_GEMMA = no -- skipping load")
else:
    loaded = load_gemma_smart(env)
    if loaded:
        gemma_call = loaded.backend
        print(f"  Gemma backend ready (mode: {loaded.mode}, "
              f"VRAM: {loaded.vram_used_gb:.2f} GB)")
    else:
        print(f"  no Gemma backend; running in HEURISTIC mode")


# ===========================================================================
# 3.5  Optional GGUF export (llama.cpp / Ollama distribution)
# ===========================================================================
if GGUF_EXPORT and loaded is not None:
    print("\n" + "=" * 76)
    print(f"[3.5/8] exporting GGUF (q={GGUF_QUANTIZATION})")
    print("=" * 76)
    gguf_path = maybe_export_gguf(loaded, env, verbose=True)
    if gguf_path:
        print(f"  GGUF artifact: {gguf_path}")


# ===========================================================================
# 4. Build server state
# ===========================================================================
print("\n" + "=" * 76)
print("[4/8] building server state")
print("=" * 76)
from duecare.server.state import ServerState
state = ServerState(db_path=DUECARE_DB, pipeline_output_dir=PIPELINE_OUT)
if gemma_call is not None:
    # Pass model metadata so the UI badge (/api/model-info) can show
    # "Backend: gemma-4-31b-it · 31.0B · 4-bit nf4" or similar.
    state.set_gemma_call(
        gemma_call,
        model_name=(loaded.model_name or GEMMA_MODEL_VARIANT) if loaded else None,
        model_size_b=loaded.model_size_b if loaded else None,
        model_quantization=loaded.quantization if loaded else None,
        model_device=loaded.device if loaded else None,
    )
    print(f"  gemma_call wired into server state "
          f"(model={loaded.model_name or GEMMA_MODEL_VARIANT}, "
          f"loader={loaded.loader if loaded else 'transformers'})")
else:
    print("  no gemma_call -- server uses heuristic fallbacks")


# ===========================================================================
# 5. Pre-load demo evidence DB
# ===========================================================================
print("\n" + "=" * 76)
print("[5/8] preloading demo evidence DB")
print("=" * 76)
sample_rows = [{
    "image_path": str(sample_dir / bundle / fname),
    "case_bundle": bundle,
    "parsed_response": {"category": cat, "extracted_facts": {}},
    "gemma_graph": {"entities": entities, "flagged_findings": flagged},
} for bundle, fname, cat, entities, flagged in [
    ("manila_recruitment_001", "recruitment_offer.md",
     "recruitment_contract",
     [{"id": 1, "type": "recruitment_agency",
       "name": "Pacific Coast Manpower"},
      {"id": 2, "type": "money", "name": "USD 1500"},
      {"id": 3, "type": "phone", "name": "+635550123456 7"},
      {"id": 4, "type": "person_or_org", "name": "Maria Santos"}],
     [{"trigger": "fee_detected", "type": "illegal_fee_flag",
       "fee_value": "USD 1500",
       "statute_violated": "PH RA 8042 sec 6(a)",
       "severity": 8, "jurisdiction": "PH"}]),
    ("manila_recruitment_001", "employment_contract.md",
     "employment_contract",
     [{"id": 1, "type": "recruitment_agency",
       "name": "Pacific Coast Manpower"},
      {"id": 2, "type": "employer",
       "name": "Al-Rashid Household Services"},
      {"id": 3, "type": "passport_number", "name": "AB1234567"}], []),
    ("hk_complaint_003", "complaint_letter.md",
     "complaint_letter",
     [{"id": 1, "type": "person_or_org", "name": "Sita Tamang"},
      {"id": 2, "type": "organization",
       "name": "Hong Kong City Credit Management Group"},
      {"id": 3, "type": "money", "name": "HKD 25000"},
      {"id": 4, "type": "passport_number", "name": "NP9876543"}],
     [{"trigger": "passport_held_by_employer",
       "type": "forced_labor_indicator",
       "ilo_indicator": "ILO C029 retention of identity documents",
       "severity": 9, "jurisdiction": "HK"}]),
]]
Path(PIPELINE_OUT).joinpath("enriched_results.json").write_text(
    json.dumps(sample_rows, indent=2, default=str), encoding="utf-8")

sample_graph = {
    "n_documents": 6, "n_entities": 6, "n_edges": 4, "n_communities": 2,
    "bad_actor_candidates": [
        {"type": "recruitment_agency",
         "value": "pacific coast manpower",
         "raw_values": ["Pacific Coast Manpower Inc.",
                         "Pacific Coast Manpower"],
         "doc_count": 5, "co_occurrence_degree": 4, "severity_max": 8},
        {"type": "organization",
         "value": "hong kong city credit management group",
         "raw_values": ["Hong Kong City Credit Management Group Inc."],
         "doc_count": 2, "co_occurrence_degree": 3, "severity_max": 9},
        {"type": "money", "value": "usd 1500",
         "raw_values": ["USD 1500"], "doc_count": 3,
         "co_occurrence_degree": 1, "severity_max": 8},
        {"type": "phone", "value": "635550123456 7",
         "raw_values": ["+63-555-0123-4567"],
         "doc_count": 2, "co_occurrence_degree": 1, "severity_max": 0},
    ],
    "top_edges": [
        {"a_type": "recruitment_agency",
         "a_value": "pacific coast manpower",
         "b_type": "money", "b_value": "usd 1500",
         "relation_type": "charged_fee_to",
         "doc_count": 3, "confidence": 0.85,
         "source": "gemma_extracted",
         "evidence": "USD 1500 placement fee"},
        {"a_type": "recruitment_agency",
         "a_value": "pacific coast manpower",
         "b_type": "organization",
         "b_value": "hong kong city credit management group",
         "relation_type": "referred_to",
         "doc_count": 2, "confidence": 0.70,
         "source": "gemma_pairwise",
         "evidence": "recruited via Pacific Coast"},
    ],
}
Path(PIPELINE_OUT).joinpath("entity_graph.json").write_text(
    json.dumps(sample_graph, indent=2), encoding="utf-8")
Path(PIPELINE_OUT).joinpath("entity_graph.html").write_text(
    "<!doctype html><html><body style='font-family:system-ui;padding:30px'>"
    "<h2>Entity graph (demo)</h2>"
    "<p>Pre-loaded from sample corpus. Run the full pipeline + ingest "
    "to replace this with the live graph.</p></body></html>",
    encoding="utf-8")

rid = state.store.ingest_run(PIPELINE_OUT)
print(f"  ingested sample run {rid} into {DUECARE_DB}")


# ===========================================================================
# 6. Launch FastAPI server in a daemon thread
# ===========================================================================
print("\n" + "=" * 76)
print("[6/8] launching FastAPI server")
print("=" * 76)
from duecare.server import create_app
import uvicorn

app = create_app(state)


def _server_thread():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


server_t = threading.Thread(target=_server_thread, daemon=True,
                              name="duecare-server")
server_t.start()
print(f"  server thread started on 0.0.0.0:{PORT}")
time.sleep(2.0)


# ===========================================================================
# 7. Open the public-URL tunnel
# ===========================================================================
print("\n" + "=" * 76)
print(f"[7/8] opening {TUNNEL} tunnel")
print("=" * 76)
public_url = None
if TUNNEL != "none":
    from duecare.server.tunnel import open_tunnel
    try:
        public_url = open_tunnel(TUNNEL, PORT)
        state.public_url = public_url
    except Exception as e:
        print(f"  tunnel FAILED: {type(e).__name__}: {e}")
        public_url = f"http://localhost:{PORT} (no public URL)"
else:
    public_url = f"http://localhost:{PORT}"


# ===========================================================================
# 8. Print URL prominently and block forever
# ===========================================================================
print("\n" + "=" * 76)
print("[8/8] DUECARE IS LIVE")
print("=" * 76)
print(f"\n   open this URL on your laptop:")
print(f"\n       {public_url}\n")
print(f"   pages:    /              (4-card homepage)")
print(f"             /enterprise    /individual    /knowledge    /settings")
print(f"   API:      /api/queue/submit  /api/queue/status/{{id}}")
print(f"             /api/query  /api/moderate  /api/worker_check")
print(f"             /api/process (background)  /api/jobs/{{id}}")
print(f"   queue:    {1 if gemma_call else 0} GPU worker, 4 CPU workers")
print(f"   mode:     {'GEMMA-POWERED' if gemma_call else 'HEURISTIC FALLBACK'}")
if DUECARE_API_TOKEN:
    print(f"   AUTH ON:  Authorization: Bearer {DUECARE_API_TOKEN}")
print(f"\n   stop the demo by interrupting this cell.\n")
print("=" * 76)


# ===========================================================================
# 8.5  Optional: auto-run the bundled smoke benchmark and print results.
# ===========================================================================
if BENCHMARK_AUTORUN:
    print("\n" + "=" * 76)
    print(f"[autobench] running bundled benchmark: {BENCHMARK_AUTORUN_SET}")
    print("=" * 76)
    try:
        import urllib.request
        import urllib.parse
        # Submit
        req = urllib.request.Request(
            f"http://localhost:{PORT}/api/benchmark/run",
            data=json.dumps({"slug": BENCHMARK_AUTORUN_SET}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST")
        sub = json.loads(urllib.request.urlopen(req, timeout=20).read())
        bid = sub["batch_id"]
        n_rows = sub.get("n_rows", "?")
        print(f"  submitted: {bid}  rows={n_rows}  "
              f"backend={sub.get('model_info', {}).get('display', '?')}")
        # Poll
        for tick in range(900):  # up to ~15 min
            time.sleep(1.0)
            s = json.loads(urllib.request.urlopen(
                f"http://localhost:{PORT}/api/benchmark/status/{bid}",
                timeout=10).read())
            c = s.get("counts", {})
            done = c.get("completed", 0) + c.get("failed", 0)
            if (tick % 5) == 0:
                sm = s.get("summary", {})
                print(f"  [{tick:3d}s] {done}/{n_rows} done · "
                      f"pass={sm.get('pass_rate','-')} · "
                      f"verdict={sm.get('verdict_acc','-')}")
            if done >= n_rows:
                # Final summary + save JSON
                sm = s.get("summary", {})
                print(f"\n  FINAL: pass_rate={sm.get('pass_rate')}  "
                      f"verdict_acc={sm.get('verdict_acc')}  "
                      f"severity_acc={sm.get('severity_acc')}  "
                      f"signal_recall={sm.get('signal_recall')}")
                out_path = Path(PIPELINE_OUT) / f"{bid}.json"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(json.dumps(s, indent=2),
                                     encoding="utf-8")
                print(f"  saved: {out_path}")
                break
    except Exception as e:
        print(f"  autobench FAILED: {type(e).__name__}: {e}")


try:
    while True:
        time.sleep(60)
        try:
            stats = state.store.fetchone("SELECT COUNT(*) AS n FROM runs")
            print(f"   [heartbeat] {time.strftime('%H:%M:%S')}  "
                    f"runs in DB: {stats['n']}  mode: "
                    f"{'gemma' if gemma_call else 'heuristic'}")
        except Exception:
            pass
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")
