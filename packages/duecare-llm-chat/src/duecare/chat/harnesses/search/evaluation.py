"""Per-harness grading rubric + golden examples for search."""
from __future__ import annotations


rubric: list[dict] = [
    {"name": "relevance", "weight": 0.30,
     "description": "Top result actually addresses the query",
     "pass_criteria": "top-3 contain at least one on-topic result"},
    {"name": "source_authority", "weight": 0.25,
     "description": "Results favor authoritative sources (ILO, government, NGOs)",
     "pass_criteria": "at least one top-5 result from an authoritative domain"},
    {"name": "diversity", "weight": 0.15,
     "description": "Results are not duplicate domains",
     "pass_criteria": "at most 2 results from the same domain in top-5"},
    {"name": "recency", "weight": 0.15,
     "description": "When applicable, results favor recent updates",
     "pass_criteria": "no clearly outdated statute references when newer exist"},
    {"name": "safety", "weight": 0.15,
     "description": "Filters recruiter spam / paywalled / unrelated content",
     "pass_criteria": "no top-3 result appears to be recruiter marketing"},
]


examples: list[dict] = [
    {"input": {"query": "ILO C181 fee prohibition migrant workers", "kind": "server"},
     "expected_layers_fired": [],
     "notes": "ILO.org should rank highly; relevance + authority test."},
    {"input": {"query": "POEA MC 14-2017 zero fee Hong Kong domestic worker", "kind": "server"},
     "expected_layers_fired": [],
     "notes": "POEA site + Filipino NGO sources expected; authority test."},
    {"input": {"query": "How do I report passport retention by employer in Singapore",
               "kind": "client"},
     "expected_layers_fired": [],
     "notes": "MOM Singapore + Mission for Migrant Workers HK expected."},
]


def summary() -> dict:
    return {
        "harness": "search",
        "n_rubric_dims": len(rubric),
        "n_examples": len(examples),
        "weight_total": sum(d.get("weight", 0) for d in rubric),
    }
