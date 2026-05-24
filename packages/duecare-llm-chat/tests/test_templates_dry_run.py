from __future__ import annotations

import sys
from pathlib import Path


# Make the chat package importable without a wheel install.
_SRC_ROOT = Path(__file__).parents[1] / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from duecare.chat.templates import (  # noqa: E402
    TEMPLATES_REGISTRY,
    TemplateField,
    TemplateSpec,
    dry_run_fill_template,
    register_template_routes,
)


def _client_with_templates():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("dry-run-fill must not call Gemma")

    app.state.gemma_call = fail_if_called
    register_template_routes(app)
    return TestClient(app)


def test_dry_run_does_not_call_gemma():
    client = _client_with_templates()
    response = client.post(
        "/api/templates/dry-run-fill",
        json={
            "template_id": "hk_ld_fdh_complaint",
            "bundle": {
                "people": [{"label": "M.A."}],
                "entities": {
                    "nationality": ["Philippines"],
                    "employer": ["Employer Household B"],
                    "agency": ["Composite Placement Agency A"],
                },
                "payments": [{"amount": "PHP 50000"}],
                "intelligence": {
                    "case_brief": "Composite worker paid a disguised fee.",
                    "ilo_indicators": ["fee_camouflage"],
                    "evidence_edges": [{"detail": "receipt summary"}],
                },
            },
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    template = TEMPLATES_REGISTRY["hk_ld_fdh_complaint"]
    assert set(body["field_sources"]) == {field.id for field in template.fields}
    assert body["n_bundle_hits"] + body["n_missing"] == len(template.fields)


def test_bucket_counts_correct():
    spec = TemplateSpec(
        id="dry_run_count_test",
        title="Dry Run Count Test",
        jurisdiction="test",
        audience="test",
        summary="test",
        body="{{worker}} {{missing_required}} {{optional_blank}} {{fee}}",
        fields=(
            TemplateField(
                id="worker",
                label="Worker",
                required=True,
                source_hint="people[0].label",
            ),
            TemplateField(
                id="missing_required",
                label="Missing required",
                required=True,
                source_hint="entities.absent[0]",
            ),
            TemplateField(
                id="optional_blank",
                label="Optional blank",
                required=False,
            ),
            TemplateField(
                id="fee",
                label="Fee",
                required=False,
                source_hint="payments[*].amount",
            ),
        ),
    )
    out = dry_run_fill_template(
        spec,
        {
            "people": [{"label": "M.A."}],
            "payments": [{"amount": "PHP 50000"}],
        },
    )
    assert out == {
        "field_sources": {
            "worker": "bundle_hint",
            "missing_required": "missing",
            "optional_blank": "missing",
            "fee": "bundle_hint",
        },
        "n_bundle_hits": 2,
        "n_missing": 2,
        "n_optional": 2,
        "n_required": 2,
    }


def test_unknown_template_id_returns_404():
    client = _client_with_templates()
    response = client.post(
        "/api/templates/dry-run-fill",
        json={"template_id": "not_a_real_template", "bundle": {}},
    )
    assert response.status_code == 404
    assert response.json()["status"] == "unknown_template"
