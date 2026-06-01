from __future__ import annotations

import importlib
import pathlib
import sys

import pytest


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

providers = importlib.import_module("public_search_providers")


def test_manual_provider_returns_browser_ready_url_without_network():
    hits, status = providers.run_search_provider(
        "manual_dork_queue",
        'site:iom.int "recruitment fees" "debt bondage"',
    )

    assert hits == []
    assert status["status"] == "manual_only"
    assert status["fallback"] == "manual_search_url"
    assert "site%3Aiom.int" in status["manual_search_url"]


def test_private_or_secret_like_queries_are_blocked_before_request():
    called = False

    def fake_request(url: str, headers: dict[str, str]) -> dict:
        nonlocal called
        called = True
        return {}

    with pytest.raises(providers.QueryPolicyError):
        private_root = "C:" + "\\" + "projects" + "\\" + "major_cases"
        email = "john.doe" + "@example.com"
        providers.run_search_provider(
            "github_search_api",
            f"{private_root} {email}",
            allow_network=True,
            request_json=fake_request,
        )

    assert called is False


def test_brave_missing_key_falls_back_without_network_request():
    called = False

    def fake_request(url: str, headers: dict[str, str]) -> dict:
        nonlocal called
        called = True
        return {}

    hits, status = providers.run_search_provider(
        "brave_search_api",
        '"forced labour" "recruitment fees" filetype:pdf',
        allow_network=True,
        env={},
        request_json=fake_request,
    )

    assert hits == []
    assert status["status"] == "missing_api_key"
    assert status["fallback"] == "manual_search_url"
    assert called is False


def test_brave_fake_response_normalizes_hits():
    def fake_request(url: str, headers: dict[str, str]) -> dict:
        assert "api.search.brave.com" in url
        assert headers["X-Subscription-Token"] == "test-token"
        return {
            "web": {
                "results": [
                    {
                        "title": "Public report",
                        "url": "https://example.org/report",
                        "description": "Public source about debt bondage indicators.",
                    }
                ]
            }
        }

    hits, status = providers.run_search_provider(
        "brave_search_api",
        '"debt bondage" "victim identification"',
        allow_network=True,
        env={"BRAVE_SEARCH_API_KEY": "test-token"},
        request_json=fake_request,
    )

    assert status == {"provider": "brave_search_api", "status": "ok", "count": 1}
    assert hits[0]["provider"] == "brave_search_api"
    assert hits[0]["rank"] == 1
    assert hits[0]["synthetic_or_public_only"] is True


def test_github_provider_is_network_disabled_by_default():
    hits, status = providers.run_search_provider(
        "github_search_api",
        "Python crawler robots.txt rate limit",
    )

    assert hits == []
    assert status["status"] == "network_disabled"
    assert "github.com/search" in status["manual_search_url"]


def test_github_fake_response_normalizes_repo_hits_without_token():
    def fake_request(url: str, headers: dict[str, str]) -> dict:
        assert "api.github.com/search/repositories" in url
        assert "Authorization" not in headers
        return {
            "items": [
                {
                    "full_name": "example/public-crawler",
                    "html_url": "https://github.com/example/public-crawler",
                    "description": "Public crawler with robots support.",
                }
            ]
        }

    hits, status = providers.run_search_provider(
        "github_search_api",
        "Python public crawler robots rate limit",
        allow_network=True,
        env={},
        request_json=fake_request,
    )

    assert status["status"] == "ok"
    assert hits == [
        {
            "provider": "github_search_api",
            "rank": 1,
            "title": "example/public-crawler",
            "url": "https://github.com/example/public-crawler",
            "snippet": "Public crawler with robots support.",
            "synthetic_or_public_only": True,
        }
    ]
