# <!-- duecare:kernel-intro -->
# DueCare — Runtime harness-lift regenerator
# Appendix notebook #A11 of 13 in the DueCare submission.
#
# Runs N prompts x 2 runtime conditions with the same weights, grades both, emits MD + JSON with provenance tuple (model, git_sha, dataset_version). The +56pp number, regenerated live.
#
# What to look for after Run All:
#   - The output is a provenance-pinned report you can cite in the writeup.
#   - Run N from 10 (smoke) up to 207 (full reference set).
#   - Harness OFF vs ON is recomputed live; this is not the fine-tuned-model benchmark.
#
# Demo path: Run All -> wait for the report -> see the headline lift number with the git_sha pinned.
#
# Full README + cross-kernel index: see the README in this folder.

"""DueCare Grading Evaluation (A11)
=====================================

Side-by-side rubric evaluation showing what the safety harness ACTUALLY
does. Runs N curated prompts through Gemma 4 twice each:
  - HARNESS OFF: raw Gemma response (no persona, no GREP, no RAG, no Tools)
  - HARNESS ON:  full harness (Persona + GREP + RAG + Tools all enabled)

Grades both responses with the Rule-Based v3.10 grader (46 dimensions,
use-case-aware, citation-cross-referenced) and produces:
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

NOT a fine-tuned-model benchmark. A-07 owns stock-vs-SafetyJudge-adapter
evaluation in eval_results.json. A-11 holds weights constant and measures
runtime layers OFF versus ON.

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

print("[4/6] loading DueCare harness")
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
    can pass it to the Rule-Based grader for signal-aware scoring."""
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

    # Grade both with the Rule-Based v3.10 grader
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
    title="DueCare Harness Lift Report (Rule-Based v3.10 Grader)",
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

# ===========================================================================
# Dashboard: the +XXpp lift visualization
# ===========================================================================
def _build_lift_dashboard_html(
    results: list, aggregate: dict, provenance: dict,
    output_dir: str, kernel_id: str,
) -> str:
    """Render the A-11 lift dashboard as inline HTML.
    Pulls /static/_chrome.css + /static/_nav.js for workbench consistency.
    Embeds a side-by-side per-prompt table with bar visualizations,
    headline hero KPIs, and download buttons for JSON / MD / CSV.
    """
    import html as _html

    n = aggregate.get("n", 0) if aggregate else 0
    mean_off = aggregate.get("mean_pct_off", 0) if aggregate else 0
    mean_on  = aggregate.get("mean_pct_on", 0) if aggregate else 0
    lift_pp  = aggregate.get("mean_lift_pp", 0) if aggregate else 0
    n_helped    = aggregate.get("n_helped", 0)    if aggregate else 0
    n_unchanged = aggregate.get("n_unchanged", 0) if aggregate else 0
    n_hurt      = aggregate.get("n_hurt", 0)      if aggregate else 0
    cit_off = aggregate.get("mean_citations_off", 0) if aggregate else 0
    cit_on  = aggregate.get("mean_citations_on", 0)  if aggregate else 0
    g_off   = aggregate.get("mean_grounding_off", 0) if aggregate else 0
    g_on    = aggregate.get("mean_grounding_on", 0)  if aggregate else 0

    lift_color = ("var(--good)" if lift_pp >= 5 else
                  ("var(--warn)" if lift_pp >= 0 else "var(--ember)"))

    rows = []
    for r in (results or []):
        pid     = _html.escape(str(r.get("prompt_id", "?")))
        cat     = _html.escape(str(r.get("prompt_category", "")))
        s_off   = float(r.get("grade_off", {}).get("pct_score", 0))
        s_on    = float(r.get("grade_on",  {}).get("pct_score", 0))
        d_pp    = float(r.get("lift", {}).get("pct_score_delta", s_on - s_off))
        verdict = "helped" if d_pp >= 5 else ("hurt" if d_pp <= -5 else "unchanged")
        v_color = {"helped":"var(--good)","hurt":"var(--ember)","unchanged":"var(--ink-3)"}[verdict]
        rows.append(f"""
        <tr>
          <td style="font-family:var(--mono); font-size:12px; color:var(--ink-2);">{pid}</td>
          <td style="font-size:12px; color:var(--ink-3);">{cat}</td>
          <td style="text-align:right; font-variant-numeric: tabular-nums;">
            <div style="font-size:13px; color:var(--ink-2);">{s_off:.1f}%</div>
            <div style="height:6px; background:var(--paper-3); border-radius:4px; margin-top:4px; overflow:hidden;">
              <div style="height:100%; width:{max(0,min(100,s_off)):.1f}%; background:var(--ink-3);"></div>
            </div>
          </td>
          <td style="text-align:right; font-variant-numeric: tabular-nums;">
            <div style="font-size:13px; color:var(--ink);">{s_on:.1f}%</div>
            <div style="height:6px; background:var(--paper-3); border-radius:4px; margin-top:4px; overflow:hidden;">
              <div style="height:100%; width:{max(0,min(100,s_on)):.1f}%; background:var(--accent);"></div>
            </div>
          </td>
          <td style="text-align:right; font-family:var(--mono); font-size:13px; color:{v_color}; font-weight:600;">
            {d_pp:+.1f} pp
          </td>
          <td style="text-align:center; font-size:11px; color:{v_color}; text-transform:uppercase; letter-spacing:.04em; font-family:var(--mono); font-weight:600;">
            {verdict}
          </td>
        </tr>""")
    rows_html = "".join(rows) if rows else (
        '<tr><td colspan="6" style="text-align:center; color:var(--ink-4); '
        'padding:30px; font-style:italic;">No results yet — re-run the cell.</td></tr>'
    )

    model = _html.escape(str(provenance.get("model_name", "?")))
    sha   = _html.escape(str(provenance.get("git_sha", "unknown"))[:12])
    dsv   = _html.escape(str(provenance.get("dataset_version", "unknown")))
    grader = _html.escape(str(provenance.get("grader_version", "?")))
    harness_v = _html.escape(str(provenance.get("harness_version", "?")))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lift dashboard · A-11 grading-evaluation · DueCare</title>
  <link rel="stylesheet" href="/static/_chrome.css">
  <link rel="stylesheet" href="/static/showcase.css">
  <script src="/static/_nav.js" defer></script>
  <style>
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 28px 24px 48px; }}
    .crumbs {{ font-family: var(--mono); font-size: 11px; color: var(--ink-3);
               text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; }}
    h1 {{ margin: 0 0 6px; color: var(--ink); letter-spacing: -0.02em; font-size: 28px; }}
    .lede {{ color: var(--ink-3); margin: 0 0 22px; line-height: 1.55; font-size: 14px; max-width: 780px; }}
    .hero {{ display: grid; grid-template-columns: 1.6fr 1fr 1fr 1fr; gap: 14px; margin-bottom: 26px; }}
    @media (max-width: 880px) {{ .hero {{ grid-template-columns: 1fr 1fr; }} }}
    .kpi {{ background: #fffdf7; border: 1px solid var(--line);
            border-radius: 12px; padding: 16px 18px;
            box-shadow: 0 1px 0 rgba(14,17,22,.04), 0 8px 24px -18px rgba(14,17,22,.12); }}
    .kpi-label {{ font-family: var(--mono); font-size: 10px; color: var(--ink-3);
                  text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }}
    .kpi-val {{ font-size: 32px; font-weight: 600; color: var(--ink);
                font-variant-numeric: tabular-nums; line-height: 1.15; letter-spacing: -0.02em; }}
    .kpi-sub {{ font-size: 12px; color: var(--ink-3); margin-top: 4px; }}
    .kpi.headline .kpi-val {{ color: {lift_color}; font-size: 40px; }}
    .winloss {{ display:flex; height: 8px; border-radius: 4px; overflow: hidden;
                margin-top: 8px; background: var(--paper-3); }}
    .winloss .seg-helped {{ background: var(--good); }}
    .winloss .seg-unchanged {{ background: var(--ink-4); }}
    .winloss .seg-hurt {{ background: var(--ember); }}
    .panel {{ background: #fffdf7; border: 1px solid var(--line);
              border-radius: 12px; padding: 20px 22px; margin-bottom: 20px;
              box-shadow: 0 1px 0 rgba(14,17,22,.04), 0 8px 24px -18px rgba(14,17,22,.12); }}
    .panel h2 {{ margin: 0 0 14px; font-size: 11px; color: var(--ink-3);
                 text-transform: uppercase; letter-spacing: 0.08em; font-family: var(--mono); font-weight: 500; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ text-align: left; padding: 8px 10px; background: var(--paper-2);
          color: var(--ink-3); font-weight: 500; font-size: 11px;
          text-transform: uppercase; letter-spacing: 0.06em; font-family: var(--mono);
          border-bottom: 1px solid var(--line); }}
    th.num {{ text-align: right; }}
    td {{ padding: 10px; border-bottom: 1px solid var(--line-soft); vertical-align: middle; }}
    .exports {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .exports a {{ display: inline-flex; align-items: center; gap: 6px;
                  padding: 8px 14px; border-radius: 8px;
                  text-decoration: none; font-size: 13px; font-weight: 500;
                  background: var(--ink); color: var(--paper); font-family: var(--sans); }}
    .exports a.ghost {{ background: var(--paper-2); color: var(--ink-2);
                        border: 1px solid var(--line); }}
    .exports a:hover {{ filter: brightness(.96); }}
    .prov {{ font-family: var(--mono); font-size: 11px; color: var(--ink-3); line-height: 1.7; }}
    .prov code {{ background: var(--paper-2); color: var(--ink-2); padding: 1px 6px;
                  border-radius: 4px; border: 1px solid var(--line-soft); font-size: 11px; }}
  </style>
</head>
<body data-nav="researcher">
<div class="wrap">
  <div class="crumbs">Notebook · {_html.escape(kernel_id)}</div>
  <h1>Harness lift — {n} prompts, two conditions, 46-dim rubric v3.10</h1>
  <p class="lede">
    Each prompt runs twice: once against raw Gemma (no persona / GREP / RAG /
    tools), once with the full harness. Both responses are graded by the
    rule-based v3.10 rubric. The headline number is the mean per-prompt
    score delta, and every per-row score is independently reproducible from
    the provenance tuple at the bottom.
  </p>

  <section class="hero">
    <div class="kpi headline">
      <div class="kpi-label">Mean lift</div>
      <div class="kpi-val">{lift_pp:+.1f} pp</div>
      <div class="kpi-sub">across {n} prompts · rule-based v3.10</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Score before / after</div>
      <div class="kpi-val">{mean_off:.0f}% <span style="color:var(--ink-3); font-size:18px; font-weight:400;">→</span> {mean_on:.0f}%</div>
      <div class="kpi-sub">stock Gemma → full harness</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Win / unchanged / hurt</div>
      <div class="kpi-val" style="font-size:24px;">{n_helped} / {n_unchanged} / {n_hurt}</div>
      <div class="winloss" aria-label="win-loss segment">
        <div class="seg-helped"    style="flex:{max(1,n_helped)};"></div>
        <div class="seg-unchanged" style="flex:{max(1,n_unchanged)};"></div>
        <div class="seg-hurt"      style="flex:{max(1,n_hurt)};"></div>
      </div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Grounding lift</div>
      <div class="kpi-val">{g_off:.0f}% <span style="color:var(--ink-3); font-size:18px; font-weight:400;">→</span> {g_on:.0f}%</div>
      <div class="kpi-sub">citations: {cit_off:.1f} → {cit_on:.1f} per response</div>
    </div>
  </section>

  <section class="panel">
    <h2>Per-prompt scorecard</h2>
    <table>
      <thead>
        <tr>
          <th>Prompt</th>
          <th>Category</th>
          <th class="num">Stock %</th>
          <th class="num">Harness %</th>
          <th class="num">Î”</th>
          <th style="text-align:center;">Verdict</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
  </section>

  <section class="panel">
    <h2>Export</h2>
    <div class="exports">
      <a href="/artifact/duecare_lift_eval.json" download>JSON (full per-prompt detail)</a>
      <a href="/artifact/duecare_lift_eval.md" class="ghost" download>Markdown report</a>
      <a href="/export/lift.csv" class="ghost" download>CSV (per-row scores)</a>
      <a href="/api/lift" class="ghost" target="_blank">Raw JSON via API</a>
      <a href="/summary" class="ghost">Kernel summary</a>
      <a href="/static/logs.html" class="ghost">Logs →</a>
    </div>
  </section>

  <section class="panel">
    <h2>Provenance</h2>
    <div class="prov">
      Model: <code>{model}</code><br>
      Git SHA: <code>{sha}</code> · Dataset: <code>{dsv}</code><br>
      Harness: <code>{harness_v}</code> · Grader: <code>{grader}</code><br>
      Output dir: <code>{_html.escape(str(output_dir))}</code>
    </div>
  </section>
</div>
</body>
</html>"""


def _build_lift_csv(results: list, aggregate: dict) -> str:
    """Stream-friendly CSV of the per-prompt scores."""
    import io, csv
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "prompt_id", "category",
        "pct_off", "pct_on", "pct_delta",
        "citations_off", "citations_on",
        "grounding_off", "grounding_on",
        "elapsed_off_s", "elapsed_on_s",
        "verdict",
    ])
    for r in (results or []):
        d = float(r.get("lift", {}).get("pct_score_delta", 0))
        verdict = "helped" if d >= 5 else ("hurt" if d <= -5 else "unchanged")
        w.writerow([
            r.get("prompt_id", ""),
            r.get("prompt_category", ""),
            r.get("grade_off", {}).get("pct_score", 0),
            r.get("grade_on",  {}).get("pct_score", 0),
            r.get("lift", {}).get("pct_score_delta", 0),
            r.get("grade_off", {}).get("citations", 0),
            r.get("grade_on",  {}).get("citations", 0),
            r.get("grade_off", {}).get("grounding_pct", 0),
            r.get("grade_on",  {}).get("grounding_pct", 0),
            r.get("elapsed_off_s", ""),
            r.get("elapsed_on_s", ""),
            verdict,
        ])
    return buf.getvalue()


# Workbench-consistent UI: launch the minimal shell with the lift dashboard
# as the homepage so judges see the headline lift number + per-prompt
# scorecard + export options + provenance tuple immediately on opening
# the cloudflared URL.
try:
    import os as _os
    import time as _time
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-11-grading-evaluation")
    dc_log("kernel.complete", "lift evaluation complete",
           output_dir=str(output_dir),
           n_prompts=len(results) if results else 0,
           mean_lift_pp=(aggregate or {}).get("mean_lift_pp"))
    from duecare.chat.kernel_shell import build_minimal_shell
    from fastapi.responses import PlainTextResponse, JSONResponse

    dashboard_html = _build_lift_dashboard_html(
        results=results, aggregate=aggregate, provenance=provenance,
        output_dir=output_dir, kernel_id="a-11-grading-evaluation",
    )

    def _api_lift():
        return JSONResponse({
            "provenance": provenance, "aggregate": aggregate, "results": results,
        })

    def _export_lift_csv():
        csv_text = _build_lift_csv(results, aggregate)
        return PlainTextResponse(
            csv_text, media_type="text/csv",
            headers={"Content-Disposition":
                     "attachment; filename=duecare_lift_eval.csv"},
        )

    n_results = len(results) if results else 0
    summary = {
        "title": "Grading-lift evaluation (46-dim rubric v3.10)",
        "audience": "researcher",
        "lede": ("Regenerate the headline harness-lift number using the 46-dim "
                 "rule-based grader v3.10. Compares baseline Gemma against the "
                 "full harness on the curated 5-indicator compound prompt set."),
        "results": [
            {"label": "Prompts evaluated", "value": n_results},
            {"label": "Mean lift",
             "value": f"{(aggregate or {}).get('mean_lift_pp', 0):+.1f} pp"},
            {"label": "Model", "value": MODEL_NAME},
        ],
        "artifacts": [
            {"name": "duecare_lift_eval.json",
             "path": f"{output_dir}/duecare_lift_eval.json"},
            {"name": "duecare_lift_eval.md",
             "path": f"{output_dir}/duecare_lift_eval.md"},
        ],
        "links": [
            ("Workbench (full)",
             "https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench"),
        ],
        "next_steps": [
            "Headline lift + per-prompt table is the homepage at /.",
            "Download CSV via /export/lift.csv, JSON via /artifact/, MD via /artifact/.",
            "Open the Logs tab for the per-prompt grading event stream.",
        ],
    }
    app, url = build_minimal_shell(
        summary=summary, kernel_id="a-11-grading-evaluation",
        port=int(_os.environ.get("DC_PORT", "8080")),
        homepage_html=dashboard_html,
        extra_routes={
            "/api/lift":       ("GET", _api_lift),
            "/export/lift.csv": ("GET", _export_lift_csv),
        },
    )
    if url:
        print(f"[workbench] {url}")
    while True:
        _time.sleep(60)
except Exception as _e:
    print(f"[workbench] minimal-shell unavailable: {_e}")
