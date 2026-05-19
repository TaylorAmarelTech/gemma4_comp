from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_external_links.py"


def test_external_link_checker_contract():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "ACTIVE_GLOBS" in text
    assert "extract_links" in text
    assert "check_url" in text
    assert "urllib.request" in text
    assert "EXISTS_BUT_NOT_FETCHABLE" in text
    assert "--check" in text
    assert "--json" in text
    assert "DueCareLinkCheck" in text


def test_external_link_checker_list_mode_runs():
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_external_links", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    refs = module.extract_links()
    assert refs
    assert any("duecare-ai.com" in ref.url for ref in refs)
    assert all("..." not in ref.url for ref in refs)
    assert all("*" not in ref.url for ref in refs)
