#!/usr/bin/env python3
"""Link registry entities to GLEIF and stamp them with the canonical LEI (splink).

Different registries name the same real-world company differently ("Sunrise Overseas
Manpower Inc" vs "SUNRISE OVERSEAS MANPOWER INCORPORATED"); none of them carry a stable
cross-source id. GLEIF does: the **Legal Entity Identifier** (CC0). This connector uses
**splink** (probabilistic record linkage, MIT, DuckDB backend) to link each registry
record to its GLEIF record and propagate that record's LEI -- so entities sharing an LEI
are the same company across every source we hold.

Model (``link_only``): block on the local registration number and on
first-name-token+jurisdiction; compare on name (Jaro-Winkler), jurisdiction (exact), and
identifier (exact -- a registry ``company_no`` matches GLEIF's ``registered_as``). The
splink parameter estimation (u via sampling, m via EM) runs on the data; the row→LEI
assignment and the prepare/identifier helpers are pure and unit-tested. splink is an
optional dependency (``pip install splink``); the pure helpers import without it.

Propose-only: writes a linkage report under reports/, never mutates the live KB.

Usage:
    python scripts/entity_link.py --gleif gleif.jsonl --registry reg.jsonl --threshold 0.9
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_WORD = re.compile(r"[^a-z0-9 ]+")
_NONALNUM = re.compile(r"[^A-Za-z0-9]+")
# legal-form / generic tokens stripped before taking the first distinctive token
_GENERIC = {"the", "ltd", "limited", "inc", "incorporated", "llc", "plc", "co", "company",
            "corp", "corporation", "pte", "pvt", "private", "sdn", "bhd", "fze", "llp", "group"}


def _norm(name: str) -> str:
    return _WORD.sub(" ", str(name).lower()).strip()


def _first_token(norm_name: str) -> str:
    for tok in norm_name.split():
        if tok not in _GENERIC and len(tok) > 1:
            return tok
    return norm_name.split()[0] if norm_name.split() else ""


def _norm_id(v) -> str:
    return _NONALNUM.sub("", str(v or "")).upper()


def extract_identifier(rec: dict) -> str:
    """Best local registration number for joining (GLEIF registered_as ↔ registry no)."""
    for key in ("registered_as", "company_no"):
        if rec.get(key):
            return _norm_id(rec[key])
    lic = rec.get("license_no") or ""
    if ":" in lic:                      # "GB-COH:2063384560" -> the number
        lic = lic.split(":", 1)[1]
    return _norm_id(lic)


def to_rows(records: list[dict], source: str) -> list[dict]:
    """Records -> splink input rows (unique_id keeps the source + index for mapping back)."""
    rows = []
    for i, r in enumerate(records):
        nm = _norm(r.get("name", ""))
        rows.append({"unique_id": f"{source}-{i}", "name": nm,
                     "name_first_token": _first_token(nm),
                     "jurisdiction": (r.get("jurisdiction") or "").upper(),
                     "identifier": extract_identifier(r)})
    return rows


def best_lei_matches(preds, gleif_by_uid: dict, registry_by_uid: dict, threshold: float) -> list[dict]:
    """Pick, per registry record, its highest-probability GLEIF match >= threshold.

    ``preds`` is the splink predictions DataFrame (rows are gleif↔registry pairs). Returns
    one linkage dict per matched registry record, carrying the propagated LEI.
    """
    best: dict[str, tuple] = {}
    for row in preds.to_dict("records"):
        l, r = str(row["unique_id_l"]), str(row["unique_id_r"])
        if l.startswith("gleif") and r.startswith("registry"):
            g_uid, reg_uid = l, r
        elif r.startswith("gleif") and l.startswith("registry"):
            g_uid, reg_uid = r, l
        else:
            continue
        prob = float(row["match_probability"])
        if prob < threshold or reg_uid not in registry_by_uid or g_uid not in gleif_by_uid:
            continue
        if reg_uid not in best or prob > best[reg_uid][0]:
            best[reg_uid] = (prob, gleif_by_uid[g_uid])
    out = []
    for reg_uid, (prob, grec) in best.items():
        rrec = registry_by_uid[reg_uid]
        rid = extract_identifier(rrec)
        out.append({"registry_name": rrec.get("name", ""), "source": rrec.get("source", ""),
                    "lei": grec.get("lei", ""), "gleif_name": grec.get("name", ""),
                    "match_probability": round(prob, 4),
                    "via": "identifier" if rid and rid == extract_identifier(grec) else "name"})
    return sorted(out, key=lambda d: -d["match_probability"])


def summarize(linkages: list[dict], n_registry: int) -> dict:
    return {"registry": n_registry, "linked": len(linkages),
            "link_rate": round(len(linkages) / n_registry, 3) if n_registry else 0.0,
            "via_identifier": sum(1 for d in linkages if d["via"] == "identifier")}


def link_to_gleif(gleif_records: list[dict], registry_records: list[dict], *,
                  threshold: float = 0.9, max_pairs: int = 200_000) -> list[dict]:
    """Run a splink ``link_only`` model and return registry→GLEIF linkages (with LEI)."""
    import pandas as pd
    from splink import DuckDBAPI, Linker, SettingsCreator, block_on
    from splink import comparison_library as cl

    g_rows, r_rows = to_rows(gleif_records, "gleif"), to_rows(registry_records, "registry")
    settings = SettingsCreator(
        link_type="link_only",
        blocking_rules_to_generate_predictions=[
            block_on("identifier"),
            block_on("name_first_token", "jurisdiction"),
        ],
        comparisons=[
            cl.JaroWinklerAtThresholds("name", [0.92, 0.85]),
            cl.ExactMatch("jurisdiction"),
            cl.ExactMatch("identifier"),
        ],
    )
    linker = Linker([pd.DataFrame(g_rows), pd.DataFrame(r_rows)], settings,
                    db_api=DuckDBAPI(), input_table_aliases=["gleif", "registry"])
    # parameter estimation -- guarded: tiny / degenerate data can make a step fail, but a
    # partially-trained model still predicts usefully (an exact id+name match scores high).
    for step in (
        lambda: linker.training.estimate_probability_two_random_records_match(
            [block_on("identifier")], recall=0.6),
        lambda: linker.training.estimate_u_using_random_sampling(max_pairs=max_pairs),
        lambda: linker.training.estimate_parameters_using_expectation_maximisation(
            block_on("name_first_token")),
    ):
        try:
            step()
        except Exception:  # noqa: BLE001 - best-effort training, never fatal
            pass
    preds = linker.inference.predict(
        threshold_match_probability=min(threshold, 0.5)).as_pandas_dataframe()
    g_by = {row["unique_id"]: rec for row, rec in zip(g_rows, gleif_records)}
    r_by = {row["unique_id"]: rec for row, rec in zip(r_rows, registry_records)}
    return best_lei_matches(preds, g_by, r_by, threshold)


def _read_jsonl(path: str) -> list[dict]:
    return [json.loads(ln) for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gleif", required=True, help="JSONL of GLEIF entities (gleif_lei.py output)")
    ap.add_argument("--registry", required=True, help="JSONL of registry entities to link")
    ap.add_argument("--threshold", type=float, default=0.9, help="min match probability")
    ap.add_argument("--out", help="propose-only linkage JSONL (under reports/)")
    args = ap.parse_args(argv)

    gleif, registry = _read_jsonl(args.gleif), _read_jsonl(args.registry)
    links = link_to_gleif(gleif, registry, threshold=args.threshold)
    print(f"linked {summarize(links, len(registry))}", file=sys.stderr)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in links), encoding="utf-8")
        print(f"wrote {out} -- PROPOSE-ONLY")
    else:
        for d in links[:15]:
            print(f"  {d['lei']}  {d['registry_name'][:38]} ~ {d['gleif_name'][:34]} "
                  f"(p={d['match_probability']}, {d['via']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
