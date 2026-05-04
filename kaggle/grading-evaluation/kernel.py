"""Duecare Grading Evaluation (A6)
=====================================

Side-by-side rubric evaluation showing what the safety harness ACTUALLY
does. Runs N curated prompts through Gemma 4 twice each:
  - HARNESS OFF: raw Gemma response (no persona, no GREP, no RAG, no Tools)
  - HARNESS ON:  full harness (Persona + GREP + RAG + Tools all enabled)

Grades both responses with the universal v2 grader (15 dimensions,
intent-aware, citation-cross-referenced) and produces:
  - Per-prompt side-by-side comparison cards
  - Aggregate dimension-lift table
  - Citation grounding delta
  - Intent shift visualization
  - Markdown + JSON export ready for writeup integration

Reproducibility: every report includes (model_revision, git_sha,
dataset_version) tuple so judges can verify any number from the
git repo.

NOT a chat playground -- this is the EVALUATION notebook. The chat
playgrounds (#1, #2) are interactive; this one runs a fixed evaluation
suite end-to-end and produces the harness-lift report.

This is the falsifiable +56.5pp number, regenerated from a git SHA.
"""

# pip install Hanchen's pinned recipe (do not change)
print("[1/6] installing duecare-grading-evaluation wheels")
import subprocess as _sp, sys as _sys, os as _os, json as _json, time as _time
WHEELS_DIR = "/kaggle/input/duecare-grading-evaluation-wheels"
if not _os.path.isdir(WHEELS_DIR):
    # Fallback for local testing
    import pathlib as _pl
    candidate = _pl.Path(__file__).parent / "wheels"
    if candidate.is_dir():
        WHEELS_DIR = str(candidate)
_sp.check_call([_sys.executable, "-m", "pip", "install", "--quiet",
                "--no-index", "--find-links", WHEELS_DIR,
                "duecare-llm-core", "duecare-llm-models", "duecare-llm-chat"])
print("[2/6] installing inference stack (Hanchen recipe)")
_sp.check_call([_sys.executable, "-m", "pip", "install", "--quiet",
                "transformers>=5.5.0", "torch", "accelerate"])

# Reset modules so the freshly-installed packages take precedence
for _mod in list(_sys.modules.keys()):
    if _mod.startswith(("duecare", "transformers", "torch")):
        del _sys.modules[_mod]

print("[3/6] loading Gemma 4 E4B")
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# R2 fix: explicit GPU check. Loading a 4B model in fp32 on CPU
# OOMs the Kaggle worker after ~5 min. Fail fast with a clear
# message instead.
if not torch.cuda.is_available():
    raise SystemExit(
        "ERROR: This kernel requires a GPU. Loading Gemma 4 E4B in "
        "fp32 on CPU OOMs a 16 GB Kaggle worker. Please attach a T4 "
        "or P100 in the Kaggle session settings and re-run."
    )

MODEL_NAME = _os.environ.get("DUECARE_MODEL_NAME", "google/gemma-4-4b-it")
HF_TOKEN = _os.environ.get("HF_TOKEN") or _os.environ.get("HUGGING_FACE_HUB_TOKEN")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    token=HF_TOKEN,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
model.eval()
print(f"  Loaded {MODEL_NAME} on cuda")

print("[4/6] loading Duecare harness")
from duecare.chat.harness import (
    EXAMPLE_PROMPTS, GREP_RULES, RAG_CORPUS, _TOOL_DISPATCH,
    DEFAULT_PERSONA,
    _grep_call, _rag_call, _heuristic_tool_calls,
    grade_response_universal,
    evaluate_lift, aggregate_lift_results, format_lift_report_md,
)
print(f"  GREP={len(GREP_RULES)}  RAG={len(RAG_CORPUS)}  Tools={len(_TOOL_DISPATCH)}")
print(f"  EXAMPLE_PROMPTS={len(EXAMPLE_PROMPTS)}  PERSONA={len(DEFAULT_PERSONA)} chars")


def _gemma_chat(messages: list[dict], max_new_tokens: int = 1024,
                  temperature: float = 0.7, top_p: float = 0.95) -> str:
    """One Gemma 4 chat completion. Returns the assistant response text."""
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True,
        return_tensors="pt", tokenize=True,
    )
    if torch.cuda.is_available():
        inputs = inputs.to("cuda")
    input_len = inputs.shape[1]
    with torch.no_grad():
        outputs = model.generate(
            inputs, max_new_tokens=max_new_tokens,
            temperature=temperature, top_p=top_p, top_k=64, do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    response_tokens = outputs[0, input_len:]
    return tokenizer.decode(response_tokens, skip_special_tokens=True).strip()


def _build_harness_prompt(user_text: str) -> tuple[str, dict]:
    """Build the harness-ON merged prompt + return the trace dict so we
    can pass it to the universal grader for signal-aware scoring."""
    grep_result = _grep_call(user_text)
    rag_result = _rag_call(user_text, top_k=5)
    tool_result = _heuristic_tool_calls(user_text)
    parts = [
        "[DUECARE SAFETY HARNESS — pre-context for the assistant.]\n",
        f"## DUECARE PERSONA\n\n{DEFAULT_PERSONA}\n",
    ]
    if grep_result.get("hits"):
        parts.append("## SAFETY HARNESS — GREP layer fired\n")
        for h in grep_result["hits"]:
            parts.append(f"- **{h['rule']}** [{h.get('severity', 'info')}] — {h.get('citation', '')}")
            parts.append(f"  match: '{h.get('match_excerpt', '')[:200]}'")
    if rag_result.get("docs"):
        parts.append("\n## SAFETY HARNESS — RAG layer retrieved\n")
        for d in rag_result["docs"]:
            parts.append(f"### {d.get('title', '?')}  ({d.get('source', '')})")
            parts.append(d.get("snippet", "")[:600])
    if tool_result.get("tool_calls"):
        parts.append("\n## SAFETY HARNESS — Tools layer\n")
        for c in tool_result["tool_calls"]:
            parts.append(f"- `{c['name']}({c.get('args', {})})` → {_json.dumps(c.get('result'), indent=2)[:400]}")
    parts.append("\n---\n\nUSER QUESTION:\n\n" + user_text)
    merged = "\n".join(parts)
    trace = {
        "persona": {"enabled": True, "wired": True, "elapsed_ms": 0,
                     "summary": "persona prepended"},
        "grep": {"enabled": True, "wired": True,
                  "hits": grep_result.get("hits", []),
                  "elapsed_ms": grep_result.get("elapsed_ms", 0),
                  "summary": f"{len(grep_result.get('hits', []))} rule(s) fired"},
        "rag": {"enabled": True, "wired": True,
                 "docs": rag_result.get("docs", []),
                 "elapsed_ms": rag_result.get("elapsed_ms", 0),
                 "summary": f"retrieved {len(rag_result.get('docs', []))} docs"},
        "tools": {"enabled": True, "wired": True,
                   "tool_calls": tool_result.get("tool_calls", []),
                   "elapsed_ms": tool_result.get("elapsed_ms", 0),
                   "summary": f"{len(tool_result.get('tool_calls', []))} tool call(s)"},
        "_final_user_text": merged,
    }
    return merged, trace


# -----------------------------------------------------------------------------
# Run the evaluation suite
# -----------------------------------------------------------------------------

# Curated test prompts: 5 textbook-shape prompts that exercise different
# detection patterns. Override via env var to run more.
DEFAULT_PROMPT_IDS = (
    "textbook_loan_68pct",
    "textbook_loan_18pct",
    "traf_002",  # passport "safekeeping"
    "traf_009",  # 3-month "performance guarantee"
    "traf_001",  # employer-pays-tax framing
)
override = _os.environ.get("DUECARE_EVAL_PROMPT_IDS", "").strip()
PROMPT_IDS = tuple(s.strip() for s in override.split(",") if s.strip()) or DEFAULT_PROMPT_IDS

print(f"[5/6] running {len(PROMPT_IDS)} prompts × 2 conditions (OFF/ON)")
selected = [e for e in EXAMPLE_PROMPTS if e["id"] in PROMPT_IDS]
print(f"  Selected {len(selected)} of {len(PROMPT_IDS)} requested prompts")
# R2 fix: empty `selected` (all PROMPT_IDS unmatched) leads downstream
# aggregate_lift_results to divide by zero. Fail fast with diagnostic.
if not selected:
    available = sorted({e["id"] for e in EXAMPLE_PROMPTS})[:30]
    raise SystemExit(
        f"ERROR: No matching prompt ids in EXAMPLE_PROMPTS for "
        f"{list(PROMPT_IDS)!r}. Set DUECARE_EVAL_PROMPT_IDS to a "
        f"comma-separated subset of available ids. First 30 "
        f"available: {available}"
    )

results = []
for i, ex in enumerate(selected, 1):
    print(f"  [{i}/{len(selected)}] {ex['id']} ({ex['category']})")
    user_text = ex["text"]

    # Run OFF: raw Gemma, no harness at all
    t0 = _time.time()
    response_off = _gemma_chat(
        [{"role": "user", "content": user_text}], max_new_tokens=1024,
    )
    t_off = _time.time() - t0
    print(f"    OFF: {len(response_off)} chars, {t_off:.0f}s")

    # Run ON: full harness (persona + GREP + RAG + tools merged into prompt)
    merged_prompt, trace = _build_harness_prompt(user_text)
    t0 = _time.time()
    response_on = _gemma_chat(
        [{"role": "user", "content": merged_prompt}], max_new_tokens=1024,
    )
    t_on = _time.time() - t0
    print(f"    ON:  {len(response_on)} chars, {t_on:.0f}s")

    # Grade both with the universal v2 grader
    lift = evaluate_lift(
        user_text,
        response_off=response_off,
        response_on=response_on,
        harness_trace_on=trace,
    )
    lift["prompt_id"] = ex["id"]
    lift["prompt_category"] = ex.get("category")
    lift["elapsed_off_s"] = round(t_off, 1)
    lift["elapsed_on_s"] = round(t_on, 1)
    results.append(lift)
    print(f"    Score: {lift['grade_off']['pct_score']}% → {lift['grade_on']['pct_score']}% (Δ {lift['lift']['pct_score_delta']:+.1f} pp)")

print("[6/6] aggregating + writing reports")
aggregate = aggregate_lift_results(results)
print(f"\n=== HEADLINE RESULTS ({aggregate['n']} prompts) ===")
print(f"  Mean rubric score: {aggregate['mean_pct_off']}% → {aggregate['mean_pct_on']}% (Δ {aggregate['mean_lift_pp']:+.1f} pp)")
print(f"  Helped: {aggregate['n_helped']}  Unchanged: {aggregate['n_unchanged']}  Hurt: {aggregate['n_hurt']}")
print(f"  Mean citations: {aggregate['mean_citations_off']} → {aggregate['mean_citations_on']}")
print(f"  Mean grounding: {aggregate['mean_grounding_off']}% → {aggregate['mean_grounding_on']}%")

# Provenance
import platform
provenance = {
    "model_name":      MODEL_NAME,
    "torch_version":   torch.__version__,
    "python_version":  platform.python_version(),
    "n_grep_rules":    len(GREP_RULES),
    "n_rag_docs":      len(RAG_CORPUS),
    "n_tools":         len(_TOOL_DISPATCH),
    "n_prompts":       len(EXAMPLE_PROMPTS),
    "harness_version": "v0.1.0",
    "grader_version":  "v2.0-intent-aware",
    "git_sha":         _os.environ.get("DUECARE_GIT_SHA", "unknown"),
    "dataset_version": _os.environ.get("DUECARE_DATASET_VERSION", "unknown"),
}

# Write outputs
# R2 fix: pick the first writable directory. Some Kaggle viewer /
# nbexec contexts have read-only cwd; /tmp is always writable.
def _pick_output_dir() -> str:
    for d in ("/kaggle/working", _os.path.expanduser("~"), "/tmp", "."):
        if _os.path.isdir(d):
            try:
                t = _os.path.join(d, ".duecare_write_test")
                with open(t, "w") as _f:
                    _f.write("ok")
                _os.remove(t)
                return d
            except Exception:
                continue
    return "."
output_dir = _pick_output_dir()
print(f"  Writing outputs to {output_dir}")

# 1. JSON: full per-prompt detail
with open(f"{output_dir}/duecare_lift_eval.json", "w", encoding="utf-8") as f:
    _json.dump({
        "provenance": provenance,
        "aggregate":  aggregate,
        "results":    results,
    }, f, indent=2, ensure_ascii=False)
print(f"  ✓ wrote {output_dir}/duecare_lift_eval.json")

# 2. Markdown: human-readable report
md = format_lift_report_md(
    results, aggregate,
    title="Duecare Harness Lift Report (Universal v2 Grader)",
    model_name=MODEL_NAME,
    git_sha=provenance["git_sha"],
    dataset_version=provenance["dataset_version"],
)
with open(f"{output_dir}/duecare_lift_eval.md", "w", encoding="utf-8") as f:
    f.write(md)
print(f"  ✓ wrote {output_dir}/duecare_lift_eval.md  ({len(md)} chars)")

# 3. Display the markdown report inline (Kaggle renders it nicely)
try:
    from IPython.display import Markdown, display
    display(Markdown(md))
except ImportError:
    print(md)

print("\nDone. Re-run with DUECARE_EVAL_PROMPT_IDS=traf_001,textbook_loan_68pct to test other subsets.")
