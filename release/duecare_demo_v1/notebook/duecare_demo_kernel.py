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
USE_GEMMA = "auto"            # "auto" | True | False
GEMMA_MODEL = "google/gemma-4-e4b-it"
PORT = 8080
TUNNEL = "cloudflared"        # "cloudflared" | "ngrok" | "none"
DUECARE_API_TOKEN = ""        # non-empty -> require auth on /api/*
DUECARE_DB = "/kaggle/working/duecare.duckdb"
PIPELINE_OUT = "/kaggle/working/multimodal_v1_output"


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

    # Local Gemma model search
    import glob as _glob
    for pat in (
        "/kaggle/input/models/google/gemma-4/transformers/gemma-4-e4b-it/*",
        "/kaggle/input/models/google/*/transformers/gemma-4-e4b-it/*",
        "/kaggle/input/**/gemma-4-e4b-it/*",
        "/kaggle/input/**/gemma-4*/*",
        "/kaggle/input/**/gemma-3-4b*/*",
    ):
        for c in _glob.glob(pat, recursive=True):
            if Path(c, "config.json").exists():
                env.attached_model_path = c
                break
        if env.attached_model_path:
            break

    return env


def get_pkg_version(pkg: str) -> Optional[str]:
    """Return the installed version of `pkg`, or None."""
    try:
        from importlib.metadata import version, PackageNotFoundError
        return version(pkg)
    except Exception:
        return None


def version_satisfies(installed: str, required: str) -> bool:
    """Lightweight check: 'X.Y.Z' >= required ('>=A.B.C' or 'A.B.C')."""
    if not required:
        return True
    if not installed:
        return False
    # Strip operators like >=, ==, ~=
    op_match = re.match(r"^(>=|==|~=|>|<=|<)?\s*(.+)$", required)
    op = op_match.group(1) or ">="
    target = op_match.group(2)
    def _parse(v):
        return tuple(int(x) for x in re.findall(r"\d+", v)[:3])
    try:
        i = _parse(installed)
        t = _parse(target)
        if op == "==":
            return i == t
        if op == ">=":
            return i >= t
        if op == ">":
            return i > t
        if op == "<=":
            return i <= t
        if op == "<":
            return i < t
        return True
    except Exception:
        return True


@dataclass
class PipSpec:
    name: str
    required: str = ""           # e.g. ">=4.56"
    optional: bool = False       # if True, don't crash on failure


def smart_pip_install(specs: list[PipSpec],
                        verbose: bool = True) -> dict[str, str]:
    """Install only what's missing or out-of-date. Returns {name: status}."""
    statuses: dict[str, str] = {}
    to_install: list[str] = []

    for spec in specs:
        installed = get_pkg_version(spec.name)
        if installed and version_satisfies(installed, spec.required):
            statuses[spec.name] = f"already {installed}"
            if verbose:
                print(f"  ✓ {spec.name:20s} {installed} (already satisfies "
                      f"{spec.required or 'any'})")
        else:
            target = (f"{spec.name}{spec.required}"
                      if spec.required else spec.name)
            to_install.append(target)
            if verbose:
                print(f"  → {spec.name:20s} need install"
                      f" ({installed or 'missing'} -> {spec.required or 'latest'})")

    if not to_install:
        return statuses

    cmd = [sys.executable, "-m", "pip", "install", "--quiet",
           "--upgrade", "--disable-pip-version-check", "--no-input",
           *to_install]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # Retry one-by-one so a single bad spec doesn't kill the others.
        if verbose:
            print(f"  bulk install failed; retrying one at a time")
        for target in to_install:
            single = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet",
                 "--upgrade", "--disable-pip-version-check", "--no-input",
                 target], capture_output=True, text=True)
            name = re.split(r"[<>=~]", target, 1)[0]
            if single.returncode == 0:
                statuses[name] = "installed (retry)"
                if verbose:
                    print(f"  ✓ {name}")
            else:
                statuses[name] = f"FAILED: {single.stderr[:200]}"
                if verbose:
                    print(f"  ✗ {name}: {single.stderr[:200]}")
    else:
        for target in to_install:
            name = re.split(r"[<>=~]", target, 1)[0]
            statuses[name] = "installed"
        if verbose:
            print(f"  ✓ installed {len(to_install)} package(s)")
    return statuses


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


def load_gemma_smart(env: Env, model_id: str = GEMMA_MODEL,
                       verbose: bool = True) -> Optional[LoadedModel]:
    """Try every reasonable load config in order. Return the first that
    works, or None if all fail."""
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
        from transformers import (AutoProcessor,
                                    AutoModelForImageTextToText,
                                    BitsAndBytesConfig)
    except Exception as e:
        if verbose:
            print(f"  transformers / torch import FAILED: "
                  f"{type(e).__name__}: {e}")
        return None

    model_path = env.attached_model_path or model_id
    if verbose:
        print(f"  model path: {model_path}")

    try:
        processor = AutoProcessor.from_pretrained(
            model_path, trust_remote_code=True)
    except Exception as e:
        if verbose:
            print(f"  processor load FAILED: {type(e).__name__}: {e}")
        return None

    # Pick configs to try in priority order, based on detected VRAM.
    vram = env.gpu.vram_gb
    configs = []
    if vram < 20:
        # T4 / P100 -- need 4-bit
        configs.append(("4bit-sdpa", "sdpa", True))
        configs.append(("4bit-eager", "eager", True))
        configs.append(("bf16-sdpa", "sdpa", False))      # may OOM
        configs.append(("bf16-eager", "eager", False))
    else:
        configs.append(("bf16-sdpa", "sdpa", False))
        configs.append(("bf16-eager", "eager", False))
        configs.append(("4bit-sdpa", "sdpa", True))
        configs.append(("4bit-eager", "eager", True))

    for label, attn, use_4bit in configs:
        if verbose:
            print(f"  trying {label} ...")
        load_kwargs: dict = dict(
            device_map={"": 0},
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
        if use_4bit:
            try:
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
            except Exception as e:
                if verbose:
                    print(f"    {label}: bnb config FAILED ({e}); "
                          f"skipping this config")
                continue
        else:
            load_kwargs["dtype"] = torch.bfloat16
        try:
            model = AutoModelForImageTextToText.from_pretrained(
                model_path, attn_implementation=attn, **load_kwargs)
        except Exception as e:
            err = str(e)[:200]
            if verbose:
                print(f"    {label} FAILED: {type(e).__name__}: {err}")
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
            continue
        model.eval()
        try:
            vram_used = torch.cuda.memory_allocated(0) / 1024**3
        except Exception:
            vram_used = 0.0
        if verbose:
            print(f"  ✓ loaded with {label}  ({vram_used:.2f} GB VRAM used)")

        @torch.inference_mode()
        def gemma_call(prompt: str, max_new_tokens: int = 300) -> str:
            msgs = [{"role": "user",
                     "content": [{"type": "text", "text": prompt}]}]
            inputs = processor.apply_chat_template(
                msgs, add_generation_prompt=True,
                tokenize=True, return_dict=True, return_tensors="pt")
            inputs = {k: v.to(model.device) if hasattr(v, "to") else v
                       for k, v in inputs.items()}
            prompt_len = inputs["input_ids"].shape[-1]
            out = model.generate(
                **inputs, max_new_tokens=max_new_tokens, do_sample=False,
                pad_token_id=(processor.tokenizer.pad_token_id
                               or processor.tokenizer.eos_token_id))
            new_tokens = out[0, prompt_len:]
            text = processor.tokenizer.decode(
                new_tokens, skip_special_tokens=True).strip()
            del out, new_tokens, inputs
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
            return text

        return LoadedModel(backend=gemma_call, processor=processor,
                             mode=label, vram_used_gb=vram_used)
    if verbose:
        print(f"  ALL Gemma load configs failed; "
              f"falling back to HEURISTIC mode")
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
print("=== ensuring PyPI deps ===")
pypi_specs = [
    PipSpec("transformers", ">=4.56"),
    PipSpec("accelerate", ">=1.0"),
    PipSpec("bitsandbytes", ">=0.46.1", optional=True),
    PipSpec("fastapi", ">=0.115.0", optional=True),
    PipSpec("uvicorn", ">=0.30.0", optional=True),
    PipSpec("duckdb", ">=1.0.0", optional=True),
    PipSpec("click", ">=8.1.0", optional=True),
]
pypi_status = smart_pip_install(pypi_specs)


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
# 4. Build server state
# ===========================================================================
print("\n" + "=" * 76)
print("[4/8] building server state")
print("=" * 76)
from duecare.server.state import ServerState
state = ServerState(db_path=DUECARE_DB, pipeline_output_dir=PIPELINE_OUT)
if gemma_call is not None:
    state.set_gemma_call(gemma_call)
    print("  gemma_call wired into server state (GPU worker active)")
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
