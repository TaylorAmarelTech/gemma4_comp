#!/usr/bin/env python3
"""Single source of truth for the entity-intelligence counts.

Every count the docs + the render `/source-verification` page quote (registries, config
specs, deterministic resolvers, catalogued sources, support orgs, connectors) is *derived*
here from the live configs + the cascade -- never hand-typed in N places. `compute_counts()`
is pure (reads `configs/duecare/research_monitor/*.yaml` + imports the cascade; no network);
`--write` regenerates the published `entity_counts.json` the render page reads; and
`tests/test_entity_count_drift.py` fails CI if any doc/page literal drifts from these values.

Usage:
    python scripts/entity_counts.py            # print the counts
    python scripts/entity_counts.py --write    # regenerate app/static/entity_counts.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CFG = _ROOT / "configs" / "duecare" / "research_monitor"
_JSON_OUT = _ROOT / "apps" / "duecare-ai.com" / "app" / "static" / "entity_counts.json"
#: the 12 session connectors (canonical map §"Connectors")
_CONNECTORS = ("gleif_lei", "gleif_rr", "openownership_bods", "entity_link",
               "cluster_registries", "domain_intel", "doj_press", "dol_whd",
               "harvest_opensanctions_sources", "opensanctions_to_specs",
               "tooling_scout", "image_enhance")


def _count_list(path: Path) -> int:
    """Length of the catalogue's record list, robust to the top-level key name."""
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    lists = [len(v) for v in data.values() if isinstance(v, list)]
    return max(lists) if lists else 0


def _cascade_registries() -> tuple[int, int, int]:
    """(total, config_specs, deterministic) from the live cascade registration (no network)."""
    def _sib(name: str):
        spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    for dep in ("registry_parsers", "registry_spec"):
        _sib(dep)
    reg = _sib("acquisition_cascade").PROVEN_REGISTRIES
    config_specs = sum(1 for v in reg.values() if "(config spec)" in str(v.get("name", "")))
    return len(reg), config_specs, len(reg) - config_specs


def compute_counts() -> dict:
    """The canonical counts. Pure -- reads configs + the cascade, never the network."""
    total, config_specs, deterministic = _cascade_registries()
    return {
        "registries": total,
        "config_specs": config_specs,
        "deterministic_resolvers": deterministic,
        "licensed_sources": _count_list(_CFG / "licensed_entity_sources.yaml"),
        "support_orgs": _count_list(_CFG / "migrant_support_orgs.yaml"),
        "monitored_sources": _count_list(_CFG / "entity_sources.yaml"),
        "connectors": sum((_ROOT / "scripts" / f"{c}.py").exists() for c in _CONNECTORS),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true",
                    help=f"regenerate {_JSON_OUT.relative_to(_ROOT)}")
    args = ap.parse_args(argv)
    counts = compute_counts()
    if args.write:
        _JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
        _JSON_OUT.write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {_JSON_OUT}", file=sys.stderr)
    print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
