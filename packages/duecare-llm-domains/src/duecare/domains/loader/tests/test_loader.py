"""Real tests for duecare.domains.loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from duecare.domains import DEFAULT_ROOT, discover_all, load_domain_pack


REPO_ROOT = Path(__file__).resolve().parents[7]
DOMAINS_ROOT = REPO_ROOT / "configs" / "duecare" / "domains"


class TestLoadDomainPack:
    def test_load_trafficking(self):
        if not (DOMAINS_ROOT / "trafficking").exists():
            pytest.skip("trafficking pack not populated")
        pack = load_domain_pack("trafficking", root=DOMAINS_ROOT)
        assert pack.id == "trafficking"

    def test_load_tax_evasion(self):
        if not (DOMAINS_ROOT / "tax_evasion").exists():
            pytest.skip("tax_evasion pack not populated")
        pack = load_domain_pack("tax_evasion", root=DOMAINS_ROOT)
        assert pack.id == "tax_evasion"

    def test_load_financial_crime(self):
        if not (DOMAINS_ROOT / "financial_crime").exists():
            pytest.skip("financial_crime pack not populated")
        pack = load_domain_pack("financial_crime", root=DOMAINS_ROOT)
        assert pack.id == "financial_crime"

    def test_load_nonexistent_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_domain_pack("nonexistent_domain", root=tmp_path)


class TestDiscoverAll:
    def test_discovers_shipped_packs(self):
        packs = discover_all(DOMAINS_ROOT)
        if not DOMAINS_ROOT.exists():
            pytest.skip("domains root not populated")
        # At least 3 packs should ship with the repo
        assert len(packs) >= 3
        ids = {p.id for p in packs}
        assert {"trafficking", "tax_evasion", "financial_crime"}.issubset(ids)

    def test_empty_root_returns_empty(self, tmp_path: Path):
        packs = discover_all(tmp_path)
        assert packs == []

    def test_nonexistent_root_returns_empty(self, tmp_path: Path):
        packs = discover_all(tmp_path / "does_not_exist")
        assert packs == []

    def test_skips_non_pack_directories(self, tmp_path: Path):
        # Create a folder without card.yaml
        (tmp_path / "not_a_pack").mkdir()
        (tmp_path / "not_a_pack" / "random.txt").write_text("hello")
        packs = discover_all(tmp_path)
        assert packs == []


def test_default_root_resolves_to_valid_path():
    root = str(DEFAULT_ROOT)
    assert "duecare" in root or "domains" in root
    assert DEFAULT_ROOT.exists()
