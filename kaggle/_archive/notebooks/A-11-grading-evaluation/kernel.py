# <!-- duecare:kernel-intro -->
# DueCare — New-model lift comparison (upload A-06 + A-07 bundles)
# Appendix notebook #A11 of 24 in the DueCare submission.
#
# Upload the bundle.zip from A-06 (fine-tuned baseline) and the bundle.zip from
# A-07 (same model + harness). A-03 runs the universal v2 grader on every
# paired prompt and renders the side-by-side lift report.
#
# What to look for after Run All:
#   - Open the printed cloudflared URL; two upload widgets accept the ZIPs.
#   - Comparison runs on CPU; no Gemma load. Takes ~30s for 200 prompts.
#   - Plotly chart of per-dimension status change + downloadable JSON + MD.
#
# Demo path: Run All -> open URL -> drop both bundles -> Run Comparison -> read the lift.
#
# Full README + cross-kernel index: see the README in this folder.

"""
============================================================================
  DUECARE A-11 GRADING EVALUATION -- Kaggle notebook (single-cell paste)
============================================================================

  Per Taylor's 2026-05-11 experiment-ladder spec, A-03 is the upload +
  comparison stage of the appendix arc. It consumes two bundles produced
  by sibling kernels:

      A-06 bundle  (fine-tuned Gemma 4 (LoRA), harness OFF, same prompt subset)
      A-07 bundle  (fine-tuned Gemma 4 (LoRA), harness ON,  same prompt subset)

  ...and emits a side-by-side lift report using
  ``duecare.chat.harness.evaluate_lift`` (universal v2 grader,
  deterministic, no model load required).

  Bundle contract: see ``docs/appendix_artifact_schema.md`` (v1.0).

  Outputs to ``/kaggle/working``:
      ``<comparison_id>_compare.json``    -- full lift results + aggregate
      ``<comparison_id>_report.md``       -- judge-readable markdown
      ``<comparison_id>_lift_chart.html`` -- interactive Plotly chart

  Requirements:
    - GPU: NOT required (rule-based grader, pure CPU)
    - Internet: ON (GitHub install only; comparison runs offline once
      packages are present)
    - Wheels dataset: none (GitHub-only install per 2026-05-11 policy)
    - Bundles: produced by sibling A-06 and A-07 runs

  Expected runtime: ~30s install + ~10s per 100 prompts of grading.

  Built with Google's Gemma 4, used under the Apache License 2.0.
============================================================================
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
import time
import zipfile
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ===========================================================================
# CONFIG
# ===========================================================================
# DEPRECATED 2026-05-11 (GitHub-only): no wheel dataset attached.
PORT = 8080
TUNNEL = "cloudflared"

OUTPUT_DIR = Path("/kaggle/working")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# PHASE 1 -- install DueCare from GitHub (no Kaggle wheel datasets)
# ===========================================================================
# Policy 2026-05-11: all DueCare packages install directly from GitHub.
# Two-tier strategy:
#   1. GitHub Release wheels at /releases/download/v{VERSION}/
#   2. GitHub source install via git+https://...@<sha>#subdirectory=...
DUECARE_VERSION    = os.environ.get("DUECARE_VERSION", "0.17.0")
DUECARE_REPO       = "TaylorAmarelTech/gemma4_comp"
DUECARE_COMMIT_SHA = "master"
DUECARE_PACKAGES   = ["duecare-llm-chat"]   # pulls in core for harness data


def install_duecare_from_github() -> bool:
    """Install DueCare packages from GitHub. Wheels-free, judge-transparent.
    Tier 1: GitHub Release wheels. Tier 2: git+https source-install.
    """
    print("=" * 76)
    print("[install] DueCare packages from GitHub (no Kaggle wheel datasets)")
    print("=" * 76)
    base_url = f"https://github.com/{DUECARE_REPO}/releases/download/v{DUECARE_VERSION}"
    success = 0
    for i, pkg in enumerate(DUECARE_PACKAGES, 1):
        wheel_name = f"{pkg.replace('-', '_')}-{DUECARE_VERSION}-py3-none-any.whl"
        url = f"{base_url}/{wheel_name}"
        print(f"  > [{i}/{len(DUECARE_PACKAGES)}] release wheel: {wheel_name}")
        cmd = [sys.executable, "-m", "pip", "install", "--no-input",
               "--disable-pip-version-check", "--timeout=60", url]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if proc.returncode == 0:
            success += 1
            print(f"  + installed {pkg} from release v{DUECARE_VERSION}")
        else:
            tail = (proc.stderr or "")[-200:]
            if "404" in tail or "Not Found" in tail:
                print(f"  - release wheel not found, falling back to source install")
                break
            print(f"  - {pkg} release wheel failed: {tail}")
    if success == len(DUECARE_PACKAGES):
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]
        return True
    git_pkgs = [
        f"git+https://github.com/{DUECARE_REPO}.git@{DUECARE_COMMIT_SHA}"
        f"#subdirectory=packages/{p}"
        for p in DUECARE_PACKAGES
    ]
    print(f"  > source install @ {DUECARE_COMMIT_SHA} ({len(git_pkgs)} pkg)")
    cmd = [sys.executable, "-m", "pip", "install", "--no-input",
           "--disable-pip-version-check", "--timeout=300", *git_pkgs]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
    if proc.returncode == 0:
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]
        print(f"  + source install ok @ {DUECARE_COMMIT_SHA}")
        return True
    raise SystemExit(
        f"DueCare GitHub install failed: {(proc.stderr or '')[-300:]}")


print("\n" + "=" * 76)
print("[1/4] installing DueCare from GitHub")
print("=" * 76)
install_duecare_from_github()
# Extra deps the comparison needs: plotly for charts + fastapi for the
# upload routes (fastapi is usually present on Kaggle but pin upgrade
# anyway).
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "plotly>=5.20.0", "fastapi>=0.115.0",
                  "uvicorn>=0.30.0", "python-multipart>=0.0.9"],
                  capture_output=True, text=True)


# ===========================================================================
# 2. Lazy imports (post-install)
# ===========================================================================
print("\n" + "=" * 76)
print("[2/4] importing duecare evaluator stack")
print("=" * 76)

from duecare.chat.harness import (
    evaluate_lift,
    aggregate_lift_results,
    format_lift_report_md,
)
import plotly.graph_objects as go
import plotly.io as pio

try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-08-new-model-comparison")
except Exception:
    def dc_log(*a, **kw): return None  # type: ignore[no-redef]
    def set_kernel_id(*a, **kw): return None  # type: ignore[no-redef]


# ===========================================================================
# 3. State + bundle parsing
# ===========================================================================
# A-03 keeps two parsed bundles in memory: "baseline" (from A-06) and
# "harness" (from A-07). Each is a parsed results.json dict per the v1.0
# schema. Comparison runs only when both slots are populated and the
# prompt_id sets match.
_SHUTDOWN_EVENT = threading.Event()
_CLOUDFLARED_PROC: dict = {"p": None}


@dataclass
class BundleState:
    """Holds a parsed v1.0 results bundle in memory."""
    filename: str = ""
    run_id: str = ""
    kernel_id: str = ""
    model_variant: str = ""
    model_kind: str = ""
    harness_enabled: bool = False
    n_results: int = 0
    parsed: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def loaded(self) -> bool:
        return self.error is None and self.n_results > 0


_BUNDLES: dict[str, BundleState] = {
    "baseline": BundleState(),
    "harness":  BundleState(),
}
_COMPARISON: dict = {
    "comparison_id": None,
    "results":       None,
    "aggregate":     None,
    "artifacts":     [],
    "warnings":      [],
    "error":         None,
    "completed_at":  None,
}


def parse_bundle_bytes(raw: bytes, filename: str) -> BundleState:
    """Parse a bundle. Accepts either a v1.0 results.json directly OR a
    v1.0 bundle.zip containing results.json + manifest.json."""
    state = BundleState(filename=filename)
    try:
        if filename.lower().endswith(".zip"):
            zf = zipfile.ZipFile(io.BytesIO(raw))
            names = set(zf.namelist())
            if "results.json" not in names:
                state.error = "bundle.zip missing results.json"
                return state
            results_raw = zf.read("results.json").decode("utf-8")
            parsed = json.loads(results_raw)
        else:
            parsed = json.loads(raw.decode("utf-8"))
        if parsed.get("schema_version") != "1.0":
            state.error = (f"unsupported schema_version "
                            f"{parsed.get('schema_version')!r}; expected 1.0")
            return state
        if "results" not in parsed or not isinstance(parsed["results"], list):
            state.error = "missing or malformed 'results' array"
            return state
        cfg = parsed.get("config", {}) or {}
        state.run_id          = parsed.get("run_id", "")
        state.kernel_id       = parsed.get("kernel_id", "")
        state.model_variant   = cfg.get("model_variant", "")
        state.model_kind      = cfg.get("model_kind", "")
        state.harness_enabled = bool(cfg.get("harness_enabled", False))
        state.n_results       = len(parsed["results"])
        state.parsed          = parsed
        return state
    except Exception as e:
        state.error = f"{type(e).__name__}: {str(e)[:200]}"
        return state


def _pair_bundles(baseline: BundleState, harness: BundleState
                    ) -> tuple[list[tuple[dict, dict]], list[str]]:
    """Pair rows by prompt_id. Returns (paired_list, warnings_list).
    Warnings include model_variant mismatch, missing prompt_ids on either
    side, and harness-enabled mismatches."""
    warnings: list[str] = []
    if baseline.model_variant and harness.model_variant and \
            baseline.model_variant != harness.model_variant:
        warnings.append(
            f"model_variant mismatch: baseline={baseline.model_variant} vs "
            f"harness={harness.model_variant}; comparison is invalid for "
            f"lift attribution (different model)")
    if baseline.harness_enabled:
        warnings.append("baseline bundle has harness_enabled=True; "
                          "expected the baseline run to be harness-OFF")
    if not harness.harness_enabled:
        warnings.append("harness bundle has harness_enabled=False; "
                          "expected the harness run to be harness-ON")
    by_pid_off = {r["prompt_id"]: r for r in baseline.parsed["results"]
                    if r.get("error") is None}
    by_pid_on  = {r["prompt_id"]: r for r in harness.parsed["results"]
                    if r.get("error") is None}
    only_off = sorted(by_pid_off.keys() - by_pid_on.keys())
    only_on  = sorted(by_pid_on.keys()  - by_pid_off.keys())
    if only_off:
        warnings.append(f"{len(only_off)} prompt_id(s) only in baseline "
                          f"(skipped): {only_off[:5]}")
    if only_on:
        warnings.append(f"{len(only_on)} prompt_id(s) only in harness "
                          f"(skipped): {only_on[:5]}")
    paired = [(by_pid_off[pid], by_pid_on[pid])
                for pid in sorted(by_pid_off.keys() & by_pid_on.keys())]
    return paired, warnings


_SAFE_VARIANT_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                            "0123456789-_")


def _safe_token(s: str, default: str = "unknown", max_len: int = 32) -> str:
    """Strip a user-supplied string to a filename-safe + URL-safe token.
    Defense in depth: any value pulled from the uploaded JSON that ends up
    in a filename or a URL path goes through this so an attacker cannot
    craft a bundle.zip whose model_variant breaks out of the comparison_id
    or smuggles HTML/JS through the artifact list."""
    if not s:
        return default
    out = "".join(c for c in s if c in _SAFE_VARIANT_CHARS)
    return (out[:max_len] or default)


def _comparison_id(baseline: BundleState, harness: BundleState) -> str:
    """Stable ID for the comparison artifact filenames. Sanitized so a
    user-supplied bundle cannot inject path / HTML into output names."""
    ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    raw_mv = baseline.model_variant or harness.model_variant or "unknown"
    mv = _safe_token(raw_mv)
    return f"a08_compare_{mv}_{ts}"


def run_comparison() -> dict:
    """Run evaluate_lift over every paired prompt_id. Idempotent: caller
    guards via the /api/run-comparison handler."""
    baseline = _BUNDLES["baseline"]
    harness  = _BUNDLES["harness"]
    if not (baseline.loaded and harness.loaded):
        return {"ok": False, "error": "both bundles must be loaded first"}
    paired, warnings = _pair_bundles(baseline, harness)
    if not paired:
        return {"ok": False, "error": "no overlapping prompt_ids in the "
                  "two bundles; comparison is impossible"}
    cid = _comparison_id(baseline, harness)
    dc_log("a08.compare.start", "lift comparison started",
            comparison_id=cid, n_pairs=len(paired))
    t0 = time.time()
    lift_results: list[dict] = []
    for idx, (row_off, row_on) in enumerate(paired, 1):
        try:
            lift = evaluate_lift(
                prompt_text=row_off.get("prompt_text", "")
                              or row_on.get("prompt_text", ""),
                response_off=row_off.get("response", ""),
                response_on=row_on.get("response", ""),
                harness_trace_on=row_on.get("harness_trace"),
            )
            lift["prompt_id"] = row_off["prompt_id"]
            lift["prompt_metadata"] = (row_off.get("prompt_metadata")
                                          or row_on.get("prompt_metadata", {}))
            lift_results.append(lift)
            if idx % 10 == 0:
                dc_log("a08.compare.progress", f"{idx}/{len(paired)} graded",
                        completed=idx, total=len(paired))
        except Exception as e:
            dc_log("a08.compare.error", "evaluate_lift failed",
                    level="error", prompt_id=row_off.get("prompt_id"),
                    err=str(e)[:200])
    elapsed = time.time() - t0
    aggregate = aggregate_lift_results(lift_results)
    # Emit artifacts.
    compare_path = OUTPUT_DIR / f"{cid}_compare.json"
    report_path  = OUTPUT_DIR / f"{cid}_report.md"
    chart_path   = OUTPUT_DIR / f"{cid}_lift_chart.html"
    compare_payload = {
        "schema_version": "1.0",
        "kernel_id":      "a-08-new-model-comparison",
        "comparison_id":  cid,
        "baseline_run_id":  baseline.run_id,
        "harness_run_id":   harness.run_id,
        "model_variant":  baseline.model_variant or harness.model_variant,
        "n_paired":       len(paired),
        "n_graded":       len(lift_results),
        "warnings":       warnings,
        "summary":        aggregate,
        "aggregate":      aggregate,    # legacy alias; canonical key is 'summary' (data_primitives.md 1.1)
        "results":        lift_results,
        "elapsed_s":      round(elapsed, 1),
        "completed_at":   time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime()),
    }
    compare_path.write_text(
        json.dumps(compare_payload, indent=2, ensure_ascii=False),
        encoding="utf-8")
    report_md = format_lift_report_md(
        lift_results, aggregate,
        title=f"DueCare lift comparison - {cid}",
        model_name=(baseline.model_variant or harness.model_variant
                    or "unknown"),
        git_sha=baseline.parsed.get("metadata", {}).get("git_sha", "?"),
        dataset_version=(f"baseline={baseline.run_id} vs "
                            f"harness={harness.run_id}"),
    )
    report_path.write_text(report_md, encoding="utf-8")
    chart_html = render_lift_chart(aggregate)
    chart_path.write_text(chart_html, encoding="utf-8")
    artifacts = [
        {"name": compare_path.name, "path": str(compare_path)},
        {"name": report_path.name,  "path": str(report_path)},
        {"name": chart_path.name,   "path": str(chart_path)},
    ]
    _COMPARISON.update({
        "comparison_id": cid,
        "results":       lift_results,
        "aggregate":     aggregate,
        "artifacts":     artifacts,
        "warnings":      warnings,
        "error":         None,
        "completed_at":  compare_payload["completed_at"],
    })
    dc_log("a08.compare.done",
            f"lift complete: mean lift +{aggregate.get('mean_lift_pp', 0)}pp "
            f"on {aggregate.get('n', 0)} prompts",
            comparison_id=cid, mean_lift_pp=aggregate.get("mean_lift_pp"))
    return {"ok": True, "comparison_id": cid,
            "n_paired": len(paired), "n_graded": len(lift_results),
            "aggregate": aggregate, "warnings": warnings,
            "artifacts": artifacts, "elapsed_s": round(elapsed, 1)}


# ===========================================================================
# 4. Plotly lift chart -- per-dimension status-change bars
# ===========================================================================

PAPER   = "#F7F6F1"
PAPER_2 = "#EFEDE4"
INK     = "#0E1116"
INK_3   = "#5B5F68"
LINE    = "#DDD8C9"
ACCENT  = "#4C7A8A"   # civic teal
GOOD    = "#3E8C65"
WARN    = "#A97935"
DANGER  = "#9E3F3F"


def render_lift_chart(aggregate: dict) -> str:
    """Render a Plotly bar chart of per-dimension status change. Returns
    a standalone HTML string (includes plotly.js inline so it works
    without a CDN)."""
    if not aggregate or "per_dimension" not in aggregate:
        return "<p>No lift data available.</p>"
    dim_stats = aggregate["per_dimension"]
    # Sort by improved-count descending so the wins lead the chart.
    rows = sorted(dim_stats.items(),
                    key=lambda kv: -kv[1].get("improved", 0))
    names      = [ds["name"] for _, ds in rows]
    improved   = [ds.get("improved", 0)  for _, ds in rows]
    same       = [ds.get("same", 0)      for _, ds in rows]
    regressed  = [ds.get("regressed", 0) for _, ds in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Improved (harness wins)",
                          y=names, x=improved, orientation="h",
                          marker_color=GOOD,
                          hovertemplate="%{y}<br>Improved: %{x}<extra></extra>"))
    fig.add_trace(go.Bar(name="Same",
                          y=names, x=same, orientation="h",
                          marker_color=INK_3,
                          hovertemplate="%{y}<br>Same: %{x}<extra></extra>"))
    fig.add_trace(go.Bar(name="Regressed (harness loses)",
                          y=names, x=regressed, orientation="h",
                          marker_color=DANGER,
                          hovertemplate="%{y}<br>Regressed: %{x}<extra></extra>"))
    fig.update_layout(
        title=dict(
            text=(f"Per-dimension lift  ·  mean +{aggregate.get('mean_lift_pp', 0)} pp  "
                    f"on {aggregate.get('n', 0)} prompts"),
            font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif",
                      size=18, color=INK)),
        barmode="stack",
        paper_bgcolor=PAPER, plot_bgcolor=PAPER_2,
        font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif",
                  color=INK_3),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        margin=dict(l=240, r=30, t=80, b=40),
        height=max(360, 40 * len(names) + 120),
        xaxis=dict(gridcolor=LINE, zeroline=False),
        yaxis=dict(gridcolor=LINE, autorange="reversed"),
    )
    return pio.to_html(fig, include_plotlyjs="inline", full_html=True)


# ===========================================================================
# 5. Homepage HTML + extra_routes (upload + run comparison + state)
# ===========================================================================
INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>DueCare A-08 . New-model lift comparison</title>
<link rel="stylesheet" href="/static/_chrome.css">
<style>
  body { background: #F7F6F1; color: #0E1116;
         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                       system-ui, sans-serif;
         margin: 0; padding: 0; line-height: 1.55; }
  .page { max-width: 1080px; margin: 0 auto; padding: 32px 28px 80px; }
  h1 { font-size: 28px; margin: 0 0 6px; font-weight: 700; }
  .lede { color: #5B5F68; margin: 0 0 28px; max-width: 740px; }
  .slots { display: grid; grid-template-columns: 1fr 1fr; gap: 18px;
            margin-bottom: 22px; }
  .slot { background: #EFEDE4; border: 1px solid #DDD8C9;
          border-radius: 12px; padding: 18px 20px; }
  .slot h3 { margin: 0 0 4px; font-size: 15px; letter-spacing: 0.02em; }
  .slot .hint { color: #5B5F68; font-size: 12.5px; margin: 0 0 12px; }
  .slot input[type=file] { width: 100%; padding: 10px;
                            border: 1px dashed #8A8E97; border-radius: 8px;
                            background: #F7F6F1; cursor: pointer; }
  .slot.loaded { border-color: #3E8C65; background: #EAF2EC; }
  .slot.error  { border-color: #9E3F3F; background: #F5E8E8; }
  .slot pre { font-family: "JetBrains Mono", ui-monospace, monospace;
              font-size: 11.5px; background: rgba(0,0,0,0.04);
              padding: 8px 10px; border-radius: 6px;
              white-space: pre-wrap; word-break: break-word;
              margin: 8px 0 0; }
  .actions { display: flex; gap: 12px; margin: 18px 0 28px;
              align-items: center; }
  button.primary { background: #0E1116; color: #F7F6F1;
                    border: none; border-radius: 999px;
                    padding: 11px 22px; font-size: 13.5px; font-weight: 600;
                    cursor: pointer; letter-spacing: 0.01em; }
  button.primary:disabled { opacity: 0.45; cursor: not-allowed; }
  button.secondary { background: transparent; color: #0E1116;
                      border: 1px solid #DDD8C9; border-radius: 999px;
                      padding: 10px 18px; font-size: 13px; cursor: pointer; }
  .panel { background: #EFEDE4; border: 1px solid #DDD8C9;
            border-radius: 12px; padding: 18px 20px; margin: 18px 0; }
  .panel h2 { font-size: 17px; margin: 0 0 12px; font-weight: 600; }
  .warn-strip { background: #F8EFD8; border: 1px solid #E2C97A;
                color: #6B4F0F; padding: 12px 16px; border-radius: 10px;
                margin-bottom: 14px; font-size: 13px; }
  .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;
            margin: 14px 0 8px; }
  .kpi { background: #F7F6F1; border: 1px solid #DDD8C9;
          border-radius: 10px; padding: 14px 16px; }
  .kpi .label { color: #5B5F68; font-size: 11.5px; text-transform: uppercase;
                  letter-spacing: 0.08em; }
  .kpi .value { font-size: 22px; font-weight: 700; margin-top: 4px;
                  color: #0E1116; }
  .kpi .delta-pos { color: #3E8C65; }
  .kpi .delta-neg { color: #9E3F3F; }
  iframe.chart { width: 100%; height: 620px; border: none;
                  background: #F7F6F1; border-radius: 10px; }
  ul.dl { margin: 6px 0 0; padding: 0; list-style: none; }
  ul.dl li { padding: 4px 0; }
  ul.dl a { color: #0E1116; text-decoration: underline;
            text-underline-offset: 3px; }
  .meta { color: #5B5F68; font-size: 12.5px; }
</style>
</head>
<body>
<div class="page">
  <h1>DueCare A-08 . New-model lift comparison</h1>
  <p class="lede">
    Upload the <code>bundle.zip</code> produced by A-06 (fine-tuned baseline,
    harness OFF) and the <code>bundle.zip</code> produced by A-07 (same
    model, harness ON). A-03 pairs results by <code>prompt_id</code> and
    runs the universal v2 grader to compute per-dimension lift. No model
    load required.
  </p>

  <div class="slots">
    <div class="slot" id="slot-baseline">
      <h3>1. Baseline bundle (A-06 . harness OFF)</h3>
      <p class="hint">Drop the <code>a06_*_bundle.zip</code> here.</p>
      <input type="file" accept=".zip,.json"
              onchange="uploadBundle('baseline', this.files[0])">
      <pre id="state-baseline">not loaded</pre>
    </div>
    <div class="slot" id="slot-harness">
      <h3>2. Harness bundle (A-07 . harness ON)</h3>
      <p class="hint">Drop the <code>a07_*_bundle.zip</code> here.</p>
      <input type="file" accept=".zip,.json"
              onchange="uploadBundle('harness', this.files[0])">
      <pre id="state-harness">not loaded</pre>
    </div>
  </div>

  <div class="actions">
    <button class="primary" id="run-btn" disabled
            onclick="runComparison()">Run comparison</button>
    <button class="secondary" onclick="refreshState()">Refresh state</button>
    <span class="meta" id="run-status"></span>
  </div>

  <div id="results-panel" style="display:none">
    <div class="panel">
      <h2>Lift summary</h2>
      <div id="warnings-strip"></div>
      <div class="kpis" id="kpis"></div>
      <ul class="dl" id="downloads"></ul>
    </div>
    <div class="panel">
      <h2>Per-dimension lift</h2>
      <iframe class="chart" id="chart-frame"></iframe>
    </div>
  </div>
</div>

<script>
async function refreshState() {
  const r = await fetch('/api/comparison-state').then(r => r.json());
  renderSlot('baseline', r.bundles.baseline);
  renderSlot('harness',  r.bundles.harness);
  document.getElementById('run-btn').disabled =
    !(r.bundles.baseline.loaded && r.bundles.harness.loaded);
  if (r.comparison && r.comparison.aggregate) {
    renderComparison(r.comparison);
  }
}

function renderSlot(slot, st) {
  const el = document.getElementById('slot-' + slot);
  const pre = document.getElementById('state-' + slot);
  el.classList.remove('loaded', 'error');
  if (st.error) {
    el.classList.add('error');
    pre.textContent = 'error: ' + st.error;
  } else if (st.loaded) {
    el.classList.add('loaded');
    pre.textContent =
      'run_id: ' + st.run_id + '\n' +
      'kernel_id: ' + st.kernel_id + '\n' +
      'model_variant: ' + st.model_variant + '\n' +
      'model_kind: ' + st.model_kind + '\n' +
      'harness_enabled: ' + st.harness_enabled + '\n' +
      'n_results: ' + st.n_results + '\n' +
      'filename: ' + st.filename;
  } else {
    pre.textContent = 'not loaded';
  }
}

async function uploadBundle(slot, file) {
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  document.getElementById('state-' + slot).textContent =
    'uploading ' + file.name + ' ...';
  const r = await fetch('/api/upload-bundle?slot=' + slot,
                          {method: 'POST', body: fd}).then(r => r.json());
  if (!r.ok) {
    document.getElementById('state-' + slot).textContent =
      'error: ' + (r.error || 'upload failed');
    document.getElementById('slot-' + slot).classList.add('error');
    return;
  }
  refreshState();
}

async function runComparison() {
  document.getElementById('run-btn').disabled = true;
  document.getElementById('run-status').textContent =
    'running comparison ...';
  const r = await fetch('/api/run-comparison', {method: 'POST'})
                .then(r => r.json());
  document.getElementById('run-btn').disabled = false;
  if (!r.ok) {
    document.getElementById('run-status').textContent =
      'error: ' + (r.error || 'run failed');
    return;
  }
  document.getElementById('run-status').textContent =
    'comparison ok . ' + r.n_graded + '/' + r.n_paired +
    ' prompts in ' + r.elapsed_s + 's';
  refreshState();
}

// All renderers below build DOM nodes via createElement + textContent
// rather than innerHTML concatenation. Bundle fields (warnings,
// artifact names, run_ids) come from uploaded JSON and must be treated
// as untrusted; only the static layout structure is allowed to be HTML.
function _el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = String(text);
  return e;
}
function _kpi(label, value, cls) {
  const el = _el('div', 'kpi');
  el.appendChild(_el('div', 'label', label));
  el.appendChild(_el('div', 'value' + (cls ? ' ' + cls : ''), value));
  return el;
}
function renderComparison(c) {
  document.getElementById('results-panel').style.display = 'block';
  const a = c.aggregate || {};
  const sign = (v) => v >= 0 ? 'delta-pos' : 'delta-neg';
  const meanLift = a.mean_lift_pp ?? 0;
  const meanSign = meanLift >= 0 ? '+' : '';
  const kpis = document.getElementById('kpis');
  kpis.replaceChildren(
    _kpi('Mean lift', meanSign + meanLift + ' pp', sign(meanLift)),
    _kpi('Prompts', (a.n ?? '-')),
    _kpi('Helped / hurt', (a.n_helped ?? 0) + ' / ' + (a.n_hurt ?? 0)),
    _kpi('Citation grounding',
          (a.mean_grounding_off ?? 0) + '% -> ' +
          (a.mean_grounding_on ?? 0) + '%')
  );
  const w = document.getElementById('warnings-strip');
  w.replaceChildren();
  if (c.warnings && c.warnings.length) {
    const strip = _el('div', 'warn-strip');
    strip.appendChild(_el('b', null, 'Warnings:'));
    const ul = document.createElement('ul');
    for (const msg of c.warnings) {
      ul.appendChild(_el('li', null, msg));
    }
    strip.appendChild(ul);
    w.appendChild(strip);
  }
  const dl = document.getElementById('downloads');
  dl.replaceChildren();
  for (const ar of (c.artifacts || [])) {
    const li = document.createElement('li');
    li.appendChild(document.createTextNode('v '));
    const link = document.createElement('a');
    // Safe: encodeURIComponent prevents path-escape / quote-escape.
    link.href = '/artifact/' + encodeURIComponent(ar.name);
    link.textContent = ar.name;   // textContent prevents HTML injection.
    li.appendChild(link);
    dl.appendChild(li);
  }
  const htmlArtifact = (c.artifacts || []).find(function(ar) {
    return typeof ar.name === 'string' && ar.name.endsWith('.html');
  });
  if (htmlArtifact) {
    document.getElementById('chart-frame').src =
      '/artifact/' + encodeURIComponent(htmlArtifact.name);
  }
}

// Initial fetch on page load.
refreshState();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# extra_routes for build_minimal_shell
# ---------------------------------------------------------------------------

def _bundle_state_dict(b: BundleState) -> dict:
    return {
        "loaded":          b.loaded,
        "error":           b.error,
        "filename":        b.filename,
        "run_id":          b.run_id,
        "kernel_id":       b.kernel_id,
        "model_variant":   b.model_variant,
        "model_kind":      b.model_kind,
        "harness_enabled": b.harness_enabled,
        "n_results":       b.n_results,
    }


async def handle_upload_bundle(slot: str, file):  # type: ignore[no-untyped-def]
    """POST /api/upload-bundle?slot=<baseline|harness>"""
    if slot not in _BUNDLES:
        return {"ok": False, "error": f"unknown slot {slot!r}"}
    raw = await file.read()
    state = parse_bundle_bytes(raw, getattr(file, "filename", "bundle"))
    _BUNDLES[slot] = state
    dc_log("a03.upload",
            f"{slot} bundle: {state.n_results} results"
            if state.loaded else f"{slot} upload error",
            slot=slot, run_id=state.run_id, n_results=state.n_results,
            err=state.error)
    return {"ok": state.loaded, "error": state.error,
            "slot": slot, "state": _bundle_state_dict(state)}


def handle_comparison_state():
    return {
        "bundles":    {k: _bundle_state_dict(v) for k, v in _BUNDLES.items()},
        "comparison": _COMPARISON,
    }


def handle_run_comparison():
    return run_comparison()


# ===========================================================================
# 6. Launch the workbench shell
# ===========================================================================
print("\n" + "=" * 76)
print("[3/4] launching A-03 lift-comparison UI")
print("=" * 76)


def _attach_extra_routes(app):
    from fastapi import UploadFile, File, Query

    @app.post("/api/upload-bundle")
    async def _upload(file: UploadFile = File(...),
                       slot: str = Query("baseline")):
        return await handle_upload_bundle(slot, file)

    @app.get("/api/comparison-state")
    def _state():
        return handle_comparison_state()

    @app.post("/api/run-comparison")
    def _run():
        return handle_run_comparison()


try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": "A-08 new-model lift comparison",
        "audience": "researcher",
        "lede": ("Upload the A-06 baseline bundle and the A-07 harnessed "
                  "bundle. A-03 pairs by prompt_id, runs the universal v2 "
                  "grader on CPU, and renders per-dimension lift + a "
                  "downloadable comparison artifact."),
        "results": [
            {"label": "Stage",    "value": "compare (3/8 in experiment ladder)"},
            {"label": "Compute",  "value": "CPU-only (no model load)"},
            {"label": "Consumes", "value": "A-06 + A-07 bundle.zip"},
            {"label": "Emits",    "value": "<comparison_id>_compare.json + _report.md + _lift_chart.html"},
        ],
        "links": [
            ("Workbench (full)",
              "https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench"),
            ("Experiment ladder spec",
              "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_experiment_ladder.md"),
            ("Artifact schema spec",
              "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_artifact_schema.md"),
        ],
        "next_steps": [
            "Drop the A-06 bundle into slot 1 (baseline, harness OFF).",
            "Drop the A-07 bundle into slot 2 (harness ON, same model).",
            "Click Run comparison. Download compare.json + report.md + lift_chart.html.",
            "For the stock-vs-finetuned arc, repeat A-06 + A-07 with the LoRA model from A-05, then run A-08.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-08-new-model-comparison",
        port=PORT,
        homepage_html=INDEX_HTML,
    )
    # Wire upload + run + state endpoints. build_minimal_shell's
    # extra_routes hook expects (method, callable) pairs but our
    # /api/upload-bundle handler needs FastAPI dependency injection
    # (UploadFile), so attach via the app directly.
    _attach_extra_routes(app)
    if public_url:
        print(f"  ok UI available at {public_url}")

    print("\n" + "=" * 76)
    print("[4/4] A-03 SHELL READY - awaiting bundle uploads")
    print("=" * 76)
    if public_url:
        print(f"\n   UI: {public_url}")
        print(f"\n   Drop A-06 + A-07 bundle.zip in the two slots, then "
              f"click Run comparison.\n")
    print("=" * 76)
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

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
print("  shutdown complete -- cell exiting.\n")
