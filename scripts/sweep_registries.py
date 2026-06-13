#!/usr/bin/env python3
"""Sweep the deterministic browser connector across the catalogued registries.

The entity-source catalogue (configs/duecare/research_monitor/entity_sources.yaml)
lists 72 real public registries. This runs the deterministic Playwright connector
(scripts/browser_scrape.py) in generic `--url` mode against the official, fetchable
ones and reports an EMPIRICAL access matrix -- not a guess:

  * extracted    -- the connector auto-parsed an agency list (turnkey, like DMW)
  * endpoint_only-- JSON data endpoint(s) discovered but the list needs a search
                    term / selector / site-specific schema (a preset candidate)
  * no_data      -- no useful JSON captured (server-rendered HTML, or needs a
                    click to load) -- candidate for the agentic Gemma agent
  * error        -- the render failed

Endpoint DISCOVERY is itself the payoff: it tells us where each registry's data
lives so a per-site preset (or the agentic agent) can finish the job. Honest by
construction -- it records what actually happened per site, nothing claimed.

Real-not-faked + propose-only: writes a matrix to reports/agency_registry/ and
NEVER mutates live knowledge. Polite: the connector is rate-limited, page-capped
(low for a sweep -- we are mapping, not bulk-pulling), and UA-identified. PDFs,
spreadsheets, manual/captcha, and freemium sources are skipped (different tools).

Usage:
    python scripts/sweep_registries.py                  # sweep official free/api registries
    python scripts/sweep_registries.py --max 8 --pages 2
    python scripts/sweep_registries.py --ids hk_eaa_search_en,bd_oep_agencies
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CATALOG = _ROOT / "configs" / "duecare" / "research_monitor" / "entity_sources.yaml"
_ALREADY_DONE = {"dmw"}  # substrings of urls/ids we have a dedicated path for


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_sweep", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_SKIP_SUFFIXES = (".pdf", ".xlsx", ".xls", ".csv", ".doc", ".docx", ".zip")


def select_candidates(sources: list[dict], *, ids: set[str] | None = None) -> list[dict]:
    """Pick official, fetchable, agency-bearing registries worth a browser sweep."""
    out = []
    for s in sources:
        sid = str(s.get("id", ""))
        url = str(s.get("url", ""))
        if ids is not None:
            if sid in ids:
                out.append(s)
            continue
        if not url.startswith("http"):
            continue
        if url.lower().rsplit("?", 1)[0].endswith(_SKIP_SUFFIXES):
            continue
        if not s.get("official"):
            continue
        if s.get("access_tier") not in ("free", "api"):  # skip manual/captcha/freemium
            continue
        if any(d in url.lower() or d in sid.lower() for d in _ALREADY_DONE):
            continue
        # must plausibly carry agency/clinic/employer entities (skip pure guidance)
        ents = set(s.get("entity_types", []))
        if not (ents & {"recruitment_agency", "manning_agency", "employer",
                        "medical_clinic", "training_center", "sanctioned_entity"}):
            continue
        out.append(s)
    return out


def _classify(n_endpoints: int, n_records: int, error: str) -> str:
    if error:
        return "error"
    if n_records > 0:
        return "extracted"
    if n_endpoints > 0:
        return "endpoint_only"
    return "no_data"


def sweep(candidates: list[dict], *, renderer=None, max_pages: int = 2,
          log=None) -> list[dict]:
    """Run the connector over each candidate; return a result row per registry.
    `renderer` is injectable for tests (no browser)."""
    bs = _load_sibling("browser_scrape")
    results = []
    for s in candidates:
        sid, url = str(s.get("id", "")), str(s.get("url", ""))
        row = {"id": sid, "url": url, "publisher": s.get("publisher", ""),
               "entity_types": s.get("entity_types", []),
               "jurisdictions": s.get("jurisdictions", []),
               "n_endpoints": 0, "agency_endpoint": "", "n_records": 0,
               "last_page": None, "sample_names": [], "status": "", "error": ""}
        try:
            cfg = bs.BrowserCapture(url=url, label=sid, max_pages=max_pages, min_interval_s=0.8)
            result = bs.render_and_capture(cfg, renderer=renderer)
            row["n_endpoints"] = len(result.discovered_endpoints)
            profiles, endpoint = bs.captures_to_profiles(result, source=f"sweep:{sid}")
            row["agency_endpoint"] = endpoint
            row["n_records"] = len(profiles)
            row["sample_names"] = [p.get("name", "") for p in profiles[:3]]
            for cap in result.payloads:  # surface a detected page count if any
                try:
                    lp = bs._pagination_last_page(json.loads(cap["text"]))
                except Exception:  # noqa: BLE001
                    lp = None
                if lp:
                    row["last_page"] = lp
                    break
        except Exception as exc:  # noqa: BLE001
            row["error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
        row["status"] = _classify(row["n_endpoints"], row["n_records"], row["error"])
        results.append(row)
        if log:
            log(f"{sid}: {row['status']} (endpoints={row['n_endpoints']}, "
                f"records={row['n_records']}{', '+row['error'] if row['error'] else ''})")
    return results


def load_catalog(path: Path | str = _CATALOG) -> list[dict]:
    import yaml
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return data.get("sources", []) if isinstance(data, dict) else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default=str(_CATALOG))
    ap.add_argument("--ids", default="", help="comma-separated source ids to sweep (overrides selection)")
    ap.add_argument("--max", type=int, default=0, help="cap the number of registries swept")
    ap.add_argument("--pages", type=int, default=2, help="max pages per registry (sweep stays shallow)")
    ap.add_argument("--out", default=str(_ROOT / "reports" / "agency_registry" / "registry_sweep.json"))
    args = ap.parse_args(argv)

    sources = load_catalog(args.catalog)
    ids = set(x.strip() for x in args.ids.split(",") if x.strip()) or None
    candidates = select_candidates(sources, ids=ids)
    if args.max:
        candidates = candidates[:args.max]
    print(f"sweeping {len(candidates)} registr(ies) with the deterministic connector "
          f"(<= {args.pages} pages each)...", file=sys.stderr)

    results = sweep(candidates, max_pages=args.pages, log=lambda m: print("  " + m, file=sys.stderr))

    from collections import Counter
    by_status = dict(Counter(r["status"] for r in results))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"_synthetic": False, "n_candidates": len(results),
                               "by_status": by_status, "results": results},
                              indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== registry sweep matrix ===", file=sys.stderr)
    for r in sorted(results, key=lambda x: (x["status"], -x["n_records"])):
        print(f"  [{r['status']:<13}] {r['id']:<34} records={r['n_records']:<5} "
              f"endpoints={r['n_endpoints']}  {r['agency_endpoint'][:60]}", file=sys.stderr)
    print(f"\nstatus totals: {by_status}", file=sys.stderr)
    print(f"matrix -> {out}", file=sys.stderr)
    extracted = [r for r in results if r["status"] == "extracted"]
    if extracted:
        print(f"\nturnkey registries ({len(extracted)}) -- ingest with entity_kb --ingest:",
              file=sys.stderr)
        for r in extracted:
            print(f"  {r['id']}: {r['n_records']} records via {r['agency_endpoint'][:70]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
