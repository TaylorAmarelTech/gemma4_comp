#!/usr/bin/env python3
"""Generate the egregious-cases gallery page: the raw-model failures, shown IN FULL (no truncation).

The study page (§05) shows three before/after examples with trimmed quotes. This builds a dedicated
companion page that shows EVERY egregious case (baseline judged >= threshold on active harm) with the
COMPLETE, untruncated baseline and harnessed replies side by side, plus the harm score, harm type, and
the judge's one-line reason. Reproducible from the stored data; HTML-escaped (the raw replies are shown
verbatim as preformatted text, never rendered, never truncated).

Safety note baked into the page: every prompt is composite/synthetic (no real people or entities); the
harmful baseline replies are shown as adversarial-review evidence of what an unharnessed model does,
always paired with the harnessed reply that refuses and cites the law.

    python scripts/build_egregious_gallery.py --threshold 7 --out apps/duecare-ai.com/app/templates/egregious-cases.html
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[1]
RANKER = _ROOT / "reports" / "egregious_ranker.jsonl"
RESP_FILES = [_ROOT / "reports" / "scheme_run.responses.jsonl",
              _ROOT / "reports" / "frontier_perdim" / "perdim.responses.jsonl"]
DEFAULT_OUT = _ROOT / "apps" / "duecare-ai.com" / "app" / "templates" / "egregious-cases.html"


def _prompt_index() -> dict[str, str]:
    idx: dict[str, str] = {}
    for f in glob.glob(str(_ROOT / "configs" / "duecare" / "benchmarks" / "*.json")):
        try:
            d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
            for p in (d.get("prompts", d) if isinstance(d, dict) else d):
                if isinstance(p, dict) and p.get("id"):
                    idx.setdefault(str(p["id"]), p.get("text", ""))
        except Exception:  # noqa: BLE001
            continue
    return idx


def load_responses() -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    pidx = _prompt_index()
    for path in RESP_FILES:
        if not path.exists():
            continue
        for ln in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if r.get("arm") in ("baseline", "harnessed") and r.get("response"):
                key = (str(r.get("model")), str(r.get("prompt_id")))
                cell = out.setdefault(key, {})
                cell[r["arm"]] = str(r["response"])
                cell["prompt_text"] = (r.get("prompt_text") or r.get("prompt")
                                       or pidx.get(str(r.get("prompt_id")), ""))
    return out


def select_cases(threshold: float, limit: int = 0) -> list[dict]:
    """Egregious cases (baseline harm >= threshold) that have BOTH full replies stored, worst first."""
    resp = load_responses()
    cases: list[dict] = []
    for ln in RANKER.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        try:
            harm = float(r.get("egregiousness") or 0)
        except (TypeError, ValueError):
            harm = 0.0
        if harm < threshold:
            continue
        key = (str(r.get("model")), str(r.get("prompt_id")))
        cell = resp.get(key)
        if not cell or "baseline" not in cell or "harnessed" not in cell:
            continue
        cases.append({"model": key[0], "prompt_id": key[1], "harm": harm,
                      "harm_type": r.get("harm_type", ""), "why": r.get("why", ""),
                      "prompt_text": cell.get("prompt_text", ""),
                      "baseline": cell["baseline"], "harnessed": cell["harnessed"]})
    cases.sort(key=lambda c: -c["harm"])
    return cases[:limit] if limit else cases


_STYLE = """
.eg-intro { border: 1px solid var(--line); border-left: 3px solid oklch(0.58 0.14 45); border-radius: 10px; padding: 18px 22px; margin: 8px 0 28px; background: oklch(0.97 0.02 45); font-size: 13.5px; line-height: 1.55; color: var(--ink-2); }
.eg-case { border: 1px solid var(--line); border-radius: 12px; margin: 0 0 26px; overflow: hidden; background: var(--paper); }
.eg-head { display: flex; flex-wrap: wrap; gap: 10px 16px; align-items: baseline; padding: 14px 22px; background: var(--paper-2); border-bottom: 1px solid var(--line); font-family: var(--mono); font-size: 12px; }
.eg-head .n { font-weight: 700; color: var(--ink); }
.eg-head .harm { color: oklch(0.45 0.16 38); font-weight: 700; }
.eg-head .type { color: var(--ink-3); }
.eg-head .pid { color: var(--ink-4); margin-left: auto; }
.eg-why { font-size: 13px; color: var(--ink-2); padding: 14px 22px 0; line-height: 1.5; }
.eg-why b { color: var(--ink); }
.eg-prompt { font-size: 13px; color: var(--ink-2); padding: 12px 22px 16px; line-height: 1.55; }
.eg-prompt b { color: var(--ink); }
.eg-arms { display: grid; grid-template-columns: 1fr 1fr; gap: 0; border-top: 1px solid var(--line); }
@media (max-width: 820px) { .eg-arms { grid-template-columns: 1fr; } }
.eg-arm { padding: 16px 22px; }
.eg-arm.raw { background: oklch(0.97 0.02 45); border-right: 1px solid var(--line); }
.eg-arm.harn { background: oklch(0.97 0.02 155); }
@media (max-width: 820px) { .eg-arm.raw { border-right: none; border-bottom: 1px solid var(--line); } }
.eg-arm .tag { font-family: var(--mono); font-size: 10.5px; letter-spacing: 0.06em; text-transform: uppercase; display: block; margin-bottom: 10px; }
.eg-arm.raw .tag { color: oklch(0.46 0.16 38); }
.eg-arm.harn .tag { color: oklch(0.38 0.12 155); }
.eg-arm pre { white-space: pre-wrap; word-wrap: break-word; font-family: var(--mono); font-size: 12px; line-height: 1.6; color: var(--ink-2); margin: 0; }
"""


def _norm(s: str) -> str:
    """Normalize em/en dashes to hyphens (per the no-em-dash style), preserving everything else."""
    return re.sub(r"\s*—\s*", " - ", (s or "")).replace("–", "-")


def _esc(s: str) -> str:
    return html.escape(_norm(s))


def render(cases: list[dict], threshold: float) -> str:
    o: list[str] = []
    o.append('<!DOCTYPE html>')
    o.append('<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" />')
    o.append('<title>Egregious cases, in full &middot; DueCare AI</title>')
    o.append('<meta name="description" content="Every egregious raw-model reply from the DueCare adversarial self-evaluation, shown in full and untruncated, paired with the harnessed reply. Composite/synthetic prompts." />')
    o.append('<link rel="stylesheet" href="/static/styles.css" /><link rel="stylesheet" href="/static/hub-pages.css" />')
    o.append("<style>" + _STYLE + "</style>")
    o.append('<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 32 32\'%3E%3Crect width=\'32\' height=\'32\' rx=\'6\' fill=\'%230E1116\'/%3E%3Ctext x=\'16\' y=\'21\' text-anchor=\'middle\' font-family=\'monospace\' font-weight=\'700\' font-size=\'14\' fill=\'%23F7F6F1\'%3ED%3C/text%3E%3C/svg%3E" />')
    o.append('</head><body>{% set active_nav = "evaluation" %}')
    o.append('{% include "_nav.html" %}')
    o.append('<section class="hp-hero" data-screen-label="Eval &middot; Egregious cases"><div class="wrap">')
    o.append('<div class="crumbs"><a href="/">Home</a><span class="sep">/</span><a href="/evaluation">Evaluation</a><span class="sep">/</span><a href="/harness-study">Harness-lift study</a><span class="sep">/</span><span>Egregious cases</span></div>')
    o.append('<span class="kicker">Adversarial self-evaluation</span>')
    o.append('<h1>The raw-model failures, in full.</h1>')
    o.append(f'<p class="lede">Every egregious case for which the complete replies were stored &mdash; <b>{len(cases)} in all</b>, each a baseline reply an egregiousness judge scored at or above {int(threshold)}/10 on active harm &mdash; shown <b>complete and untruncated</b> next to the same model wrapped in the DueCare harness. This is the failure mode the harness exists to prevent, shown in full so nothing is hidden.</p></div></section>')
    o.append('<section class="hp-section"><div class="wrap">')
    o.append('<div class="eg-intro"><b>Read this first.</b> Every prompt below is <b>composite and synthetic</b> &mdash; no real people, agencies, or case numbers. The harmful left-hand replies are shown as evidence of what an <i>unharnessed</i> model produces when asked a disguised exploitation question; they are always paired with the harnessed reply that refuses and cites the governing law. The schemes themselves (fee-splitting, document retention, debt bondage) are already documented in public anti-trafficking literature. We show them in full for honest adversarial review, not as instructions.</div>')
    for i, c in enumerate(cases, 1):
        ht = _esc(str(c.get("harm_type") or "")).replace("_", " ")
        o.append('<div class="eg-case">')
        o.append(f'<div class="eg-head"><span class="n">Case {i}</span>'
                 f'<span class="harm">harm {c["harm"]:.0f}/10</span>'
                 f'<span class="type">{ht}</span><span class="pid">{_esc(c["model"])} &middot; {_esc(c["prompt_id"])}</span></div>')
        if c.get("why"):
            o.append(f'<p class="eg-why"><b>Why it is harmful:</b> {_esc(c["why"])}</p>')
        if c.get("prompt_text"):
            o.append(f'<p class="eg-prompt"><b>The ask:</b> {_esc(c["prompt_text"])}</p>')
        o.append('<div class="eg-arms">')
        o.append(f'<div class="eg-arm raw"><span class="tag">Raw {_esc(c["model"])} &middot; harm {c["harm"]:.0f}/10</span><pre>{_esc(c["baseline"])}</pre></div>')
        o.append(f'<div class="eg-arm harn"><span class="tag">Same model + DueCare harness</span><pre>{_esc(c["harnessed"])}</pre></div>')
        o.append('</div></div>')
    o.append(f'<p class="hp-note" style="margin-top:18px">{len(cases)} cases, regenerated from the public repository by <code>scripts/build_egregious_gallery.py</code>. Back to the <a href="/harness-study">harness-lift study</a>.</p>')
    o.append('</div></section>')
    o.append('</body></html>')
    return "\n".join(o) + "\n"


def _scheme_meta() -> dict[str, dict]:
    meta: dict[str, dict] = {}
    try:
        d = json.loads((_ROOT / "configs" / "duecare" / "benchmarks" / "scheme_prompts.json").read_text(encoding="utf-8"))
        for p in d.get("prompts", []):
            meta[str(p["id"])] = {"category": p.get("category", ""), "corridor": p.get("corridor", "")}
    except Exception:  # noqa: BLE001
        pass
    return meta


def post_markdown(cases: list[dict], n: int = 3) -> str:
    """Markdown for the Kaggle post: N distinct-scheme-type cases, full input + full replies, no em dashes."""
    meta = _scheme_meta()

    def _topic(pt: str) -> str:
        p = (pt or "").lower()
        if "passport" in p or "seaman" in p or ("document" in p and any(k in p for k in ("retain", "custody", "safekeep"))):
            return "passport and document retention"
        if any(k in p for k in ("foundation", "non-profit", "sister", "ngo")):
            return "fee camouflage via a non-profit"
        return "recruitment-fee evasion"

    picked: list[tuple] = []
    for c in cases[:n]:                       # worst first; duplicate scheme types are fine (include many)
        m = meta.get(c["prompt_id"])
        label = m["category"].replace("_", " ") if m else _topic(c["prompt_text"])
        corr = m.get("corridor", "").replace("->", " to ") if m else ""
        picked.append((c, label, corr))
    o: list[str] = []
    for i, (c, cat, corr) in enumerate(picked, 1):
        o.append(f"### Example {i}: {cat}" + (f" ({corr})" if corr else "") + "\n")
        o.append("*The model input, verbatim:*\n")
        o.append("> " + _norm(c["prompt_text"]).replace("\n", "\n> ") + "\n")
        o.append(f"*The complete raw reply (`{c['model']}`, verbatim and untruncated):*\n")
        o.append("```text\n" + _norm(c["baseline"]).strip() + "\n```\n")
        o.append("*The complete harnessed reply, verbatim and untruncated:*\n")
        o.append("```text\n" + _norm(c["harnessed"]).strip() + "\n```\n")
    return "\n".join(o)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threshold", type=float, default=7.0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--post-md", type=int, default=0,
                    help="emit N-example post markdown to reports/_scratch/post_examples.md instead of the page")
    args = ap.parse_args(argv)
    cases = select_cases(args.threshold, args.limit)
    if not cases:
        print("no egregious cases with full responses found", flush=True)
        return 1
    if args.post_md:
        md = post_markdown(cases, args.post_md)
        outp = _ROOT / "reports" / "_scratch" / "post_examples.md"
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(md, encoding="utf-8")
        print(f"wrote {args.post_md}-example post markdown -> {outp}")
        return 0
    out = pathlib.Path(args.out)
    out.write_text(render(cases, args.threshold), encoding="utf-8")
    print(f"wrote {len(cases)} full before/after cases -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
