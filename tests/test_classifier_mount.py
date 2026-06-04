"""The /classifier structured-output sub-app is mounted on the main chat app.

The Platform-safety links (showcase-platform.html x2, all-tools.html) point at
/classifier; before the mount they 404'd. Verifies the sub-app serves its UI
and that the href used by those pages resolves rather than 404ing. No model
load (mount works model-less; evaluate degrades gracefully).
"""
from __future__ import annotations

from duecare.chat.app import create_app
from fastapi.testclient import TestClient


def test_classifier_is_mounted_and_serves_ui():
    app = create_app()
    assert getattr(app.state, "classifier_mounted", False) is True, \
        getattr(app.state, "classifier_mount_error", "classifier not mounted")
    client = TestClient(app)
    r = client.get("/classifier/")                 # mounted sub-app root UI
    assert r.status_code == 200
    assert "<" in r.text                            # real HTML, not an error string


def test_classifier_href_does_not_404():
    # the bare href="/classifier" used by showcase-platform.html / all-tools.html
    # must resolve (200) or redirect to the slashed root (307/308) -- never 404.
    client = TestClient(create_app())
    assert client.get("/classifier", follow_redirects=False).status_code in (200, 307, 308)
