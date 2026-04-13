"""Package-level smoke test for duecare-llm-domains."""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
DOMAINS_ROOT = REPO_ROOT / "configs" / "duecare" / "domains"


def test_top_level_imports():
    from duecare.domains import (
        DEFAULT_ROOT,
        DomainPack,
        FileDomainPack,
        discover_all,
        domain_registry,
        load_domain_pack,
        register_discovered,
    )
    assert DomainPack is not None
    assert domain_registry.kind == "domain"


def test_register_all_three_shipped_packs():
    if not DOMAINS_ROOT.exists():
        pytest.skip("domain packs not populated")
    from duecare.domains import domain_registry, register_discovered

    # The fixture in conftest may or may not have pre-registered; idempotent
    register_discovered(root=DOMAINS_ROOT)

    ids = set(domain_registry.all_ids())
    assert {"trafficking", "tax_evasion", "financial_crime"}.issubset(ids)


def test_trafficking_has_seed_prompts():
    if not DOMAINS_ROOT.exists():
        pytest.skip("domain packs not populated")
    from duecare.domains import load_domain_pack

    pack = load_domain_pack("trafficking", root=DOMAINS_ROOT)
    prompts = list(pack.seed_prompts())
    assert len(prompts) >= 12  # 74K+ after benchmark extraction


def test_tax_evasion_prompts_have_graded_responses():
    if not DOMAINS_ROOT.exists():
        pytest.skip("domain packs not populated")
    from duecare.domains import load_domain_pack

    pack = load_domain_pack("tax_evasion", root=DOMAINS_ROOT)
    prompts = list(pack.seed_prompts())
    assert len(prompts) >= 3
    # Every prompt has at least one graded response example
    for prompt in prompts:
        assert "graded_responses" in prompt
        assert len(prompt["graded_responses"]) >= 1


def test_financial_crime_rubric_has_guardrails():
    if not DOMAINS_ROOT.exists():
        pytest.skip("domain packs not populated")
    from duecare.domains import load_domain_pack

    pack = load_domain_pack("financial_crime", root=DOMAINS_ROOT)
    rubric = pack.rubric()
    assert "guardrails" in rubric
    assert "grade_scale" in rubric["guardrails"]
