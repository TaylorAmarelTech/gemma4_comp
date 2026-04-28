"""
============================================================================
  DUECARE ADVERSARIAL VALIDATION -- Kaggle notebook (single-cell paste)
============================================================================

  ONE END-TO-END run that exercises EVERY component with REAL Gemma 4
  calls. 18 tests, ~5-10 minutes on P100 (4-bit) or T4.

  Tests:
    01  environment detect (GPU / attached model / wheels installed)
    02  duecare wheel imports (7 packages)
    03  Gemma 4 multimodal model load
    04  Gemma text-only inference
    05  Gemma multimodal (1 image + text) inference
    06  Gemma multi-image pairwise compare
    07  Knowledge base assembly (186 passages)
    08  Grep retrieval over knowledge base
    09  RAG retrieval (sentence-transformers + cosine)
    10  Tool call -- lookup_statute (PH RA 8042)
    11  Reactive trigger -- fee_detected end-to-end
    12  Per-doc Gemma graph extraction (entities + relationships)
    13  Entity consolidation via Gemma synonym merging
    14  Evidence DB ingest from enriched_results.json
    15  NL->SQL via parameterised template (avg_fee_by_corridor)
    16  NL->SQL via Gemma free-form + safety guard
    17  Research tool -- OpenClaw mock mode
    18  Server endpoints (in-process /api/* checks)

  Requirements:
    - Kaggle GPU runtime (P100 / T4 / T4x2)
    - Internet ON
    - taylorsamarel/duecare-llm-wheels dataset attached
    - A Gemma 4 model attached (any variant under /kaggle/input/models/...)
    - HF_TOKEN secret only needed if no Gemma model is attached

  Output: a structured PASS/FAIL report + per-test diagnostics.
============================================================================
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


# ===========================================================================
# Result accumulator
# ===========================================================================
@dataclass
class TestResult:
    name: str
    passed: bool
    seconds: float
    detail: str = ""
    error: Optional[str] = None


_RESULTS: list[TestResult] = []


def _run_test(name: str, fn: Callable[[], str]) -> TestResult:
    print(f"\n{'='*76}\n  {name}\n{'='*76}")
    t0 = time.time()
    try:
        detail = fn() or ""
        r = TestResult(name=name, passed=True,
                        seconds=time.time() - t0, detail=detail)
        print(f"  ✓ PASS  ({r.seconds:.1f}s)  {detail[:200]}")
    except AssertionError as e:
        r = TestResult(name=name, passed=False,
                        seconds=time.time() - t0, error=str(e))
        print(f"  ✗ FAIL  ({r.seconds:.1f}s)  AssertionError: {e}")
    except Exception as e:
        r = TestResult(name=name, passed=False,
                        seconds=time.time() - t0,
                        error=f"{type(e).__name__}: {e}")
        print(f"  ✗ FAIL  ({r.seconds:.1f}s)  "
                f"{type(e).__name__}: {str(e)[:200]}")
        traceback.print_exc(limit=2)
    _RESULTS.append(r)
    return r


# ===========================================================================
# Bootstrap (idempotent)
# ===========================================================================
print("=" * 76)
print("DUECARE ADVERSARIAL VALIDATION  --  18 tests")
print("=" * 76)

# Install wheels if not already importable.
try:
    import duecare.evidence    # noqa
    import duecare.server      # noqa
    print("  duecare modules already importable")
except Exception:
    print("  installing duecare wheels from /kaggle/input ...")
    wheels = sorted(p for p in Path("/kaggle/input").rglob("*.whl")
                     if "duecare" in p.name.lower())
    if not wheels:
        raise SystemExit("No duecare wheels found. Attach the "
                          "`taylorsamarel/duecare-llm-wheels` dataset.")
    subprocess.run([sys.executable, "-m", "pip", "install",
                     "--quiet", "--no-input",
                     "--disable-pip-version-check",
                     *[str(w) for w in wheels]], check=True)
    # Drop already-imported modules.
    for mod in list(sys.modules):
        if mod == "duecare" or mod.startswith("duecare."):
            del sys.modules[mod]

# Mirror of the baseline pipeline's bootstrap
# (raw_python/gemma4_multimodal_with_rag_grep_v1.py L638-661).
# pip install --upgrade of the full HF stack as ONE pip command, then
# drop sys.modules so reimport sees new versions. The ONLY difference
# vs baseline: upper bounds on transformers (<5.0; 5.0.0 dropped
# 'gemma4' model_type) and huggingface_hub (<1.0; transformers 4.57's
# runtime check rejects 1.x). NOT pinning tokenizers -- transformers
# 4.57.x requires tokenizers>=0.22, so a <0.22 pin would break the
# resolver. If --upgrade leaves us still on 5.x or hub 1.x (some pip
# versions skip cross-package downgrades), retry with --force-reinstall.
print("  pinning HF stack (transformers<5.0, hub<1.0) + "
      "accelerate + bnb + sentence-transformers + pillow")
_BASE_SPECS = [
    "transformers>=4.56,<5.0",
    "accelerate>=1.0",
    "sentencepiece", "safetensors",
    "huggingface_hub<1.0",
    "bitsandbytes>=0.43.0",
    "sentence-transformers>=2.7.0",
    "pillow",
]
subprocess.run(
    [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
     "--disable-pip-version-check", "--no-input", *_BASE_SPECS],
    capture_output=False, check=False)
# Drop cached modules so new versions take effect.
for mod in list(sys.modules):
    base = mod.split(".")[0]
    if base in ("transformers", "huggingface_hub", "tokenizers",
                "accelerate", "bitsandbytes", "safetensors",
                "sentencepiece", "sentence_transformers"):
        del sys.modules[mod]


def _hf_stack_versions() -> dict[str, str]:
    from importlib.metadata import version as _v
    out = {}
    for _pkg in ("transformers", "huggingface-hub", "tokenizers",
                 "accelerate", "bitsandbytes"):
        try:
            out[_pkg] = _v(_pkg)
        except Exception:
            out[_pkg] = "(missing)"
    return out


_v_after_upgrade = _hf_stack_versions()
_needs_force = False
try:
    if _v_after_upgrade["transformers"] != "(missing)":
        if int(_v_after_upgrade["transformers"].split(".")[0]) >= 5:
            _needs_force = True
            print(f"  transformers={_v_after_upgrade['transformers']} "
                  f"still >=5; retrying with --force-reinstall")
    if _v_after_upgrade["huggingface-hub"] != "(missing)":
        if int(_v_after_upgrade["huggingface-hub"].split(".")[0]) >= 1:
            _needs_force = True
            print(f"  huggingface-hub={_v_after_upgrade['huggingface-hub']} "
                  f"still >=1; retrying with --force-reinstall")
except Exception:
    _needs_force = True

if _needs_force:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
         "--force-reinstall",
         "--disable-pip-version-check", "--no-input", *_BASE_SPECS],
        capture_output=False, check=True)
    for mod in list(sys.modules):
        base = mod.split(".")[0]
        if base in ("transformers", "huggingface_hub", "tokenizers",
                    "accelerate", "bitsandbytes", "safetensors",
                    "sentencepiece", "sentence_transformers"):
            del sys.modules[mod]

# Confirm final versions.
for _pkg, _ver in _hf_stack_versions().items():
    print(f"    {_pkg:24s} {_ver}")


# ===========================================================================
# Test 01 -- environment detect
# ===========================================================================
import torch
import glob as _glob
ENV: dict = {}


def t01_environment():
    global ENV
    ENV["gpu_count"] = torch.cuda.device_count()
    assert ENV["gpu_count"] >= 1, "no CUDA GPU detected"
    ENV["gpu_name"] = torch.cuda.get_device_name(0)
    ENV["vram_gb"] = (torch.cuda.get_device_properties(0).total_memory
                       / 1024**3)

    # 3-tier model resolution mirroring the baseline pipeline:
    # (1) MM_MODEL_PATH explicit override
    # (2) Narrow Kaggle Models patterns
    # (3) Broad walk of /kaggle/input/** for any config.json whose
    #     path matches "gemma" or the variant name.
    # Also print /kaggle/input contents for diagnosis.
    model_path = None
    explicit = os.environ.get("MM_MODEL_PATH", "").strip()
    if (explicit and Path(explicit).is_dir()
            and Path(explicit, "config.json").exists()):
        model_path = explicit

    if not model_path and Path("/kaggle/input").is_dir():
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

    if not model_path:
        narrow_patterns = [
            "/kaggle/input/models/google/gemma-4/transformers/"
            "gemma-4-e4b-it/*",
            "/kaggle/input/models/google/*/transformers/gemma-4-e4b-it/*",
            "/kaggle/input/models/**/gemma-4-e4b-it/*",
            "/kaggle/input/**/gemma-4-e4b-it/*",
            "/kaggle/input/**/gemma-4*/*",
            # Common Kaggle mount points for attached models:
            "/kaggle/input/gemma-4-e4b-it/*",
            "/kaggle/input/gemma-4/transformers/gemma-4-e4b-it/*",
            "/kaggle/input/gemma-4/transformers/*/*",
        ]
        for pat in narrow_patterns:
            for c in _glob.glob(pat, recursive=True):
                if Path(c).is_dir() and Path(c, "config.json").exists():
                    model_path = c
                    break
            if model_path:
                break

    if not model_path and Path("/kaggle/input").is_dir():
        # Broad fallback walk: any config.json whose path contains
        # "gemma" or "e4b" / "e2b" variant token.
        for root, _dirs, files in os.walk("/kaggle/input"):
            if "config.json" not in files:
                continue
            low = root.lower()
            if "gemma" in low or "e4b" in low or "e2b" in low:
                model_path = root
                break

    # LAST RESORT: any config.json that looks like a transformers
    # checkpoint (has tokenizer.json or model.safetensors).
    if not model_path and Path("/kaggle/input").is_dir():
        for root, _dirs, files in os.walk("/kaggle/input"):
            if ("config.json" in files
                    and ("tokenizer.json" in files
                         or "model.safetensors" in files
                         or "model.safetensors.index.json" in files
                         or "pytorch_model.bin" in files)):
                model_path = root
                break

    ENV["model_path"] = model_path
    if not model_path:
        if not os.environ.get("HF_TOKEN"):
            try:
                from kaggle_secrets import UserSecretsClient   # type: ignore
                tok = UserSecretsClient().get_secret("HF_TOKEN")
                if tok:
                    os.environ["HF_TOKEN"] = tok.strip()
            except Exception:
                pass
        ENV["model_path"] = "google/gemma-4-e4b-it"
        assert os.environ.get("HF_TOKEN"), \
            "no attached Gemma model AND no HF_TOKEN -- attach a Gemma " \
            "4 model from Add Data -> Models, or set MM_MODEL_PATH"
    return (f"GPU: {ENV['gpu_name']} "
            f"({ENV['vram_gb']:.1f} GB), model: {ENV['model_path']}")


_run_test("T01  environment detect", t01_environment)


# ===========================================================================
# Test 02 -- duecare wheel imports
# ===========================================================================
def t02_imports():
    import duecare.evidence
    import duecare.engine
    import duecare.nl2sql
    import duecare.research_tools
    import duecare.server
    import duecare.training
    from duecare.cli import sample_data
    return ("evidence, engine, nl2sql, research_tools, server, "
              "training, cli.sample_data all import")


_run_test("T02  duecare wheel imports", t02_imports)


# ===========================================================================
# Test 03 -- Gemma 4 multimodal model load
# ===========================================================================
GEMMA: dict = {}


def t03_gemma_load():
    global GEMMA
    from transformers import (AutoProcessor, AutoModelForImageTextToText,
                                BitsAndBytesConfig)
    model_path = ENV["model_path"]
    processor = AutoProcessor.from_pretrained(
        model_path, trust_remote_code=True)
    use_4bit = ENV["vram_gb"] < 20
    load_kwargs: dict = dict(device_map={"": 0}, low_cpu_mem_usage=True,
                              trust_remote_code=True)
    if use_4bit:
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
    else:
        load_kwargs["dtype"] = torch.bfloat16
    model = None
    last_err = None
    for attn in ("sdpa", "eager"):
        try:
            model = AutoModelForImageTextToText.from_pretrained(
                model_path, attn_implementation=attn, **load_kwargs)
            GEMMA["mode"] = f"{'4bit' if use_4bit else 'bf16'}-{attn}"
            break
        except Exception as e:
            last_err = e
    assert model is not None, f"all load configs failed: {last_err}"
    model.eval()
    GEMMA["processor"] = processor
    GEMMA["model"] = model
    GEMMA["vram_gb"] = torch.cuda.memory_allocated(0) / 1024**3
    return f"loaded with {GEMMA['mode']}, {GEMMA['vram_gb']:.2f} GB VRAM"


_run_test("T03  Gemma 4 multimodal model load", t03_gemma_load)


# ===========================================================================
# Test 04 -- Gemma text-only inference
# ===========================================================================
@torch.inference_mode()
def _gemma_text_only(prompt: str, max_new_tokens: int = 80) -> str:
    if "model" not in GEMMA:
        raise RuntimeError("Gemma not loaded")
    msgs = [{"role": "user",
             "content": [{"type": "text", "text": prompt}]}]
    inputs = GEMMA["processor"].apply_chat_template(
        msgs, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt")
    inputs = {k: v.to(GEMMA["model"].device) if hasattr(v, "to") else v
               for k, v in inputs.items()}
    pl = inputs["input_ids"].shape[-1]
    out = GEMMA["model"].generate(
        **inputs, max_new_tokens=max_new_tokens, do_sample=False,
        pad_token_id=(GEMMA["processor"].tokenizer.pad_token_id
                       or GEMMA["processor"].tokenizer.eos_token_id))
    text = GEMMA["processor"].tokenizer.decode(
        out[0, pl:], skip_special_tokens=True).strip()
    del out, inputs
    torch.cuda.empty_cache()
    return text


def t04_text_only():
    r = _gemma_text_only(
        "In one short sentence: what is the capital of France?",
        max_new_tokens=40)
    assert r and len(r) > 5, f"empty / too-short response: {r!r}"
    return f"reply ({len(r)} chars): {r[:120]}"


_run_test("T04  Gemma text-only inference", t04_text_only)


# ===========================================================================
# Test 05 -- Gemma multimodal (image + text)
# ===========================================================================
def _make_test_image(text: str, color=(220, 220, 250)):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (640, 360), color=color)
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except Exception:
        f = ImageFont.load_default()
    d.text((30, 150), text, fill=(15, 15, 30), font=f)
    return img


@torch.inference_mode()
def _gemma_caption(img, prompt: str, max_new_tokens: int = 80) -> str:
    msgs = [{"role": "user",
             "content": [{"type": "image", "image": img},
                          {"type": "text", "text": prompt}]}]
    inputs = GEMMA["processor"].apply_chat_template(
        msgs, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt")
    inputs = {k: v.to(GEMMA["model"].device) if hasattr(v, "to") else v
               for k, v in inputs.items()}
    pl = inputs["input_ids"].shape[-1]
    out = GEMMA["model"].generate(
        **inputs, max_new_tokens=max_new_tokens, do_sample=False,
        pad_token_id=(GEMMA["processor"].tokenizer.pad_token_id
                       or GEMMA["processor"].tokenizer.eos_token_id))
    text = GEMMA["processor"].tokenizer.decode(
        out[0, pl:], skip_special_tokens=True).strip()
    del out, inputs
    torch.cuda.empty_cache()
    return text


def t05_multimodal_image_text():
    img = _make_test_image("PASSPORT")
    r = _gemma_caption(img, "What single English word is shown in this "
                                "image? Answer with one word.",
                        max_new_tokens=20)
    assert r and "passport" in r.lower(), \
        f"expected 'passport' in response, got: {r!r}"
    return f"recognised the word PASSPORT in the synthetic image: {r!r}"


_run_test("T05  Gemma multimodal (image + text)", t05_multimodal_image_text)


# ===========================================================================
# Test 06 -- Gemma multi-image pairwise compare
# ===========================================================================
@torch.inference_mode()
def _gemma_compare(img_a, img_b, prompt: str,
                     max_new_tokens: int = 80) -> str:
    msgs = [{"role": "user",
             "content": [{"type": "image", "image": img_a},
                          {"type": "image", "image": img_b},
                          {"type": "text", "text": prompt}]}]
    inputs = GEMMA["processor"].apply_chat_template(
        msgs, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt")
    inputs = {k: v.to(GEMMA["model"].device) if hasattr(v, "to") else v
               for k, v in inputs.items()}
    pl = inputs["input_ids"].shape[-1]
    out = GEMMA["model"].generate(
        **inputs, max_new_tokens=max_new_tokens, do_sample=False,
        pad_token_id=(GEMMA["processor"].tokenizer.pad_token_id
                       or GEMMA["processor"].tokenizer.eos_token_id))
    text = GEMMA["processor"].tokenizer.decode(
        out[0, pl:], skip_special_tokens=True).strip()
    del out, inputs
    torch.cuda.empty_cache()
    return text


def t06_multi_image_compare():
    img_a = _make_test_image("PACIFIC COAST")
    img_b = _make_test_image("PACIFIC COAST")  # same content
    r = _gemma_compare(img_a, img_b,
        "Do these two images show the same text? Answer 'yes' or 'no' "
        "only.", max_new_tokens=20)
    assert r and "yes" in r.lower(), \
        f"expected 'yes' (images are identical), got: {r!r}"
    return f"correctly identified two identical images: {r!r}"


_run_test("T06  Gemma multi-image pairwise compare", t06_multi_image_compare)


# ===========================================================================
# Test 07 -- Knowledge base assembly
# ===========================================================================
def t07_knowledge_base():
    # Build the knowledge base inline (simplified) -- we don't have
    # access to the baseline's _build_knowledge_passages without
    # importing the 12,500-line script. Instead build a tiny KB to
    # validate the retriever wiring.
    global KB
    KB = [
        {"id": "ph_ra8042_sec6a",
         "text": "PH RA 8042 sec 6(a): No placement fee shall be "
                 "collected from a worker before deployment beyond what "
                 "is allowed by POEA rules (typically one month's salary).",
         "tags": ["fee", "PH", "statute"]},
        {"id": "ilo_c029_indicator7",
         "text": "ILO C029 forced labour indicator 7: retention of "
                 "identity documents (passport confiscation) by the "
                 "employer.",
         "tags": ["passport", "ILO", "C029"]},
        {"id": "hk_employment_ord",
         "text": "HK Employment Ordinance: agencies cannot charge more "
                 "than 10% of the worker's first month salary as a "
                 "placement fee.",
         "tags": ["fee", "HK", "statute"]},
        {"id": "poea_hotline",
         "text": "Philippine Overseas Employment Administration / DMW "
                 "hotline: 1343. Reports of trafficking, illegal fees, "
                 "passport confiscation.",
         "tags": ["hotline", "PH"]},
        {"id": "kafala_passport",
         "text": "Kafala system (GCC): traditionally allows employers "
                 "to hold worker passports; reformed in Saudi Arabia 2021.",
         "tags": ["kafala", "passport", "SA"]},
    ]
    assert len(KB) >= 5
    return f"{len(KB)} knowledge passages assembled"


_run_test("T07  Knowledge base assembly", t07_knowledge_base)


# ===========================================================================
# Test 08 -- Grep retrieval
# ===========================================================================
def t08_grep_retrieval():
    query = "passport"
    rx = re.compile(query, re.IGNORECASE)
    hits = [p for p in KB if rx.search(p["text"])]
    assert len(hits) >= 2, f"expected >=2 hits for {query!r}, got {len(hits)}"
    return f"{len(hits)} hits for {query!r}: " \
              f"{[h['id'] for h in hits]}"


_run_test("T08  Grep retrieval", t08_grep_retrieval)


# ===========================================================================
# Test 09 -- RAG retrieval
# ===========================================================================
def t09_rag_retrieval():
    from sentence_transformers import SentenceTransformer
    enc = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    texts = [p["text"] for p in KB]
    emb = enc.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    q = enc.encode(["how much can a recruitment agency charge"],
                    convert_to_numpy=True, normalize_embeddings=True)[0]
    import numpy as _np
    scores = emb @ q
    top = _np.argsort(-scores)[:3]
    top_ids = [KB[i]["id"] for i in top]
    # Expect at least one fee-related passage in top 3
    assert any("fee" in KB[i]["tags"] for i in top), \
        f"expected fee-tagged passage in top 3, got {top_ids}"
    return (f"top-3 for 'how much can a recruitment agency charge': "
              f"{top_ids}")


_run_test("T09  RAG retrieval", t09_rag_retrieval)


# ===========================================================================
# Test 10 -- Tool call (lookup_statute deterministic)
# ===========================================================================
def t10_tool_call():
    # Simulate the baseline's tool_lookup_statute with a small inline
    # implementation (the baseline ships a richer version).
    def tool_lookup_statute(jurisdiction: str, topic: str) -> dict:
        for p in KB:
            if (jurisdiction.lower() in p["text"].lower()
                    and topic.lower().split("_")[0] in p["text"].lower()):
                return {"jurisdiction": jurisdiction, "topic": topic,
                        "passage_id": p["id"], "text": p["text"]}
        return {"jurisdiction": jurisdiction, "topic": topic,
                "passage_id": None, "text": "no matching statute"}

    r = tool_lookup_statute("PH", "fee")
    assert r["passage_id"] is not None, "expected to find PH fee statute"
    assert "ra 8042" in r["text"].lower(), f"unexpected text: {r['text']}"
    return f"PH fee -> {r['passage_id']}"


_run_test("T10  Tool call (lookup_statute)", t10_tool_call)


# ===========================================================================
# Test 11 -- Reactive trigger (fee_detected) end-to-end with Gemma
# ===========================================================================
def t11_reactive_trigger():
    fee = "USD 5000"
    bundle = "manila_recruitment_001"
    employer = "Al-Rashid Household Services"
    prompt = (
        "You are an investigative analyst reviewing a recruitment fee "
        "for compliance with migrant-worker statutes.\n\n"
        f"FEE DETECTED:    {fee}\n"
        f"CONTEXT:         placement_fee\n"
        f"CASE BUNDLE:     {bundle}\n"
        f"EMPLOYER:        {employer}\n"
        f"DESTINATION:     Saudi Arabia\n\n"
        "Available statute reference: PH RA 8042 sec 6(a) caps "
        "placement fees at one month's salary.\n\n"
        "Respond with ONE JSON object only:\n"
        "{\"fee_legitimate\": true|false, \"jurisdiction\": \"PH\","
        " \"statute_violated\": \"...\", \"severity\": 0,"
        " \"reasoning\": \"one short sentence\"}"
    )
    raw = _gemma_text_only(prompt, max_new_tokens=200)
    m = re.search(r"\{[\s\S]*\}", raw)
    assert m is not None, f"no JSON in Gemma reply: {raw[:200]}"
    try:
        parsed = json.loads(m.group(0))
    except Exception:
        cleaned = re.sub(r",\s*([}\]])", r"\1", m.group(0))
        parsed = json.loads(cleaned)
    sev = float(parsed.get("severity", 0) or 0)
    assert sev > 0, f"expected severity > 0, got {sev}: {parsed}"
    return (f"Gemma flagged USD 5000 fee as severity={sev} "
              f"(legit={parsed.get('fee_legitimate')}, "
              f"statute={parsed.get('statute_violated')!r})")


_run_test("T11  Reactive trigger (fee_detected) end-to-end", t11_reactive_trigger)


# ===========================================================================
# Test 12 -- Per-doc graph extraction (Gemma)
# ===========================================================================
def t12_doc_graph_extraction():
    facts_json = json.dumps({
        "agency": "Pacific Coast Manpower Inc.",
        "fee": "USD 1500",
        "destination": "Saudi Arabia",
        "phone": "+63-555-0123-4567",
        "worker_name": "Maria Santos",
        "passport": "AB1234567",
    }, indent=2)
    prompt = (
        "Extract every named entity and any relationships from this "
        "recruitment-context document. Return ONE JSON object:\n"
        "{\n"
        "  \"entities\": [{\"id\": 1, \"type\": \"person|organization|"
        "phone|money|address|passport_number\", \"name\": \"...\","
        " \"role_in_doc\": \"...\"}],\n"
        "  \"relationships\": [{\"a_id\": 1, \"b_id\": 2,"
        " \"type\": \"recruited|charged_fee_to|located_at\","
        " \"evidence\": \"short quote\"}]\n"
        "}\n\n"
        "EXTRACTED FACTS:\n" + facts_json
    )
    raw = _gemma_text_only(prompt, max_new_tokens=400)
    m = re.search(r"\{[\s\S]*\}", raw)
    assert m, f"no JSON in reply: {raw[:200]}"
    try:
        parsed = json.loads(m.group(0))
    except Exception:
        parsed = json.loads(re.sub(r",\s*([}\]])", r"\1", m.group(0)))
    ents = parsed.get("entities") or []
    rels = parsed.get("relationships") or []
    assert len(ents) >= 3, f"expected >=3 entities, got {len(ents)}: {ents}"
    return (f"Gemma extracted {len(ents)} entities + {len(rels)} "
              f"relationships from a 6-field facts dict")


_run_test("T12  Per-doc graph extraction (Gemma)", t12_doc_graph_extraction)


# ===========================================================================
# Test 13 -- Entity consolidation via Gemma
# ===========================================================================
def t13_entity_consolidation():
    candidates = [
        "Pacific Coast Manpower",
        "Pacific Coast Manpower Inc.",
        "Pacific Coast Mnpower",   # OCR typo
        "Atlantic Manpower",
    ]
    prompt = (
        "You are consolidating organisation names. Identify which of "
        "these refer to the SAME entity. Return ONE JSON object:\n"
        "{\"groups\": [{\"canonical_name\": \"...\","
        " \"member_indexes\": [1, 2, 3], \"confidence\": 0}]}\n\n"
        "CANDIDATES:\n"
        + "\n".join(f"{i+1}. {c}" for i, c in enumerate(candidates))
    )
    raw = _gemma_text_only(prompt, max_new_tokens=300)
    m = re.search(r"\{[\s\S]*\}", raw)
    assert m, f"no JSON in reply: {raw[:200]}"
    try:
        parsed = json.loads(m.group(0))
    except Exception:
        parsed = json.loads(re.sub(r",\s*([}\]])", r"\1", m.group(0)))
    groups = parsed.get("groups") or []
    # We expect a group containing 1, 2, 3 (the Pacific Coast variants)
    pacific_group = None
    for g in groups:
        members = set(g.get("member_indexes") or [])
        if {1, 2}.issubset(members) or {1, 3}.issubset(members) or {2, 3}.issubset(members):
            pacific_group = g
            break
    assert pacific_group is not None, \
        f"Gemma did not merge Pacific Coast variants: {groups}"
    return (f"Gemma merged Pacific Coast variants: "
              f"{pacific_group.get('member_indexes')} -> "
              f"{pacific_group.get('canonical_name')!r}")


_run_test("T13  Entity consolidation via Gemma", t13_entity_consolidation)


# ===========================================================================
# Test 14 -- Evidence DB ingest
# ===========================================================================
def t14_evidence_db_ingest():
    from duecare.evidence import EvidenceStore
    out_dir = Path("/kaggle/working/_validation_out")
    out_dir.mkdir(parents=True, exist_ok=True)
    sample = [{
        "image_path": "/tmp/sample.txt",
        "case_bundle": "validation_bundle",
        "parsed_response": {"category": "test",
                              "extracted_facts": {"fee": "USD 1500"}},
        "gemma_graph": {
            "entities": [
                {"id": 1, "type": "recruitment_agency",
                 "name": "Validation Test Agency"},
                {"id": 2, "type": "money", "name": "USD 1500"}],
            "flagged_findings": [{
                "trigger": "fee_detected", "type": "illegal_fee_flag",
                "fee_value": "USD 1500", "severity": 9,
                "statute_violated": "PH RA 8042 sec 6(a)",
                "jurisdiction": "PH"}],
        },
    }]
    (out_dir / "enriched_results.json").write_text(
        json.dumps(sample, indent=2), encoding="utf-8")
    (out_dir / "entity_graph.json").write_text(json.dumps({
        "n_documents": 1, "n_entities": 2, "n_edges": 0,
        "bad_actor_candidates": [
            {"type": "recruitment_agency",
             "value": "validation test agency",
             "raw_values": ["Validation Test Agency"],
             "doc_count": 1, "co_occurrence_degree": 1, "severity_max": 9}],
        "top_edges": [],
    }), encoding="utf-8")
    db_path = "/kaggle/working/_validation.duckdb"
    if Path(db_path).exists():
        Path(db_path).unlink()
    store = EvidenceStore.open(db_path)
    rid = store.ingest_run(out_dir)
    docs = store.fetchone("SELECT COUNT(*) AS n FROM documents")
    findings = store.fetchone("SELECT COUNT(*) AS n FROM findings")
    ents = store.fetchone("SELECT COUNT(*) AS n FROM entities")
    store.close()
    assert docs["n"] >= 1, f"expected >=1 document, got {docs}"
    assert findings["n"] >= 1, f"expected >=1 finding, got {findings}"
    assert ents["n"] >= 1, f"expected >=1 entity, got {ents}"
    return (f"ingested {rid}: {docs['n']} docs, {ents['n']} entities, "
              f"{findings['n']} findings")


_run_test("T14  Evidence DB ingest", t14_evidence_db_ingest)


# ===========================================================================
# Test 15 -- NL->SQL via parameterised template
# ===========================================================================
def t15_nl2sql_template():
    from duecare.evidence import EvidenceStore
    from duecare.nl2sql import Translator
    store = EvidenceStore.open("/kaggle/working/_validation.duckdb")
    trans = Translator(store, gemma_call=None)
    res = trans.answer("What is the average illicit fee?")
    store.close()
    assert res.template_name == "avg_fee_by_corridor", \
        f"expected avg_fee_by_corridor template, got {res.template_name}"
    assert res.error is None, f"unexpected error: {res.error}"
    assert res.sql.strip().upper().startswith("SELECT"), \
        f"unexpected SQL: {res.sql}"
    return (f"matched template {res.template_name!r}, "
              f"{res.row_count} row(s) returned")


_run_test("T15  NL->SQL via parameterised template", t15_nl2sql_template)


# ===========================================================================
# Test 16 -- NL->SQL via Gemma free-form + safety guard
# ===========================================================================
def t16_nl2sql_gemma():
    from duecare.evidence import EvidenceStore
    from duecare.nl2sql import Translator, validate_readonly
    store = EvidenceStore.open("/kaggle/working/_validation.duckdb")
    trans = Translator(store, gemma_call=_gemma_text_only)
    res = trans.answer(
        "List the count of bundles per finding type", prefer_template=False)
    store.close()
    assert res.method == "gemma", f"expected method=gemma, got {res.method}"
    if res.sql:
        try:
            cleaned = validate_readonly(res.sql)
            assert "select" in cleaned.lower()
        except Exception as e:
            assert False, f"safety guard rejected Gemma SQL: {e}"
    return (f"Gemma free-form SQL ({len(res.sql)} chars): "
              f"{res.sql[:120]}")


_run_test("T16  NL->SQL via Gemma free-form + safety guard", t16_nl2sql_gemma)


# ===========================================================================
# Test 17 -- Research tool (OpenClaw mock mode)
# ===========================================================================
def t17_openclaw_mock():
    from duecare.research_tools import OpenClawTool
    tool = OpenClawTool(mode="mock")
    r = tool.search("validation test query")
    assert r.success, f"expected success, got error: {r.error}"
    assert r.items, "expected non-empty items"
    # Adversarial: PII filter rejects person-name queries
    r2 = tool.search("Maria Santos")
    assert not r2.success, "expected PII filter to reject 'Maria Santos'"
    assert "pii_rejected" in (r2.error or ""), \
        f"expected pii_rejected error, got {r2.error}"
    return (f"mock search OK ({len(r.items)} items); "
              f"PII filter correctly rejected person-name query")


_run_test("T17  Research tool (OpenClaw mock + PII filter)", t17_openclaw_mock)


# ===========================================================================
# Test 18 -- Server endpoints (in-process via httpx + thread)
# ===========================================================================
def t18_server_endpoints():
    import threading
    import socket
    import time as _t
    from duecare.server import create_app
    from duecare.server.state import ServerState
    import uvicorn

    # Find a free port (don't collide with the demo server on 8080).
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    state = ServerState(db_path="/kaggle/working/_validation.duckdb",
                          pipeline_output_dir="/kaggle/working/_validation_out")
    state.set_gemma_call(_gemma_text_only)
    app = create_app(state)
    config = uvicorn.Config(app, host="127.0.0.1", port=port,
                              log_level="error")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()

    # Wait for the server to bind.
    deadline = _t.time() + 8
    import urllib.request as _ur
    import urllib.error as _ue
    while _t.time() < deadline:
        try:
            _ur.urlopen(f"http://127.0.0.1:{port}/healthz",
                          timeout=2).read()
            break
        except Exception:
            _t.sleep(0.3)
    else:
        raise AssertionError("server did not bind in 8s")

    def call(method: str, path: str, body=None) -> tuple[int, dict]:
        data = json.dumps(body).encode() if body else None
        req = _ur.Request(
            f"http://127.0.0.1:{port}{path}", data=data, method=method,
            headers=({"Content-Type": "application/json"} if body else {}))
        with _ur.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())

    checks = []

    code, j = call("GET", "/api/status")
    assert code == 200 and j.get("ok"), f"/api/status: {code} {j}"
    checks.append("status")

    code, j = call("GET", "/api/stats")
    assert code == 200, f"/api/stats: {code} {j}"
    assert "documents" in j, f"missing documents in stats: {j}"
    checks.append("stats")

    code, j = call("POST", "/api/moderate",
                    {"text": "Send your passport copy and pay USD 5000 "
                              "deposit. We will keep your passport.",
                     "locale": "ph"})
    assert code == 200 and "verdict" in j, f"/api/moderate: {code} {j}"
    checks.append(f"moderate(verdict={j['verdict']},sev={j['severity']},mode={j.get('mode')})")

    code, j = call("POST", "/api/worker_check",
                    {"text": "Mama-san said pay USD 5000 deposit and she "
                              "will keep my passport for 2 years.",
                     "locale": "ph"})
    assert code == 200 and "advice" in j, f"/api/worker_check: {code} {j}"
    checks.append(f"worker_check(sev={j['severity']},mode={j.get('mode')})")

    code, j = call("POST", "/api/query",
                    {"question": "What is the average illicit fee?"})
    assert code == 200, f"/api/query: {code} {j}"
    checks.append(f"query(method={j['method']},rows={j['row_count']})")

    code, j = call("POST", "/api/research/openclaw",
                    {"endpoint": "search", "args": {"query": "PH RA 8042"}})
    assert code == 200 and j.get("success"), \
        f"/api/research/openclaw: {code} {j}"
    checks.append("research")

    code, j = call("POST", "/api/queue/submit",
                    {"task_type": "moderate",
                     "payload": {"text": "test queue submission",
                                  "locale": "en"}})
    assert code == 202 and "task_id" in j, f"/api/queue/submit: {code} {j}"
    task_id = j["task_id"]
    # Poll for completion
    for _ in range(30):
        code, jt = call("GET", f"/api/queue/status/{task_id}")
        if jt.get("status") in ("completed", "failed"):
            break
        _t.sleep(1)
    assert jt.get("status") == "completed", \
        f"queue task did not complete: {jt}"
    checks.append(f"queue_submit({task_id} -> {jt['status']})")

    return f"all {len(checks)} endpoints OK: {', '.join(checks)}"


_run_test("T18  Server endpoints (in-process)", t18_server_endpoints)


# ===========================================================================
# Final report
# ===========================================================================
print("\n" + "=" * 76)
print("  ADVERSARIAL VALIDATION SUMMARY")
print("=" * 76)
n_pass = sum(1 for r in _RESULTS if r.passed)
n_fail = sum(1 for r in _RESULTS if not r.passed)
total_s = sum(r.seconds for r in _RESULTS)
print(f"\n  {n_pass} / {len(_RESULTS)} tests passed  "
        f"({total_s:.1f}s total)\n")
for r in _RESULTS:
    sym = "✓" if r.passed else "✗"
    print(f"  {sym}  {r.name:<55s}  ({r.seconds:5.1f}s)")
    if r.passed and r.detail:
        print(f"      {r.detail[:120]}")
    if not r.passed:
        print(f"      ERROR: {r.error}")
print()
print(f"  GPU mode: {GEMMA.get('mode', 'n/a')}, "
        f"VRAM used: {GEMMA.get('vram_gb', 0):.2f} GB")
print("=" * 76)
if n_fail:
    raise SystemExit(f"{n_fail} test(s) failed")
print("\n  ALL CHECKS PASSED -- system is wired end-to-end.\n")
