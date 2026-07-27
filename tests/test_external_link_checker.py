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
    assert module._should_skip_url("https://site/path")
    assert module._should_skip_url("https://api.example.net/v1/items")
    assert module._should_skip_url("https://gov.example/advisory")
    assert module._should_skip_url("https://github.com/<org>/duecare")
    assert module._should_skip_url("https://github.com/acme/repo.git@master#subdirectory=pkg")
    assert not module._should_skip_url("https://duecare-ai.com/project-status")


def test_concurrent_checks_preserve_input_order(monkeypatch):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("check_external_links_order", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    refs = [
        module.LinkRef("https://example.net/b", "b.md", 2),
        module.LinkRef("https://example.net/a", "a.md", 1),
    ]

    def fake_check(ref, timeout):
        return module.LinkResult(ref.url, True, 200, "", ref.file, ref.line, int(timeout))

    monkeypatch.setattr(module, "check_url", fake_check)
    results = module.check_links(refs, timeout=3, workers=2)

    assert [result.url for result in results] == [ref.url for ref in refs]
