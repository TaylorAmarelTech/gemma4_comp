from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_policy():
    spec = importlib.util.spec_from_file_location(
        "artifact_path_policy", ROOT / "scripts" / "artifact_path_policy.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["artifact_path_policy"] = module
    spec.loader.exec_module(module)
    return module


policy = _load_policy()


def test_public_text_avoids_stale_external_file_placeholder():
    stale_placeholder = "external/" + "<file>"
    roots = [ROOT / "docs", ROOT / "scripts", ROOT / "tests"]
    handoff_paths = [
        ROOT / "PROJECT_BIBLE.md",
        ROOT / "Plans.md",
        ROOT / "CLAUDE.md",
        ROOT / "ROOT_FILES.md",
        ROOT / ".claude" / "rules" / "05_project_bible_pickup.md",
    ]
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".py"}:
                text = path.read_text(encoding="utf-8")
                if stale_placeholder in text:
                    offenders.append(path.relative_to(ROOT).as_posix())
    for path in handoff_paths:
        text = path.read_text(encoding="utf-8")
        if stale_placeholder in text:
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def test_handoff_artifact_path_keeps_safe_external_filename(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    external = tmp_path / "scratch" / "review_packet.json"

    assert policy.handoff_artifact_path(external, root=root) == "external/review_packet.json"


def test_handoff_artifact_path_keeps_safe_repo_relative_path(tmp_path):
    root = tmp_path / "repo"
    path = root / "reports" / "review_packet.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")

    assert policy.handoff_artifact_path(path, root=root) == "reports/review_packet.json"


def test_handoff_artifact_path_redacts_private_repo_relative_path(tmp_path):
    root = tmp_path / "repo"
    email_path = root / "reports" / "worker@example.invalid-case.json"
    numeric_path = root / "reports" / "case-12345678.json"
    email_path.parent.mkdir(parents=True)
    email_path.write_text("{}", encoding="utf-8")
    numeric_path.write_text("{}", encoding="utf-8")

    assert policy.handoff_artifact_path(email_path, root=root) == "external/custom_or_invalid"
    assert policy.handoff_artifact_path(numeric_path, root=root) == "external/custom_or_invalid"


def test_handoff_artifact_path_redacts_private_external_filename(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    external = tmp_path / "scratch" / "worker@example.invalid-case.json"

    assert policy.handoff_artifact_path(external, root=root) == "external/custom_or_invalid"


def test_handoff_artifact_path_redacts_hidden_private_filename(tmp_path):
    root = tmp_path / "repo"
    hidden = root / ".scratch" / "worker@example.invalid-case.json"

    assert policy.handoff_artifact_path(hidden, root=root) == "external/custom_or_invalid"


def test_handoff_artifact_path_redacts_when_resolve_fails(tmp_path):
    class BadPath:
        name = "worker@example.invalid-case.json"

        def is_absolute(self):
            return True

        def resolve(self):
            raise OSError("private path should not leak")

    root = tmp_path / "repo"
    root.mkdir()

    assert policy.handoff_artifact_path(BadPath(), root=root) == "external/custom_or_invalid"
