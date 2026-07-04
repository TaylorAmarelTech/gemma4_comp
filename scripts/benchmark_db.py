#!/usr/bin/env python3
"""Index the harness-lift benchmark checkpoints into SQLite, and audit their integrity.

The run checkpoints are large append-only JSONL files -- ``reports/rich_lift/results.jsonl`` is ~73 MB
(11.5k responses) and ``panel.jsonl`` is ~7.5 MB (28k judge rows). Every analysis re-parses the whole
file; there is no index and no integrity check. This ingests both into a single indexed SQLite database
(fast queries, and the substrate for future analyses to stop re-scanning JSONL), and runs a data-quality
AUDIT that reconciles the numbers a reviewer would ask about:

  * counts per model / arm / judge, and how many judges graded each cell (self-family exclusion means
    2-3, not always 3);
  * DUPLICATE rows (a cell generated or graded twice), ORPHANS (a score with no stored response, or a
    response never scored), and COMPLETENESS (prompts missing an arm);
  * out-of-range scores / components and empty responses -- the malformed rows that would silently skew
    a mean.

The DB is written under the gitignored ``reports/`` tree; the audit report is committable (counts only,
no prompt or response text). Deterministic; no model calls.

    python scripts/benchmark_db.py                 # ingest + audit (default)
    python scripts/benchmark_db.py --audit-only     # re-audit an existing db
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sqlite3
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = _ROOT / "reports" / "rich_lift"
PANEL = OUT_DIR / "panel.jsonl"
RESULTS = OUT_DIR / "results.jsonl"
DB_DEFAULT = OUT_DIR / "benchmark.db"
AUDIT_OUT = _ROOT / "docs" / "research" / "benchmark_data_audit.md"
ARMS = ("baseline", "harness_core", "harness_full")
COMPONENT_MAX = {"a": 25, "b": 20, "c": 25, "d": 15, "e": 15}


def connect(path: str | pathlib.Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS panel;
        DROP TABLE IF EXISTS results;
        CREATE TABLE panel (
            model TEXT, prompt_id TEXT, arm TEXT, judge TEXT, score REAL,
            a REAL, b REAL, c REAL, d REAL, e REAL
        );
        CREATE TABLE results (
            model TEXT, prompt_id TEXT, arm TEXT, response TEXT, resp_len INTEGER
        );
        """
    )


def _panel_row(r: dict) -> tuple | None:
    try:
        c = r.get("components") if isinstance(r.get("components"), dict) else {}
        return (str(r["model"]), str(r["prompt_id"]), str(r["arm"]), str(r.get("judge", "")),
                float(r["score_0_100"]),
                *(float(c[k.upper()]) if isinstance(c.get(k.upper()), (int, float)) else None
                  for k in ("a", "b", "c", "d", "e")))
    except (KeyError, TypeError, ValueError):
        return None


def _result_row(r: dict) -> tuple | None:
    try:
        resp = str(r.get("response", "") or "")
        return (str(r["model"]), str(r["prompt_id"]), str(r["arm"]), resp, len(resp))
    except (KeyError, TypeError, ValueError):
        return None


def _iter_jsonl(path: pathlib.Path):
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def ingest(conn: sqlite3.Connection, *, panel: list[dict] | None = None,
           results: list[dict] | None = None) -> dict:
    """Ingest panel + results rows into a fresh schema. Returns {panel, results, panel_skipped, ...}."""
    create_schema(conn)
    p_rows = [t for r in (panel or []) if (t := _panel_row(r)) is not None]
    r_rows = [t for r in (results or []) if (t := _result_row(r)) is not None]
    conn.executemany("INSERT INTO panel VALUES (?,?,?,?,?,?,?,?,?,?)", p_rows)
    conn.executemany("INSERT INTO results VALUES (?,?,?,?,?)", r_rows)
    conn.executescript(
        """
        CREATE INDEX ix_panel_cell ON panel(model, prompt_id, arm);
        CREATE INDEX ix_panel_judge ON panel(judge);
        CREATE INDEX ix_results_cell ON results(model, prompt_id, arm);
        """
    )
    conn.commit()
    return {"panel": len(p_rows), "results": len(r_rows),
            "panel_skipped": len(panel or []) - len(p_rows),
            "results_skipped": len(results or []) - len(r_rows)}


def ingest_files(conn: sqlite3.Connection, panel_path: pathlib.Path = PANEL,
                 results_path: pathlib.Path = RESULTS) -> dict:
    return ingest(conn, panel=list(_iter_jsonl(panel_path)), results=list(_iter_jsonl(results_path)))


def _rows(conn: sqlite3.Connection, sql: str) -> list[sqlite3.Row]:
    return list(conn.execute(sql))


def audit(conn: sqlite3.Connection) -> dict:
    cur = conn.execute
    n_panel = cur("SELECT count(*) FROM panel").fetchone()[0]
    n_results = cur("SELECT count(*) FROM results").fetchone()[0]
    per_model = {r["model"]: r["n"] for r in _rows(conn,
                 "SELECT model, count(*) n FROM results GROUP BY model ORDER BY n DESC")}
    per_arm = {r["arm"]: r["n"] for r in _rows(conn,
               "SELECT arm, count(*) n FROM results GROUP BY arm ORDER BY n DESC")}
    per_judge = {r["judge"]: r["n"] for r in _rows(conn,
                 "SELECT judge, count(*) n FROM panel GROUP BY judge ORDER BY n DESC")}

    dup_panel = cur("SELECT count(*) FROM (SELECT 1 FROM panel GROUP BY model, prompt_id, arm, judge "
                    "HAVING count(*) > 1)").fetchone()[0]
    dup_results = cur("SELECT count(*) FROM (SELECT 1 FROM results GROUP BY model, prompt_id, arm "
                      "HAVING count(*) > 1)").fetchone()[0]
    orphan_panel = cur("SELECT count(*) FROM (SELECT DISTINCT p.model, p.prompt_id, p.arm FROM panel p "
                       "LEFT JOIN results r ON p.model=r.model AND p.prompt_id=r.prompt_id AND p.arm=r.arm "
                       "WHERE r.model IS NULL)").fetchone()[0]
    orphan_results = cur("SELECT count(*) FROM (SELECT r.model, r.prompt_id, r.arm FROM results r "
                         "LEFT JOIN panel p ON p.model=r.model AND p.prompt_id=r.prompt_id AND p.arm=r.arm "
                         "WHERE p.model IS NULL)").fetchone()[0]

    # judges per graded cell (self-family exclusion -> often 2-3)
    jpc = collections.Counter(r["j"] for r in _rows(conn,
          "SELECT count(DISTINCT judge) j FROM panel GROUP BY model, prompt_id, arm"))
    judges_per_cell = {int(k): v for k, v in sorted(jpc.items())}

    # completeness: response cells present in all 3 arms per (model, prompt_id)
    arms_per_prompt = collections.Counter(r["k"] for r in _rows(conn,
        "SELECT count(DISTINCT arm) k FROM results GROUP BY model, prompt_id"))
    complete_prompts = arms_per_prompt.get(3, 0)
    partial_prompts = sum(v for k, v in arms_per_prompt.items() if k < 3)

    score_oor = cur("SELECT count(*) FROM panel WHERE score < 0 OR score > 100").fetchone()[0]
    comp_oor = sum(cur(f"SELECT count(*) FROM panel WHERE {col} IS NOT NULL AND ({col} < 0 OR {col} > ?)",
                       (mx,)).fetchone()[0] for col, mx in COMPONENT_MAX.items())
    empty_resp = cur("SELECT count(*) FROM results WHERE resp_len = 0").fetchone()[0]
    unknown_arm = cur("SELECT count(*) FROM results WHERE arm NOT IN (?,?,?)", ARMS).fetchone()[0]

    return {
        "n_panel": n_panel, "n_results": n_results,
        "per_model": per_model, "per_arm": per_arm, "per_judge": per_judge,
        "dup_panel": dup_panel, "dup_results": dup_results,
        "orphan_panel": orphan_panel, "orphan_results": orphan_results,
        "judges_per_cell": judges_per_cell,
        "complete_prompts": complete_prompts, "partial_prompts": partial_prompts,
        "score_out_of_range": score_oor, "component_out_of_range": comp_oor,
        "empty_responses": empty_resp, "unknown_arm": unknown_arm,
    }


def neg_lift_instances(conn: sqlite3.Connection, *, arm: str = "harness_full",
                       limit: int = 25) -> list[dict]:
    """The worst negative-lift instances (a harnessed arm scored BELOW baseline), from the DB.

    One indexed SQL query over per-cell mean scores -- the fast, queryable substitute for re-parsing the
    JSONL. Returns prompt ids + scores only (no text); pull the prompt by id to review it. Useful for
    "study the negative-lift instances" and for choosing prompts to improve.
    """
    sql = """
        WITH cell AS (
            SELECT model, prompt_id, arm, avg(score) s, count(DISTINCT judge) nj
            FROM panel GROUP BY model, prompt_id, arm
        )
        SELECT b.model AS model, b.prompt_id AS prompt_id,
               round(b.s, 1) AS baseline, round(h.s, 1) AS harnessed,
               round(h.s - b.s, 1) AS lift, h.nj AS judges,
               rb.resp_len AS base_len, rh.resp_len AS full_len
        FROM cell b JOIN cell h ON b.model = h.model AND b.prompt_id = h.prompt_id
        LEFT JOIN results rb ON rb.model = b.model AND rb.prompt_id = b.prompt_id AND rb.arm = 'baseline'
        LEFT JOIN results rh ON rh.model = h.model AND rh.prompt_id = h.prompt_id AND rh.arm = h.arm
        WHERE b.arm = 'baseline' AND h.arm = ? AND h.s < b.s
        ORDER BY (h.s - b.s) ASC
        LIMIT ?
    """
    return [dict(r) for r in conn.execute(sql, (arm, limit))]


def build_audit_report(a: dict) -> str:
    o: list[str] = []
    o.append("# Benchmark data audit (SQLite index over the run checkpoints)\n")
    o.append("> Ingests `reports/rich_lift/{panel,results}.jsonl` into `reports/rich_lift/benchmark.db` "
             "and audits integrity. Regenerate with `python scripts/benchmark_db.py`. Counts only; no "
             "prompt or response text.\n")
    o.append(f"**{a['n_results']:,} responses** and **{a['n_panel']:,} judge rows** "
             f"({a['n_panel'] / (a['n_results'] or 1):.2f} judges per response on average -- "
             "self-family exclusion keeps this below the 3-judge panel size).\n")

    def _issue(label: str, n: int) -> str:
        return f"- {'[ok]' if n == 0 else '[!!]'} **{label}: {n:,}**"
    o.append("## Integrity checks\n")
    o.append("\n".join([
        _issue("Duplicate judge rows (same model/prompt/arm/judge)", a["dup_panel"]),
        _issue("Duplicate responses (same model/prompt/arm)", a["dup_results"]),
        _issue("Scored cells with no stored response (orphan panel)", a["orphan_panel"]),
        _issue("Responses never scored (orphan results)", a["orphan_results"]),
        _issue("Scores out of 0-100 range", a["score_out_of_range"]),
        _issue("Components out of their max range", a["component_out_of_range"]),
        _issue("Empty responses", a["empty_responses"]),
        _issue("Responses with an unknown arm", a["unknown_arm"]),
    ]) + "\n")

    o.append("## Coverage\n")
    o.append(f"- Prompts with all 3 arms generated: **{a['complete_prompts']:,}**; "
             f"partial (missing an arm): **{a['partial_prompts']:,}**.\n")
    o.append("- Judges per graded cell: "
             + ", ".join(f"{k} judge(s): {v:,}" for k, v in a["judges_per_cell"].items()) + ".\n")

    o.append("## Responses per model\n")
    o.append("| Model | responses |")
    o.append("|---|---:|")
    for m, n in a["per_model"].items():
        o.append(f"| `{m}` | {n:,} |")
    o.append("")
    o.append("Per arm: " + ", ".join(f"`{k}` {v:,}" for k, v in a["per_arm"].items()) + ".  ")
    o.append("Per judge: " + ", ".join(f"`{k}` {v:,}" for k, v in a["per_judge"].items()) + ".\n")
    return "\n".join(o) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(DB_DEFAULT))
    ap.add_argument("--out", default=str(AUDIT_OUT))
    ap.add_argument("--audit-only", action="store_true", help="audit an existing db without re-ingesting")
    ap.add_argument("--neg-lift", type=int, default=0, metavar="N",
                    help="also print the N worst negative-lift instances (harness_full < baseline)")
    args = ap.parse_args(argv)
    conn = connect(args.db)
    if not args.audit_only:
        if not PANEL.exists():
            print(f"no panel at {PANEL} -- nothing to ingest", file=sys.stderr)
            return 1
        stats = ingest_files(conn)
        print(f"ingested panel={stats['panel']:,} results={stats['results']:,} "
              f"(skipped {stats['panel_skipped']}+{stats['results_skipped']} malformed) -> {args.db}")
    a = audit(conn)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_audit_report(a), encoding="utf-8")
    issues = (a["dup_panel"] + a["dup_results"] + a["orphan_panel"] + a["score_out_of_range"]
              + a["component_out_of_range"] + a["empty_responses"] + a["unknown_arm"])
    print(f"audit -> {out} | {a['n_results']:,} responses, {a['n_panel']:,} judge rows, "
          f"{issues} integrity issue(s)")
    if args.neg_lift:
        rows = neg_lift_instances(conn, limit=args.neg_lift)
        print(f"\nWorst {len(rows)} negative-lift instances (harness_full < baseline):")
        print("  (lengths in chars; COLLAPSE = full arm < 40% of a substantive baseline)")
        for r in rows:
            bl, fl = r.get("base_len"), r.get("full_len")
            tag = "  <-COLLAPSE" if (bl and fl is not None and bl > 200 and fl < 0.4 * bl) else ""
            print(f"  {r['lift']:+6.1f}  {r['model']:<14} {r['prompt_id']:<30} "
                  f"base={r['baseline']}/{bl}c full={r['harnessed']}/{fl}c{tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
