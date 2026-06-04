"""Render the harness-lift judge checkpoint into a self-contained HTML report.

Reads the per-cell Opus-judge checkpoint + the persisted responses + the prompt
corpus and produces reports/harness_lift_report.html with:
  * the with/without-harness lift table (per candidate model),
  * per dimension-GROUP lift (where the harness helps most),
  * EGREGIOUS baseline (no-harness) examples -- the worst-scoring baseline
    responses shown next to their harnessed counterpart, so a reviewer can see
    exactly what the harness fixed.

Self-contained (inline CSS, warm-paper civic-tech palette per 60_notebook_
presentation.md), no external assets, no truncation of displayed text. Synthetic
content only (public prompts + model responses); no PII. Regeneratable.

Run: python scripts/build_lift_report.py   (output under reports/, gitignored)
"""
from __future__ import annotations

import collections
import glob
import html
import json
import os
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_BENCH = _ROOT / "configs" / "duecare" / "benchmarks"
_CKPT = _ROOT / os.environ.get("LIFT_REPORT_CKPT", "reports/harness_lift_500_opus.jsonl")
_OUT = _ROOT / os.environ.get("LIFT_REPORT_OUT", "reports/harness_lift_report.html")

# Civic-tech warm-paper palette (60_notebook_presentation.md).
_PAPER, _PAPER2, _INK, _INK3, _LINE = "#F7F6F1", "#EFEDE4", "#0E1116", "#5B5F68", "#DDD8C9"
_GOOD, _WARN, _EMBER = "#2e7d57", "#b08900", "#c2410c"


def _load_jsonl(path: pathlib.Path) -> list[dict]:
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def _load_prompts() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in glob.glob(str(_BENCH / "harness_lift_prompts_*.json")):
        try:
            for p in json.loads(pathlib.Path(f).read_text(encoding="utf-8"))["prompts"]:
                out[str(p["id"])] = p["text"]
        except Exception:
            continue
    for r in _load_jsonl(_BENCH / "harness_lift_prompts_expansion.jsonl"):
        if r.get("id"):
            out[str(r["id"])] = r.get("text", "")
    return out


def _load_responses() -> dict[tuple, str]:
    out: dict[tuple, str] = {}
    for f in glob.glob(str(_ROOT / "reports" / "*.responses.jsonl")):
        for r in _load_jsonl(pathlib.Path(f)):
            try:
                out[(str(r["prompt_id"]), str(r["model"]), str(r["arm"]))] = r.get("response", "")
            except Exception:
                continue
    return out


def _color(score: float) -> str:
    return _GOOD if score >= 6.5 else (_WARN if score >= 4 else _EMBER)


def build() -> pathlib.Path:
    cells = _load_jsonl(_CKPT)
    prompts, responses = _load_prompts(), _load_responses()

    # Aggregate per (model, arm) overall + per group; per (prompt, model, arm) mean.
    by_ma: dict[tuple, list[float]] = collections.defaultdict(list)
    by_mag: dict[tuple, list[float]] = collections.defaultdict(list)
    by_pma: dict[tuple, list[float]] = collections.defaultdict(list)
    prompts_seen: dict[str, set] = collections.defaultdict(set)
    for c in cells:
        m, a, s = c["model"], c["arm"], float(c["score"])
        grp = str(c["dim"]).split(".", 1)[0]
        by_ma[(m, a)].append(s)
        by_mag[(m, a, grp)].append(s)
        by_pma[(c["prompt_id"], m, a)].append(s)
        prompts_seen[m].add(c["prompt_id"])

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    models = sorted({m for (m, _a) in by_ma})
    rows = []
    for m in models:
        b, h = mean(by_ma.get((m, "baseline"), [])), mean(by_ma.get((m, "harnessed"), []))
        rows.append((m, b, h, h - b, len(prompts_seen[m])))
    rows.sort(key=lambda r: r[3], reverse=True)

    # Egregious baseline examples: (prompt, model) with both arms, lowest baseline
    # mean (worst no-harness), preferring large harness lift.
    pairs = []
    for (pid, m, a), xs in by_pma.items():
        if a != "baseline":
            continue
        hk = (pid, m, "harnessed")
        if hk in by_pma:
            bm, hm = mean(xs), mean(by_pma[hk])
            pairs.append((bm, hm, hm - bm, pid, m))
    pairs.sort(key=lambda p: (p[0], -p[2]))  # worst baseline first, then biggest lift
    egregious = pairs[:12]

    # ---- render ----
    def esc(s):
        return html.escape(str(s))

    css = (f"body{{background:{_PAPER};color:{_INK};font:15px/1.55 -apple-system,"
           f"Segoe UI,Inter,sans-serif;margin:0;padding:32px;max-width:1100px}}"
           f"h1{{font-size:26px;margin:0 0 4px}}h2{{font-size:19px;margin:34px 0 10px;"
           f"border-bottom:2px solid {_LINE};padding-bottom:6px}}.sub{{color:{_INK3};margin:0 0 18px}}"
           f"table{{border-collapse:collapse;width:100%;margin:8px 0}}"
           f"th,td{{text-align:left;padding:8px 12px;border-bottom:1px solid {_LINE}}}"
           f"th{{background:{_PAPER2};font-size:13px;letter-spacing:.02em}}"
           f".num{{text-align:right;font-variant-numeric:tabular-nums}}"
           f".bar{{height:9px;border-radius:5px;background:{_GOOD};display:inline-block;vertical-align:middle}}"
           f".ex{{border:1px solid {_LINE};border-radius:10px;margin:14px 0;overflow:hidden;background:#fff}}"
           f".ex .hd{{background:{_PAPER2};padding:10px 14px;font-size:13px;color:{_INK3}}}"
           f".ex .pr{{padding:12px 14px;border-bottom:1px solid {_LINE};white-space:pre-wrap}}"
           f".arm{{padding:12px 14px;white-space:pre-wrap;border-top:1px solid {_LINE}}}"
           f".tag{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;"
           f"font-weight:600;color:#fff}}.muted{{color:{_INK3}}}")

    out = [f"<!doctype html><html><head><meta charset='utf-8'>"
           f"<title>DueCare Harness-Lift Report</title><style>{css}</style></head><body>"]
    out.append("<h1>DueCare &mdash; Harness-Lift Report</h1>")
    out.append(f"<p class='sub'>Baseline vs DueCare-harnessed, graded by Opus&nbsp;4.8 across "
               f"{len({c['dim'] for c in cells})} dimensions &middot; {len(cells):,} graded cells "
               f"&middot; {len(prompts)} prompts in corpus. Lift = harnessed &minus; baseline (0&ndash;10).</p>")

    # Lift table
    out.append("<h2>Harness lift by model</h2><table><tr><th>Model</th>"
               "<th class='num'>Baseline</th><th class='num'>Harnessed</th>"
               "<th class='num'>Lift</th><th class='num'>Prompts</th><th>Lift</th></tr>")
    maxlift = max((r[3] for r in rows), default=1) or 1
    for m, b, h, lift, npr in rows:
        w = int(max(0, lift) / maxlift * 180)
        out.append(f"<tr><td>{esc(m)}</td><td class='num'>{b:.2f}</td>"
                   f"<td class='num'>{h:.2f}</td><td class='num' style='color:{_color(6.5 if lift>0 else 0)};"
                   f"font-weight:600'>{lift:+.2f}</td><td class='num'>{npr}</td>"
                   f"<td><span class='bar' style='width:{w}px'></span></td></tr>")
    out.append("</table>")

    # Per-group lift for the top model
    if rows:
        top = rows[0][0]
        out.append(f"<h2>Where the harness helps most &mdash; {esc(top)}, by dimension group</h2>")
        grps = sorted({g for (mm, _a, g) in by_mag if mm == top})
        gl = []
        for g in grps:
            b, h = mean(by_mag.get((top, "baseline", g), [])), mean(by_mag.get((top, "harnessed", g), []))
            gl.append((g, b, h, h - b))
        gl.sort(key=lambda x: x[3], reverse=True)
        out.append("<table><tr><th>Dimension group</th><th class='num'>Baseline</th>"
                   "<th class='num'>Harnessed</th><th class='num'>Lift</th><th>Lift</th></tr>")
        gmax = max((x[3] for x in gl), default=1) or 1
        for g, b, h, lift in gl:
            w = int(max(0, lift) / gmax * 180)
            out.append(f"<tr><td>{esc(g)}</td><td class='num'>{b:.2f}</td><td class='num'>{h:.2f}</td>"
                       f"<td class='num' style='font-weight:600'>{lift:+.2f}</td>"
                       f"<td><span class='bar' style='width:{w}px'></span></td></tr>")
        out.append("</table>")

    # Egregious baseline examples
    out.append("<h2>Egregious baseline (no-harness) responses &mdash; and what the harness did</h2>")
    out.append("<p class='sub'>Worst-scoring baseline answers; the harnessed answer to the same prompt "
               "is shown beneath for contrast.</p>")
    for bm, hm, lift, pid, m in egregious:
        ptext = prompts.get(str(pid), "(prompt text unavailable)")
        br = responses.get((str(pid), m, "baseline"), "(response unavailable)")
        hr = responses.get((str(pid), m, "harnessed"), "(response unavailable)")
        out.append("<div class='ex'>")
        out.append(f"<div class='hd'>{esc(m)} &middot; prompt <code>{esc(pid)}</code> &middot; "
                   f"baseline <b style='color:{_color(bm)}'>{bm:.1f}</b> &rarr; "
                   f"harnessed <b style='color:{_color(hm)}'>{hm:.1f}</b> "
                   f"(<b>{lift:+.1f}</b>)</div>")
        out.append(f"<div class='pr'><b>Prompt:</b> {esc(ptext)}</div>")
        out.append(f"<div class='arm'><span class='tag' style='background:{_EMBER}'>BASELINE "
                   f"{bm:.1f}</span><br>{esc(br)}</div>")
        out.append(f"<div class='arm'><span class='tag' style='background:{_GOOD}'>HARNESSED "
                   f"{hm:.1f}</span><br>{esc(hr)}</div>")
        out.append("</div>")

    out.append("</body></html>")
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text("\n".join(out), encoding="utf-8")
    return _OUT


def main() -> None:
    path = build()
    print(f"[lift-report] wrote {path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
