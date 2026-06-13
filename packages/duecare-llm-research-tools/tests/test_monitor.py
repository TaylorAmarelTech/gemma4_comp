"""Tests for the Public Information Research Monitor (Component 5 MVP).

Fully offline: an injected mock ``fetch`` makes :func:`check_sources` pure, so
there is no network and no clock. Covers the plan's required tests: changed-hash
detection, 404/unreachable, proposal schema validation, and the critical
no-auto-mutation invariant.
"""
from __future__ import annotations

from duecare.research_tools.monitor import (
    MonitorSource, FetchResult, ProposedUpdate,
    check_sources, build_report, content_hash, scrub,
)


def mk(text: str = "", *, ok: bool = True, status: int = 200, error: str | None = None):
    return lambda _url: FetchResult(ok=ok, status=status, text=text, error=error)


SRC = [MonitorSource(id="s1", url="https://example.org/a", kind="law", label="A")]


def test_new_source_flagged_and_proposed():
    findings, state, props = check_sources(SRC, mk("hello world"), {})
    assert findings[0].change == "new"
    assert state["s1"] == content_hash("hello world")
    assert len(props) == 1 and props[0].change == "new" and props[0].needs_review is True


def test_unchanged_makes_no_proposal():
    prior = {"s1": content_hash("hello world")}
    findings, _state, props = check_sources(SRC, mk("hello   world"), prior)  # ws-normalized
    assert findings[0].change == "unchanged"
    assert props == []


def test_changed_detected_and_proposed():
    prior = {"s1": content_hash("old text")}
    findings, state, props = check_sources(SRC, mk("new different text"), prior)
    assert findings[0].change == "changed"
    assert findings[0].prior_hash == prior["s1"] and findings[0].new_hash == state["s1"]
    assert len(props) == 1 and props[0].change == "changed"


def test_unreachable_404_flagged_no_hash():
    findings, state, props = check_sources(SRC, mk(ok=False, status=404, error="HTTP 404"), {})
    assert findings[0].change == "unreachable" and findings[0].status == 404
    assert "s1" not in state  # an unreachable page records no content hash
    assert len(props) == 1 and props[0].change == "unreachable"


def test_volatile_boilerplate_does_not_false_flag():
    a = content_hash("Rules v1 csrf_token=ABC123 nonce=xyz 2026-06-06T10:00:00Z body")
    b = content_hash("Rules v1 csrf_token=ZZZ999 nonce=qqq 2026-06-07T11:22:33Z body")
    assert a == b  # only per-request chrome differs -> not a real change


def test_spa_and_gov_portal_chrome_does_not_false_flag():
    """The 2026-06-13 normalizer tuning: SPA / gov-portal per-request chrome
    (CSP nonce, session id, Nuxt build hash, CF ray id, UUID, hydration marker,
    HTTP-date, relative time) must not register as a content change."""
    page = (
        'Licensed agencies list. <script nonce="{nonce}"></script>'
        ' <a href="/_nuxt/{asset}.js">app</a> JSESSIONID={sess}'
        ' cf-ray: {ray} buildId="{build}"'
        ' data-v-{scoped} <time>{httpdate}</time> updated {rel} ago.'
        ' Agency: Sunrise Overseas Manpower (POEA-1001) -- VALID.'
    )
    a = content_hash(page.format(
        nonce="aB3xK9pQ", asset="lKhMb37E", sess="A1B2C3D4E5",
        ray="8abc1234def-LAX", build="b513d05a-de85-4a25-9e78-0762f4ea982d",
        scoped="1a2b3c", httpdate="Fri, 13 Jun 2026 03:08:29 GMT", rel="2 hours"))
    b = content_hash(page.format(
        nonce="zZ9qW0eR", asset="9XyZ12Ab", sess="Z9Y8X7W6V5",
        ray="9def5678abc-SIN", build="ffffffff-1111-2222-3333-444444444444",
        scoped="9f8e7d", httpdate="Sat, 14 Jun 2026 11:59:01 GMT", rel="5 minutes"))
    assert a == b  # every difference is volatile chrome -> not a real change


def test_apex_portal_hidden_state_does_not_false_flag():
    """Oracle-APEX / Django / Rails portals embed rotating hidden form-state
    tokens (app_session, p_instance, p_page_submission_id, csrfmiddlewaretoken)
    that change every fetch. Verified empirically against the ILO NORMLEX
    legal-text pages, which otherwise false-flagged on every run."""
    page = (
        '<script>var app_session="{sess}";</script>'
        '<form action="wwv_flow.accept?p_context=1000:12100:{sess}">'
        '<input type="hidden" name="p_instance" value="{inst}" id="pInstance" />'
        '<input type="hidden" name="p_page_submission_id" value="{tok}" />'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">'
        '</form>'
        'ILO Convention No. 29 -- Forced Labour Convention, 1930. Article 1.'
    )
    a = content_hash(page.format(sess="7556101071286", inst="17532485136319",
                                 tok="MjU2MjA1ODkz", csrf="aB3xK9pQ"))
    b = content_hash(page.format(sess="3079254040966", inst="12198485200859",
                                 tok="NzYwODI3MTky", csrf="zZ9qW0eR"))
    assert a == b  # only hidden form-state rotates -> not a real change
    # but a change to the VISIBLE legal text is still detected
    c = content_hash(page.format(sess="7556101071286", inst="17532485136319",
                                 tok="MjU2MjA1ODkz", csrf="aB3xK9pQ")
                     .replace("Article 1.", "Article 1. [amended]"))
    assert c != a


def test_real_content_change_still_detected_after_tuning():
    """Guard against over-stripping: a genuine content change (a new agency, a
    status flip, new advisory prose) must still produce a different hash."""
    base = "Licensed agencies: Sunrise Overseas Manpower (POEA-1001) -- VALID."
    # a real status change
    assert content_hash(base) != content_hash(base.replace("VALID", "CANCELLED"))
    # a new agency added
    assert content_hash(base) != content_hash(base + " Pacific Bridge (POEA-1002) -- VALID.")
    # a date-only "as of" change is a real refresh signal -> NOT stripped
    assert content_hash("status as of 2026-05-01") != content_hash("status as of 2026-06-13")


def test_scrub_redacts_pii():
    s = scrub("call 415-555-0199 or write me@example.com today")
    assert "415-555-0199" not in s and "me@example.com" not in s and "[redacted]" in s


def test_proposal_schema_roundtrip_needs_review():
    p = ProposedUpdate(source_id="s1", url="https://x/y", kind="law", change="changed", summary="x")
    restored = ProposedUpdate.model_validate(p.model_dump())
    assert restored.needs_review is True  # never auto-applied


def test_no_auto_mutation_writes_nothing(tmp_path):
    """check_sources is propose-only: it returns data and writes no files."""
    before = set(tmp_path.iterdir())
    check_sources(SRC, mk("content"), {})
    assert set(tmp_path.iterdir()) == before


def test_report_counts():
    srcs = [MonitorSource(id=f"s{i}", url=f"https://e/{i}", kind="law", label=str(i))
            for i in range(3)]
    findings, _state, props = check_sources(srcs, mk("same"), {})
    rep = build_report(findings, props)
    assert rep.n_sources == 3 and rep.n_new == 3 and rep.n_unchanged == 0
