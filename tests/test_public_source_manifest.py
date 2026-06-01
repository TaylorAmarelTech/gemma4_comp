from __future__ import annotations

import importlib
import json
import pathlib
import sys

import pytest


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

manifest = importlib.import_module("public_source_manifest")


def _candidate(url: str, *, score: int = 70, signals: list[str] | None = None) -> dict:
    return {
        "id": "SRC-CAND-TEST",
        "url": url,
        "source_family": "intergovernmental",
        "source_tier": "intergovernmental",
        "jurisdictions": ["global"],
        "score": score,
        "signals": signals or ["debt_bondage"],
    }


def _jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_manifest_rows_plan_extractors_without_fetching():
    rows = manifest.manifest_rows(
        [
            _candidate("https://Example.org/report.pdf?utm_source=x", score=90, signals=["forced_labor"]),
            _candidate("https://example.org/path/page.html#section", score=80, signals=["online_bait"]),
        ]
    )

    assert [row["content_kind"] for row in rows] == ["pdf", "html"]
    assert rows[0]["url"] == "https://example.org/report.pdf"
    assert rows[0]["extractor_plan"]["primary"] == "pdfplumber_optional"
    assert rows[1]["extractor_plan"]["primary"] == "trafilatura_optional"
    assert rows[0]["fetch_policy"]["network_fetch_default"] is False
    assert rows[0]["fetch_policy"]["requires_robots_check"] is True
    assert rows[0]["privacy"]["raw_private_cases_ingested"] is False


def test_rejects_non_public_urls():
    with pytest.raises(manifest.SourceManifestError):
        manifest.manifest_rows([_candidate("file:///local/private.txt")])


def test_domain_frontier_groups_domains_and_sitemap_candidates():
    rows = manifest.manifest_rows(
        [
            _candidate("https://example.org/a.pdf", signals=["debt_bondage"]),
            _candidate("https://example.org/b", signals=["forced_criminality"]),
            _candidate("https://agency.gov/report", signals=["referral"]),
        ]
    )
    domains = manifest.domain_frontier_rows(rows)
    by_domain = {row["domain"]: row for row in domains}

    assert by_domain["example.org"]["source_count"] == 2
    assert by_domain["example.org"]["robots_url"] == "https://example.org/robots.txt"
    assert "https://example.org/sitemap.xml" in by_domain["example.org"]["sitemap_candidates"]
    assert by_domain["example.org"]["queue_policy"]["manual_review_before_fetch"] is True


def test_pipeline_writes_manifest_artifacts(tmp_path):
    out_dir = tmp_path / "research_spider"
    out_dir.mkdir()
    candidates = [
        _candidate("https://example.org/a.pdf", score=75),
        _candidate("https://example.org/a.pdf", score=70),
        _candidate("https://agency.gov/page", score=74),
    ]
    (out_dir / "source_candidates.jsonl").write_text(
        "\n".join(json.dumps(row) for row in candidates) + "\n",
        encoding="utf-8",
    )

    summary = manifest.run_pipeline(out_dir)

    assert summary["source_fetch_manifest"] == 2
    assert summary["source_domain_frontier"] == 2
    assert summary["privacy"]["network_fetch_default"] is False
    fetch_rows = _jsonl(out_dir / "source_fetch_manifest.jsonl")
    domain_rows = _jsonl(out_dir / "source_domain_frontier.jsonl")
    assert len(fetch_rows) == 2
    assert len(domain_rows) == 2
    combined = "\n".join(path.read_text(encoding="utf-8") for path in out_dir.iterdir())
    assert '"raw_private_cases_ingested": true' not in combined
    assert '"network_fetch_default": true' not in combined
