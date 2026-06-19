#!/usr/bin/env python3
"""Domain OSINT enricher -- a scam/recruitment domain -> registrant + infra edges.

Turns a bare domain (e.g. a recruitment-scam website) into entities + ownership-graph
edges in the shared ``{subject, predicate, object, source, weight, qualifier}`` schema,
so a domain can be linked to the org behind it and clustered with sibling domains that
share registrar / nameserver / mail infrastructure -- then screened against the
registries via ``entity_screen``.

Two signals, both pure-Python + permissive (optional deps):
- **RDAP** (``whoisit``, BSD-3): structured registrant / registrar / admin / tech
  contacts -> ``org --registers/registrar_of/...--> domain``. Post-GDPR most gTLD
  registrant fields are "DATA REDACTED" -- handled honestly (skipped + a
  ``registrant_redacted`` flag); registrar + DNS still pivot.
- **DNS** (``dnspython``): NS / MX -> ``domain --hosted_on/mail_via--> host``. Shared
  NS/MX across two scam domains is a strong clustering edge.

Lookups are injectable, so the parsing is unit-tested offline; live mode uses whoisit +
dnspython if installed. Propose-only -- writes under reports/, never the live KB.

Usage:
    python scripts/domain_intel.py --domain suspicious-jobs.example
    python scripts/domain_intel.py --domains-file domains.txt --out reports/entity_kb/domains.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# RDAP contact role -> (edge predicate, confidence weight)
_ROLE_PRED = {"registrant": ("registers", 0.8), "registrar": ("registrar_of", 0.5),
              "administrative": ("admin_of", 0.6), "technical": ("tech_of", 0.4)}
_REDACTED = ("redacted", "data redacted", "not disclosed", "privacy", "withheld",
             "gdpr masked", "statutory masking enabled", "non-public data")


def _is_redacted(name: str) -> bool:
    n = (name or "").strip().lower()
    return not n or any(tok in n for tok in _REDACTED)


def parse_rdap(domain: str, rdap: dict) -> tuple[list[dict], list[dict]]:
    """RDAP record -> (entities, edges). Redacted/empty contacts are skipped."""
    server = rdap.get("whois_server") or rdap.get("rir") or "rdap"
    ents: list[dict] = []
    edges: list[dict] = []
    for role, (pred, weight) in _ROLE_PRED.items():
        for e in (rdap.get("entities") or {}).get(role) or []:
            name = (e.get("organization") or e.get("org") or e.get("name") or "").strip()
            if _is_redacted(name):
                continue
            ents.append({"name": name, "entity_type": "organization", "role": role,
                         "source": f"rdap:{server}"})
            edges.append({"subject_id": name, "predicate": pred, "object_id": domain,
                          "source": f"rdap:{server}", "weight": weight,
                          "qualifier": {"role": role, "email": e.get("email", "")}})
    return ents, edges


def parse_dns(domain: str, nameservers=None, mx=None) -> list[dict]:
    """NS / MX hosts -> domain --hosted_on/mail_via--> host edges."""
    edges = []
    for ns in nameservers or []:
        edges.append({"subject_id": domain, "predicate": "hosted_on",
                      "object_id": str(ns).lower().rstrip("."), "source": "dns",
                      "weight": 0.4, "qualifier": {"record": "NS"}})
    for m in mx or []:
        edges.append({"subject_id": domain, "predicate": "mail_via",
                      "object_id": str(m).lower().rstrip("."), "source": "dns",
                      "weight": 0.4, "qualifier": {"record": "MX"}})
    return edges


# ---------------------------------------------------------------------------
# Live lookups (optional deps; injectable for tests)
# ---------------------------------------------------------------------------

_BOOTSTRAPPED = [False]


def _live_rdap(domain: str) -> dict:
    import whoisit
    if not _BOOTSTRAPPED[0]:
        whoisit.bootstrap()
        _BOOTSTRAPPED[0] = True
    return whoisit.domain(domain)


def _live_dns(domain: str) -> tuple[list[str], list[str]]:
    import dns.resolver
    def _q(rtype):
        try:
            return [str(r.target if hasattr(r, "target") else r.exchange).rstrip(".")
                    for r in dns.resolver.resolve(domain, rtype)]
        except Exception:  # noqa: BLE001 - missing record set -> empty
            return []
    return _q("NS"), _q("MX")


def enrich(domain: str, *, rdap_fn=_live_rdap, dns_fn=_live_dns) -> dict:
    """Enrich one domain -> {domain, entities, edges, registrant_redacted}.

    Each lookup is best-effort: a failed RDAP or DNS call just yields fewer edges, never
    an exception, so a batch never dies on one bad domain.
    """
    domain = domain.strip().lower()
    rdap = {}
    try:
        rdap = rdap_fn(domain) or {}
    except Exception:  # noqa: BLE001 - RDAP unavailable / domain not found
        rdap = {}
    ents, edges = parse_rdap(domain, rdap)
    try:
        ns, mx = dns_fn(domain)
    except Exception:  # noqa: BLE001
        ns, mx = [], []
    edges += parse_dns(domain, ns, mx)
    return {"domain": domain, "entities": ents, "edges": edges,
            "registrant_redacted": not any(e["role"] == "registrant" for e in ents)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--domain", help="a single domain")
    src.add_argument("--domains-file", help="file with one domain per line")
    ap.add_argument("--out", help="propose-only edges JSONL (under reports/)")
    args = ap.parse_args(argv)

    domains = ([args.domain] if args.domain
               else [ln.strip() for ln in Path(args.domains_file).read_text(encoding="utf-8").splitlines()
                     if ln.strip()])
    results = [enrich(d) for d in domains]
    n_edges = sum(len(r["edges"]) for r in results)
    n_red = sum(1 for r in results if r["registrant_redacted"])
    print(f"domain_intel: {len(domains)} domains -> {n_edges} edges "
          f"({n_red} registrant-redacted)", file=sys.stderr)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results), encoding="utf-8")
        print(f"wrote {out} -- PROPOSE-ONLY")
    else:
        for r in results:
            for e in r["edges"][:8]:
                print(f"  {e['subject_id']} --{e['predicate']}--> {e['object_id']}  ({e['source']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
