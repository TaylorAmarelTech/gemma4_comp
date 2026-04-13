"""Real tests for duecare.domains.pack.FileDomainPack."""

from __future__ import annotations

from pathlib import Path

import pytest

from duecare.domains import FileDomainPack


REPO_ROOT = Path(__file__).resolve().parents[7]
TRAF_PACK_ROOT = REPO_ROOT / "configs" / "duecare" / "domains" / "trafficking"


@pytest.fixture
def trafficking_pack() -> FileDomainPack:
    if not TRAF_PACK_ROOT.exists():
        pytest.skip("trafficking pack not populated")
    return FileDomainPack(root=TRAF_PACK_ROOT)


class TestFileDomainPack:
    def test_card_populated(self, trafficking_pack: FileDomainPack):
        card = trafficking_pack.card()
        assert card.id == "trafficking"
        assert card.version == "0.1.0"
        assert "Migrant" in card.display_name

    def test_id_shortcuts(self, trafficking_pack: FileDomainPack):
        assert trafficking_pack.id == "trafficking"
        assert trafficking_pack.version == "0.1.0"

    def test_taxonomy_structure(self, trafficking_pack: FileDomainPack):
        taxonomy = trafficking_pack.taxonomy()
        assert "categories" in taxonomy
        assert "indicators" in taxonomy
        assert len(taxonomy["categories"]) >= 5
        assert len(taxonomy["indicators"]) >= 10

    def test_rubric_structure(self, trafficking_pack: FileDomainPack):
        rubric = trafficking_pack.rubric()
        assert "guardrails" in rubric
        assert "grade_scale" in rubric["guardrails"]

    def test_pii_spec_structure(self, trafficking_pack: FileDomainPack):
        pii_spec = trafficking_pack.pii_spec()
        assert "critical_categories" in pii_spec
        assert "given_name" in pii_spec["critical_categories"]

    def test_seed_prompts_iterable(self, trafficking_pack: FileDomainPack):
        prompts = list(trafficking_pack.seed_prompts())
        assert len(prompts) > 0
        assert "id" in prompts[0]
        assert "text" in prompts[0]

    def test_evidence_iterable(self, trafficking_pack: FileDomainPack):
        evidence = list(trafficking_pack.evidence())
        assert len(evidence) > 0
        assert all("id" in e for e in evidence)

    def test_missing_root_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            FileDomainPack(root=tmp_path / "does_not_exist")

    def test_empty_optional_files_return_empty(self, tmp_path: Path):
        # Create a minimal pack with only card.yaml
        pack_dir = tmp_path / "minimal"
        pack_dir.mkdir()
        (pack_dir / "card.yaml").write_text(
            'id: minimal\ndisplay_name: "Minimal"\nversion: "0.1.0"\n',
            encoding="utf-8",
        )
        pack = FileDomainPack(root=pack_dir)
        assert pack.taxonomy() == {}
        assert pack.rubric() == {}
        assert pack.pii_spec() == {}
        assert list(pack.seed_prompts()) == []
        assert list(pack.evidence()) == []
        assert list(pack.known_failures()) == []
