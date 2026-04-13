"""Tests for the document acquisition/processing pipeline."""

from __future__ import annotations

from duecare.domains.pipeline.extractor import extract_facts
from duecare.domains.pipeline.classifier import classify_fact


class TestFactExtractor:
    def test_extracts_legal_citations(self):
        text = "Under ILO C181 Article 7 and Philippine RA 10022, workers should not pay fees."
        facts = extract_facts(text)
        types = [f.fact_type.value if hasattr(f.fact_type, 'value') else str(f.fact_type) for f in facts]
        assert any("legal" in t for t in types) or any("organisation" in t for t in types)

    def test_extracts_monetary_amounts(self):
        text = "The agency charged PHP 50,000 for placement and USD 2,000 for training."
        facts = extract_facts(text)
        values = [f.value for f in facts]
        assert any("50,000" in v or "50000" in v for v in values)

    def test_extracts_countries(self):
        text = "Workers from the Philippines going to Saudi Arabia face exploitation."
        facts = extract_facts(text)
        values = [f.value.lower() for f in facts]
        assert any("philippines" in v for v in values) or any("saudi" in v for v in values)

    def test_handles_empty_text(self):
        facts = extract_facts("")
        assert isinstance(facts, list)
        assert len(facts) == 0

    def test_extracts_organizations(self):
        text = "Contact POEA at 1343 or report to IOM and IJM for assistance."
        facts = extract_facts(text)
        values = [f.value for f in facts]
        assert "POEA" in values or "IOM" in values


class TestFactClassifier:
    def test_classifies_sector(self):
        result = classify_fact(fact_type="text", value="domestic worker in Hong Kong household", context="employment scenario")
        assert hasattr(result, 'sector')
        assert result.sector is not None

    def test_classifies_exploitation_type(self):
        result = classify_fact(fact_type="text", value="passport confiscated by employer", context="document retention scenario")
        assert result is not None
        assert hasattr(result, 'exploitation_type')
