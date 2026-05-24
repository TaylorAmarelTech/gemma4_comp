"""End-to-end contract for POST /api/knowledge/polish-envelope.

The polish endpoint runs two Gemma 4 passes (critique then rewrite) on
a draft knowledge envelope. The handler logic lives in
`packages/duecare-llm-chat/src/duecare/chat/harnesses/extraction/handler.py`
under `_build_polish_response`, and the route is wired in
`register_routes` (`POST /api/knowledge/polish-envelope`). The polish
endpoint is the substrate the knowledge.html UI's "Polish further
(Gemma 4)" button uses, and it will be reused by search.html in the
Codex follow-up (`docs/codex_followup_goals.md` Goal 1).

These tests pin the contract pieces that are easiest to regress:

- the response shape is `{envelope, critique, passes, diff}`
- when Gemma is available, the stub is called exactly twice (one
  critique, one rewrite)
- when Gemma is NOT available, the endpoint still returns a
  standardized envelope with `polish_skipped` explaining why
- when Gemma's critique JSON does not parse, the rewrite pass is
  skipped and `polish_critique_error` is surfaced
- when Gemma reports zero issues, the rewrite is skipped and
  `polish_clean_pass=True` is set
- the polished envelope carries `polished_by_gemma=True` and
  `polish_passes=2` so the UI can show the badge correctly
- the per-field diff has `changed=True` only for fields the rewrite
  actually altered

If any of these regress, the knowledge.html polish UI shows the wrong
provenance, the activity log mis-reports passes, or the search.html
port (Goal 1) silently breaks.
"""
from __future__ import annotations

import json as _json
from typing import Any

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


def _make_envelope(
    *,
    knowledge_object_type: str = "extracted_fact",
    content: dict | None = None,
) -> dict:
    """A minimal envelope shaped like what /api/knowledge/draft-envelope
    actually returns (post-standardize). The polish endpoint reads
    `envelope.content` + `envelope.knowledge_object_type` and is
    indifferent to the other top-level keys, but we include the
    realistic set so the diff renderer sees the same shape it would
    see in production."""
    return {
        "schema_version": "1.0",
        "knowledge_object_type": knowledge_object_type,
        "id": "polish-test-draft",
        "version": "v1-draft",
        "provenance": {
            "created_at": "2026-05-24T00:00:00Z",
            "created_by": "test:polish-endpoint",
            "source_sha256": "synthetic-fixture",
        },
        "content": content or {
            "fact_type": "fee_or_debt_signal",
            "indicators": ["fee_camouflage"],
            "corridor": "PH-HK",
            "evidence_quote": (
                "Recruiter charged a worker about PHP 50000 in placement fees "
                "and then deducted HKD 4000 monthly from arrival wages."
            ),
            "entity_names": ["a recruitment agency"],
        },
        "tags": ["branch:matching"],
        "extensions": {
            "draft": True,
            "needs_review": True,
            "model_call_requested": True,
            "model_call_available": True,
            "noise_scrubbed_before_gemma": False,
            "standardized_shape": True,
        },
    }


class _StubGemma:
    """Records every call and returns canned responses.

    The polish endpoint expects two calls per polish: one critique pass
    (returns issues JSON) and one rewrite pass (returns content JSON).
    This stub lets a test queue up the exact strings each pass should
    return and then inspect what was sent in."""

    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, msgs: Any, *, max_new_tokens: int = 512, temperature: float = 0.2) -> str:
        # The handler passes a list-of-message-dicts shaped like
        # [{"role": "system", "content": [{"type": "text", "text": ...}]}, ...].
        # Record the system + user texts so tests can inspect what
        # Gemma actually saw without depending on the verbatim prompt.
        if isinstance(msgs, list):
            system_text = ""
            user_text = ""
            for m in msgs:
                role = m.get("role")
                chunks = m.get("content") or []
                text = ""
                for c in chunks:
                    if isinstance(c, dict) and c.get("type") == "text":
                        text += c.get("text", "")
                if role == "system":
                    system_text = text
                elif role == "user":
                    user_text = text
            self.calls.append({
                "system_text": system_text,
                "user_text": user_text,
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
            })
        else:
            # Some callers pass a raw prompt string.
            self.calls.append({
                "prompt": str(msgs),
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
            })
        if not self._responses:
            raise AssertionError("stub gemma ran out of canned responses")
        return self._responses.pop(0)


@pytest.fixture
def app():
    from duecare.chat.app import create_app
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------
# Happy-path: critique + rewrite both succeed
# ---------------------------------------------------------------------


class TestPolishEndpointHappyPath:
    def test_two_pass_polish_calls_gemma_twice(self, app, client):
        """A successful polish invokes Gemma exactly twice: once for
        the critique pass, once for the rewrite. Single-call or
        triple-call regressions would silently change the cost +
        latency profile of the UI button."""
        stub = _StubGemma(
            # critique pass — Gemma flags one issue
            _json.dumps({
                "issues": [{
                    "category": "vague_phrasing",
                    "field": "evidence_quote",
                    "why": "the quote uses 'about' where a concrete number would land harder",
                    "suggested_fix": "drop hedging language and state the exact amount",
                }],
                "overall": "one phrasing nit",
            }),
            # rewrite pass — Gemma applies the fix
            _json.dumps({
                "evidence_quote": (
                    "Recruiter charged a worker PHP 50000 in placement fees and "
                    "deducted HKD 4000 monthly from arrival wages."
                ),
                "indicators": ["fee_camouflage", "fee_bondage"],
            }),
        )
        app.state.gemma_call = stub

        r = client.post("/api/knowledge/polish-envelope", json={
            "envelope": _make_envelope(),
            "use_gemma": True,
            "max_passes": 2,
        })
        assert r.status_code == 200, r.text
        assert len(stub.calls) == 2, (
            f"expected exactly 2 Gemma calls (critique + rewrite), "
            f"got {len(stub.calls)}"
        )

    def test_response_shape(self, app, client):
        """The handler must always return the four canonical top-level
        keys so the JS polish renderer can blindly read them."""
        stub = _StubGemma(
            _json.dumps({"issues": [], "overall": "clean"}),
        )
        app.state.gemma_call = stub
        r = client.post("/api/knowledge/polish-envelope", json={
            "envelope": _make_envelope(),
            "use_gemma": True,
        })
        assert r.status_code == 200
        body = r.json()
        for key in ("envelope", "critique", "passes", "diff"):
            assert key in body, f"missing top-level key: {key}"
        assert isinstance(body["envelope"], dict)
        assert isinstance(body["diff"], list)

    def test_envelope_marked_polished(self, app, client):
        """After a full two-pass polish, the envelope's extensions must
        carry polished_by_gemma=True + polish_passes=2 so the UI badge
        renders the correct state."""
        stub = _StubGemma(
            _json.dumps({
                "issues": [{
                    "category": "vague_phrasing",
                    "field": "evidence_quote",
                    "why": "hedging",
                    "suggested_fix": "drop hedging",
                }],
                "overall": "one nit",
            }),
            _json.dumps({"evidence_quote": "Recruiter charged PHP 50000."}),
        )
        app.state.gemma_call = stub
        r = client.post("/api/knowledge/polish-envelope", json={
            "envelope": _make_envelope(),
            "use_gemma": True,
        })
        body = r.json()
        ext = body["envelope"]["extensions"]
        assert ext.get("polished_by_gemma") is True
        assert ext.get("polish_passes") == 2
        assert ext.get("standardized_shape") is True
        assert body["passes"] == 2

    def test_diff_reflects_changes(self, app, client):
        """Per-field diff entries must have changed=True only for the
        fields the rewrite actually altered. The polish renderer
        filters by `changed` and shows only the rewritten keys."""
        stub = _StubGemma(
            _json.dumps({
                "issues": [{"category": "vague_phrasing", "field": "evidence_quote", "why": "x", "suggested_fix": "y"}],
                "overall": "one fix",
            }),
            _json.dumps({
                "evidence_quote": "Recruiter charged PHP 50000.",
            }),
        )
        app.state.gemma_call = stub
        r = client.post("/api/knowledge/polish-envelope", json={
            "envelope": _make_envelope(),
            "use_gemma": True,
        })
        diff_by_key = {d["key"]: d for d in r.json()["diff"]}
        assert "evidence_quote" in diff_by_key
        # The evidence_quote entry should be flagged as changed.
        assert diff_by_key["evidence_quote"]["changed"] is True

    def test_polish_preserves_unchanged_fields(self, app, client):
        """The rewrite pass is merged on top of the original content,
        so a field Gemma did not return must stay at its original
        value. Without this, Gemma can silently drop fields it didn't
        intend to change."""
        stub = _StubGemma(
            _json.dumps({
                "issues": [{"category": "vague_phrasing", "field": "evidence_quote", "why": "x", "suggested_fix": "y"}],
                "overall": "one fix",
            }),
            _json.dumps({
                # Only return the rewritten field; indicators + corridor
                # should be preserved from the original.
                "evidence_quote": "Recruiter charged PHP 50000.",
            }),
        )
        app.state.gemma_call = stub
        r = client.post("/api/knowledge/polish-envelope", json={
            "envelope": _make_envelope(),
            "use_gemma": True,
        })
        polished = r.json()["envelope"]["content"]
        assert polished.get("corridor") == "PH-HK"
        assert "fee_camouflage" in polished.get("indicators", [])


# ---------------------------------------------------------------------
# Fallback paths
# ---------------------------------------------------------------------


class TestPolishEndpointFallback:
    def test_no_gemma_skips_and_standardizes(self, app, client):
        """When gemma_call is None, the endpoint must NOT raise. It
        returns a standardized envelope + polish_skipped reason so the
        UI can fall back gracefully without an error toast."""
        app.state.gemma_call = None
        r = client.post("/api/knowledge/polish-envelope", json={
            "envelope": _make_envelope(),
            "use_gemma": True,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["passes"] == 0
        ext = body["envelope"]["extensions"]
        assert ext.get("polish_skipped"), "polish_skipped reason must be present"
        assert "no model loaded" in str(ext["polish_skipped"]).lower()
        # standardize ran even though Gemma didn't
        assert ext.get("standardized_shape") is True
        # polished_by_gemma must NOT be set when no passes ran
        assert ext.get("polished_by_gemma") is not True

    def test_use_gemma_false_skips_and_standardizes(self, app, client):
        """Caller explicitly opting out of Gemma should also skip
        cleanly, with a distinct polish_skipped reason."""
        # Even if a model is loaded, use_gemma=False must short-circuit
        # before the critique pass.
        app.state.gemma_call = _StubGemma()  # would raise if called
        r = client.post("/api/knowledge/polish-envelope", json={
            "envelope": _make_envelope(),
            "use_gemma": False,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["passes"] == 0
        ext = body["envelope"]["extensions"]
        assert "gemma disabled" in str(ext.get("polish_skipped", "")).lower()

    def test_critique_json_parse_fails_skips_rewrite(self, app, client):
        """If Gemma's critique output cannot be parsed as JSON, the
        rewrite pass must be skipped (no point asking Gemma to apply a
        critique we can't read) and polish_critique_error surfaced."""
        stub = _StubGemma(
            # Garbage that the JSON extractor cannot recover
            "this is not even close to JSON; just chatty prose"
        )
        app.state.gemma_call = stub
        r = client.post("/api/knowledge/polish-envelope", json={
            "envelope": _make_envelope(),
            "use_gemma": True,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["passes"] == 1, "critique attempted, rewrite skipped"
        ext = body["envelope"]["extensions"]
        assert ext.get("polish_critique_error"), (
            "polish_critique_error must surface the parse failure"
        )
        # Only one Gemma call should have happened (the failed critique).
        assert len(stub.calls) == 1

    def test_clean_pass_returns_one_pass(self, app, client):
        """When Gemma's critique returns zero issues, the rewrite pass
        must be skipped (nothing to rewrite) and polish_clean_pass=True
        set so the UI can show 'Gemma found no issues' messaging."""
        stub = _StubGemma(
            _json.dumps({"issues": [], "overall": "draft reads clean"}),
        )
        app.state.gemma_call = stub
        r = client.post("/api/knowledge/polish-envelope", json={
            "envelope": _make_envelope(),
            "use_gemma": True,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["passes"] == 1
        ext = body["envelope"]["extensions"]
        assert ext.get("polish_clean_pass") is True
        assert ext.get("standardized_shape") is True
        # Critique made exactly one call; no rewrite
        assert len(stub.calls) == 1

    def test_missing_envelope_returns_400(self, client):
        """An empty body or missing envelope.content must 400 with a
        clear message — protects the polish UI from sending mangled
        payloads silently."""
        r = client.post("/api/knowledge/polish-envelope", json={})
        assert r.status_code == 400
        r = client.post("/api/knowledge/polish-envelope", json={
            "envelope": {"id": "x"},  # missing content
        })
        assert r.status_code == 400

    def test_invalid_json_body_returns_400(self, client):
        """Malformed JSON must surface as 400, not a 500."""
        r = client.post(
            "/api/knowledge/polish-envelope",
            content="{not even close to JSON",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------
# Prompt-content sanity (light — pin only what would break the UI)
# ---------------------------------------------------------------------


class TestPolishPromptContract:
    def test_critique_prompt_includes_envelope_content(self, app, client):
        """The critique prompt's user text must include the draft
        content so Gemma can reason about specific fields. If a future
        refactor accidentally ships an empty user message, the critique
        becomes useless without the test failing in a single endpoint
        call."""
        stub = _StubGemma(
            _json.dumps({"issues": [], "overall": "clean"}),
        )
        app.state.gemma_call = stub
        client.post("/api/knowledge/polish-envelope", json={
            "envelope": _make_envelope(),
            "use_gemma": True,
        })
        crit_call = stub.calls[0]
        user_text = crit_call.get("user_text") or crit_call.get("prompt", "")
        # The original evidence_quote must appear in the prompt so
        # Gemma can critique it.
        assert "Recruiter charged" in user_text
        assert "extracted_fact" in user_text

    def test_rewrite_prompt_includes_critique(self, app, client):
        """The rewrite prompt's user text must include the critique
        JSON so Gemma applies the fixes. Without this, the rewrite
        becomes 'rewrite the draft however you like' — non-deterministic
        and uncontrollable."""
        stub = _StubGemma(
            _json.dumps({
                "issues": [{
                    "category": "vague_phrasing",
                    "field": "evidence_quote",
                    "why": "hedging",
                    "suggested_fix": "drop hedging",
                }],
                "overall": "one nit",
            }),
            _json.dumps({"evidence_quote": "Recruiter charged PHP 50000."}),
        )
        app.state.gemma_call = stub
        client.post("/api/knowledge/polish-envelope", json={
            "envelope": _make_envelope(),
            "use_gemma": True,
        })
        rewrite_call = stub.calls[1]
        user_text = rewrite_call.get("user_text") or rewrite_call.get("prompt", "")
        assert "Critique" in user_text or "critique" in user_text
        assert "vague_phrasing" in user_text
