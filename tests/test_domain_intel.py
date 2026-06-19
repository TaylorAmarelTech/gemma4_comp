"""Tests for scripts/domain_intel.py -- domain RDAP/DNS -> entity + edge enrichment.

Offline: the RDAP/DNS parsing is pure; the live lookups are injected. The RDAP fixture
mirrors a real whoisit response (cloudflare.com, captured 2026-06-19) incl. GDPR-redacted
registrant.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


di = _load("domain_intel", _ROOT / "scripts" / "domain_intel.py")

RDAP = {"name": "cloudflare.com", "whois_server": "whois.cloudflare.com", "entities": {
    "registrar": [{"name": "Cloudflare, Inc.", "email": "registrar-admin@cloudflare.com"}],
    "registrant": [{"name": "DATA REDACTED", "email": None}],
    "administrative": [{"name": "DATA REDACTED"}],
    "technical": [{"name": "DATA REDACTED"}]}}

RDAP_NAMED = {"whois_server": "whois.nic.example", "entities": {
    "registrant": [{"organization": "Sunrise Overseas Recruitment", "email": "x@sunrise.example"}]}}


def test_parse_rdap_emits_named_contacts_and_skips_redacted():
    ents, edges = di.parse_rdap("cloudflare.com", RDAP)
    assert {e["name"] for e in ents} == {"Cloudflare, Inc."}     # redacted registrant/admin/tech dropped
    e = next(x for x in edges if x["predicate"] == "registrar_of")
    assert e["subject_id"] == "Cloudflare, Inc." and e["object_id"] == "cloudflare.com"
    assert e["source"] == "rdap:whois.cloudflare.com"


def test_parse_rdap_uses_named_registrant_when_present():
    ents, edges = di.parse_rdap("sunrise.example", RDAP_NAMED)
    assert ents[0]["name"] == "Sunrise Overseas Recruitment"
    assert edges[0]["predicate"] == "registers" and edges[0]["weight"] == 0.8


def test_is_redacted():
    assert di._is_redacted("DATA REDACTED") and di._is_redacted("")
    assert di._is_redacted("Redacted for Privacy") and di._is_redacted("Statutory Masking Enabled")
    assert not di._is_redacted("Acme Corp")


def test_parse_dns_normalizes_ns_mx_edges():
    edges = di.parse_dns("x.com", nameservers=["NS1.Example.COM."], mx=["mail.example.com."])
    pairs = {(e["predicate"], e["object_id"]) for e in edges}
    assert ("hosted_on", "ns1.example.com") in pairs and ("mail_via", "mail.example.com") in pairs


def test_enrich_combines_rdap_and_dns_and_flags_redaction():
    r = di.enrich("Cloudflare.com", rdap_fn=lambda d: RDAP, dns_fn=lambda d: (["ns1.x"], []))
    assert r["domain"] == "cloudflare.com"                       # lowercased
    preds = {e["predicate"] for e in r["edges"]}
    assert "registrar_of" in preds and "hosted_on" in preds
    assert r["registrant_redacted"] is True                     # registrant was redacted


def test_enrich_is_best_effort_when_rdap_fails():
    def boom(_):
        raise RuntimeError("rdap unavailable")
    r = di.enrich("x.com", rdap_fn=boom, dns_fn=lambda d: (["ns1.x"], []))
    assert r["entities"] == [] and len(r["edges"]) == 1         # DNS still contributes
