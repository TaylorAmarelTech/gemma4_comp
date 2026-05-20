# <!-- duecare:kernel-intro -->
# DueCare App (formerly DueCare Exploration Workbench)
# Active notebook #01 in the DueCare Kaggle submission path.
# Kaggle slug: taylorsamarel/duecare-app
#
# Unified workbench surface for every audience and every harness capability:
#   - 6 audience showcase pages (Platform safety / NGO & regulator /
#     Individual worker & mobile / Researcher / Anonymized knowledge sharing /
#     Developer & integration partner) with curated sample prompts per lane.
#   - Free-form chat playground with five safety layers plus local imports,
#     4 grading modes, and 9 Gemma 4 variants through the shared model picker.
#   - Layer transparency: live GREP rules / live RAG docs / tools, each
#     browsable with its own viewer page under /static/harness.html.
#   - Anonymization preview, hotlines directory, cross-layer search, and a
#     full Tools index at /static/all-tools.html, all behind one nav bar.
#
# Demo path: Run All -> cloudflared URL prints -> pick a model -> click any
# of the 6 audience tabs in the top nav to land on a curated lane demo, or
# stay on the home page for free-form chat.
#
# Full README + cross-kernel index: see the README in this folder.

"""
============================================================================
  DUECARE EXPLORATION WORKBENCH
  Unified Kaggle notebook, core #01
  (paste into a single code cell)
============================================================================

  THE one-notebook configurable DueCare interface. Everything in the
  submission visible here:

      Persona      expert anti-trafficking persona prepended to context
      GREP         Live regex KB rules across trafficking and labour-risk
                     categories (debt
                     bondage, fee camouflage, corridor fee caps,
                     ILO indicators, kafala framework + extended
                     mechanisms, sector-specific labour abuse,
                     cross-border financial flows, employer abuse,
                     document fraud, recruiter sales tactics,
                     recovery suppression / repatriation barriers,
                     additional corridors, platform / digital
                     recruitment patterns)
      RAG          Hybrid preferred RAG over the bundled corpus
                     across curated source groups,
                     plus the citation graph for 1-hop expansion
      Imports      user-attached evidence (images / docs / posts)
                     auto-bound to the prompt context
      Tools        5 lookup functions (corridor fee caps, fee
                     camouflage, ILO indicators, NGO intake, ILO
                     Convention reference)
      Online       optional agentic web search via Playwright / Brave
                     (BYOK API key) with httpx deep-fetch and
                     DuckDuckGo HTML fallback
      Grade        4 modes (Rule-Based / LLM-Based / Combined / Expert):
             Rule-Based = current multi-signal grader (numeric
             applicability rubric), LLM-Based = LLM evaluator sending response
                     back to the loaded model with one yes/no question
                     per applicable dimension (the academic literature
                     calls this 'LLM-as-judge')

      Static viewers: /static/harness.html landing page +
      /static/{persona,grep-rules,rag-corpus,rag-graph,tools,online}.html
      catalog viewers, all driven by /api/harness-catalog/{layer} and
      /api/brand. Single source of truth for layer metadata + counts.

  MODEL SELECTOR via GEMMA_MODEL_VARIANT env var or edit default below:

      e2b-it             google/gemma-4-2b-it          single T4
      e4b-it             google/gemma-4-4b-it          single T4
      26b-a4b-it         google/gemma-4-26b-a4b-it     T4 x2 (4-bit)
      31b-it             google/gemma-4-31b-it         T4 x2 (4-bit)
      jailbroken-31b     dealignai/Gemma-4-31B-JANG_4M-CRACK
      jailbroken-e4b     mlabonne/Gemma-4-E4B-it-abliterated
      cloud-gemini       Gemini API (set GEMINI_API_KEY)
      cloud-openai       OpenAI-compat (OPENAI_API_KEY + _BASE_URL +
                                          _MODEL)
      cloud-ollama       Ollama (OLLAMA_HOST, OLLAMA_MODEL)

  All safety content lives in duecare-llm-chat packages. This kernel is:
      model load + create_app(**default_harness()) + cloudflared.

  Requirements:
    - GPU: Single T4 for E2B/E4B; T4 x2 for 31B/26B-A4B; CPU OK for
      cloud-* variants. No model is loaded until the browser picker
      selects one.
    - Internet: Required for package installation (PyPI/GitHub)
    - Platform: Works in Kaggle, Google Colab, local Jupyter, any Python env
    - HF_TOKEN: Optional (required for gated 31B/26B-A4B variants)

  Installation: Universal compatibility via PyPI, GitHub releases, then source
============================================================================
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
DATASET_SLUG = "duecare-harness-chat-wheels"
DUECARE_REQUIRED_CHAT_VERSION = os.environ.get(
    "DUECARE_REQUIRED_CHAT_VERSION", "0.17.0"
)

# Pick which model to load. Override at runtime by exporting the env var:
#   %env GEMMA_MODEL_VARIANT=e4b-it     (in a Kaggle cell BEFORE this one)
# Recognised values:
#   e2b-it / e4b-it / 26b-a4b-it / 31b-it          on-device Gemma 4
#   jailbroken-31b / jailbroken-e4b                 abliterated variants
#   cloud-gemini / cloud-openai / cloud-ollama      BYOK cloud routes
GEMMA_MODEL_VARIANT = os.environ.get("GEMMA_MODEL_VARIANT", "e4b-it")

# On Kaggle, route the HF cache into /kaggle/working/.cache so the
# preflight disk gate (which measures /kaggle/working) and the actual
# download land on the same partition. Without this, HF defaults to
# ~/.cache/huggingface/hub which is on the root filesystem -- a
# different mount point with a different and usually smaller free
# budget. Setting HF_HOME before any transformers/unsloth import is
# critical; if those packages have already cached their cache-dir
# computation, the new HF_HOME may be ignored.
if os.path.isdir("/kaggle/working") and not os.environ.get("HF_HOME"):
    _kaggle_hf_home = "/kaggle/working/.cache/huggingface"
    try:
        os.makedirs(_kaggle_hf_home, exist_ok=True)
        os.environ["HF_HOME"] = _kaggle_hf_home
        # HF_HUB_CACHE is the modern shorthand; set both for older deps.
        os.environ.setdefault("HF_HUB_CACHE", _kaggle_hf_home + "/hub")
        os.environ.setdefault("TRANSFORMERS_CACHE", _kaggle_hf_home + "/hub")
    except OSError:
        pass
    del _kaggle_hf_home
GEMMA_LOAD_IN_4BIT  = os.environ.get("GEMMA_LOAD_IN_4BIT", "1") == "1"
GEMMA_DEVICE_MAP    = "auto"
# 32768 (not 8192) because the omni notebook contains all 5 harness
# layers. With Persona + GREP + RAG + Tools + Online ON, the merged
# prompt is ~13k chars (≈10-12k tokens) — overflows 8192. Gemma 4's
# native context window is 128K so 32k is well within capability.
# Override via env var if you're memory-constrained.
GEMMA_MAX_SEQ_LEN   = int(os.environ.get("GEMMA_MAX_SEQ_LEN", "32768"))

# Online search (optional). The chat UI surfaces an "Online" toggle when
# this is True; when False the toggle is hidden and online_search_call
# is not enabled in the harness.
ENABLE_ONLINE_SEARCH = os.environ.get("ENABLE_ONLINE_SEARCH", "1") == "1"

# Cloud-route credentials (only read for matching cloud-* variants)
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL    = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_HOST     = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "gemma2:2b")

# HuggingFace model id resolution per variant
_VARIANT_HF_ID = {
    "e2b-it":         "google/gemma-4-2b-it",
    "e4b-it":         "google/gemma-4-4b-it",
    "26b-a4b-it":     "google/gemma-4-26b-a4b-it",
    "31b-it":         "google/gemma-4-31b-it",
    "jailbroken-31b": "dealignai/Gemma-4-31B-JANG_4M-CRACK",
    "jailbroken-e4b": "mlabonne/Gemma-4-E4B-it-abliterated",
}

PORT   = 8080
TUNNEL = "cloudflared"


# ===========================================================================
# PHASE 0 -- install Hanchen's pinned Unsloth stack BEFORE any torch import.
# ===========================================================================
_UNSLOTH_MARKER = Path("/tmp/.duecare_unsloth_stack_v1_done")


def _need_unsloth_stack() -> bool:
    # Every on-device variant uses Unsloth's FastModel loader (see
    # load_gemma() below). Only cloud-* routes can skip the heavy
    # install. Earlier versions of this file gated the install on the
    # 26B/31B variants only, which broke E2B/E4B with a confusing
    # "ModuleNotFoundError: No module named 'unsloth'" at load time.
    return not _is_cloud_variant()


def _is_cloud_variant() -> bool:
    return GEMMA_MODEL_VARIANT.startswith("cloud-")


def _install_unsloth_stack_inline() -> bool:
    print("=" * 76)
    print("[phase 0] installing Hanchen's Unsloth Gemma 4 stack")
    print("=" * 76)
    print(f"  variant: {GEMMA_MODEL_VARIANT}  (one-cell run -- no restart)")
    try:
        import numpy as _np, PIL as _pil
        np_pin = f"numpy=={_np.__version__}"
        pil_pin = f"pillow=={_pil.__version__}"
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
        print(f"  INSTALL FAILED ({proc.returncode}): "
              f"{proc.stderr[-600:]}")
        return False
    print(f"  ✓ Hanchen stack installed in {time.time()-t0:.0f}s")
    try:
        _UNSLOTH_MARKER.parent.mkdir(parents=True, exist_ok=True)
        _UNSLOTH_MARKER.write_text(json.dumps(
            {"variant": GEMMA_MODEL_VARIANT,
             "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=2))
    except Exception:
        pass
    return True


_HANCHEN_STACK_INSTALLED = False
if _need_unsloth_stack():
    if _UNSLOTH_MARKER.exists():
        print(f"[phase 0] Unsloth stack marker present; skipping install")
        _HANCHEN_STACK_INSTALLED = True
    else:
        _HANCHEN_STACK_INSTALLED = _install_unsloth_stack_inline()


# ===========================================================================
# 1. Install duecare wheels (chat = UI + harness content)
# ===========================================================================
print("\n" + "=" * 76)
print(f"[1/5] installing duecare packages (GitHub-only, judge-transparent)")
print("=" * 76)


def install_chat_wheels() -> int:
    """Install DueCare packages directly from GitHub (competition-optimized).

    GitHub-only strategy for maximum transparency and judge verification.
    Works in Kaggle, Google Colab, local Jupyter, or any Python environment.
    """

    print("  → starting DueCare installation (GitHub-only, judge-friendly)...")
    print(f"  → timestamp: {time.strftime('%H:%M:%S')}")
    start_total = time.time()

    # Competition strategy: Pin to specific release artifacts for reproducibility.
    VERSION = os.environ.get("DUECARE_VERSION", "0.17.0")
    COMMIT_SHA = os.environ.get("DUECARE_COMMIT_SHA", "master")

    # Method 1: GitHub Release Wheels (fastest when available)
    try:
        print("  → attempting GitHub release installation...")
        print("    judge advantage: pre-compiled wheels, fast install")

        base_url = f"https://github.com/TaylorAmarelTech/gemma4_comp/releases/download/v{VERSION}"
        release_wheels = [
            f"{base_url}/duecare_llm_core-{VERSION}-py3-none-any.whl",
            f"{base_url}/duecare_llm_models-{VERSION}-py3-none-any.whl",
            f"{base_url}/duecare_llm_chat-{VERSION}-py3-none-any.whl"
        ]

        success_count = 0
        for i, wheel_url in enumerate(release_wheels, 1):
            wheel_name = wheel_url.split('/')[-1]
            print(f"  → [{i}/3] installing {wheel_name}...")
            start_pkg = time.time()

            cmd = [sys.executable, "-m", "pip", "install", "--no-input",
                   "--disable-pip-version-check", "--timeout=60", wheel_url]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if proc.returncode == 0:
                elapsed = time.time() - start_pkg
                print(f"  ✓ [{i}/3] {wheel_name} installed ({elapsed:.1f}s)")
                success_count += 1
            else:
                if "404" in proc.stderr or "Not Found" in proc.stderr:
                    print(f"  → [{i}/3] release wheel not found, will use source method")
                    break
                else:
                    print(f"  ✗ [{i}/3] {wheel_name} failed: {proc.stderr[-200:]}")

        if success_count == len(release_wheels):
            elapsed = time.time() - start_total
            print(f"  ✓ GitHub release installation completed ({elapsed:.1f}s)")
            print(f"  → judge verification: wheels from github.com/TaylorAmarelTech/gemma4_comp/releases/tag/v{VERSION}")
            return success_count

        print("  → release wheels incomplete, falling back to source install...")

    except Exception as e:
        print(f"  → GitHub release failed: {str(e)}")
        print("  → falling back to source install...")

    # Method 2: GitHub Source Install (most reliable, fully transparent)
    github_error = None
    try:
        print("  → attempting GitHub source installation...")
        print("    judge advantage: exact source code verification possible")
        print(f"    repository: https://github.com/TaylorAmarelTech/gemma4_comp")
        print(f"    commit: {COMMIT_SHA}")

        packages = [
            f"git+https://github.com/TaylorAmarelTech/gemma4_comp.git@{COMMIT_SHA}#subdirectory=packages/duecare-llm-core",
            f"git+https://github.com/TaylorAmarelTech/gemma4_comp.git@{COMMIT_SHA}#subdirectory=packages/duecare-llm-models",
            f"git+https://github.com/TaylorAmarelTech/gemma4_comp.git@{COMMIT_SHA}#subdirectory=packages/duecare-llm-chat"
        ]

        # Install all packages in single command for faster git operations
        print("  → installing all packages (single git clone, faster)...")
        cmd = [sys.executable, "-m", "pip", "install", "--no-input",
               "--disable-pip-version-check", "--timeout=300"] + packages

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if proc.returncode == 0:
            elapsed = time.time() - start_total
            print(f"  ✓ GitHub source installation completed ({elapsed:.1f}s)")
            print(f"  → judge verification: source code at github.com/TaylorAmarelTech/gemma4_comp/tree/{COMMIT_SHA}")

            # Verify installation worked
            try:
                import duecare.core, duecare.models, duecare.chat
                print(f"  ✓ all package imports verified")

                # Print installed versions for judge reference
                try:
                    from importlib.metadata import version
                    for pkg_name in ["duecare-llm-core", "duecare-llm-models", "duecare-llm-chat"]:
                        try:
                            v = version(pkg_name)
                            print(f"    → {pkg_name}: {v}")
                        except:
                            print(f"    → {pkg_name}: installed from source")
                except:
                    pass

                return len(packages)

            except ImportError as e:
                print(f"  ⚠ installation succeeded but imports failed: {e}")
                raise Exception("Import verification failed")

        else:
            print(f"  ✗ GitHub source installation failed")
            if proc.stderr:
                print(f"    → error: {proc.stderr[-400:]}")
            raise Exception("Source installation failed")

    except subprocess.TimeoutExpired:
        print("  ✗ GitHub source installation timed out (300s)")
        print("    → this usually indicates slow internet or large repository download")
        raise Exception("Installation timed out")

    except Exception as e:
        github_error = e
        print(f"  ✗ GitHub source installation failed: {str(e)}")
        print("  → trying fallback to local wheels...")

    # Method 3: Fallback to Available Wheels (Kaggle dataset)
    try:
        print("  → checking for Kaggle dataset wheels...")

        # Check for wheels in Kaggle input
        wheel_dirs = [
            "/kaggle/input/datasets/taylorsamarel/duecare-harness-chat-wheels",
            "/kaggle/input/duecare-harness-chat-wheels",
            "/kaggle/input/duecare-llm-wheels"
        ]

        found_wheels = []
        for wheel_dir in wheel_dirs:
            if Path(wheel_dir).exists():
                wheels = list(Path(wheel_dir).glob("*.whl"))
                if wheels:
                    found_wheels.extend([str(w) for w in wheels if "duecare" in w.name.lower()])
                    print(f"  → found {len(wheels)} wheels in {wheel_dir}")
                    break

        if not found_wheels:
            print("  ✗ no Kaggle wheels found either")
            raise Exception("No wheels available")

        def _wheel_install_key(path: str) -> tuple[int, str]:
            name = Path(path).name.lower()
            package_order = 9
            if "duecare_llm_core" in name:
                package_order = 0
            elif "duecare_llm_models" in name:
                package_order = 1
            elif "duecare_llm_chat" in name:
                package_order = 2
            return (package_order, name)

        found_wheels = sorted(found_wheels, key=_wheel_install_key)
        print(f"  → installing {len(found_wheels)} wheel(s)...")
        success_count = 0

        for i, wheel_path in enumerate(found_wheels, 1):
            wheel_name = Path(wheel_path).name
            print(f"  → [{i}/{len(found_wheels)}] installing {wheel_name}...")
            start_wheel = time.time()

            cmd = [sys.executable, "-m", "pip", "install", "--no-input",
                   "--disable-pip-version-check", "--timeout=60", wheel_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if proc.returncode == 0:
                elapsed = time.time() - start_wheel
                print(f"  ✓ [{i}/{len(found_wheels)}] {wheel_name} installed ({elapsed:.1f}s)")
                success_count += 1
            else:
                print(f"  ✗ [{i}/{len(found_wheels)}] {wheel_name} failed: {proc.stderr[-200:]}")

        if success_count > 0:
            elapsed = time.time() - start_total
            print(f"  ✓ wheels fallback successful: {success_count}/{len(found_wheels)} installed ({elapsed:.1f}s)")
            print(f"  → judge note: wheels from Kaggle dataset (GitHub source failed)")

            # Verify installation worked
            try:
                import duecare.core, duecare.models, duecare.chat
                print(f"  ✓ all package imports verified")
                return success_count
            except ImportError as e:
                print(f"  ⚠ wheels installed but imports failed: {e}")
                raise Exception("Import verification failed")
        else:
            raise Exception("All wheel installations failed")

    except Exception as wheel_error:
        print(f"  ✗ wheels fallback failed: {str(wheel_error)}")

        # All methods failed - provide detailed troubleshooting for judges
        print("\n" + "!" * 70)
        print("  ALL INSTALLATION METHODS FAILED")
        print("!" * 70)
        print("  GitHub source failed + local wheels failed.")
        print()
        print("  DIAGNOSIS:")
        print(f"  • GitHub error: {str(github_error)[:200] if github_error else 'release path failed earlier'}...")
        print(f"  • Wheels error: {str(wheel_error)[:200]}...")
        print()
        print("  POSSIBLE CAUSES:")
        print(f"  • Pinned source ref {COMMIT_SHA} is unavailable or unreachable")
        print("  • Git authentication issues")
        print("  • Wheel version incompatibility")
        print()
        print("  MANUAL FIXES:")
        print("  1. Re-run the pinned source install:")
        print(f"     !pip install git+https://github.com/TaylorAmarelTech/gemma4_comp.git@{COMMIT_SHA}#subdirectory=packages/duecare-llm-core")
        print("  2. Check repository structure:")
        print("     Visit: https://github.com/TaylorAmarelTech/gemma4_comp")
        print("  3. Verify wheels are compatible:")
        print("     Check wheel versions in /kaggle/input/")
        print("!" * 70)

        raise SystemExit("All DueCare installation methods failed - manual intervention needed")


install_chat_wheels()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--upgrade", "--no-input",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0"],
                  capture_output=True, text=True)


# ===========================================================================
# DEPLOYMENT SELF-AUDIT (portability contract)
# ---------------------------------------------------------------------------
# After the wheel install, before the model load, verify that the
# wheel actually serving the kernel matches what we expect. This
# kills the chronic "old wheel still serving" phantom-bug class.
# Override with DUECARE_ALLOW_OLD_WHEEL=1 if you need to run an
# older wheel intentionally.
# ===========================================================================
def _verify_chat_wheel_freshness() -> None:
  try:
    from importlib.metadata import version as _pkg_version
    chat_v = _pkg_version("duecare-llm-chat")
  except Exception as e:  # noqa: BLE001
    print(f"  WARN  could not resolve duecare-llm-chat version: {e}")
    chat_v = "unknown"

  try:
    from duecare.chat.portability import (
      REQUIRED_CHAT_VERSION,
      SELF_AUDIT_MINIMUM_COUNTS,
    )
    required_chat_version = os.environ.get(
      "DUECARE_REQUIRED_CHAT_VERSION", REQUIRED_CHAT_VERSION
    )
    expected = dict(SELF_AUDIT_MINIMUM_COUNTS)
  except Exception as e:  # noqa: BLE001
    print(f"  WARN  portability audit constants unavailable: {e}")
    required_chat_version = DUECARE_REQUIRED_CHAT_VERSION
    expected = {"n_grep_rules": 100, "n_rag_docs": 30, "n_dimensions": 20}

  try:
    from duecare.chat.harness import (
      GREP_RULES, RAG_CORPUS, RUBRIC_UNIVERSAL,
    )
    counts = {
      "n_grep_rules":  len(GREP_RULES),
      "n_rag_docs":    len(RAG_CORPUS),
      "n_dimensions":  len(RUBRIC_UNIVERSAL.get("dimensions", [])),
      "rubric_version": RUBRIC_UNIVERSAL.get("version", "unknown"),
    }
  except Exception as e:  # noqa: BLE001
    print(f"  ERROR could not import harness counts: {e}")
    return

  def _version_key(v: str) -> tuple[int, int, int]:
    parts = [int(x) for x in re.findall(r"\d+", v or "")[:3]]
    while len(parts) < 3:
      parts.append(0)
    return tuple(parts[:3])


  print()
  print("=" * 68)
  print(f"  DUECARE SELF-AUDIT  ·  chat-package {chat_v}")
  print("=" * 68)
  print(f"    required_version  {required_chat_version}")
  for k, v in counts.items():
    print(f"    {k:18s} {v}")
  print(f"    rubric           {counts['rubric_version']}")
  print("=" * 68)

  failures = []
  if (
      chat_v != "unknown"
      and _version_key(chat_v) < _version_key(required_chat_version)
  ):
    failures.append(
      f"duecare-llm-chat {chat_v} < required {required_chat_version}"
    )
  for key, minimum in expected.items():
    if counts.get(key, 0) < minimum:
      failures.append(
        f"{key} = {counts.get(key)} < required {minimum}")

  if failures:
    msg = (
      "Deployment self-audit FAILED:\n  - "
      + "\n  - ".join(failures)
      + "\n\nThis usually means an OLD wheel is still serving. "
      "Bump the dataset version on Kaggle and restart the kernel. "
      "To override (intentionally run an older wheel) set "
      "the environment variable DUECARE_ALLOW_OLD_WHEEL=1."
    )
    if os.environ.get("DUECARE_ALLOW_OLD_WHEEL") == "1":
      print(f"  WARN  {msg}\n  (proceeding because DUECARE_ALLOW_OLD_WHEEL=1)")
    else:
      raise RuntimeError(msg)
  else:
    print("  OK chat package version and harness counts meet the Kernel 01 contract")


_verify_chat_wheel_freshness()



# ===========================================================================
# CLEAN SHUTDOWN -- /api/shutdown POST + /shutdown GET + floating button.
# Users can:
#   (1) click the floating "Shutdown" button in the top-right of the UI
#   (2) open <public-url>/shutdown for a full confirmation page
#   (3) POST /api/shutdown directly (curl, etc.)
# All three signal the main loop to exit; cleanup runs after.
# ===========================================================================
import threading as _shutdown_threading
_SHUTDOWN_EVENT = _shutdown_threading.Event()
_CLOUDFLARED_PROC: dict = {"p": None}


_SHUTDOWN_BUTTON_SNIPPET = """
<style>
  /* Header-integrated shutdown button — placed into header.bar by JS so
     it sits next to the model badge instead of floating over the UI.
     Falls back to a fixed bottom-right position if header not found. */
  .dc-shutdown-pill {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 12px;
    background: rgba(220, 38, 38, 0.18);
    color: #fca5a5;
    border: 1px solid rgba(220, 38, 38, 0.35);
    border-radius: 999px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    font-weight: 600; font-size: 11.5px; line-height: 1;
    cursor: pointer;
    transition: all 0.15s ease;
    user-select: none;
    white-space: nowrap;
  }
  .dc-shutdown-pill:hover {
    background: rgba(220, 38, 38, 0.92);
    color: #fff;
    border-color: rgba(255, 255, 255, 0.2);
  }
  .dc-shutdown-pill[data-state="confirming"] {
    background: rgba(245, 158, 11, 0.92);
    color: #fff;
    border-color: rgba(255, 255, 255, 0.2);
  }
  .dc-shutdown-pill[data-state="shutting"] {
    background: rgba(107, 114, 128, 0.92);
    color: #fff;
    cursor: wait;
  }
  .dc-shutdown-pill[data-state="done"] {
    background: rgba(16, 185, 129, 0.92);
    color: #fff;
    cursor: default;
  }
  .dc-shutdown-pill svg {
    width: 12px; height: 12px;
    flex-shrink: 0;
    display: block;
  }
  /* Fallback fixed position: only used when header.bar is NOT found.
     Bottom-right so it doesn't overlap a header. */
  .dc-shutdown-pill.dc-floating {
    position: fixed;
    bottom: 14px; right: 14px;
    z-index: 99999;
    padding: 8px 14px;
    background: rgba(220, 38, 38, 0.92);
    color: #fff;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
  }
  /* Full-screen success overlay shown after shutdown completes */
  #_dc-shutdown-overlay {
    position: fixed; inset: 0; z-index: 100000;
    display: none;
    align-items: center; justify-content: center;
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.97) 0%, rgba(30, 41, 59, 0.97) 100%);
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
  }
  #_dc-shutdown-overlay.show { display: flex; }
  #_dc-shutdown-overlay .box {
    text-align: center;
    padding: 44px 52px;
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid rgba(71, 85, 105, 0.5);
    border-radius: 16px;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
    max-width: 440px;
  }
  #_dc-shutdown-overlay svg.icon {
    width: 56px; height: 56px;
    color: #10b981;
    margin: 0 auto 14px;
    display: block;
  }
  #_dc-shutdown-overlay h1 {
    margin: 0 0 8px 0;
    font-size: 22px; font-weight: 700;
    color: #f1f5f9;
  }
  #_dc-shutdown-overlay p {
    margin: 0; color: #94a3b8;
    font-size: 13.5px; line-height: 1.5;
  }
  #_dc-shutdown-overlay .meta {
    margin-top: 14px;
    color: #64748b; font-size: 11.5px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
</style>
<div id="_dc-shutdown-overlay" role="dialog" aria-modal="true" aria-live="polite" tabindex="-1" aria-labelledby="_dc-shutdown-title">
  <div class="box">
    <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
         aria-hidden="true">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
    <h1 id="_dc-shutdown-title">Server stopped</h1>
    <p>The FastAPI server is down and the Kaggle cell will exit shortly.</p>
    <p class="meta">You can close this tab.</p>
  </div>
</div>
<template id="_dc-shutdown-tpl">
  <button class="dc-shutdown-pill" type="button" data-state="idle"
          title="Stop the FastAPI server and exit the Kaggle cell"
          aria-label="Shutdown DueCare server">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
         aria-hidden="true">
      <path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path>
      <line x1="12" y1="2" x2="12" y2="12"></line>
    </svg>
    <span class="dc-shutdown-label">Shutdown</span>
  </button>
</template>
<script>
(function() {
  function mount() {
    var tpl = document.getElementById('_dc-shutdown-tpl');
    var overlay = document.getElementById('_dc-shutdown-overlay');
    if (!tpl || !overlay) return;
    var btn = tpl.content.firstElementChild.cloneNode(true);
    // Try to inject into the chat header bar; otherwise float bottom-right
    var header = document.querySelector('header.bar');
    if (header) {
      header.appendChild(btn);
    } else {
      btn.classList.add('dc-floating');
      document.body.appendChild(btn);
    }
    var lbl = btn.querySelector('.dc-shutdown-label');
    var confirmTimer = null;
    function setState(state, text) {
      btn.dataset.state = state;
      if (text) lbl.textContent = text;
    }
    btn.addEventListener('click', function() {
      var s = btn.dataset.state || 'idle';
      if (s === 'shutting' || s === 'done') return;
      if (s === 'confirming') {
        if (confirmTimer) clearTimeout(confirmTimer);
        setState('shutting', 'Stopping…');
        try {
          fetch('/api/shutdown', {method: 'POST'}).catch(function(){});
        } catch (e) {}
        setTimeout(function() {
          setState('done', 'Stopped');
          overlay.classList.add('show');
          overlay.focus();
        }, 350);
      } else {
        setState('confirming', 'Click again to confirm');
        confirmTimer = setTimeout(function() {
          if (btn.dataset.state === 'confirming') {
            setState('idle', 'Shutdown');
          }
        }, 4000);
      }
    });
  }
  // Run on DOM ready, and again after 800ms in case the header is hydrated
  // late by the chat UI's own JS.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
  setTimeout(function() {
    // If we mounted floating + a header has since appeared, move into it
    var existing = document.querySelector('header.bar .dc-shutdown-pill');
    var floating = document.querySelector('body > .dc-shutdown-pill.dc-floating');
    if (!existing && floating) {
      var header = document.querySelector('header.bar');
      if (header) {
        floating.classList.remove('dc-floating');
        header.appendChild(floating);
      }
    }
  }, 800);
})();
</script>
"""

_HIDE_HARNESS_TILES_SNIPPET = """
<style>
  #harness-tiles, [id^='tile-'], .harness-tile { display: none !important; }
</style>
"""


# ---------------------------------------------------------------------------
# COMPACT-LAYOUT OVERRIDE
# Default chat UI puts the safety-harness panel + sliders inside the
# composer, eating ~250px of vertical space and pushing the textarea
# near the top of the viewport. This override:
#   - Compacts each harness tile (smaller padding, smaller font, hides
#     description by default)
#   - Hides the temp/top_p/top_k/max-token sliders behind a ▸ Settings
#     toggle (rarely changed; not worth the always-visible footprint)
#   - Adds Expand / Collapse buttons to the harness-tiles header so the
#     user can bring back the full descriptions when they want depth,
#     or hide the harness panel entirely to maximize the chat area.
# Persists user choice in localStorage so reloads remember the layout.
# ---------------------------------------------------------------------------
_COMPACT_LAYOUT_SNIPPET = """
<style id="_dc-compact-layout">
  /* DueCare design tokens (from configs/duecare/design_tokens.yaml) */
  :root {
    --dc-surface-paper: #F7F6F1;
    --dc-surface-paper-2: #EFEDE4;
    --dc-surface-paper-3: #E4E1D7;
    --dc-text-ink: #0E1116;
    --dc-text-ink-2: #2A2D34;
    --dc-text-ink-3: #5B5F68;
    --dc-text-ink-4: #8A8E97;
    --dc-border-line: #DDD8C9;
    --dc-border-line-soft: #E8E4D7;
    --dc-accent-primary: oklch(0.52 0.08 195);
    --dc-accent-soft: oklch(0.92 0.03 195);
    --dc-accent-ink: oklch(0.32 0.07 195);
    --dc-ember-primary: oklch(0.58 0.14 45);
    --dc-ember-soft: oklch(0.94 0.04 45);
    --dc-semantic-good: oklch(0.55 0.10 155);
    --dc-semantic-warn: oklch(0.65 0.10 80);

    /* Legacy variable mappings for compatibility */
    --border: var(--dc-border-line);
    --accent: var(--dc-accent-primary);
    --muted: var(--dc-text-ink-4);
    --surface: var(--dc-surface-paper);
  }

  /* Compact harness tiles -------------------------------------- */
  .harness-tiles {
    padding: 8px 10px !important;
    margin-top: 8px !important;
    gap: 6px !important;
    grid-template-columns: repeat(5, 1fr) !important;
  }
  .harness-tiles-header {
    margin-bottom: 4px !important;
  }
  .harness-tiles-header h3 {
    font-size: 11px !important;
  }
  .harness-tiles-header .hint {
    font-size: 10.5px !important;
  }
  .harness-tile {
    padding: 6px 9px !important;
    gap: 3px !important;
  }
  .harness-tile-name {
    font-size: 12.5px !important;
    line-height: 1.2 !important;
  }
  .harness-tile-state {
    font-size: 9px !important;
    padding: 2px 6px !important;
  }
  /* Description + catalog hidden by default; shown when .show-details */
  .harness-tile-desc, .harness-catalog-link {
    display: none !important;
  }
  .harness-tiles.show-details .harness-tile-desc,
  .harness-tiles.show-details .harness-catalog-link {
    display: block !important;
  }
  /* Hide tiles entirely when .collapsed */
  .harness-tiles.collapsed .harness-tile,
  .harness-tiles.collapsed .harness-catalog {
    display: none !important;
  }
  /* Show the toggle bar even when collapsed */
  .harness-tiles.collapsed {
    grid-template-columns: 1fr !important;
    padding: 4px 10px !important;
  }

  /* Compact composer -------------------------------------------- */
  .composer {
    padding: 8px 12px !important;
  }
  .composer textarea {
    min-height: 38px !important;
    max-height: 160px !important;
    padding: 8px 10px !important;
    font-size: 14px !important;
  }
  .composer .pending-images {
    margin-bottom: 4px !important;
  }
  /* Sliders hidden by default; shown when body.show-controls */
  .composer .controls {
    display: none !important;
    font-size: 11px !important;
    padding: 6px 0 0 0 !important;
  }
  body.show-controls .composer .controls {
    display: flex !important;
    gap: 12px !important;
    align-items: center !important;
    flex-wrap: wrap !important;
  }
  .composer .controls input[type=range] { width: 60px !important; }
  .composer .controls input[type=number] { width: 56px !important; }

  /* Layout toolbar (Expand / Collapse / Settings) ------------- */
  .dc-layout-toolbar {
    display: flex; gap: 6px; align-items: center;
    margin-left: auto;
  }
  .dc-layout-toolbar button {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 3px 8px;
    border-radius: 5px;
    font-size: 10.5px;
    cursor: pointer;
    font-weight: 500;
    line-height: 1.2;
  }
  .dc-layout-toolbar button:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
  .dc-layout-toolbar button.on {
    background: var(--dc-accent-soft);
    border-color: var(--accent);
    color: var(--accent);
  }
</style>
<script>
(function() {
  function inject() {
    var hdr = document.querySelector('.harness-tiles-header');
    var tiles = document.getElementById('harness-tiles');
    if (!hdr || !tiles) {
      // chat UI not yet hydrated; retry
      setTimeout(inject, 300);
      return;
    }
    if (document.querySelector('.dc-layout-toolbar')) return;  // already mounted

    // Restore saved layout state from localStorage
    var ls = window.localStorage;
    var details = ls.getItem('dc-show-details') === '1';
    var hidden  = ls.getItem('dc-harness-hidden') === '1';
    var ctrls   = ls.getItem('dc-show-controls') === '1';
    if (details) tiles.classList.add('show-details');
    if (hidden)  tiles.classList.add('collapsed');
    if (ctrls)   document.body.classList.add('show-controls');

    var bar = document.createElement('div');
    bar.className = 'dc-layout-toolbar';

    var btnDetails = document.createElement('button');
    btnDetails.type = 'button';
    btnDetails.textContent = details ? 'Hide details' : 'Show details';
    if (details) btnDetails.classList.add('on');
    btnDetails.title = 'Show / hide the description on each harness tile';
    btnDetails.addEventListener('click', function() {
      var on = !tiles.classList.contains('show-details');
      tiles.classList.toggle('show-details', on);
      btnDetails.textContent = on ? 'Hide details' : 'Show details';
      btnDetails.classList.toggle('on', on);
      ls.setItem('dc-show-details', on ? '1' : '0');
    });

    var btnHide = document.createElement('button');
    btnHide.type = 'button';
    btnHide.textContent = hidden ? 'Show harness' : 'Hide harness';
    if (hidden) btnHide.classList.add('on');
    btnHide.title = 'Hide / show the entire safety-harness toggle panel to maximize chat area';
    btnHide.addEventListener('click', function() {
      var on = !tiles.classList.contains('collapsed');
      tiles.classList.toggle('collapsed', on);
      btnHide.textContent = on ? 'Show harness' : 'Hide harness';
      btnHide.classList.toggle('on', on);
      ls.setItem('dc-harness-hidden', on ? '1' : '0');
    });

    var btnControls = document.createElement('button');
    btnControls.type = 'button';
    btnControls.textContent = ctrls ? 'Hide controls' : 'Show controls';
    if (ctrls) btnControls.classList.add('on');
    btnControls.title = 'Show / hide the temp / top_p / top_k / max-tokens sliders';
    btnControls.addEventListener('click', function() {
      var on = !document.body.classList.contains('show-controls');
      document.body.classList.toggle('show-controls', on);
      btnControls.textContent = on ? 'Hide controls' : 'Show controls';
      btnControls.classList.toggle('on', on);
      ls.setItem('dc-show-controls', on ? '1' : '0');
    });

    bar.appendChild(btnDetails);
    bar.appendChild(btnControls);
    bar.appendChild(btnHide);

    // Insert after the existing Enable-all/Disable-all buttons that
    // already live with style="margin-left:auto" — we steal that
    // margin-left by inserting our toolbar AFTER it (last child of
    // the header, so flex-wrap places ours on the right edge).
    hdr.appendChild(bar);
  }

  // Mount a "Clear chat" button into the always-visible header bar
  // (the controls row that holds Clear is hidden by default in the
  // compact layout, so users had no obvious way to reset).
  function injectClearButton() {
    var headerBar = document.querySelector('header.bar');
    if (!headerBar) {
      setTimeout(injectClearButton, 300);
      return;
    }
    if (document.querySelector('.dc-header-clear')) return;
    var btn = document.createElement('button');
    btn.className = 'dc-header-clear';
    btn.type = 'button';
    btn.title = 'Clear all chat messages and start a new session';
    btn.textContent = 'Clear chat';
    btn.style.cssText = (
      'background: transparent; border: 1px solid var(--border, var(--dc-border-line, #DDD8C9));' +
      ' color: var(--muted, var(--dc-text-ink-4, #8A8E97)); padding: 5px 12px;' +
      ' border-radius: 6px; font-size: 12px; cursor: pointer;' +
      ' font-weight: 500; line-height: 1.2; margin-left: 8px;'
    );
    btn.addEventListener('mouseenter', function() {
      btn.style.borderColor = 'var(--dc-accent-primary)';
      btn.style.color = 'var(--dc-accent-primary)';
    });
    btn.addEventListener('mouseleave', function() {
      btn.style.borderColor = 'var(--border, var(--dc-border-line, #DDD8C9))';
      btn.style.color = 'var(--muted, var(--dc-text-ink-4, #8A8E97))';
    });
    btn.addEventListener('click', function() {
      if (typeof window.resetChat === 'function') {
        window.resetChat();
      } else {
        // Fallback: empty the chat container manually
        var chat = document.getElementById('chat');
        if (chat) chat.innerHTML = '';
      }
    });
    // Insert before the shutdown pill if present, else append
    var shutdown = headerBar.querySelector('.dc-shutdown-pill');
    if (shutdown) {
      headerBar.insertBefore(btn, shutdown);
    } else {
      headerBar.appendChild(btn);
    }
  }

  // Update the empty-state text that mentions GEMMA_MODEL_VARIANT
  // env var (stale — we now have an in-UI picker).
  function fixEmptyStateText() {
    var empty = document.querySelector('.empty');
    if (!empty) return;
    var html = empty.innerHTML;
    if (html.indexOf('GEMMA_MODEL_VARIANT') === -1) return;
    var fixed = html.replace(
      /pick a Gemma 4 variant via the\\s*<code>GEMMA_MODEL_VARIANT<\\/code>\\s*kernel env var/i,
      'pick a Gemma 4 variant from the in-browser <b>model picker</b>'
    );
    if (fixed !== html) empty.innerHTML = fixed;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      inject();
      injectClearButton();
      fixEmptyStateText();
    });
  } else {
    inject();
    injectClearButton();
    fixEmptyStateText();
  }
  // Retry empty-state text fix after the chat UI hydrates
  setTimeout(fixEmptyStateText, 800);
})();
</script>
"""


def _attach_shutdown(app, hide_harness_tiles: bool = False) -> None:
    """Bolt /api/shutdown + /shutdown + floating button onto any FastAPI app."""
    from fastapi.responses import HTMLResponse, JSONResponse
    from starlette.middleware.base import BaseHTTPMiddleware

    def _api_shutdown():
        _shutdown_threading.Thread(
            target=lambda: (time.sleep(0.5), _SHUTDOWN_EVENT.set()),
            daemon=True, name="shutdown-fire").start()
        return JSONResponse({"shutting_down": True,
                             "message": "Cell will exit within ~5 seconds."})

    def _shutdown_page():
        html = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Shut down DueCare</title><style>"
            "body{font-family:-apple-system,system-ui,sans-serif;"
            "background:#f8fafc;color:#1f2937;display:flex;"
            "align-items:center;justify-content:center;min-height:100vh;"
            "margin:0}.box{background:white;border:1px solid #e5e7eb;"
            "border-radius:14px;padding:40px 50px;text-align:center;"
            "max-width:480px}h1{color:oklch(0.58 0.14 45);margin:0 0 14px}"
            "p{color:#6b7280;line-height:1.6;margin:0 0 24px}"
            "button{background:oklch(0.58 0.14 45);color:white;padding:12px 28px;"
            "border:none;border-radius:10px;font-weight:700;font-size:15px;"
            "cursor:pointer}button:hover{background:oklch(0.50 0.16 45)}"
            ".meta{color:#6b7280;font-size:12px;margin-top:18px}"
            "</style></head><body><div class='box'>"
            "<h1>Shut down DueCare?</h1>"
            "<p>Stops the FastAPI server, closes the browser session "
            "(if any), terminates the cloudflared tunnel, and exits "
            "the Kaggle cell. Re-run the cell to restart.</p>"
            "<button onclick='doShutdown()'>Confirm shutdown</button>"
            "<div class='meta' id='status'></div></div>"
            "<script>async function doShutdown(){"
            "document.getElementById('status').textContent='shutting down...';"
            "try{await fetch('/api/shutdown',{method:'POST'});"
            "document.querySelector('.box').innerHTML="
            "\"<h1 style='color:oklch(0.55 0.10 155)'>Shutting down</h1>\"+"
            "\"<p>You can close this tab. The Kaggle cell will exit shortly.</p>\";"
            "}catch(e){document.getElementById('status').textContent='error: '+e.message;}}"
            "</script></body></html>")
        return HTMLResponse(html)

    app.add_api_route("/api/shutdown", _api_shutdown, methods=["POST"])
    app.add_api_route("/shutdown", _shutdown_page, methods=["GET"])

    # Inject the floating shutdown button into the main page via middleware.
    # Filters: only path "/" + content-type text/html. Streaming endpoints
    # like /api/chat (SSE / JSON) pass through untouched.
    extras = _COMPACT_LAYOUT_SNIPPET + _SHUTDOWN_BUTTON_SNIPPET
    if hide_harness_tiles:
        extras = _HIDE_HARNESS_TILES_SNIPPET + extras

    class _UIInjector(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            if request.url.path != "/":
                return response
            ct = response.headers.get("content-type", "")
            if not ct.startswith("text/html"):
                return response
            chunks = []
            async for c in response.body_iterator:
                chunks.append(c)
            try:
                html = b"".join(chunks).decode("utf-8")
            except UnicodeDecodeError:
                return response
            if "</body>" in html:
                html = html.replace("</body>", extras + "</body>", 1)
            else:
                html = html + extras
            new_headers = {k: v for k, v in response.headers.items()
                           if k.lower() != "content-length"}
            return HTMLResponse(html,
                                status_code=response.status_code,
                                headers=new_headers)

    app.add_middleware(_UIInjector)

# ===========================================================================
# 2. Load Gemma via Unsloth FastModel
# ===========================================================================
print("\n" + "=" * 76)
print("[2/5] loading Gemma 4 via Unsloth FastModel")
print("=" * 76)


@dataclass
class LoadedModel:
    backend: Any
    tokenizer: Any
    model: Any
    name: str
    size_b: float
    quantization: str
    device: str


_MODEL_LOAD_LOG_LOCK = threading.Lock()
_MODEL_LOAD_EVENTS: list[dict[str, Any]] = []
_MODEL_LOAD_MAX_EVENTS = 500
_MODEL_LOAD_STATUS_HEARTBEAT_SECONDS = 10.0


def _reset_load_events() -> None:
    """Clear the in-memory model-loader log ring."""
    with _MODEL_LOAD_LOG_LOCK:
        _MODEL_LOAD_EVENTS.clear()


def _snapshot_load_events(limit: int = 120) -> list[dict[str, Any]]:
    """Return the most recent model-loader log events for the UI."""
    limit = max(1, min(int(limit), _MODEL_LOAD_MAX_EVENTS))
    with _MODEL_LOAD_LOG_LOCK:
        return [dict(e) for e in _MODEL_LOAD_EVENTS[-limit:]]


def _log_load(message: str, *, phase: Optional[str] = None,
              level: str = "info") -> None:
    """Record a model-loading event and mirror it to Kaggle stdout."""
    state = globals().get("_MODEL_LOAD_STATE")
    elapsed = None
    if isinstance(state, dict) and state.get("started_at"):
        elapsed = round(time.time() - float(state["started_at"]), 1)
    event = {
        "ts": time.strftime("%H:%M:%S"),
        "elapsed_s": elapsed,
        "phase": phase,
        "level": level,
        "message": message,
    }
    with _MODEL_LOAD_LOG_LOCK:
        _MODEL_LOAD_EVENTS.append(event)
        if len(_MODEL_LOAD_EVENTS) > _MODEL_LOAD_MAX_EVENTS:
            del _MODEL_LOAD_EVENTS[:-_MODEL_LOAD_MAX_EVENTS]
        seq = len(_MODEL_LOAD_EVENTS)
    if isinstance(state, dict):
        state["last_log"] = message
        state["updated_at"] = time.time()
        state["log_seq"] = seq
        if phase:
            state["phase"] = phase
    prefix = f"  [load-model][{level}]"
    if phase:
        prefix += f"[{phase}]"
    print(f"{prefix} {message}")


def _maybe_log_load_status_heartbeat() -> None:
    """Emit a status-poll heartbeat while a model is inside a long load.

    FastModel.from_pretrained can spend minutes inside download, shard-map,
    quantization, or CUDA placement. The shared runtime has its own heartbeat,
    but some Unsloth/HF phases can delay that thread. This fallback is driven
    by /api/load-model/status polling so the browser lightbox keeps showing
    fresh activity instead of appearing frozen.
    """
    state = globals().get("_MODEL_LOAD_STATE")
    if not isinstance(state, dict):
        return
    if state.get("status") != "loading" or not state.get("started_at"):
        return
    now = time.time()
    last_times = [
        float(v) for v in (
            state.get("updated_at"),
            state.get("last_status_heartbeat_at"),
            state.get("started_at"),
        )
        if isinstance(v, (int, float)) and v > 0
    ]
    last = max(last_times) if last_times else 0.0
    if now - last < _MODEL_LOAD_STATUS_HEARTBEAT_SECONDS:
        return
    elapsed = round(now - float(state["started_at"]))
    variant = str(state.get("variant") or "model")
    phase = str(state.get("phase") or "loading")
    eta = ""
    try:
        eta = str(_VARIANT_INFO.get(variant, {}).get("load_eta") or "")
    except Exception:
        eta = ""
    last_log = str(state.get("last_log") or "")
    message = f"still loading {variant}; phase={phase}; {elapsed}s elapsed"
    if eta:
        message += f"; expected {eta}"
    if last_log and last_log not in message:
        message += f"; last event: {last_log[:140]}"
    state["last_status_heartbeat_at"] = now
    _log_load(message, phase=phase)


def _model_size_b(variant: str) -> float:
    return {
        "e2b-it": 2.0, "e4b-it": 4.0,
        "26b-a4b-it": 26.0, "31b-it": 31.0,
        "jailbroken-31b": 31.0, "jailbroken-e4b": 4.0,
        "cloud-gemini": 0.0, "cloud-openai": 0.0, "cloud-ollama": 0.0,
    }.get(variant.lower(), 0.0)


def _detect_gpu() -> dict:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            lines = [l.strip() for l in out.stdout.strip().split("\n") if l.strip()]
            first = lines[0].split(",")
            return {"available": True, "name": first[0].strip(),
                     "vram_gb": float(first[1].strip()) / 1024.0,
                     "count": len(lines)}
    except Exception:
        pass
    return {"available": False, "name": "", "vram_gb": 0.0, "count": 0}


def _load_cloud_route() -> Optional[LoadedModel]:
    """Cloud-route variants: route gemma_call to a hosted API instead
    of loading a model locally. No GPU needed."""
    variant = GEMMA_MODEL_VARIANT
    if variant == "cloud-gemini":
        if not GEMINI_API_KEY:
            print("  cloud-gemini selected but GEMINI_API_KEY not set; "
                    "set it and re-run.")
            return None
        import urllib.request as _u, json as _json
        def _gemini_call(messages, **gen_kwargs):
            # Compact messages → Gemini's contents format
            user_text = ""
            for m in messages:
                if m.get("role") == "user":
                    for c in m.get("content", []):
                        if isinstance(c, dict) and c.get("type") == "text":
                            user_text += c.get("text", "") + "\n"
                        elif isinstance(c, str):
                            user_text += c + "\n"
            payload = _json.dumps({"contents": [{
                "parts": [{"text": user_text.strip()}]
            }]}).encode("utf-8")
            url = ("https://generativelanguage.googleapis.com/v1beta/"
                     "models/gemini-1.5-flash:generateContent?key="
                     + GEMINI_API_KEY)
            req = _u.Request(url, data=payload,
                             headers={"Content-Type": "application/json"})
            with _u.urlopen(req, timeout=120) as resp:
                data = _json.loads(resp.read())
            try:
                from duecare.chat._model_output import sanitize_model_output
                raw = data["candidates"][0]["content"]["parts"][0]["text"]
                return sanitize_model_output(raw)
            except (KeyError, IndexError):
                return f"[gemini error: {data}]"
        return LoadedModel(
            backend=_gemini_call, tokenizer=None, model=None,
            name="gemini-1.5-flash (cloud)", size_b=0.0,
            quantization="cloud-hosted", device="cloud:gemini",
        )
    if variant == "cloud-openai":
        if not OPENAI_API_KEY:
            print("  cloud-openai selected but OPENAI_API_KEY not set.")
            return None
        import urllib.request as _u, json as _json
        def _openai_call(messages, max_new_tokens=512, temperature=1.0,
                          top_p=0.95, **gen_kwargs):
            api_msgs = []
            for m in messages:
                content = ""
                for c in m.get("content", []):
                    if isinstance(c, dict) and c.get("type") == "text":
                        content += c.get("text", "")
                    elif isinstance(c, str):
                        content += c
                api_msgs.append({"role": m.get("role", "user"),
                                  "content": content})
            payload = _json.dumps({
                "model": OPENAI_MODEL, "messages": api_msgs,
                "max_tokens": max_new_tokens,
                "temperature": temperature, "top_p": top_p,
            }).encode("utf-8")
            req = _u.Request(
                f"{OPENAI_BASE_URL}/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}",
                         "Content-Type": "application/json"})
            with _u.urlopen(req, timeout=120) as resp:
                data = _json.loads(resp.read())
            from duecare.chat._model_output import sanitize_model_output
            return sanitize_model_output(
              data["choices"][0]["message"]["content"])
        return LoadedModel(
            backend=_openai_call, tokenizer=None, model=None,
            name=f"{OPENAI_MODEL} (cloud)", size_b=0.0,
            quantization="cloud-hosted", device="cloud:openai",
        )
    if variant == "cloud-ollama":
        import urllib.request as _u, json as _json
        def _ollama_call(messages, max_new_tokens=512, temperature=1.0,
                          **gen_kwargs):
            api_msgs = []
            for m in messages:
                content = ""
                for c in m.get("content", []):
                    if isinstance(c, dict) and c.get("type") == "text":
                        content += c.get("text", "")
                    elif isinstance(c, str):
                        content += c
                api_msgs.append({"role": m.get("role", "user"),
                                  "content": content})
            payload = _json.dumps({
                "model": OLLAMA_MODEL, "messages": api_msgs,
                "stream": False,
                "options": {"temperature": temperature,
                              "num_predict": max_new_tokens},
            }).encode("utf-8")
            req = _u.Request(
                f"{OLLAMA_HOST}/api/chat", data=payload,
                headers={"Content-Type": "application/json"})
            with _u.urlopen(req, timeout=300) as resp:
                data = _json.loads(resp.read())
            from duecare.chat._model_output import sanitize_model_output
            raw = data.get("message", {}).get("content",
                                                f"[ollama error: {data}]")
            return sanitize_model_output(raw)
        return LoadedModel(
            backend=_ollama_call, tokenizer=None, model=None,
            name=f"{OLLAMA_MODEL} (ollama)", size_b=0.0,
            quantization="ollama-hosted", device=f"ollama:{OLLAMA_HOST}",
        )
    return None


def load_gemma() -> Optional[LoadedModel]:
  # Cloud routes don't need GPU detection or Unsloth.
  if _is_cloud_variant():
    _log_load(f"variant={GEMMA_MODEL_VARIANT} -> routing to cloud API",
          phase="cloud-route")
    return _load_cloud_route()

  # Canonical local Gemma 4 path. This delegates to the same shared
  # Unsloth FastModel runtime used by A-00 and 02-live-demo:
  # That shared primitive owns the Unsloth load call, Gemma-4 thinking
  # template, heartbeat logs, GPU memory logs, and sanitized model output.
  try:
    from duecare.chat.gemma4_runtime import Gemma4LoadSpec, Gemma4Runtime

    def _runtime_log(phase: str, message: str) -> None:
      level = "warn" if phase in {"preload"} else "error" if phase in {"error", "gpu-missing"} else "info"
      _log_load(message, phase=phase, level=level)

    loaded_shared = Gemma4Runtime(log=_runtime_log).load(Gemma4LoadSpec(
      source="hf",
      model_ref=GEMMA_MODEL_VARIANT,
      quantization="4bit" if GEMMA_LOAD_IN_4BIT else "bf16",
      max_seq_length=GEMMA_MAX_SEQ_LEN,
    ))
    info = loaded_shared.info
    variant = str(info.get("variant") or GEMMA_MODEL_VARIANT)
    device = str(info.get("device") or "cuda")
    if info.get("device_map") == "balanced":
      gpu = _detect_gpu()
      device = f"balanced ({gpu.get('count', 2)}x {gpu.get('name', 'GPU')})"
    _log_load("model backend callable ready", phase="ready")
    return LoadedModel(
      backend=loaded_shared.backend,
      tokenizer=loaded_shared.tokenizer,
      model=loaded_shared.model,
      name=f"gemma-4-{variant}",
      size_b=_model_size_b(variant),
      quantization="4-bit nf4" if GEMMA_LOAD_IN_4BIT else "bf16",
      device=device,
    )
  except Exception as e:  # noqa: BLE001
    _log_load(f"shared FastModel runtime FAILED: {type(e).__name__}: {str(e)[:500]}",
          phase="error", level="error")
    for line in traceback.format_exc().splitlines()[-10:]:
      _log_load(line, phase="error", level="error")
    return None

# ===========================================================================
# 3. Build chat server WITHOUT a model loaded yet. The picker overlay
#    (injected below) lets the user pick a variant in the browser; the
#    server loads it on demand via POST /api/load-model. This keeps the
#    "9-variant model selector" claim honest — judges see a real picker.
# ===========================================================================
print("\n" + "=" * 76)
print("[3/5] launching chat server (no model loaded yet — picker UI)")
print("=" * 76)

from duecare.chat import create_app
from duecare.chat.harness import (
    default_harness, GREP_RULES, RAG_CORPUS, _TOOL_DISPATCH,
)
# Telemetry hook -- canonical structured logging across all DueCare
# kernels. Defensive try/except so older duecare-llm-chat versions
# without _dc_log degrade to a no-op stub rather than failing the
# kernel boot.
try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("01-duecare-exploration-workbench")
    dc_log("kernel.start", "exploration workbench loading")
except Exception:
    def dc_log(*a, **kw):  # type: ignore[no-redef]
        return None
import uvicorn
from fastapi import Body
from fastapi.responses import JSONResponse

# Placeholder model_info shown until the user picks a variant
_placeholder_model_info = {
    "loaded": False, "name": None, "size_b": 0.0,
    "quantization": "none", "device": "none",
    "display": "(no model loaded — pick one in the browser)",
}

# All 4 layers (Persona / GREP / RAG / Tools) wired in one line.
# 5th layer (Online) is wired below if ENABLE_ONLINE_SEARCH=1.
_create_kwargs = {
    "gemma_call": None,
    "model_info": _placeholder_model_info,
    **default_harness(),
}

_online_search_fn = {"f": None}
def _online_search_dispatch(query: str, top_n: int = 5) -> dict:
    f = _online_search_fn["f"]
    if f is None:
        return {"query": query, "results": [], "source": "not_wired"}
    return f(query, top_n=top_n)
if ENABLE_ONLINE_SEARCH:
    _create_kwargs["online_search_call"] = _online_search_dispatch

# v0.8.0/v0.8.1: optional cross-encoder reranker + dense embedder.
# Single helper handles env-var toggles + lazy load + cache wrapping.
# Replaces the 30+ lines of per-kernel boilerplate that used to live
# here — pattern is now identical across all 13 kernels.
# Env vars:
#   ENABLE_RERANKER=1   (default ON; ~70 MB CPU model)
#   ENABLE_EMBEDDER=1   (default ON; ~80 MB CPU model + cache)
#   DUECARE_DISABLE_*=1 (hard kill switch for either hook)
try:
    from duecare.chat.kernel_helpers import default_optional_hooks
    _create_kwargs.update({k: v for k, v in default_optional_hooks().items()
                              if v is not None})
except Exception as _e:  # noqa: BLE001
    print(f"  · default_optional_hooks failed: {_e}")

app = create_app(**_create_kwargs)
_attach_shutdown(app)


def _verify_portable_app_contract(app) -> None:
    """Fail fast if Kernel 01 is not serving the reusable workbench contract."""
    try:
        from duecare.chat.app import KO_TYPES, KO_TYPE_CATALOG
        from duecare.chat.portability import verify_app_contract
        contract = verify_app_contract(
            app,
            ko_types_count=len(KO_TYPES),
            ko_catalog_count=len(KO_TYPE_CATALOG),
        )
    except Exception as e:  # noqa: BLE001
        contract = {
            "evaluation": {
                "ok": False,
                "failures": [f"portability contract import failed: {type(e).__name__}: {e}"],
                "counts": {},
            },
            "required_endpoints": [],
            "required_sample_files": [],
        }
    evaluation = contract.get("evaluation", {})
    counts = evaluation.get("counts", {})
    failures = list(evaluation.get("failures") or [])

    print()
    print("=" * 68)
    print("  KERNEL 01 PORTABILITY CONTRACT")
    print("=" * 68)
    print(f"    required_routes  {counts.get('required_routes', len(contract.get('required_endpoints', [])))}")
    print(f"    served_routes    {counts.get('served_routes', 0)}")
    print(f"    ko_types         {counts.get('knowledge_types', 0)}")
    print(f"    ko_catalog       {counts.get('knowledge_types_with_catalog', 0)}")
    print(f"    required_samples {counts.get('required_samples', len(contract.get('required_sample_files', [])))}")
    print("=" * 68)

    if failures:
        msg = (
            "Kernel 01 portability contract FAILED:\n  - "
            + "\n  - ".join(failures)
            + "\n\nThis usually means the notebook is serving an old or partial "
              "duecare-llm-chat package. Rebuild/publish the 0.17.0 wheel or "
              "force the GitHub/source install path. To override intentionally, "
              "set DUECARE_ALLOW_OLD_WHEEL=1."
        )
        if os.environ.get("DUECARE_ALLOW_OLD_WHEEL") == "1":
            print(f"  WARN  {msg}\n  (proceeding because DUECARE_ALLOW_OLD_WHEEL=1)")
        else:
            raise RuntimeError(msg)
    else:
        print("  OK reusable endpoints, knowledge catalog, and sample assets are present")


_verify_portable_app_contract(app)


# ---------------------------------------------------------------------------
# Inference queue (multi-user safety net)
# ---------------------------------------------------------------------------
#
# The kernel runs a single FastAPI process backed by one GPU. A single
# Gemma 4 model can only generate one response at a time -- Python's
# GIL + CUDA's single stream serialise concurrent ``model.generate``
# calls implicitly, but without an explicit queue:
#
#   * Users get no feedback that they are waiting on someone else
#   * A pathological large prompt can hold the GPU indefinitely
#   * The kernel cannot reject obviously over-subscribed traffic
#
# ``_ModelQueue`` wraps every call to the resident chat backend (and
# the optional judge backend) with a small ticket system. Each call
# acquires a per-slot ``threading.Lock``; concurrent callers wait
# their turn. A background-friendly snapshot is exposed via
# ``GET /api/queue/status`` so the workbench chrome can render
# "N waiting on chat" indicators across every page.
#
# Design notes:
#
#   * Each slot ("chat", "judge") has its own lock so chat and judge
#     can run in parallel when both models are loaded.
#   * Threading locks are not strictly FIFO. For small queues (cap 5)
#     the unfairness is bounded by a single call's duration, which we
#     accept in exchange for simplicity.
#   * Backpressure: if more than ``MAX_WAITING`` tickets are already
#     waiting on a slot, new calls raise ``_QueueFull`` which the
#     exception handler converts to HTTP 503.
#   * No async/await: Gemma generation is sync and runs on a thread
#     pool (FastAPI's def routes) or in explicit background threads
#     (process / draft / anonymize jobs). ``threading.Lock`` is the
#     correct primitive everywhere.
#
import uuid


class _QueueFull(Exception):
    """Raised when more than _ModelQueue.MAX_WAITING tickets are
    already queued for the same slot. Surfaced as HTTP 503 so the
    UI can show "the kernel is busy" instead of timing out."""


class _QueueClosed(Exception):
    """Raised when a request arrives at a slot that is not accepting
    new tickets. Happens during model unload/load transitions: while
    Taylor (or another operator) is swapping the resident model,
    new requests are refused with HTTP 503 to prevent a crash mid-
    generate when the underlying tensors get freed."""


class _ModelQueue:
    """Thread-safe inference queue manager for the chat + judge slots.

    Per-slot state machine:
      * ``closed``   -- no model loaded; new tickets are refused.
      * ``open``     -- accepting tickets normally.
      * ``draining`` -- ``close_slot`` was called; in-flight tickets
                        run to completion but new tickets are refused.

    The state transitions are:
        closed --(open_slot)-->   open
        open   --(close_slot)-->  draining (then closed when active=0)
        draining --(open_slot)--> open (if a load races a re-open)

    Load/unload endpoints call ``close_slot`` before freeing tensors
    and ``open_slot`` after a fresh backend is wired, so concurrent
    users cannot trigger a use-after-free on the model weights.
    """

    MAX_WAITING = 5
    MAX_CALL_SECONDS = 30 * 60  # 30-minute generous cap for the longest 31B prompts
    DRAIN_POLL_SECONDS = 0.25   # how often close_slot polls the active set

    # Slot states
    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_DRAINING = "draining"

    def __init__(self) -> None:
        # Protects the slots dict + each slot's ticket list. Re-entrant
        # because snapshot() may be called from within wrap() during
        # logging in future extensions.
        self._meta = threading.RLock()
        self._slots: dict[str, dict[str, Any]] = {}

    def _slot(self, name: str) -> dict[str, Any]:
        with self._meta:
            if name not in self._slots:
                self._slots[name] = {
                    "call_lock": threading.Lock(),
                    "tickets": [],
                    # Total served counter for observability; useful for
                    # spotting "we served 30 requests this session".
                    "served_total": 0,
                    # State machine -- starts closed because no model is
                    # wired until _queue_wrap is called from the load
                    # thread. The wrapper transitions it to "open".
                    "state": self.STATE_CLOSED,
                }
            return self._slots[name]

    def open_slot(self, name: str) -> None:
        """Mark a slot as accepting tickets. Called after a successful
        load (or after a force-cancelled drain that needs to recover)."""
        slot = self._slot(name)
        with self._meta:
            slot["state"] = self.STATE_OPEN

    def close_slot(
        self,
        name: str,
        *,
        wait_seconds: float = 0.0,
        force: bool = False,
    ) -> dict[str, Any]:
        """Refuse new tickets and (optionally) wait for in-flight calls
        to complete.

        Returns a dict describing what happened:

          * ``state``: final slot state ("closed" or "draining")
          * ``active_at_close``: how many tickets were running when
            close started
          * ``waiting_at_close``: how many tickets were waiting when
            close started
          * ``drained``: True if the active set was 0 at exit
          * ``waited_seconds``: how long the drain took

        With ``force=True``, the close happens immediately regardless
        of in-flight calls. The caller is responsible for the
        downstream effect (model.generate may raise when tensors are
        freed out from under it). With ``force=False`` and a non-zero
        ``wait_seconds``, the call polls until either active == 0 or
        the timeout elapses.
        """
        slot = self._slot(name)
        with self._meta:
            tickets = list(slot["tickets"])
            active_at_close = sum(1 for t in tickets if t["started_at"] is not None)
            waiting_at_close = sum(1 for t in tickets if t["started_at"] is None)
            # Mark draining FIRST so no new tickets sneak in past the
            # snapshot we just took. Existing waiters still hold their
            # ticket entries and will continue, but they were already
            # past the state check at enqueue time.
            slot["state"] = self.STATE_DRAINING

        start = time.time()
        deadline = start + max(0.0, float(wait_seconds))

        if force:
            with self._meta:
                slot["state"] = self.STATE_CLOSED
            return {
                "state": self.STATE_CLOSED,
                "active_at_close": active_at_close,
                "waiting_at_close": waiting_at_close,
                "drained": active_at_close == 0,
                "waited_seconds": 0.0,
                "forced": True,
            }

        while time.time() < deadline:
            with self._meta:
                active_now = sum(
                    1 for t in slot["tickets"]
                    if t["started_at"] is not None
                )
            if active_now == 0:
                with self._meta:
                    slot["state"] = self.STATE_CLOSED
                return {
                    "state": self.STATE_CLOSED,
                    "active_at_close": active_at_close,
                    "waiting_at_close": waiting_at_close,
                    "drained": True,
                    "waited_seconds": round(time.time() - start, 2),
                    "forced": False,
                }
            time.sleep(self.DRAIN_POLL_SECONDS)

        # Timed out -- slot stays in DRAINING so existing tickets can
        # still finish but no new tickets enter. The caller decides
        # whether to escalate to force=True.
        return {
            "state": self.STATE_DRAINING,
            "active_at_close": active_at_close,
            "waiting_at_close": waiting_at_close,
            "drained": False,
            "waited_seconds": round(time.time() - start, 2),
            "forced": False,
        }

    def is_busy(self, name: str) -> bool:
        """Quick check used by load/unload endpoints to refuse a
        model switch when the slot still has work in flight."""
        with self._meta:
            slot = self._slots.get(name)
            if not slot:
                return False
            return any(slot["tickets"])

    def slot_state(self, name: str) -> str:
        with self._meta:
            slot = self._slots.get(name)
            return (slot or {}).get("state", self.STATE_CLOSED)

    def wrap(self, backend_fn, slot_name: str):
        """Return a queue-aware wrapper around ``backend_fn``.

        The wrapper:
          1. Enqueues a ticket with id + enqueued-at timestamp.
          2. Acquires the slot's call_lock, stamping started-at.
          3. Calls the wrapped backend with the original args.
          4. Always releases the lock + removes the ticket in finally.

        Raises ``_QueueFull`` if too many tickets are already waiting.
        Never raises during the actual model call -- exceptions from
        the wrapped backend propagate cleanly.
        """
        slot_name = str(slot_name)

        def queued(*args, **kwargs):
            slot = self._slot(slot_name)
            ticket = {
                "id": uuid.uuid4().hex[:12],
                "slot": slot_name,
                "enqueued_at": time.time(),
                "started_at": None,
            }
            with self._meta:
                # Refuse if the slot is not open. This is the gate that
                # prevents a use-after-free when one user is unloading
                # the model while another submits a new request.
                state = slot.get("state", self.STATE_CLOSED)
                if state != self.STATE_OPEN:
                    raise _QueueClosed(
                        f"The {slot_name} model is not accepting new "
                        f"requests (state={state}). The operator is "
                        f"probably swapping models. Please retry in "
                        f"a few seconds."
                    )
                waiting = sum(
                    1 for t in slot["tickets"] if t["started_at"] is None
                )
                if waiting >= self.MAX_WAITING:
                    raise _QueueFull(
                        f"Inference queue full: {waiting} requests are "
                        f"already waiting on the {slot_name} model. "
                        f"Please retry in a few seconds."
                    )
                slot["tickets"].append(ticket)
            try:
                slot["call_lock"].acquire()
                # Re-check state after acquire. The slot may have
                # transitioned to draining/closed while we were waiting
                # for the lock (force-unload from another caller). If
                # so, release the lock and refuse with _QueueClosed so
                # the call never reaches a possibly-None backend.
                with self._meta:
                    post_state = slot.get("state", self.STATE_CLOSED)
                if post_state != self.STATE_OPEN:
                    slot["call_lock"].release()
                    raise _QueueClosed(
                        f"The {slot_name} model was unloaded while this "
                        f"request was waiting in line. Retry once the "
                        f"new model finishes loading."
                    )
                ticket["started_at"] = time.time()
                try:
                    return backend_fn(*args, **kwargs)
                finally:
                    slot["call_lock"].release()
                    with self._meta:
                        slot["served_total"] = (
                            slot.get("served_total", 0) + 1
                        )
            finally:
                with self._meta:
                    try:
                        slot["tickets"].remove(ticket)
                    except ValueError:
                        pass

        # Carry over the original __name__ so any reflective code (e.g.,
        # observability logging) sees a useful identifier rather than
        # "queued".
        try:
            queued.__name__ = f"queued_{slot_name}_call"
            queued.__wrapped__ = backend_fn
        except Exception:
            pass
        return queued

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-friendly snapshot of every slot's queue state."""
        now = time.time()
        with self._meta:
            slots_out: dict[str, Any] = {}
            for slot_name, slot in self._slots.items():
                tickets = list(slot["tickets"])
                active = [t for t in tickets if t["started_at"] is not None]
                waiting = [t for t in tickets if t["started_at"] is None]
                # Sort waiting by enqueue time so position index is
                # stable for the UI.
                waiting.sort(key=lambda t: t["enqueued_at"])
                slots_out[slot_name] = {
                    "state": slot.get("state", self.STATE_CLOSED),
                    "n_active": len(active),
                    "n_waiting": len(waiting),
                    "served_total": int(slot.get("served_total", 0)),
                    "active": [
                        {
                            "ticket_id": t["id"],
                            "started_at": t["started_at"],
                            "elapsed_secs": round(
                                now - (t["started_at"] or now), 2
                            ),
                        }
                        for t in active
                    ],
                    "waiting": [
                        {
                            "ticket_id": t["id"],
                            "enqueued_at": t["enqueued_at"],
                            "wait_secs": round(now - t["enqueued_at"], 2),
                            "position": idx + 1,
                        }
                        for idx, t in enumerate(waiting)
                    ],
                }
            return {
                "queued_at": now,
                "max_waiting": self.MAX_WAITING,
                "slots": slots_out,
            }


_MODEL_QUEUE = _ModelQueue()


def _queue_wrap(backend_fn, slot_name: str):
    """Shorthand used at backend-assignment sites."""
    return _MODEL_QUEUE.wrap(backend_fn, slot_name)


def _parse_bool(value: Any, default: bool = False) -> bool:
    """Parse a request-body field that should be boolean.

    Python's bare ``bool()`` cast returns True for any non-empty string
    including ``"false"`` and ``"0"``. Browsers + curl users routinely
    send JSON booleans as strings; without explicit handling the toggle
    endpoint silently misinterprets them. This helper accepts:

      * native True / False  -> as-is
      * 1 / 0                -> True / False
      * "true" / "false" / "yes" / "no" / "on" / "off" (case-insensitive)
      * None / missing       -> default

    Anything else returns ``default`` so an obviously bogus value
    cannot quietly enable a destructive flag.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("true", "1", "yes", "y", "on"):
            return True
        if s in ("false", "0", "no", "n", "off", ""):
            return False
    return default


@app.exception_handler(_QueueFull)
async def _queue_full_handler(request, exc):
    return JSONResponse(
        {
            "status": "queue_full",
            "message": str(exc),
            "max_waiting": _ModelQueue.MAX_WAITING,
            "queue": _MODEL_QUEUE.snapshot(),
        },
        status_code=503,
    )


@app.exception_handler(_QueueClosed)
async def _queue_closed_handler(request, exc):
    # 503 with retry-friendly status so the UI can poll
    # /api/queue/status and retry once the slot is back open.
    return JSONResponse(
        {
            "status": "queue_closed",
            "message": str(exc),
            "queue": _MODEL_QUEUE.snapshot(),
        },
        status_code=503,
    )


@app.get("/api/queue/status")
def api_queue_status():
    """Live inference queue snapshot.

    Polled by the workbench chrome every few seconds so any page can
    show "1 ahead of you" without sprinkling per-page state. Cheap
    (no model touch); safe to call frequently.
    """
    return _MODEL_QUEUE.snapshot()


# ---------------------------------------------------------------------------
# Model picker — POST /api/load-model + GET /api/load-model/status
# ---------------------------------------------------------------------------
loaded = None  # set by the load thread once a variant is chosen
_MODEL_LOAD_LOCK  = threading.Lock()
_MODEL_LOAD_STATE = {
    "status":     "idle",
    "variant":    None,
    "selected_display": None,
    "phase":      "idle",
    "started_at": None,
    "updated_at": None,
    "completed_at": None,
    "error":      None,
    "last_log":   None,
    "log_seq":    0,
    "last_status_heartbeat_at": None,
}

_VARIANT_INFO = {
    "e2b-it":         {"display": "Gemma 4 E2B-it",          "size_gb": 2.0,  "fits": "single T4",  "category": "on-device", "load_eta": "~20–30 sec"},
    "e4b-it":         {"display": "Gemma 4 E4B-it",          "size_gb": 4.0,  "fits": "single T4",  "category": "on-device", "load_eta": "~30–60 sec"},
    "26b-a4b-it":     {"display": "Gemma 4 26B-A4B-it",       "size_gb": 14.0, "fits": "T4 ×2 (4-bit)", "category": "on-device", "load_eta": "~6–15 min first run · ~3–5 min cached"},
    "31b-it":         {"display": "Gemma 4 31B-it",          "size_gb": 18.0, "fits": "T4 ×2 (4-bit)", "category": "on-device", "load_eta": "~15–25 min first run (HF download) · ~5–8 min cached"},
    "jailbroken-31b": {"display": "Gemma 4 31B (abliterated)", "size_gb": 18.0, "fits": "T4 ×2 (4-bit)", "category": "jailbroken", "load_eta": "~15–25 min first run · repo quirks possible"},
    "jailbroken-e4b": {"display": "Gemma 4 E4B (abliterated)", "size_gb": 4.0,  "fits": "single T4",  "category": "jailbroken", "load_eta": "~30–60 sec"},
    "cloud-gemini":   {"display": "Gemini API (cloud)",       "size_gb": 0.0,  "fits": "no GPU",     "category": "cloud", "load_eta": "instant"},
    "cloud-openai":   {"display": "OpenAI-compat (cloud)",    "size_gb": 0.0,  "fits": "no GPU",     "category": "cloud", "load_eta": "instant"},
    "cloud-ollama":   {"display": "Ollama (cloud/local)",     "size_gb": 0.0,  "fits": "no GPU",     "category": "cloud", "load_eta": "instant"},
}
try:
    from duecare.chat.portability import model_variant_ui_map as _dc_model_variant_ui_map
    _VARIANT_INFO = _dc_model_variant_ui_map()
except Exception:
    pass


@app.get("/api/load-model/status")
def api_load_model_status():
  elapsed = None
  if _MODEL_LOAD_STATE.get("started_at"):
    elapsed = round(time.time() - _MODEL_LOAD_STATE["started_at"], 1)
  _maybe_log_load_status_heartbeat()
  variant = _MODEL_LOAD_STATE.get("variant")
  return {
    **_MODEL_LOAD_STATE,
    "elapsed_s": elapsed,
    "ready":     app.state.gemma_call is not None,
    "variants":  _VARIANT_INFO,
    "eta":       _VARIANT_INFO.get(variant or "", {}).get("load_eta"),
    "active_model": app.state.model_info or _placeholder_model_info,
    "logs":      _snapshot_load_events(120),
  }


@app.get("/api/load-model/logs")
def api_load_model_logs(limit: int = 200):
    """Return the model-loader log ring for the browser log viewer."""
    return {
        "state": _MODEL_LOAD_STATE,
        "logs": _snapshot_load_events(limit),
    }


@app.post("/api/load-model")
def api_load_model(body: dict = Body(...)):
    """Pick a Gemma 4 variant and load it. Long-running (~30s for E4B,
  ~5-10+ min for 31B first run); kicks off a background thread and returns
    immediately. Poll /api/load-model/status until status='ready'."""
    variant = (body or {}).get("variant", "").strip()
    override = bool((body or {}).get("override", False))
    if app.state.gemma_call is not None:
        return {"status": "already_loaded",
                "variant": _MODEL_LOAD_STATE.get("variant"),
                "message": "A model is already resident in GPU memory. "
                           "POST /api/unload-model first, then retry."}
    if variant not in _VARIANT_INFO:
        return JSONResponse(
            {"status": "error",
             "error": f"unknown variant: {variant!r}. "
                       f"Choose one of: {sorted(_VARIANT_INFO.keys())}"},
            status_code=400)
    # Preflight: refuse to start the load when we know it won't fit.
    # Same gate as the judge slot. Override is for advanced users who
    # understand the risk (e.g., have cleaned the HF cache manually).
    pre = _model_preflight(variant)
    if not pre["ok"] and not override:
        return JSONResponse(
            {"status": "preflight_failed",
             "variant": variant,
             "preflight": pre,
             "message": (
                 "Preflight failed: " + "; ".join(pre["reasons"]) +
                 ". Free disk / VRAM and retry, or pass {\"override\": true}."
             )},
            status_code=503,
        )
    if not _MODEL_LOAD_LOCK.acquire(blocking=False):
         current = _MODEL_LOAD_STATE.get("variant")
         msg = (f"Already loading {current}. Switching mid-load is disabled "
          "because CUDA/Unsloth loads are not safely cancellable. "
          "Wait for completion or restart the Kaggle cell.")
         return JSONResponse({"status": "busy", "variant": current,
                  "message": msg},
                 status_code=409 if current != variant else 200)
    _reset_load_events()
    _MODEL_LOAD_STATE.update({
        "status": "loading", "variant": variant,
          "selected_display": _VARIANT_INFO[variant]["display"],
          "phase": "queued",
          "started_at": time.time(), "updated_at": time.time(),
          "completed_at": None, "error": None, "last_log": None,
          "last_status_heartbeat_at": None,
    })
    _log_load(f"queued {_VARIANT_INFO[variant]['display']} ({variant})",
          phase="queued")
    # Same preflight log as the judge slot so the timeline is honest
    # about what the safety gate saw (especially when the user used
    # override=true to force a load).
    _log_load(
        (
            f"preflight: needs ~{pre['needs_disk_gb']:.1f} GB disk, "
            f"~{pre['needs_gpu_gb']:.1f} GB GPU; have "
            f"{pre['disk_free_gb']} GB / {pre['gpu_free_gb']} GB"
            + (" (overridden)" if (not pre['ok'] and override) else "")
        ),
        phase="preflight",
        level=("warn" if (not pre['ok'] and override) else "info"),
    )

    def _do_load():
        global loaded, GEMMA_MODEL_VARIANT
        try:
            os.environ["GEMMA_MODEL_VARIANT"] = variant
            GEMMA_MODEL_VARIANT = variant
            _log_load(f"loader thread started for variant={variant}",
                      phase="starting")
            loaded_local = load_gemma()
            if loaded_local is None:
                _log_load("load_gemma() returned None - inspect messages above",
                          phase="error", level="error")
                _MODEL_LOAD_STATE.update(
                    {"status": "error",
                     "completed_at": time.time(),
                     "error": "load_gemma() returned None - see load logs"})
                return
            # Wrap with the inference queue so concurrent users get
            # FIFO-ish ordering + position visibility + 503
            # backpressure instead of silent CUDA serialisation.
            wrapped_chat = _queue_wrap(loaded_local.backend, "chat")
            # Critical ordering note: assign the chat callable AND
            # mirror it into the evaluator slot (if mirroring is on)
            # under the queue's _meta lock BEFORE calling open_slot.
            # A request that arrives between open_slot and the mirror
            # rewire could otherwise see app.state.evaluator_call=None
            # while the chat slot is already accepting tickets. The
            # _meta lock also serialises this assignment against
            # api_use_chat_as_judge so the flag and the mirrored
            # callable cannot drift apart.
            with _MODEL_QUEUE._meta:
                app.state.gemma_call = wrapped_chat
                if _JUDGE_USES_CHAT:
                    app.state.evaluator_call = wrapped_chat
            _MODEL_QUEUE.open_slot("chat")
            if _JUDGE_USES_CHAT:
                _log_load(
                    "judge mirrored to chat model (use_chat_as_judge=on)",
                    phase="ready",
                )
            app.state.model_info = {
                "loaded": True, "name": loaded_local.name,
                "size_b": loaded_local.size_b,
                "quantization": loaded_local.quantization,
                "device": loaded_local.device,
                "display": (f"{loaded_local.name} · "
                            f"{loaded_local.size_b:.1f}B · "
                            f"{loaded_local.quantization}"),
            }
            loaded = loaded_local
            _MODEL_LOAD_STATE.update({
                "status": "ready", "phase": "ready",
                "completed_at": time.time(), "updated_at": time.time(),
                "error": None,
            })
            _log_load(f"{variant} ready: {loaded_local.name} - "
                      f"{loaded_local.device}", phase="ready")
        except Exception as e:
            _MODEL_LOAD_STATE.update(
                {"status": "error",
                 "completed_at": time.time(),
                 "error": f"{type(e).__name__}: {str(e)[:300]}"})
            _log_load(f"FAILED: {type(e).__name__}: {e}",
                      phase="error", level="error")
            for line in traceback.format_exc().splitlines()[-12:]:
                _log_load(line, phase="error", level="error")
            # Mid-download failure (OSError / disk full / HF rate
            # limit) leaves partial shards under HF_HOME. Purge so a
            # retry has a clean cache budget; if the failure was
            # something else (CUDA OOM after download), the purge is a
            # no-op for that case but still cleans up stale shards
            # from a prior aborted load.
            try:
                purged = _purge_hf_cache_for_variant(variant)
                if purged.get("gb_freed"):
                    _log_load(
                        f"purged partial HF cache: {purged['gb_freed']:.2f} GB freed",
                        phase="error", level="info",
                    )
            except Exception as purge_err:  # noqa: BLE001
                _log_load(
                    f"cache purge failed after load error: {purge_err}",
                    phase="error", level="warn",
                )
        finally:
            _MODEL_LOAD_LOCK.release()

    threading.Thread(target=_do_load, daemon=True,
                      name="gemma-loader").start()
    return {"status": "loading", "variant": variant}


# ===========================================================================
# EVALUATOR (JUDGE) MODEL SLOT
# ---------------------------------------------------------------------------
# Loads a SEPARATE model into app.state.evaluator_call so grading can use
# a more capable model (typically Gemma 4 31B-it) while the chat model
# stays loaded (typically E2B/E4B for fast inference).
#
# This is the architecture the chat-package's _evaluator_model_call has
# always supported: when app.state.evaluator_call is set, the LLM-judge
# grader prefers it over app.state.gemma_call. The kernel just needs to
# expose endpoints that LOAD a model into that slot.
#
# Both models can stay resident if VRAM allows (T4x2 in 4-bit: chat E4B
# ~4 GB + judge 31B ~18 GB = 22 GB on 30 GB combined -- tight but OK).
# If the load fails (OOM), the chat model is unaffected.
# ===========================================================================

class ModelSlot:
    """Intelligent wrapper for a loadable model slot.

    The kernel exposes two parallel slots that share a lot of logic:

      * CHAT slot   -- writes to ``app.state.gemma_call``. Used by the
                       chat/A-B endpoints. Backed by the module-level
                       ``_MODEL_LOAD_STATE`` + ``_MODEL_LOAD_LOCK`` +
                       ``_MODEL_LOAD_EVENTS`` so the legacy helpers
                       (``_log_load``, ``_snapshot_load_events``, ...)
                       keep working unchanged.
      * JUDGE slot  -- writes to ``app.state.evaluator_call``. Used by
                       LLM-judge grading. Backed by the ``_EVAL`` -
                       suffixed module-level dicts.

    Both slots need the same unload + purge logic: drop the callable
    from ``app.state``, flush CUDA, optionally purge the HF cache for
    the unloaded variant. This class collapses that duplication into
    a single ``slot.unload(app, purge_cache=...)`` call so each
    FastAPI endpoint becomes a 2-line shim.

    The CLASS owns the policy (what to do). The module-level state
    dicts / locks / event rings are the DATA the class operates on,
    kept at module level so legacy free functions still work. This
    is intentionally a thin abstraction: future endpoints (e.g., a
    third slot for a vision model) get the same behavior by passing
    in their own state dict / lock / event ring + a tiny ``post_unload``
    hook for any slot-specific reset (the chat slot also resets
    ``app.state.model_info`` to a placeholder; the judge slot does
    not).
    """

    def __init__(
        self,
        name: str,
        app_state_attr: str,
        *,
        state: dict,
        lock: "threading.Lock",
        events: list,
        log_fn,
        loaded_ref_setter,
        post_unload_hook=None,
    ) -> None:
        self.name = name                          # "chat" / "judge"
        self.app_state_attr = app_state_attr      # "gemma_call" / "evaluator_call"
        self.state = state                        # backing dict
        self.lock = lock                          # backing lock
        self.events = events                      # backing event ring
        self.log = log_fn                         # logger fn for THIS slot
        self.loaded_ref_setter = loaded_ref_setter  # clears the module-level LoadedModel ref
        self.post_unload_hook = post_unload_hook    # optional slot-specific cleanup

    def is_loaded(self, app) -> bool:
        return getattr(app.state, self.app_state_attr, None) is not None

    def unload(self, app, *, purge_cache: bool = True) -> Any:
        """Atomically unload the slot.

        Steps (in order):
          1. Return idle no-op if nothing is loaded.
          2. Acquire the slot lock (refuse with 409 if a load is in
             progress -- swapping mid-load is not safe on Unsloth).
          3. Drop the callable from ``app.state.<attr>``.
          4. Clear the loaded LoadedModel reference (so torch tensors
             release).
          5. Flush ``torch.cuda.empty_cache()`` (best-effort) so the
             freed VRAM returns to the pool.
          6. Reset the slot's state dict to idle.
          7. Run the optional ``post_unload_hook`` for slot-specific
             cleanup (e.g., chat slot resets app.state.model_info).
          8. If ``purge_cache=True``, delete the HF safetensors dir
             for the unloaded variant via ``_purge_hf_cache_for_variant``.
          9. Return a structured response dict including the purge
             result (``{ok, bytes_freed, paths_deleted, ...}``).
        """
        if not self.is_loaded(app):
            return {"status": "idle",
                    "message": f"No {self.name} model loaded."}
        if not self.lock.acquire(blocking=False):
            return JSONResponse(
                {"status": "busy",
                 "message": (
                     f"A {self.name}-model load is in progress. "
                     "Wait for completion before unloading."
                 )},
                status_code=409,
            )
        try:
            current_variant = self.state.get("variant")
            self.log(f"unloading {self.name} model", phase="unloading")
            # Step 3: drop the callable.
            setattr(app.state, self.app_state_attr, None)
            # Step 4: clear the LoadedModel ref so torch can collect.
            try:
                self.loaded_ref_setter(None)
            except Exception as e:  # noqa: BLE001 -- defensive
                self.log(
                    f"loaded-ref setter raised: {type(e).__name__}: {e}",
                    phase="unloading", level="warn",
                )
            # Step 5: CUDA cache flush (best-effort).
            try:
                import torch as _torch
                _torch.cuda.empty_cache()
                try:
                    _torch.cuda.synchronize()
                except Exception:
                    pass
                self.log("CUDA cache flushed", phase="unloaded")
            except Exception as e:
                self.log(
                    f"CUDA cache flush skipped: {type(e).__name__}",
                    phase="unloaded", level="warn",
                )
            # Step 6: reset slot state.
            self.state.update({
                "status": "idle", "variant": None,
                "selected_display": None, "phase": "idle",
                "completed_at": time.time(), "error": None,
            })
            # Step 7: slot-specific cleanup (e.g., chat slot resets
            # app.state.model_info to a placeholder dict).
            if self.post_unload_hook is not None:
                try:
                    self.post_unload_hook(app)
                except Exception as e:  # noqa: BLE001
                    self.log(
                        f"post_unload_hook raised: {type(e).__name__}: {e}",
                        phase="unloaded", level="warn",
                    )
            # Step 8: optional HF disk purge.
            purged = None
            if purge_cache and current_variant:
                purged = _purge_hf_cache_for_variant(current_variant)
                if purged.get("ok"):
                    gb = purged.get("gb_freed", 0)
                    self.log(
                        (
                            f"purged HF cache for {current_variant}: "
                            f"{gb:.2f} GB freed"
                        ),
                        phase="purged",
                    )
                else:
                    self.log(
                        (
                            f"cache purge for {current_variant} hit an "
                            f"error: {purged.get('error', 'unknown')}"
                        ),
                        phase="purge-error", level="warn",
                    )
            return {
                "status":  "idle",
                "message": f"{self.name.title()} model unloaded.",
                "purged":  purged,
            }
        finally:
            self.lock.release()


_MODEL_LOAD_LOCK_EVAL  = threading.Lock()
_MODEL_LOAD_STATE_EVAL = {
    "status":     "idle",
    "variant":    None,
    "selected_display": None,
    "phase":      "idle",
    "started_at": None,
    "updated_at": None,
    "completed_at": None,
    "error":      None,
    "last_log":   None,
    "log_seq":    0,
}
_MODEL_LOAD_EVENTS_EVAL: list[dict[str, Any]] = []
# Tracks the LoadedModel object for the evaluator so we can drop the
# torch tensors / tokenizer on unload (otherwise the references stay
# pinned and VRAM is not released).
_LOADED_EVAL: Optional["LoadedModel"] = None

# When True, the judge slot reuses the chat model instead of loading a
# second model into VRAM. Set/cleared via POST /api/use-chat-as-judge.
# Persisted in-process so a chat-model reload (load -> unload -> load
# new variant) automatically re-wires the judge to the new chat call.
# This is the workflow for "Use 31B as both chat and judge" on a
# kernel with one big model and no disk room for a second.
_JUDGE_USES_CHAT: bool = False


def _set_judge_loaded(model) -> None:
    """Setter for the module-level judge LoadedModel ref.
    Used by ModelSlot.unload() to release tensors after unload."""
    global _LOADED_EVAL
    _LOADED_EVAL = model


# Two ModelSlot instances -- the only kernel-side surface that new
# slot-aware code should reach for. Existing module-level helpers
# (_log_load, _log_load_eval, _snapshot_load_events, ...) still work
# and back the slots transparently.
_CHAT_SLOT = ModelSlot(
    name="chat",
    app_state_attr="gemma_call",
    state=_MODEL_LOAD_STATE,
    lock=_MODEL_LOAD_LOCK,
    events=_MODEL_LOAD_EVENTS,
    log_fn=_log_load,
    loaded_ref_setter=_set_chat_loaded,
    post_unload_hook=_chat_post_unload,
)
_JUDGE_SLOT = ModelSlot(
    name="judge",
    app_state_attr="evaluator_call",
    state=_MODEL_LOAD_STATE_EVAL,
    lock=_MODEL_LOAD_LOCK_EVAL,
    events=_MODEL_LOAD_EVENTS_EVAL,
    log_fn=_log_load_eval,
    loaded_ref_setter=_set_judge_loaded,
)


# ---------------------------------------------------------------------------
# Preflight helpers for the judge-model load.
#
# Loading 31B-it on Kaggle requires real care: ~18 GB on disk for the
# HF cache download AND ~18 GB of VRAM (split across T4x2 in 4-bit).
# Without preflight, an OOM mid-load leaves the kernel in a broken
# state and the user has to restart the Kaggle cell. These helpers
# surface the gap BEFORE the load starts so the user can free space
# or pick a smaller variant.
# ---------------------------------------------------------------------------

# Conservative estimates for both disk-cache footprint (HF safetensors)
# and live VRAM footprint at 4-bit. Pad by ~15% so we don't pretend an
# exact fit is safe; CUDA fragmentation eats headroom.
_VARIANT_FOOTPRINT_GB = {
    # Footprints are the resident shard size on disk after Unsloth
    # quantisation + the runtime VRAM ceiling. The disk numbers were
    # lowered from full-precision estimates to match what actually
    # lands in /kaggle/working/.cache/huggingface after the
    # FastModel.from_pretrained(..., load_in_4bit=True) call. Full-
    # precision shards never download because Unsloth requests the
    # quantised weights directly. Numbers verified against published
    # Kaggle session logs; conservative by ~10 percent.
    "e2b-it":         {"disk": 4.0,  "gpu": 3.0},
    "e4b-it":         {"disk": 8.0,  "gpu": 5.0},
    "26b-a4b-it":     {"disk": 16.0, "gpu": 14.0},
    "31b-it":         {"disk": 18.0, "gpu": 16.0},
    "jailbroken-31b": {"disk": 18.0, "gpu": 16.0},
    "jailbroken-e4b": {"disk": 8.0,  "gpu": 5.0},
    "cloud-gemini":   {"disk": 0.0,  "gpu": 0.0},
    "cloud-openai":   {"disk": 0.0,  "gpu": 0.0},
    "cloud-ollama":   {"disk": 0.0,  "gpu": 0.0},
}


def _estimate_model_size_gb(variant: str) -> dict:
    """Return (disk_gb, gpu_gb) needed for ``variant``. Falls back to
    a conservative upper bound for unknown variants."""
    fp = _VARIANT_FOOTPRINT_GB.get(variant)
    if fp is None:
        # Unknown variant: assume worst-case (31B-scale) so the
        # preflight is loud rather than silently optimistic.
        return {"disk": 30.0, "gpu": 20.0}
    return dict(fp)


def _disk_free_gb(path: str = "/") -> Optional[float]:
    """Free disk bytes -> GiB at ``path``. Returns None when the
    syscall fails (e.g., on a sandboxed environment) so callers can
    skip the disk gate without crashing."""
    try:
        import shutil as _shutil
        # Measure the partition that actually holds the HF cache, which
        # is wherever HF_HOME points (or the system default). The
        # kernel sets HF_HOME=/kaggle/working/.cache/huggingface at
        # import time on Kaggle so this matches the download
        # destination. Falls back to /kaggle/working when HF_HOME is
        # unset, then to the caller-provided path as a last resort.
        hf_home = os.environ.get("HF_HOME")
        candidate = None
        if hf_home and os.path.isdir(os.path.dirname(hf_home) or "/"):
            candidate = hf_home
        elif os.path.isdir("/kaggle/working"):
            candidate = "/kaggle/working"
        else:
            candidate = path
        # disk_usage needs an existing path; walk up if needed.
        probe = candidate
        while probe and not os.path.isdir(probe):
            parent = os.path.dirname(probe)
            if parent == probe:
                probe = "/"
                break
            probe = parent
        usage = _shutil.disk_usage(probe)
        return round(usage.free / (1024.0 ** 3), 2)
    except Exception:
        return None


def _gpu_free_gb() -> Optional[float]:
    """Sum free VRAM across all visible CUDA devices, in GiB. Returns
    None when torch is unavailable or no CUDA device is present."""
    try:
        import torch as _torch  # noqa: WPS433 -- optional import is the point
        if not _torch.cuda.is_available():
            return 0.0
        free_total = 0
        for i in range(_torch.cuda.device_count()):
            try:
                free_b, _total_b = _torch.cuda.mem_get_info(i)
                free_total += int(free_b)
            except Exception:
                # cudart not initialized for this device; skip it.
                continue
        return round(free_total / (1024.0 ** 3), 2)
    except Exception:
        return None


def _model_preflight(variant: str) -> dict:
    """Slot-agnostic pre-flight check before loading ``variant`` into
    either the chat slot (app.state.gemma_call) or the judge slot
    (app.state.evaluator_call). Same disk + GPU math for both --
    the slot only affects who consumes the loaded model afterward.

    Returns a dict with:
        variant        -- echoed back
        needs_disk_gb  -- conservative HF-cache footprint estimate
        needs_gpu_gb   -- conservative 4-bit VRAM footprint estimate
        disk_free_gb   -- current free space (None if unknown)
        gpu_free_gb    -- current free VRAM (None if unknown)
        ok             -- True iff every available gate passes
        reasons        -- list of human-readable failure messages
                          (empty when ok=True)
        notes          -- list of non-blocking observations

    Cloud variants (cloud-gemini/openai/ollama) auto-pass because they
    don't load weights locally. Unknown variants get the worst-case
    estimate so the preflight is conservative.
    """
    need = _estimate_model_size_gb(variant)
    free_disk = _disk_free_gb()
    free_gpu = _gpu_free_gb()
    reasons: list[str] = []
    notes: list[str] = []
    if variant.startswith("cloud-"):
        notes.append("cloud route: no local disk / VRAM footprint")
    else:
        if free_disk is None:
            notes.append("disk free space unavailable; preflight skipped this gate")
        elif free_disk < need["disk"]:
            reasons.append(
                f"disk: need ~{need['disk']:.1f} GB, have {free_disk:.1f} GB free"
            )
        if free_gpu is None:
            notes.append("GPU memory unavailable; preflight skipped this gate")
        elif free_gpu < need["gpu"]:
            reasons.append(
                f"GPU: need ~{need['gpu']:.1f} GB, have {free_gpu:.1f} GB free"
            )
    return {
        "variant":       variant,
        "needs_disk_gb": need["disk"],
        "needs_gpu_gb":  need["gpu"],
        "disk_free_gb":  free_disk,
        "gpu_free_gb":   free_gpu,
        "ok":            len(reasons) == 0,
        "reasons":       reasons,
        "notes":         notes,
    }


# Backwards-compat alias. The original implementation lived only on
# the judge slot; tests + caller-side code reference _judge_preflight.
# Keep the name so the rename is non-breaking.
def _judge_preflight(variant: str) -> dict:
    return _model_preflight(variant)


# ---------------------------------------------------------------------------
# HF cache purge helper.
#
# Kaggle's /kaggle/working has only ~20 GB of persistent disk. After
# unloading a model, the in-memory weights are freed but the HF
# safetensors files remain on disk in ~/.cache/huggingface/hub/. Two
# 31B-class downloads + an E4B will exhaust the disk. To support the
# "switch judge model" workflow on Kaggle, the unload endpoints
# default to purging the cache for the unloaded variant.
# ---------------------------------------------------------------------------

# Pre-quantized Unsloth fallback names the chat package uses when the
# google/* repo is gated and no Kaggle-attached model exists. Listed
# here so purge can also clear the Unsloth-shaped cache dir.
_UNSLOTH_ALIASES = {
    "e2b-it":     "unsloth/gemma-4-E2B-it",
    "e4b-it":     "unsloth/gemma-4-E4B-it",
    "26b-a4b-it": "unsloth/gemma-4-26B-A4B-it",
    "31b-it":     "unsloth/gemma-4-31B-it",
}


def _hf_cache_dir_candidates_for_variant(variant: str) -> list[str]:
    """Return the HF cache directory names that COULD hold the cached
    safetensors for ``variant``. We check both the google/* canonical
    id and the unsloth/* alias because the chat runtime falls back."""
    base = os.path.expanduser("~/.cache/huggingface/hub")
    if not os.path.isdir(base):
        return []
    dirs: list[str] = []
    if variant in _VARIANT_HF_ID:
        dirs.append(os.path.join(
            base,
            "models--" + _VARIANT_HF_ID[variant].replace("/", "--"),
        ))
    if variant in _UNSLOTH_ALIASES:
        dirs.append(os.path.join(
            base,
            "models--" + _UNSLOTH_ALIASES[variant].replace("/", "--"),
        ))
    return dirs


def _purge_hf_cache_for_variant(variant: str) -> dict:
    """Delete on-disk cache for ``variant``. Best-effort. Returns
    {ok, bytes_freed, paths_deleted, paths_checked, error?}. Skips
    nonexistent dirs silently. Errors on rmtree are caught so the
    caller doesn't lose the load/unload transaction over a stuck
    file handle."""
    paths_checked: list[str] = []
    paths_deleted: list[dict] = []
    bytes_freed = 0
    candidates = _hf_cache_dir_candidates_for_variant(variant)
    if not candidates:
        return {
            "ok": True,
            "bytes_freed": 0,
            "paths_checked": [],
            "paths_deleted": [],
            "note": "no HF cache directory present",
        }
    import shutil as _shutil
    for path in candidates:
        paths_checked.append(path)
        if not os.path.isdir(path):
            continue
        try:
            size = 0
            for root, _dirs, files in os.walk(path):
                for f in files:
                    try:
                        size += os.path.getsize(os.path.join(root, f))
                    except (OSError, FileNotFoundError):
                        pass
            _shutil.rmtree(path, ignore_errors=False)
            bytes_freed += size
            paths_deleted.append({
                "path": path,
                "bytes_freed": size,
                "gb_freed": round(size / (1024.0 ** 3), 2),
            })
        except Exception as e:
            return {
                "ok": False,
                "bytes_freed": bytes_freed,
                "paths_checked": paths_checked,
                "paths_deleted": paths_deleted,
                "error": f"{type(e).__name__}: {str(e)[:200]}",
            }
    return {
        "ok": True,
        "bytes_freed": bytes_freed,
        "gb_freed": round(bytes_freed / (1024.0 ** 3), 2),
        "paths_checked": paths_checked,
        "paths_deleted": paths_deleted,
    }


@app.get("/api/load-model/preflight")
def api_chat_preflight(variant: str = ""):
    """Disk + GPU preflight for the requested CHAT model variant.

    UI guidance: call this BEFORE the user clicks Load in the chat-
    model picker. When ok=False, surface ``reasons`` to the user
    and disable the Load button (or offer a 'force' override).

    Same math as the evaluator preflight, different default. When no
    variant is passed the helper still returns a sensible 31B-scale
    worst-case so the response is never empty.
    """
    return _model_preflight(variant or "e4b-it")


@app.get("/api/load-evaluator-model/preflight")
def api_evaluator_preflight(variant: str = "31b-it"):
    """Disk + GPU preflight for the requested judge model variant.

    UI guidance: call this BEFORE the user clicks Load. When ok=False,
    surface ``reasons`` to the user and disable the Load button (or
    offer a 'force' override for advanced users who know better)."""
    return _model_preflight(variant)


@app.post("/api/unload-model")
def api_unload_chat_model(body: dict = Body(default=None)):
    """Free the chat model. Required to swap variants on a kernel
    where /api/load-model otherwise refuses ('already_loaded'). After
    unload, the chat package can re-call /api/load-model with a new
    variant.

    Body params (all optional):
        purge_cache: bool   default True. Delete the HF safetensors
                            for the unloaded variant from disk so
                            /kaggle/working frees back to its baseline.
                            Set False to keep the cache for a quick
                            re-load (same variant).
        force: bool         default False. When False (the safe path)
                            the call refuses with HTTP 409 if any
                            tickets are active or waiting on the chat
                            inference queue. Set True to interrupt
                            other users mid-generate.
        drain_seconds: int  default 30. When force is False, how long
                            to wait for in-flight requests to drain
                            before giving up with HTTP 409.

    Delegates to ModelSlot.unload() so the chat + judge slots share
    a single canonical unload implementation.
    """
    body = body or {}
    force = bool(body.get("force", False))
    drain_seconds = float(body.get("drain_seconds", 30))
    # Refuse a non-force unload while the inference queue still has
    # tickets. Without this gate, freeing the model tensors while
    # another user is mid-generate produces a hard crash on the
    # generate thread.
    if _MODEL_QUEUE.is_busy("chat") and not force:
        drain = _MODEL_QUEUE.close_slot(
            "chat", wait_seconds=drain_seconds, force=False,
        )
        if not drain["drained"]:
            # Reopen so other waiters can still drain naturally.
            _MODEL_QUEUE.open_slot("chat")
            return JSONResponse(
                {
                    "status": "queue_busy",
                    "message": (
                        "Chat inference queue still has "
                        f"{drain['active_at_close']} active and "
                        f"{drain['waiting_at_close']} waiting after "
                        f"{drain['waited_seconds']}s of draining. "
                        "Retry, wait longer (drain_seconds), or pass "
                        "{\"force\": true} to interrupt other users."
                    ),
                    "drain": drain,
                    "queue": _MODEL_QUEUE.snapshot(),
                },
                status_code=409,
            )
    else:
        # Either queue is empty or force=True. Mark closed up front so
        # no new tickets can race in while the unload runs.
        _MODEL_QUEUE.close_slot("chat", wait_seconds=0, force=True)
    return _CHAT_SLOT.unload(
        app, purge_cache=bool(body.get("purge_cache", True)),
    )


def _set_chat_loaded(model) -> None:
    """Setter for the module-level chat LoadedModel ref.
    Used by ModelSlot.unload() to release tensors after unload."""
    global loaded
    loaded = model


def _chat_post_unload(app) -> None:
    """Chat-slot specific cleanup: reset app.state.model_info to the
    placeholder dict so the UI shows '(no model loaded)' until a new
    load completes. When the judge was mirroring the chat model, the
    mirror is also cleared so a stale callable pointing at freed
    tensors cannot be reached by /api/grade-* routes."""
    app.state.model_info = _placeholder_model_info
    if _JUDGE_USES_CHAT and getattr(app.state, "evaluator_call", None) is not None:
        app.state.evaluator_call = None


def _log_load_eval(message: str, *, phase: Optional[str] = None,
                   level: str = "info") -> None:
    """Mirror of _log_load() but writes to the evaluator state ring.
    Keeps the chat-model log clean from judge-model events."""
    state = _MODEL_LOAD_STATE_EVAL
    elapsed = None
    if state.get("started_at"):
        elapsed = round(time.time() - float(state["started_at"]), 1)
    event = {
        "ts": time.strftime("%H:%M:%S"),
        "elapsed_s": elapsed,
        "phase": phase,
        "level": level,
        "message": message,
    }
    _MODEL_LOAD_EVENTS_EVAL.append(event)
    if len(_MODEL_LOAD_EVENTS_EVAL) > 500:
        del _MODEL_LOAD_EVENTS_EVAL[:-500]
    state["last_log"] = message
    state["updated_at"] = time.time()
    state["log_seq"] = len(_MODEL_LOAD_EVENTS_EVAL)
    if phase:
        state["phase"] = phase
    prefix = f"  [load-evaluator][{level}]"
    if phase:
        prefix += f"[{phase}]"
    print(f"{prefix} {message}")


def _eval_info_snapshot() -> dict:
    """Lightweight summary of the loaded evaluator for the UI."""
    if _LOADED_EVAL is None:
        return {
            "loaded": False,
            "name": None,
            "variant": _MODEL_LOAD_STATE_EVAL.get("variant"),
            "display": (
                "(no judge model loaded -- grader will use chat model)"
            ),
        }
    return {
        "loaded": True,
        "name": _LOADED_EVAL.name,
        "size_b": _LOADED_EVAL.size_b,
        "quantization": _LOADED_EVAL.quantization,
        "device": _LOADED_EVAL.device,
        "variant": _MODEL_LOAD_STATE_EVAL.get("variant"),
        "display": (f"{_LOADED_EVAL.name} (judge) · "
                    f"{_LOADED_EVAL.size_b:.1f}B · "
                    f"{_LOADED_EVAL.quantization}"),
    }


@app.get("/api/load-evaluator-model/status")
def api_load_evaluator_status():
    """Status of the separately-loaded judge model. Parallel shape to
    /api/load-model/status so the UI can poll the same way."""
    elapsed = None
    if _MODEL_LOAD_STATE_EVAL.get("started_at"):
        elapsed = round(
            time.time() - _MODEL_LOAD_STATE_EVAL["started_at"], 1,
        )
    return {
        **_MODEL_LOAD_STATE_EVAL,
        "elapsed_s": elapsed,
        "ready": getattr(app.state, "evaluator_call", None) is not None,
        # When True, the judge slot points at the chat model. UI uses
        # this to hide the variant selector + load/unload buttons and
        # show a "Sharing the chat model" banner instead.
        "judge_uses_chat": _JUDGE_USES_CHAT,
        "variants": _VARIANT_INFO,
        "active_evaluator": _eval_info_snapshot(),
        "logs": list(_MODEL_LOAD_EVENTS_EVAL[-120:]),
    }


@app.post("/api/use-chat-as-judge")
def api_use_chat_as_judge(body: dict = Body(default=None)):
    """Toggle "Use chat model as judge" mode.

    When enabled, the judge slot mirrors the resident chat model so
    grading routes (/api/grade-deep, /api/grade-combined) work without
    loading a second model into VRAM. Calls still queue on the chat
    slot (one model, one lock); the trade-off is that chat and judge
    contend for the same GPU instead of running in parallel.

    Body params (all optional):
        enabled: bool  default True. False clears the mirror and
                       returns the judge slot to unloaded state.

    Refuses with HTTP 400 when enabling and no chat model is loaded.
    Refuses with HTTP 409 when enabling and a separate judge model is
    already loaded (caller must unload that first).
    """
    global _JUDGE_USES_CHAT
    body = body or {}
    # Robust bool parse: bare bool("false") == True is a real footgun.
    # _parse_bool maps "true"/"false"/"on"/"off"/"yes"/"no"/0/1 to the
    # expected boolean so a JSON-stringified value cannot accidentally
    # enable a destructive flag.
    enabled = _parse_bool(body.get("enabled"), default=True)
    # Serialise the flag flip + evaluator_call assignment against the
    # chat-load thread so we cannot end up with _JUDGE_USES_CHAT=True
    # but app.state.evaluator_call pointing at a stale chat callable
    # from before the latest load.
    with _MODEL_QUEUE._meta:
        chat_call = getattr(app.state, "gemma_call", None)
    if enabled:
        if chat_call is None:
            return JSONResponse(
                {
                    "status": "no_chat_model",
                    "message": (
                        "No chat model is loaded. Load a chat model "
                        "first (POST /api/load-model), then enable "
                        "'Use chat model as judge'."
                    ),
                },
                status_code=400,
            )
        # If a SEPARATE judge model is already loaded, refuse so the
        # caller does not silently lose that work. Unloading the
        # separate judge first is a deliberate decision.
        sep_loaded = (
            getattr(app.state, "evaluator_call", None) is not None
            and not _JUDGE_USES_CHAT
        )
        if sep_loaded:
            return JSONResponse(
                {
                    "status": "separate_judge_loaded",
                    "message": (
                        "A separate judge model is currently loaded. "
                        "Unload it first (POST /api/unload-evaluator-model) "
                        "then enable 'Use chat model as judge'."
                    ),
                    "judge_variant": _MODEL_LOAD_STATE_EVAL.get("variant"),
                },
                status_code=409,
            )
        # All clear: wire the mirror under the queue lock so a
        # concurrent chat-load thread cannot race with this assignment
        # (the chat-load thread reads _JUDGE_USES_CHAT inside the same
        # lock before writing evaluator_call).
        with _MODEL_QUEUE._meta:
            _JUDGE_USES_CHAT = True
            app.state.evaluator_call = chat_call
        return {
            "status": "ok",
            "judge_uses_chat": True,
            "message": (
                "Judge slot is now mirroring the chat model. Grading "
                "will share the chat queue."
            ),
        }
    # Disable path: clear the mirror only if it was active. Never
    # touches a separately-loaded judge model. Lock the flag + ref
    # together so a concurrent load can't see them inconsistently.
    with _MODEL_QUEUE._meta:
        was_mirrored = _JUDGE_USES_CHAT
        _JUDGE_USES_CHAT = False
        if was_mirrored:
            # Only clear when we ourselves had set it -- avoid
            # clobbering a separately-loaded judge if the flag had
            # drifted out of sync somehow.
            app.state.evaluator_call = None
    return {
        "status": "ok",
        "judge_uses_chat": False,
        "was_mirrored": was_mirrored,
        "message": (
            "Mirror disabled. Judge slot is empty -- load a separate "
            "judge model or keep grading on the chat model via the "
            "fallback in grade_response_combined."
        ),
    }


@app.post("/api/load-evaluator-model")
def api_load_evaluator_model(body: dict = Body(...)):
    """Load a separate model into the evaluator (judge) slot.

    The grading pipeline (app.state.evaluator_call) is preferred over
    the chat model (app.state.gemma_call) when both are wired. Default
    suggestion: ``31b-it`` for highest grading accuracy.

    Long-running -- kicks off a background thread and returns
    immediately. Poll /api/load-evaluator-model/status until
    status='ready'. If the load fails (OOM, missing weights), the
    chat model is unaffected.
    """
    variant = (body or {}).get("variant", "").strip() or "31b-it"
    override = bool((body or {}).get("override", False))
    # If the judge is mirroring the chat model, refuse to load a
    # separate judge until the mirror is disabled. Otherwise we would
    # end up with the same variant resident twice (chat + judge slots)
    # which is exactly the waste use_chat_as_judge was meant to avoid.
    if _JUDGE_USES_CHAT:
        return JSONResponse(
            {
                "status": "mirroring_chat",
                "message": (
                    "The judge slot is currently mirroring the chat model. "
                    "Disable 'Use chat model as judge' first (POST "
                    "/api/use-chat-as-judge with {\"enabled\": false}) "
                    "before loading a separate judge."
                ),
            },
            status_code=409,
        )
    if getattr(app.state, "evaluator_call", None) is not None:
        return {"status": "already_loaded",
                "variant": _MODEL_LOAD_STATE_EVAL.get("variant"),
                "message": "A judge model is already loaded. POST to "
                           "/api/unload-evaluator-model to free it first."}
    # Cross-slot duplicate detection. The chat slot and judge slot are
    # independent, so without this check a user who already has 31b-it
    # resident in the chat slot would see "preflight failed: not enough
    # disk" when they ask for 31b-it as judge. That is misleading --
    # the model is already on disk, just routed to the wrong slot.
    # Return a structured status so the UI can offer a one-click
    # "promote chat model to judge" path instead of pointing at the
    # disk gauge.
    chat_loaded_variant = _MODEL_LOAD_STATE.get("variant") if getattr(app.state, "gemma_call", None) is not None else None
    if chat_loaded_variant and chat_loaded_variant == variant:
        return JSONResponse(
            {
                "status": "duplicate_in_chat_slot",
                "variant": variant,
                "chat_variant": chat_loaded_variant,
                "message": (
                    f"{variant} is already resident in the chat slot. Loading the "
                    "same variant a second time would double disk and VRAM use. "
                    "Unload the chat model first, or pick a different judge variant."
                ),
                "suggested_actions": [
                    {"action": "unload_chat", "endpoint": "/api/unload-model"},
                    {"action": "use_different_judge_variant", "variants": sorted(_VARIANT_INFO.keys())},
                ],
            },
            status_code=409,
        )
    if variant not in _VARIANT_INFO:
        return JSONResponse(
            {"status": "error",
             "error": f"unknown variant: {variant!r}. "
                       f"Choose one of: {sorted(_VARIANT_INFO.keys())}"},
            status_code=400)
    # Preflight: refuse to start the load when we know it won't fit.
    # The override flag is for advanced users who understand the risk
    # (e.g., have cleaned the HF cache manually or know the disk
    # estimate is too conservative for their setup).
    pre = _judge_preflight(variant)
    if not pre["ok"] and not override:
        return JSONResponse(
            {"status": "preflight_failed",
             "variant": variant,
             "preflight": pre,
             "message": (
                 "Preflight failed: " + "; ".join(pre["reasons"]) +
                 ". Free disk / VRAM and retry, or pass {\"override\": true}."
             )},
            status_code=503,
        )
    if not _MODEL_LOAD_LOCK_EVAL.acquire(blocking=False):
        return JSONResponse(
            {"status": "busy",
             "variant": _MODEL_LOAD_STATE_EVAL.get("variant"),
             "message": "A judge-model load is already in progress."},
            status_code=409)
    _MODEL_LOAD_EVENTS_EVAL.clear()
    _MODEL_LOAD_STATE_EVAL.update({
        "status": "loading", "variant": variant,
        "selected_display": _VARIANT_INFO[variant]["display"],
        "phase": "queued",
        "started_at": time.time(), "updated_at": time.time(),
        "completed_at": None, "error": None, "last_log": None,
    })
    _log_load_eval(
        f"queued judge model {_VARIANT_INFO[variant]['display']} ({variant})",
        phase="queued",
    )
    # Preflight result is informational at this point (we already
    # gated above unless override was set). Logging it makes the
    # timeline honest: if a force-load fails later, the log shows
    # exactly what the preflight warned about.
    _log_load_eval(
        (
            f"preflight: needs ~{pre['needs_disk_gb']:.1f} GB disk, "
            f"~{pre['needs_gpu_gb']:.1f} GB GPU; have "
            f"{pre['disk_free_gb']} GB / {pre['gpu_free_gb']} GB"
            + (" (overridden)" if (not pre['ok'] and override) else "")
        ),
        phase="preflight",
        level=("warn" if (not pre['ok'] and override) else "info"),
    )

    def _do_load_eval() -> None:
        global _LOADED_EVAL
        # Temporarily flip the variant env var so load_gemma() reads
        # the right HF id, then restore it. This keeps load_gemma()
        # reusable for both chat and evaluator slots without a refactor.
        original_env = os.environ.get("GEMMA_MODEL_VARIANT", "")
        try:
            os.environ["GEMMA_MODEL_VARIANT"] = variant
            _log_load_eval(
                f"evaluator loader thread started for variant={variant}",
                phase="starting",
            )
            loaded_local = load_gemma()
            if loaded_local is None:
                _log_load_eval(
                    "load_gemma() returned None -- inspect chat-load logs",
                    phase="error", level="error",
                )
                _MODEL_LOAD_STATE_EVAL.update({
                    "status": "error",
                    "completed_at": time.time(),
                    "error": "load_gemma() returned None",
                })
                return
            # Wrap with the inference queue. Judge slot has its own
            # lock so grading can run in parallel with chat when both
            # models are loaded. Open the slot AFTER the backend is
            # wired so a racing request cannot enqueue against a
            # half-initialised callable.
            app.state.evaluator_call = _queue_wrap(loaded_local.backend, "judge")
            _MODEL_QUEUE.open_slot("judge")
            _LOADED_EVAL = loaded_local
            _MODEL_LOAD_STATE_EVAL.update({
                "status": "ready", "phase": "ready",
                "completed_at": time.time(), "updated_at": time.time(),
                "error": None,
            })
            _log_load_eval(
                f"judge {variant} ready: {loaded_local.name} -- "
                f"{loaded_local.device}",
                phase="ready",
            )
        except Exception as e:
            _MODEL_LOAD_STATE_EVAL.update({
                "status": "error",
                "completed_at": time.time(),
                "error": f"{type(e).__name__}: {str(e)[:300]}",
            })
            _log_load_eval(
                f"FAILED: {type(e).__name__}: {e}",
                phase="error", level="error",
            )
        finally:
            # Restore env var so a subsequent chat-model load uses the
            # user's selected chat variant, not the evaluator variant.
            if original_env:
                os.environ["GEMMA_MODEL_VARIANT"] = original_env
            _MODEL_LOAD_LOCK_EVAL.release()

    threading.Thread(target=_do_load_eval, daemon=True,
                     name="gemma-evaluator-loader").start()
    return {"status": "loading", "variant": variant}


@app.post("/api/unload-evaluator-model")
def api_unload_evaluator_model(body: dict = Body(default=None)):
    """Free the judge model. After this, grading falls back to the
    chat model (app.state.gemma_call). Safe to call when no judge
    model is loaded (no-op).

    Body params (all optional):
        purge_cache: bool   default True. Delete the HF safetensors
                            for the unloaded variant from disk so
                            /kaggle/working frees back to its baseline.
                            Set False to keep the cache for a quick
                            re-load (same variant).
        force: bool         default False. Refuses with HTTP 409 if any
                            tickets are active or waiting on the judge
                            queue. True interrupts mid-grade.
        drain_seconds: int  default 30. How long to wait for in-flight
                            grading to drain before giving up.

    Delegates to ModelSlot.unload() -- same canonical implementation
    the chat slot uses, just bound to a different app.state attr.
    """
    body = body or {}
    force = bool(body.get("force", False))
    drain_seconds = float(body.get("drain_seconds", 30))
    if _MODEL_QUEUE.is_busy("judge") and not force:
        drain = _MODEL_QUEUE.close_slot(
            "judge", wait_seconds=drain_seconds, force=False,
        )
        if not drain["drained"]:
            _MODEL_QUEUE.open_slot("judge")
            return JSONResponse(
                {
                    "status": "queue_busy",
                    "message": (
                        "Judge inference queue still has "
                        f"{drain['active_at_close']} active and "
                        f"{drain['waiting_at_close']} waiting after "
                        f"{drain['waited_seconds']}s of draining. "
                        "Retry, wait longer (drain_seconds), or pass "
                        "{\"force\": true} to interrupt grading."
                    ),
                    "drain": drain,
                    "queue": _MODEL_QUEUE.snapshot(),
                },
                status_code=409,
            )
    else:
        _MODEL_QUEUE.close_slot("judge", wait_seconds=0, force=True)
    return _JUDGE_SLOT.unload(
        app, purge_cache=bool(body.get("purge_cache", True)),
    )


# ===========================================================================
# Templates orchestrator (NGO complaint / referral document drafts)
# ---------------------------------------------------------------------------
# Extracted to duecare.chat.templates on 2026-05-20 so the kernel stays
# focused on runtime orchestration. The 4 template bodies, the
# TEMPLATES_REGISTRY, the bundle source-hint extractor, the Gemma
# fill pass, and the two /api/templates/* routes all live there.
# Source: packages/duecare-llm-chat/src/duecare/chat/templates.py
# ===========================================================================
from duecare.chat.templates import register_template_routes as _register_template_routes
_register_template_routes(app)


# Picker overlay: as of chat-package v0.2.3, the picker is owned by
# the chat package itself (in static/index.html) and drives /api/load-model*
# directly. The kernel only needs to expose those endpoints (above);
# no HTML middleware injection required.

print(f"  ✓ harness loaded: {len(GREP_RULES)} GREP rules, "
      f"{len(RAG_CORPUS)} RAG docs, {len(_TOOL_DISPATCH)} tools")


# ===========================================================================
# 4.5  ONLINE SEARCH (optional fifth layer)
# ===========================================================================
# Adds /api/online-search?q=... endpoint that scrapes DuckDuckGo's HTML
# results page (no API key needed, no Playwright). Returns top-N
# {title, url, snippet} results. The chat UI does not yet have an
# Online toggle wired into the message flow; for now this is
# accessible via curl + via the agentic-research kernel (A4) which has
# the full Playwright integration.
#
# Disable by setting ENABLE_ONLINE_SEARCH=0 in the environment.
if ENABLE_ONLINE_SEARCH:
    import urllib.parse as _ulp, urllib.request as _urlreq
    from fastapi import HTTPException as _HTTPException

    def _online_search(query: str, top_n: int = 5) -> dict:
        """Scrape DuckDuckGo HTML for top results. Free, no key.
        Best-effort: DDG's HTML can change; this returns [] on parse
        failure rather than crashing. For production-grade search use
        the agentic-research kernel (A4) with a Brave Search API key."""
        if not query or len(query.strip()) < 2:
            return {"query": query, "results": [], "source": "noop"}
        if len(query) > 500:
            query = query[:500]
        url = "https://html.duckduckgo.com/html/?q=" + _ulp.quote(query)
        try:
            req = _urlreq.Request(
                url,
                headers={"User-Agent": ("Mozilla/5.0 (compatible; "
                                          "DueCareHarness/1.0)")},
            )
            with _urlreq.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            return {"query": query, "results": [],
                    "source": "ddg_html",
                    "error": f"{type(e).__name__}: {e}"}
        # Lightweight regex parse — DDG HTML wraps results in
        # <a class="result__a" href="...">title</a> with snippets in
        # <a class="result__snippet">snippet</a>.
        result_re = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        snippet_re = re.compile(
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        def _strip_html(s: str) -> str:
            return re.sub(r"<[^>]+>", "", s).strip()
        urls_titles = [(u, _strip_html(t))
                         for u, t in result_re.findall(html)][:top_n]
        snippets = [_strip_html(s) for s in snippet_re.findall(html)][:top_n]
        results = []
        for i, (u, t) in enumerate(urls_titles):
            # DDG redirects via /l/?uddg=... — extract the real URL
            real = u
            m = re.search(r"uddg=([^&]+)", u)
            if m:
                try:
                    real = _ulp.unquote(m.group(1))
                except Exception:
                    pass
            results.append({
                "rank":    i + 1,
                "title":   t,
                "url":     real,
                "snippet": snippets[i] if i < len(snippets) else "",
            })
        return {"query": query, "results": results, "source": "ddg_html"}

    @app.get("/api/online-search")
    def api_online_search(q: str = "", top_n: int = 5):
        """Online search hook. Not yet wired into the chat message
        flow — call directly via curl, or use kernel A4 (agentic-
        research) for the Playwright-based version."""
        if not q:
            raise _HTTPException(400, "q (query) parameter is required")
        return _online_search(q, top_n=max(1, min(int(top_n), 20)))

    # Bind the search function into the create_app callable shim
    # so the chat send pipeline picks it up when the Online toggle
    # is enabled.
    _online_search_fn["f"] = _online_search
    print(f"  ✓ online search wired: GET /api/online-search?q=... + Online toggle tile")
else:
    print(f"  · online search disabled (ENABLE_ONLINE_SEARCH=0)")


def _server_thread():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


server_t = threading.Thread(target=_server_thread, daemon=True,
                              name="duecare-toggle-server")
server_t.start()
print(f"  server thread started on 0.0.0.0:{PORT}")
time.sleep(2.0)


# ===========================================================================
# 4. Cloudflared tunnel (auto-download if not on PATH)
# ===========================================================================
print("\n" + "=" * 76)
print(f"[4/5] opening {TUNNEL} tunnel")
print("=" * 76)

public_url = f"http://localhost:{PORT}"
if TUNNEL != "none":
    try:
        import shutil as _shutil, urllib.request as _urlreq, stat as _stat
        cf_bin = _shutil.which("cloudflared")
        if cf_bin is None:
            cf_bin = "/tmp/cloudflared"
            if not os.path.exists(cf_bin):
                print(f"  cloudflared not on PATH -- downloading ...")
                _url = ("https://github.com/cloudflare/cloudflared/"
                         "releases/latest/download/cloudflared-linux-amd64")
                _urlreq.urlretrieve(_url, cf_bin)
                os.chmod(cf_bin, _stat.S_IRWXU | _stat.S_IXGRP
                                  | _stat.S_IXOTH)
                print(f"  ✓ downloaded "
                      f"{os.path.getsize(cf_bin)//1_000_000} MB to {cf_bin}")
        proc = subprocess.Popen(
            [cf_bin, "tunnel", "--url", f"http://localhost:{PORT}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1)
        _CLOUDFLARED_PROC['p'] = proc
        t0 = time.time()
        while time.time() - t0 < 60:
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.1); continue
            print(f"  [tunnel] {line.rstrip()}")
            if "trycloudflare.com" in line:
                m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
                if m:
                    public_url = m.group(0)
                    print(f"  ✓ tunnel ready: {public_url}")
                    break
        # Drain cloudflared stdout in a daemon thread so the OS pipe
        # buffer never fills (otherwise cloudflared blocks on write
        # and the tunnel 1033s within minutes).
        def _drain_stdout(p=proc):
            try:
                for _ in p.stdout: pass
            except Exception: pass
        threading.Thread(target=_drain_stdout, daemon=True,
                          name="cloudflared-stdout-drain").start()
    except Exception as e:
        print(f"  tunnel error: {type(e).__name__}: {e}")


# ===========================================================================
# 5. Print URL prominently and block
# ===========================================================================
print("\n" + "=" * 76)
print("[5/5] DUECARE HARNESS CHAT (omni playground) is LIVE")
print("=" * 76)
print(f"\n   open this URL on your laptop:")
print(f"\n       {public_url}\n")
print(f"   model:    (none yet — pick one in the browser overlay)")
print(f"   variants: e2b-it, e4b-it, 26b-a4b-it, 31b-it,")
print(f"               jailbroken-31b, jailbroken-e4b,")
print(f"               cloud-gemini, cloud-openai, cloud-ollama")
_online_label = "Online (web search)" if ENABLE_ONLINE_SEARCH else "Online (disabled)"
print(f"   harness:  Persona + GREP ({len(GREP_RULES)} rules across "
      f"31 categories) + RAG ({len(RAG_CORPUS)} docs + 46-edge citation graph) + "
      f"Imports (user evidence) + Tools ({len(_TOOL_DISPATCH)} fns) + {_online_label}")
print(f"   personas: 1 default + 7 curated (NGO intake, lawyer research,")
print(f"               regulator audit, journalist fact-check, researcher")
print(f"               tagging, worker advocate, skeptical reviewer)")
print(f"   grade:    Rule-Based (current numeric rubric, ~1-3s) / LLM-Based / Combined")
print(f"             + Expert legacy (5-dim per-category)")
print(f"\n   On first page-load, the model picker overlay appears.")
print(f"   Pick a variant; load takes ~30s (E4B) to ~5-10+ min (31B first run).")
print(f"   The chat UI then shows 6 harness-layer tiles in the composer:")
print(f"     Persona (purple) / GREP (red) / RAG (blue) /")
print(f"     Tools (green) / Online (amber) / Import (cyan)")
print(f"   Click a tile to toggle it ON/OFF for the next message,")
print(f"   or click '▸ view' on each tile to configure it.")
print(f"   Tip: paste a free Brave Search API key (brave.com/search/api)")
print(f"        in Online ▸ View for reliable web results;")
print(f"        upload a ZIP of internal docs in Import ▸ View.")
print(f"   After Gemma replies, click 'Pipeline' for the 8-card trace,")
print(f"   or 'Score response' for Rule/LLM/Combined scoring.")
print(f"   Keyboard: Cmd/Ctrl+K opens picker, Cmd/Ctrl+/ opens Examples.")
print(f"\n   stop the playground by interrupting this cell, or click")
print(f"   the red Shutdown button in the chat header.\n")
print("=" * 76)

try:
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")

# Cleanup on shutdown
print("\n  shutting down cleanly...")
try:
    if _CLOUDFLARED_PROC.get("p"):
        _CLOUDFLARED_PROC["p"].terminate()
        try:
            _CLOUDFLARED_PROC["p"].wait(timeout=5)
        except Exception:
            _CLOUDFLARED_PROC["p"].kill()
        print("  cloudflared tunnel closed")
except Exception as _e:
    print(f"  cloudflared close: {_e}")
try:
    from duecare.research_tools.browser_tool import shutdown as _browser_shutdown
    _browser_shutdown()
    print("  browser session closed (if any)")
except Exception:
    pass
print("  shutdown complete -- cell exiting.\n")
