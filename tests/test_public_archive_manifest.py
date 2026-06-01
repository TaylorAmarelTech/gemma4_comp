from __future__ import annotations

import importlib
import json
import pathlib
import sys


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

archive = importlib.import_module("public_archive_manifest")


def _fetch_row(url: str, *, kind: str = "html", score: int = 70) -> dict:
    return {
        "url": url,
        "domain": "example.org",
        "content_kind": kind,
        "score": score,
        "source_candidate_id": "SRC-1",
        "source_family": "test_family",
        "signals": ["debt_bondage"],
        "extractor_plan": {"primary": "trafilatura_optional"},
        "fetch_policy": {"max_bytes": 1234},
    }


def _jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_archive_rows_are_manifest_only_and_no_network_default():
    rows = archive.archive_rows([_fetch_row("https://example.org/report.html")])

    assert len(rows) == 1
    row = rows[0]
    assert row["id"].startswith("ARCH-")
    assert row["capture_policy"]["network_fetch_default"] is False
    assert row["capture_policy"]["requires_robots_check"] is True
    assert row["capture_policy"]["store_raw_body_outside_git_only"] is True
    assert row["planned_cache"]["commit_raw_archive_to_git"] is False
    assert row["privacy"]["raw_response_committed"] is False


def test_replay_manifest_summarizes_content_kinds_and_boundaries():
    rows = archive.archive_rows(
        [
            _fetch_row("https://example.org/a.pdf", kind="pdf", score=90),
            _fetch_row("https://example.org/b.html", kind="html", score=80),
        ]
    )
    replay = archive.replay_manifest(rows)

    assert replay["counts"]["archive_entries"] == 2
    assert replay["counts"]["content_kinds"] == {"html": 1, "pdf": 1}
    assert replay["operational_boundary"]["raw_archives_committed_to_git"] is False
    assert replay["operational_boundary"]["manual_review_and_robots_required"] is True


def test_pipeline_writes_archive_artifacts(tmp_path):
    out_dir = tmp_path / "research_spider"
    out_dir.mkdir()
    fetch_rows = [
        _fetch_row("https://example.org/a.pdf", kind="pdf", score=90),
        _fetch_row("https://example.org/b.html", kind="html", score=80),
    ]
    (out_dir / "source_fetch_manifest.jsonl").write_text(
        "\n".join(json.dumps(row) for row in fetch_rows) + "\n",
        encoding="utf-8",
    )

    summary = archive.run_pipeline(out_dir)

    assert summary["source_archive_manifest"] == 2
    assert summary["privacy"]["network_fetch_default"] is False
    assert len(_jsonl(out_dir / "source_archive_manifest.jsonl")) == 2
    assert (out_dir / "source_replay_manifest.json").exists()
    assert (out_dir / "source_archive_summary.json").exists()
    combined = "\n".join(path.read_text(encoding="utf-8") for path in out_dir.iterdir())
    assert '"raw_private_cases_ingested": true' not in combined
    assert '"raw_response_committed": true' not in combined
