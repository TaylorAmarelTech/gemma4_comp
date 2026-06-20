#!/usr/bin/env python3
"""Multi-layer acquisition cascade -- escalate from cheap to powerful, archive all.

"Can we have multiple layers of agents -- research agents, LLM-driven browsers,
deterministic/LLM-assisted scrapers?" Yes: this is the orchestrator that runs
them as an ESCALATING WATERFALL. It tries the cheapest, most-deterministic layer
first and only escalates to a more powerful (and token-hungry) one when the
cheaper layer fails -- the same triage pattern the project uses elsewhere
(GREP -> fast model -> deep).

Layers (cheap -> powerful), each a pluggable acquirer:
  tier 0  RESEARCH       -- OpenClaw/Hermes + the research monitor: discover WHERE
                            the data lives (source/endpoint) for an unknown target
  tier 1  DETERMINISTIC  -- browser_scrape (JSON API / table / preset), hk_eaa,
                            scrape_agency_sources: free, reliable, NO tokens
  tier 2  LLM_ASSISTED   -- llm_scrape (rules -> LLM gap-fill): a few tokens
  tier 3  AGENTIC        -- agentic_browse (Gemma drives the browser): more tokens
  tier 4  VISION         -- llm_scrape screenshot -> Gemma 4 vision: opaque DOMs

Robustness + PROVENANCE: every outbound URL the cascade touches (the target plus
any endpoints an acquirer discovers) is submitted to web archives (Wayback +
archive.today) via archive_source -- a complete, citable trail. Archival is
best-effort and NEVER breaks acquisition.

Design: acquirers and the archive function are injectable, so the escalation
logic, fault isolation, cost accounting, and the archive sweep are tested
offline with fakes -- no browser, no model, no network. Propose-only.

Usage:
    python scripts/acquisition_cascade.py --url https://reg.gov/agencies \
        --fields name,license_no,status --max-tier 3
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_cascade", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _err(tier, name, exc):
    return {"tier": tier, "name": name, "records": [], "n": 0, "confidence": 0.0,
            "cost": "n/a", "discovered_urls": [], "note": "", "error": f"{type(exc).__name__}: {exc}"[:180]}


# ---- the cascade core (tested) --------------------------------------------

def run_cascade(target: dict, acquirers, *, escalate: bool = True, min_records: int = 1,
                archive_fn=None, archived_at: str = "") -> dict:
    """Run `acquirers` (ordered cheap->powerful) over `target`. Escalate: stop at
    the first layer that yields >= min_records. Then archive every URL touched.

    Each acquirer is `callable(target) -> {tier,name,records,n,confidence,cost,
    discovered_urls,note,error}` and must not raise (guarded here regardless).
    `archive_fn(url) -> result` is injectable; archival is best-effort."""
    url = target.get("url", "")
    archived_urls: list[str] = [url] if url else []
    seen_urls = set(archived_urls)
    attempts, won, records = [], None, []

    for acq in acquirers:
        try:
            r = acq(target)
        except Exception as exc:  # noqa: BLE001 -- belt-and-braces
            r = _err("?", getattr(acq, "__name__", "acquirer"), exc)
        for u in (r.get("discovered_urls") or []):
            if u and u not in seen_urls:
                seen_urls.add(u)
                archived_urls.append(u)
        attempts.append({k: r.get(k) for k in ("tier", "name", "n", "confidence", "cost", "note", "error")})
        if r.get("records"):
            if not records:
                records, won = r["records"], r
            if escalate and len(r["records"]) >= min_records:
                break

    archived = []
    if archive_fn:
        for u in archived_urls:
            try:
                archived.append(archive_fn(u))
            except Exception as exc:  # noqa: BLE001 -- archival never breaks acquisition
                archived.append({"url": u, "status": f"error_{type(exc).__name__}"})

    return {"target": target.get("name") or url, "won_by": won["name"] if won else None,
            "tier": won.get("tier") if won else None, "n_records": len(records),
            "records": records, "attempts": attempts,
            "archived_urls": archived_urls, "archived": archived, "archived_at": archived_at}


# ---- built-in acquirers (thin real adapters; cheap -> powerful) ------------

def acq_deterministic(target: dict) -> dict:
    """Tier 1: deterministic scrape (browser_scrape preset/generic). No tokens."""
    try:
        preset = target.get("preset", "")
        # a registry with a special deterministic resolver (e.g. hk_eaa result.php)
        if preset in REGISTRY_RESOLVERS:
            return REGISTRY_RESOLVERS[preset](target)
        bs = _sibling("browser_scrape")
        url = target.get("url", "")
        if preset in bs.PRESETS:
            cfg = bs.PRESETS[preset]
        elif url:
            cfg = bs.BrowserCapture(url=url, label="cascade", max_pages=int(target.get("max_pages", 2)))
        else:
            return {"tier": 1, "name": "deterministic", "records": [], "n": 0, "confidence": 0.0,
                    "cost": "none", "discovered_urls": [], "note": "no url/preset", "error": ""}
        result = bs.render_and_capture(cfg)
        profiles, endpoint = bs.captures_to_profiles(result, source="cascade")
        return {"tier": 1, "name": "deterministic", "records": profiles, "n": len(profiles),
                "confidence": 0.9 if profiles else 0.0, "cost": "none",
                "discovered_urls": ([url] + list(result.discovered_endpoints[:6])),
                "note": f"endpoint {endpoint}" if endpoint else "rendered", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(1, "deterministic", exc)


def acq_llm_assisted(target: dict) -> dict:
    """Tier 2: llm_scrape (deterministic rules -> LLM gap-fill). Few tokens."""
    try:
        ls = _sibling("llm_scrape")
        url = target.get("url", "")
        fields = target.get("fields") or ["name", "license_no", "status", "address", "phone", "email"]
        mf = ls.text_model_fn()
        res = ls.scrape_page(url, fields, model_fn=mf, tier="auto")
        rec = res.get("extracted") or {}
        records = [rec] if any(rec.values()) else []
        return {"tier": 2, "name": "llm_assisted", "records": records, "n": len(records),
                "confidence": 0.7 if records else 0.0,
                "cost": "tokens" if res.get("tokens_used") else "none",
                "discovered_urls": [url], "note": f"det={res.get('n_deterministic')}", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(2, "llm_assisted", exc)


def acq_agentic(target: dict) -> dict:
    """Tier 3: agentic_browse -- Gemma drives the browser. More tokens."""
    try:
        ab = _sibling("agentic_browse")
        url, goal = target.get("url", ""), target.get("goal", "extract the list of records on this page")
        cfg = ab._model_config()
        if not cfg["base_url"]:
            return {"tier": 3, "name": "agentic", "records": [], "n": 0, "confidence": 0.0,
                    "cost": "tokens", "discovered_urls": [url], "note": "no model endpoint", "error": ""}
        executor = ab.make_playwright_executor()
        try:
            executor.navigate(url)
            result = ab.run_agent(goal, executor, lambda **kw: ab.gemma_model_fn(cfg=cfg, **kw),
                                  max_steps=int(target.get("max_steps", 8)))
        finally:
            getattr(executor, "close", lambda: None)()
        recs = result.get("records", [])
        return {"tier": 3, "name": "agentic", "records": recs, "n": len(recs),
                "confidence": 0.6 if recs else 0.0, "cost": "tokens",
                "discovered_urls": [url], "note": result.get("stop_reason", ""), "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(3, "agentic", exc)


def acq_vision(target: dict) -> dict:
    """Tier 4: llm_scrape vision -- screenshot -> Gemma 4 vision. Opaque DOMs."""
    try:
        ls = _sibling("llm_scrape")
        url = target.get("url", "")
        fields = target.get("fields") or ["name", "license_no", "status", "address"]
        vf = ls.vision_model_fn()
        if vf is None:
            return {"tier": 4, "name": "vision", "records": [], "n": 0, "confidence": 0.0,
                    "cost": "vision-tokens", "discovered_urls": [url], "note": "no model", "error": ""}
        res = ls.scrape_page(url, fields, vision_model_fn=vf, want_screenshot=True, tier="deterministic")
        rec = res.get("vision_extracted") or {}
        records = [rec] if any(rec.values()) else []
        return {"tier": 4, "name": "vision", "records": records, "n": len(records),
                "confidence": 0.5 if records else 0.0, "cost": "vision-tokens",
                "discovered_urls": [url], "note": "screenshot read", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(4, "vision", exc)


# ---- registry presets (proven deterministic routes win at tier 1, free) ----

def _resolve_hk_eaa(target: dict) -> dict:
    """HK EAA via the deterministic result.php path (cookie bypass + token POST)."""
    try:
        hk = _sibling("hk_eaa_collector")
        res = hk._playwright_collect_live(max_pages=int(target.get("max_pages", 400)))
        recs = hk.records_to_entities(res.get("records", []))
        return {"tier": 1, "name": "deterministic", "records": recs, "n": len(recs),
                "confidence": 0.95 if recs else 0.0, "cost": "none",
                "discovered_urls": ["https://www.eaa.labour.gov.hk/en/result.php"],
                "note": f"hk_eaa result.php {res.get('pages')}pg", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(1, "deterministic", exc)


def _resolve_ofac_sdn(target: dict) -> dict:
    """OFAC SDN sanctioned entities (keyless CSV)."""
    try:
        ss = _sibling("sanctions_sources")
        recs = ss.fetch_ofac_sdn()
        return {"tier": 1, "name": "deterministic", "records": recs, "n": len(recs),
                "confidence": 0.95 if recs else 0.0, "cost": "none",
                "discovered_urls": [ss.OFAC_SDN_CSV], "note": "OFAC SDN csv", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(1, "deterministic", exc)


def _resolve_worldbank_debarred(target: dict) -> dict:
    """World Bank debarred firms (browser-captured keyless JSON)."""
    try:
        ss = _sibling("sanctions_sources")
        recs = ss.fetch_worldbank_debarred()
        return {"tier": 1, "name": "deterministic", "records": recs, "n": len(recs),
                "confidence": 0.95 if recs else 0.0, "cost": "none",
                "discovered_urls": [ss.WORLDBANK_DEBARRED_PAGE], "note": "WB SANCTIONED_FIRM", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(1, "deterministic", exc)


def _resolve_hk_money_lenders(target: dict) -> dict:
    """HK Companies Registry licensed money lenders (deterministic PDF parse)."""
    try:
        hk = _sibling("hk_money_lenders")
        recs = hk.records_to_entities(hk.collect())
        return {"tier": 1, "name": "deterministic", "records": recs, "n": len(recs),
                "confidence": 0.95 if recs else 0.0, "cost": "none",
                "discovered_urls": [hk.ML_PDF], "note": "HK CR money-lender PDF", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(1, "deterministic", exc)


def _resolve_bd_oep(target: dict) -> dict:
    """BD OEP/BMET licensed overseas recruiting agencies (deterministic HTML table)."""
    try:
        bd = _sibling("bd_oep_agencies")
        recs = bd.records_to_entities(bd.collect())
        return {"tier": 1, "name": "deterministic", "records": recs, "n": len(recs),
                "confidence": 0.95 if recs else 0.0, "cost": "none",
                "discovered_urls": [bd.OEP_URL], "note": "BD OEP recruiting agencies", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(1, "deterministic", exc)


def _resolve_bd_mra(target: dict) -> dict:
    """BD MRA licensed microfinance institutions (deterministic JSON API)."""
    try:
        bd = _sibling("bd_mra_mfi")
        recs = bd.records_to_entities(bd.collect())
        return {"tier": 1, "name": "deterministic", "records": recs, "n": len(recs),
                "confidence": 0.95 if recs else 0.0, "cost": "none",
                "discovered_urls": [bd.MRA_URL], "note": "BD MRA licensed MFIs", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(1, "deterministic", exc)


def _resolve_cn_mara(target: dict) -> dict:
    """CN MARA distant-water-fishing enterprise compliance (deterministic HTML)."""
    try:
        cn = _sibling("cn_mara_dwf")
        recs = cn.records_to_entities(cn.collect())
        return {"tier": 1, "name": "deterministic", "records": recs, "n": len(recs),
                "confidence": 0.95 if recs else 0.0, "cost": "none",
                "discovered_urls": [cn.MARA_URL], "note": "CN MARA DWF compliance", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(1, "deterministic", exc)


def _resolve_au_afma(target: dict) -> dict:
    """AU AFMA commercial-fishery concession holders (deterministic XLSX sweep)."""
    try:
        au = _sibling("au_afma_concessions")
        recs = au.records_to_entities(au.collect())
        return {"tier": 1, "name": "deterministic", "records": recs, "n": len(recs),
                "confidence": 0.95 if recs else 0.0, "cost": "none",
                "discovered_urls": [au.AFMA_PAGE], "note": "AU AFMA concession holders", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(1, "deterministic", exc)


def _resolve_gleif_lei(target: dict) -> dict:
    """GLEIF LEI legal entities (CC0). The corpus is ~2.5M, so a cascade pull takes a
    bounded slice -- pass ``--arg country=AE``, ``--arg limit=300``, ``--arg name_filter=...``;
    defaults to a Nepal (origin-corridor) sample at limit 200."""
    try:
        gl = _sibling("gleif_lei")
        country = target.get("country") or "NP"
        name = target.get("name_filter")
        limit = int(target.get("limit", 200))
        recs = gl.fetch_lei_records(country=country, name=name, limit=limit)
        note = f"GLEIF LEI country={country} limit={limit}" + (f" name={name}" if name else "")
        return {"tier": 1, "name": "deterministic", "records": recs, "n": len(recs),
                "confidence": 0.9 if recs else 0.0, "cost": "none",
                "discovered_urls": [gl._BASE], "note": note, "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(1, "deterministic", exc)


_BODS_DEFAULT_URL = ("https://raw.githubusercontent.com/openownership/data-standard/"
                     "main/examples/bods-package.json")


def _resolve_openownership_bods(target: dict) -> dict:
    """OpenOwnership BODS beneficial-ownership entities (CC0). The full register is bulk
    (~GB); a cascade pull takes whatever BODS slice it is pointed at -- pass
    ``--arg bods_url=<https json/jsonl>`` (or use ``openownership_bods.py --file`` for a
    local bulk file). Defaults to the CC0 data-standard example package."""
    try:
        bods = _sibling("openownership_bods")
        url = target.get("bods_url") or _BODS_DEFAULT_URL
        recs = bods.parse_bods(bods.iter_statements(bods.load_text(url=url)))
        return {"tier": 1, "name": "deterministic", "records": recs, "n": len(recs),
                "confidence": 0.9 if recs else 0.0, "cost": "none",
                "discovered_urls": [url], "note": f"OpenOwnership BODS {url}", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return _err(1, "deterministic", exc)


# registries with a SPECIAL deterministic resolver (not a plain browser_scrape preset)
REGISTRY_RESOLVERS = {"hk_eaa": _resolve_hk_eaa, "ofac_sdn": _resolve_ofac_sdn,
                      "worldbank_debarred": _resolve_worldbank_debarred,
                      "hk_money_lenders": _resolve_hk_money_lenders,
                      "bd_oep": _resolve_bd_oep, "bd_mra": _resolve_bd_mra,
                      "cn_mara": _resolve_cn_mara, "au_afma": _resolve_au_afma,
                      "gleif_lei": _resolve_gleif_lei,
                      "openownership_bods": _resolve_openownership_bods}

# proven deterministic registries addressable by --registry (dmw_lra is a
# browser_scrape preset; the rest have resolvers above).
PROVEN_REGISTRIES = {
    "dmw_lra": {"preset": "dmw_lra", "name": "PH DMW -- licensed recruitment agencies (master-api)"},
    "hk_eaa": {"preset": "hk_eaa", "name": "HK EAA -- licensed employment agencies (result.php)"},
    "hk_money_lenders": {"preset": "hk_money_lenders", "name": "HK CR -- licensed money lenders (PDF)"},
    "bd_oep": {"preset": "bd_oep", "name": "BD OEP/BMET -- licensed recruiting agencies (HTML)"},
    "bd_mra": {"preset": "bd_mra", "name": "BD MRA -- licensed microfinance institutions (JSON)"},
    "cn_mara": {"preset": "cn_mara", "name": "CN MARA -- distant-water-fishing compliance (HTML)"},
    "au_afma": {"preset": "au_afma", "name": "AU AFMA -- fishery concession holders (XLSX)"},
    "ofac_sdn": {"preset": "ofac_sdn", "name": "US OFAC SDN -- sanctioned entities (CSV)"},
    "worldbank_debarred": {"preset": "worldbank_debarred", "name": "World Bank -- debarred firms (JSON)"},
    "gleif_lei": {"preset": "gleif_lei", "name": "GLEIF -- LEI legal entities + ownership (CC0; bounded slice via --arg country=/limit=)"},
    "openownership_bods": {"preset": "openownership_bods", "name": "OpenOwnership BODS -- beneficial owners (CC0; --arg bods_url=, else CC0 sample)"},
}


def _make_spec_resolver(spec_id: str, url: str):
    """A tier-1 resolver that runs a config-driven registry_spec by id."""
    def _resolve(target: dict) -> dict:
        try:
            rs = _sibling("registry_spec")
            recs = rs.resolve_id(spec_id)
            return {"tier": 1, "name": "deterministic", "records": recs, "n": len(recs),
                    "confidence": 0.9 if recs else 0.0, "cost": "none",
                    "discovered_urls": [url], "note": f"spec {spec_id}", "error": ""}
        except Exception as exc:  # noqa: BLE001
            return _err(1, "deterministic", exc)
    return _resolve


# every spec in registry_specs.yaml becomes an addressable --registry id (guarded:
# a missing/broken spec catalogue must never break the rest of the cascade).
try:
    for _sid, _spec in _sibling("registry_spec").load_specs().items():
        if _sid not in REGISTRY_RESOLVERS:
            REGISTRY_RESOLVERS[_sid] = _make_spec_resolver(_sid, _spec.get("url", ""))
            PROVEN_REGISTRIES[_sid] = {"preset": _sid,
                                       "name": _spec.get("source", _sid) + " (config spec)"}
except Exception:  # noqa: BLE001
    pass

_CATALOGS = (
    _ROOT / "configs" / "duecare" / "research_monitor" / "entity_sources.yaml",
    _ROOT / "configs" / "duecare" / "research_monitor" / "licensed_entity_sources.yaml",
)


def load_known_sources(paths=_CATALOGS) -> dict:
    """id -> url for every catalogued registry across BOTH catalogues (the
    trafficking-corridor sources + the country x industry licensed-entity matrix),
    so the cascade can target any of them by id."""
    out: dict = {}
    try:
        import yaml
    except Exception:  # noqa: BLE001
        return out
    for p in ([paths] if isinstance(paths, (str, Path)) else paths):
        try:
            data = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
            for s in (data.get("sources") or []):
                if s.get("id") and s.get("url"):
                    out[str(s["id"])] = str(s["url"])
        except Exception:  # noqa: BLE001
            continue
    return out


def resolve_registry(key: str, *, sources=None) -> dict:
    """Resolve a registry key to a target spec: a proven preset, else a catalogued
    source URL (which runs the generic ladder), else {}."""
    if key in PROVEN_REGISTRIES:
        return dict(PROVEN_REGISTRIES[key])
    srcs = sources if sources is not None else load_known_sources()
    if key in srcs:
        return {"url": srcs[key], "name": key}
    return {}


# acquirers in escalation order; slice by --max-tier
LADDER = [acq_deterministic, acq_llm_assisted, acq_agentic, acq_vision]


# ---- CLI -------------------------------------------------------------------

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:50] or "target"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", help="target URL to acquire records from")
    ap.add_argument("--preset", default="", help="a browser_scrape preset (e.g. dmw_lra)")
    ap.add_argument("--registry", default="", help="a registry key (proven preset or catalogued id)")
    ap.add_argument("--list-registries", action="store_true", help="list addressable registries + exit")
    ap.add_argument("--arg", action="append", default=[],
                    help="KEY=VALUE resolver param (repeatable), e.g. country=NP limit=300 for gleif_lei")
    ap.add_argument("--fields", default="name,license_no,status,address,phone,email")
    ap.add_argument("--goal", default="extract the list of records on this page")
    ap.add_argument("--max-tier", type=int, default=4, help="highest layer to escalate to (1-4)")
    ap.add_argument("--no-escalate", action="store_true", help="run every layer (do not stop at first success)")
    ap.add_argument("--no-archive", action="store_true", help="skip archiving outbound URLs")
    ap.add_argument("--archives", default="wayback,archive_today")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    known = load_known_sources()
    if args.list_registries:
        print("PROVEN deterministic registries (win at tier 1, free):", file=sys.stderr)
        for k, v in PROVEN_REGISTRIES.items():
            print(f"  {k:<16} {v['name']}", file=sys.stderr)
        print(f"\nCatalogued sources addressable by --registry <id> ({len(known)}):", file=sys.stderr)
        for k in sorted(known):
            print(f"  {k}", file=sys.stderr)
        return 0

    url, preset = args.url or "", args.preset
    if args.registry:
        spec = resolve_registry(args.registry, sources=known)
        if not spec:
            print(f"unknown registry {args.registry!r}; --list-registries to see options", file=sys.stderr)
            return 2
        preset = spec.get("preset", preset)
        url = spec.get("url", url)
    if not url and not preset:
        ap.error("provide --url, --preset, or --registry")
    extra = {}
    for _kv in args.arg:
        if "=" in _kv:
            _k, _v = _kv.split("=", 1)
            extra[_k.strip()] = _v.strip()
    target = {"url": url, "preset": preset,
              "fields": [f.strip() for f in args.fields.split(",") if f.strip()],
              "goal": args.goal, **extra}

    acquirers = [a for i, a in enumerate(LADDER) if i + 1 <= args.max_tier]

    archive_fn = None
    if not args.no_archive:
        ar = _sibling("archive_source")
        archs = tuple(s.strip() for s in args.archives.split(",") if s.strip())
        archive_fn = lambda u: {a: ar.archive_one(u, a) for a in archs}

    print(f"cascade over {len(acquirers)} layer(s) (max-tier {args.max_tier}); "
          f"archive={not args.no_archive}", file=sys.stderr)
    res = run_cascade(target, acquirers, escalate=not args.no_escalate, archive_fn=archive_fn)

    out = Path(args.out) if args.out else (_ROOT / "reports" / "acquisition" / f"cascade_{_slug(args.url or args.preset)}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"_synthetic": False, **res}, indent=2, ensure_ascii=False), encoding="utf-8")
    for a in res["attempts"]:
        flag = f"ERROR {a['error']}" if a["error"] else f"{a['n']} records (cost={a['cost']})"
        print(f"  [tier {a['tier']}: {a['name']:<14}] {flag}", file=sys.stderr)
    print(f"\nWON BY: {res['won_by']} (tier {res['tier']}) -> {res['n_records']} records", file=sys.stderr)
    print(f"archived {len(res['archived_urls'])} outbound URL(s) -> {out}", file=sys.stderr)
    return 0 if res["n_records"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
