from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from duecare.chat import templates as tpl
from duecare.chat.harnesses._safe_text import STANDARD_FACT_INDICATORS
from duecare.chat.templates import (
    TEMPLATES_REGISTRY,
    TemplateField,
    TemplateSpec,
    extract_template_knowledge_facts,
    gemma_fill_batch,
    recommend_templates_for_bundle,
    register_template_routes,
    select_relevant_templates_for_bundle,
    template_relevance_indicators,
    template_sample_bundle,
)


def _spec(
    template_id: str,
    fields: tuple[TemplateField, ...],
    *,
    relevance_indicators: tuple[str, ...] = (),
) -> TemplateSpec:
    body = "\n".join(f"{f.label}: {{{{{f.id}}}}}" for f in fields)
    return TemplateSpec(
        id=template_id,
        title=template_id.replace("_", " ").title(),
        jurisdiction="Test",
        audience="Test reviewer",
        summary="Test template",
        body=body,
        fields=fields,
        relevance_indicators=relevance_indicators,
    )


class TestFillBatch:
    def test_shared_excerpt_computed_once(self, monkeypatch):
        calls = []

        def fake_excerpt(bundle, *, max_chars=3000):
            calls.append((bundle, max_chars))
            return "SHARED EXCERPT"

        def fake_gemma(prompt, **kwargs):
            assert "SHARED EXCERPT" in prompt
            if "TEMPLATE: First Template" in prompt:
                return '{"fields": {"first": "from first"}}'
            return '{"fields": {"second": "from second"}}'

        monkeypatch.setattr(tpl, "bundle_excerpt_for_template", fake_excerpt)
        first = _spec("first_template", (TemplateField("first", "First"),))
        second = _spec("second_template", (TemplateField("second", "Second"),))

        out = gemma_fill_batch([first, second], {"intelligence": {}}, {}, fake_gemma)

        assert len(calls) == 1
        assert out["shared_excerpt_chars"] == len("SHARED EXCERPT")
        assert [d["template_id"] for d in out["drafts"]] == [
            "first_template",
            "second_template",
        ]
        assert all(d["used_gemma"] is True for d in out["drafts"])

    def test_per_template_provenance_independent(self):
        first = _spec(
            "first_template",
            (
                TemplateField("from_bundle", "Bundle", source_hint="intelligence.case_brief"),
                TemplateField("manual_only", "Manual"),
            ),
        )
        second = _spec("second_template", (TemplateField("from_gemma", "Gemma"),))

        def fake_gemma(prompt, **kwargs):
            return '{"fields": {"from_gemma": "model value", "manual_only": "ignored"}}'

        out = gemma_fill_batch(
            [first, second],
            {"intelligence": {"case_brief": "bundle value"}},
            {"first_template": {"manual_only": "manual value"}},
            fake_gemma,
        )

        first_draft, second_draft = out["drafts"]
        assert first_draft["provenance"]["from_bundle"] == "bundle_hint"
        assert first_draft["provenance"]["manual_only"] == "manual"
        assert "from_gemma" not in first_draft["provenance"]
        assert second_draft["provenance"]["from_gemma"] == "gemma"
        assert "manual_only" not in second_draft["provenance"]

    def test_indicator_overlap_selection_in_helper(self):
        fee = _spec(
            "fee_template",
            (TemplateField("fee", "Fee"),),
            relevance_indicators=("fee_bondage",),
        )
        doc = _spec(
            "doc_template",
            (TemplateField("doc", "Document"),),
            relevance_indicators=("document_control",),
        )
        bundle = {"intelligence": {"ilo_indicators": ["fee_bondage"]}}

        selected = select_relevant_templates_for_bundle(
            bundle,
            templates={fee.id: fee, doc.id: doc},
        )

        assert [s.id for s in selected] == ["fee_template"]
        assert fee.summary_payload()["relevance_indicators"] == ["fee_bondage"]

    def test_indicator_aliases_survive_template_relevance_normalization(self):
        alias = _spec(
            "alias_template",
            (TemplateField("wages", "Withheld wages"),),
            relevance_indicators=(
                "FeeBondage",
                "withholding_of_wages",
                "deception",
                "contract substitution",
                "wage assignment",
                "restriction_of_movement",
                "retention_of_identity_documents",
            ),
        )
        bundle = {
            "intelligence": {
                "ilo_indicators": ["withheld_wages", "deceptive_recruitment"],
            }
        }

        selected = select_relevant_templates_for_bundle(
            bundle,
            templates={alias.id: alias},
        )

        assert [s.id for s in selected] == ["alias_template"]
        assert template_relevance_indicators(alias) == (
            "fee_bondage",
            "withheld_wages",
            "deceptive_recruitment",
            "wage_assignment",
            "movement_restriction",
            "passport_retention",
        )
        assert alias.summary_payload()["relevance_indicators"] == [
            "fee_bondage",
            "withheld_wages",
            "deceptive_recruitment",
            "wage_assignment",
            "movement_restriction",
            "passport_retention",
        ]

    def test_template_indicator_vocab_reuses_safe_text_vocab(self):
        assert tpl._CANONICAL_TEMPLATE_INDICATORS == STANDARD_FACT_INDICATORS

    def test_builtin_explicit_relevance_indicators_do_not_collapse_to_one_tag(self):
        refund = TEMPLATES_REGISTRY["recruitment_fee_refund_and_loan_void_demand"]
        substitution = TEMPLATES_REGISTRY["contract_substitution_complaint"]

        assert template_relevance_indicators(refund) == (
            "debt_bondage",
            "withheld_wages",
            "deceptive_recruitment",
        )
        assert template_relevance_indicators(substitution) == (
            "deceptive_recruitment",
            "abuse_of_vulnerability",
        )

    def test_unknown_template_id_returns_404(self):
        app = FastAPI()
        register_template_routes(app)
        client = TestClient(app)

        response = client.post(
            "/api/templates/fill-batch",
            json={"template_ids": ["does_not_exist"], "bundle": {}},
        )

        assert response.status_code == 404
        body = response.json()
        assert body["status"] == "unknown_template"
        assert "available" in body

    def test_template_sample_bundle_recommends_its_target(self):
        app = FastAPI()
        register_template_routes(app)
        client = TestClient(app)
        template = TEMPLATES_REGISTRY["hk_ld_fdh_complaint"]

        listing = client.get("/api/templates/list").json()["templates"]
        listed = next(t for t in listing if t["id"] == template.id)
        assert listed["sample_bundle_url"] == (
            "/api/templates/sample-bundle/hk_ld_fdh_complaint"
        )

        sample = client.get(listed["sample_bundle_url"])

        assert sample.status_code == 200
        bundle = sample.json()
        assert bundle["_meta"]["synthetic"] is True
        assert bundle["_meta"]["contains_real_pii"] is False
        assert bundle["config"]["target_template"] == template.id
        assert bundle["knowledge_fact_candidates"]

        rec = client.post(
            "/api/templates/recommend",
            json={"bundle": bundle, "use_gemma": False},
        )

        assert rec.status_code == 200
        body = rec.json()
        assert body["used_gemma"] is False
        ids = [r["template_id"] for r in body["recommendations"]]
        assert template.id in ids
        assert body["knowledge_fact_candidates"]

    def test_gemma_recommendation_can_add_valid_template_only(self):
        template_ids = list(TEMPLATES_REGISTRY)
        deterministic_id = template_ids[0]
        gemma_id = next(tid for tid in template_ids if tid != deterministic_id)
        bundle = template_sample_bundle(TEMPLATES_REGISTRY[deterministic_id])

        def fake_gemma(prompt, **kwargs):
            assert "TEMPLATE OPTIONS" in prompt
            return {
                "recommendations": [
                    {"template_id": gemma_id, "reason": "Adjacent route"},
                    {"template_id": "fabricated_template", "reason": "Ignore"},
                ],
            }

        out = recommend_templates_for_bundle(bundle, gemma_call=fake_gemma)

        ids = [r["template_id"] for r in out["recommendations"]]
        assert out["used_gemma"] is True
        assert deterministic_id in ids
        assert gemma_id in ids
        assert "fabricated_template" not in ids

    def test_extracted_fact_cards_redact_contact_like_pii(self):
        bundle = {
            "intelligence": {
                "case_brief": (
                    "Worker wrote jane@example.com, called +852 1234 5678, "
                    "and cited passport no A1234567 in the fee complaint."
                ),
                "ilo_indicators": ["fee_bondage"],
            }
        }

        facts = extract_template_knowledge_facts(bundle)
        text = str(facts)

        assert "jane@example.com" not in text
        assert "+852 1234 5678" not in text
        assert "A1234567" not in text
        assert "redacted" in text
