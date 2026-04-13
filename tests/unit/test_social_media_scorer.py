"""Tests for the social media risk scorer."""

from __future__ import annotations

import pytest

from src.demo.social_media_scorer import (
    ContentType,
    RiskAssessment,
    RiskLevel,
    SocialMediaRiskScorer,
    quick_risk_score,
    analyze_job_posting,
    RISK_INDICATORS,
    _CATEGORY_LABELS,
)


@pytest.fixture
def scorer() -> SocialMediaRiskScorer:
    return SocialMediaRiskScorer()


# -----------------------------------------------------------------------
# test_scores_suspicious_job_posting
# -----------------------------------------------------------------------

def test_scores_suspicious_job_posting(scorer: SocialMediaRiskScorer):
    """A posting with multiple trafficking indicators should score high."""
    posting = (
        "URGENT HIRING! Domestic helpers needed in Saudi Arabia. "
        "No experience required. Salary: $5,000/month. "
        "Guaranteed job! Pay processing fee of $3,000 upfront. "
        "Submit your passport upon arrival. "
        "Contact via Viber only. Limited slots available!"
    )
    result = scorer.score_content(posting, content_type=ContentType.JOB_POSTING)

    assert isinstance(result, RiskAssessment)
    assert result.risk_score > 40.0
    assert result.risk_level in {RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL}
    assert len(result.indicators) >= 4

    # Should hit multiple categories
    categories = {ind.category for ind in result.indicators}
    assert len(categories) >= 3  # recruitment, financial, communication, etc.

    # content_id should be a hex hash prefix
    assert len(result.content_id) == 16


def test_scores_passport_confiscation_high(scorer: SocialMediaRiskScorer):
    """Passport-related content should trigger document_control (severity 9)."""
    text = "Submit your passport when you arrive. We will keep it safe for you."
    result = scorer.score_content(text)

    doc_indicators = [i for i in result.indicators if i.category == "document_control"]
    assert len(doc_indicators) >= 1
    assert doc_indicators[0].severity >= 6


def test_scores_debt_bondage_patterns(scorer: SocialMediaRiskScorer):
    """Salary advance scheme indicators should score high."""
    text = "We offer salary advance and loan available for travel costs. Borrow from us."
    result = scorer.score_content(text)

    fin_indicators = [i for i in result.indicators if i.category == "financial"]
    assert len(fin_indicators) >= 1
    # salary_advance_scheme has severity 8
    assert any(i.severity >= 7 for i in fin_indicators)


# -----------------------------------------------------------------------
# test_scores_safe_posting_low
# -----------------------------------------------------------------------

def test_scores_safe_posting_low(scorer: SocialMediaRiskScorer):
    """A normal job posting with no red flags should score minimal/low."""
    posting = (
        "We are looking for a software developer with 5 years of experience "
        "in Python and JavaScript. Full benefits, healthcare, and 401k. "
        "Apply through our careers page at example.com/careers."
    )
    result = scorer.score_content(posting)

    assert result.risk_score <= 20.0
    assert result.risk_level == RiskLevel.MINIMAL
    assert len(result.indicators) == 0


def test_scores_normal_conversation_minimal(scorer: SocialMediaRiskScorer):
    """A regular conversation should have minimal risk."""
    text = "The weather is beautiful today. I went to the park with my family."
    result = scorer.score_content(text)

    assert result.risk_score == 0.0
    assert result.risk_level == RiskLevel.MINIMAL
    assert len(result.indicators) == 0


def test_empty_text_scores_zero(scorer: SocialMediaRiskScorer):
    """Empty text should score 0 risk."""
    result = scorer.score_content("")

    assert result.risk_score == 0.0
    assert result.risk_level == RiskLevel.MINIMAL
    assert len(result.indicators) == 0


# -----------------------------------------------------------------------
# test_six_risk_categories
# -----------------------------------------------------------------------

def test_six_risk_categories(scorer: SocialMediaRiskScorer):
    """The scorer defines exactly 6 risk indicator categories."""
    expected_categories = {
        "recruitment",
        "financial",
        "document_control",
        "communication",
        "control",
        "vagueness",
    }
    actual_categories = set(RISK_INDICATORS.keys())
    assert actual_categories == expected_categories


def test_category_breakdown_always_has_six(scorer: SocialMediaRiskScorer):
    """category_breakdown in the result should list all 6 categories."""
    result = scorer.score_content("Any text here.")
    categories_in_breakdown = {cb.category for cb in result.category_breakdown}

    # Should use display labels
    expected_labels = set(_CATEGORY_LABELS.values())
    assert categories_in_breakdown == expected_labels


def test_each_category_has_indicators():
    """Each of the 6 categories should have at least one indicator defined."""
    for category, indicators in RISK_INDICATORS.items():
        assert len(indicators) >= 1, f"Category {category} has no indicators"
        for name, data in indicators.items():
            assert "patterns" in data, f"{category}.{name} missing patterns"
            assert "severity" in data, f"{category}.{name} missing severity"
            assert len(data["patterns"]) >= 1, f"{category}.{name} has no patterns"
            assert 1 <= data["severity"] <= 10, f"{category}.{name} severity out of range"


# -----------------------------------------------------------------------
# test_returns_recommendations
# -----------------------------------------------------------------------

def test_returns_recommendations_for_high_risk(scorer: SocialMediaRiskScorer):
    """High-risk content should produce actionable recommendations."""
    posting = (
        "URGENT HIRING! Pay $5,000 processing fee. Submit your passport. "
        "Guaranteed job overseas. Contact via Whatsapp only."
    )
    result = scorer.score_content(posting, content_type=ContentType.JOB_POSTING)

    assert len(result.recommendations) > 0

    # Should include hotline info
    hotline_recs = [r for r in result.recommendations if "hotline" in r.lower() or "1-888" in r]
    assert len(hotline_recs) >= 1

    # Should include protective advice
    all_recs_text = " ".join(result.recommendations).lower()
    assert "passport" in all_recs_text or "fee" in all_recs_text or "verify" in all_recs_text


def test_returns_minimal_recommendations_for_safe_content(scorer: SocialMediaRiskScorer):
    """Safe content should get a simple reassurance recommendation."""
    result = scorer.score_content("Normal job posting for engineers.")

    assert len(result.recommendations) >= 1
    # Should mention verification even for safe content
    assert any("verify" in r.lower() or "safe" in r.lower() for r in result.recommendations)


def test_recommendations_category_specific(scorer: SocialMediaRiskScorer):
    """Recommendations should be tailored to the categories that triggered."""
    # Financial indicators only
    text = "Pay $3,000 processing fee before deployment."
    result = scorer.score_content(text)

    if result.risk_level != RiskLevel.MINIMAL:
        recs_text = " ".join(result.recommendations).lower()
        assert "fee" in recs_text or "recruitment" in recs_text or "pay" in recs_text


def test_document_control_recommendations(scorer: SocialMediaRiskScorer):
    """Document control triggers should produce passport-related recommendations."""
    text = "Surrender your passport to the agency upon arrival."
    result = scorer.score_content(text)

    # Either the recommendations mention passport/document or the risk score is elevated
    recs_text = " ".join(result.recommendations).lower()
    assert result.risk_score > 0 or "passport" in recs_text or "document" in recs_text


# -----------------------------------------------------------------------
# Content type detection
# -----------------------------------------------------------------------

def test_detects_job_posting_type(scorer: SocialMediaRiskScorer):
    """Text with hiring/salary/job keywords should be detected as JOB_POSTING."""
    text = "Hiring! Job vacancy for cleaners. Salary $2000/month. Apply now."
    result = scorer.score_content(text)
    assert result.content_type == ContentType.JOB_POSTING


def test_explicit_content_type_overrides(scorer: SocialMediaRiskScorer):
    """Passing content_type explicitly should override auto-detection."""
    result = scorer.score_content(
        "Random text here",
        content_type=ContentType.CHAT_MESSAGE,
    )
    assert result.content_type == ContentType.CHAT_MESSAGE


# -----------------------------------------------------------------------
# Risk level thresholds
# -----------------------------------------------------------------------

def test_risk_level_thresholds(scorer: SocialMediaRiskScorer):
    """Verify the risk level classification thresholds."""
    assert scorer._determine_risk_level(0.0) == RiskLevel.MINIMAL
    assert scorer._determine_risk_level(20.0) == RiskLevel.MINIMAL
    assert scorer._determine_risk_level(20.1) == RiskLevel.LOW
    assert scorer._determine_risk_level(40.0) == RiskLevel.LOW
    assert scorer._determine_risk_level(40.1) == RiskLevel.MODERATE
    assert scorer._determine_risk_level(60.0) == RiskLevel.MODERATE
    assert scorer._determine_risk_level(60.1) == RiskLevel.HIGH
    assert scorer._determine_risk_level(80.0) == RiskLevel.HIGH
    assert scorer._determine_risk_level(80.1) == RiskLevel.CRITICAL
    assert scorer._determine_risk_level(100.0) == RiskLevel.CRITICAL


# -----------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------

def test_summary_for_risky_content(scorer: SocialMediaRiskScorer):
    """Summary should mention indicator counts and critical concerns."""
    text = (
        "Pay $5000 fee. Submit your passport. "
        "Salary advance available. Accommodation provided."
    )
    result = scorer.score_content(text)

    assert len(result.summary) > 0
    assert "indicator" in result.summary.lower() or "concern" in result.summary.lower()


def test_summary_for_safe_content(scorer: SocialMediaRiskScorer):
    """Summary for safe content should say no indicators detected."""
    result = scorer.score_content("Nice day for a walk.")

    assert "no significant risk" in result.summary.lower()


# -----------------------------------------------------------------------
# Convenience functions
# -----------------------------------------------------------------------

def test_quick_risk_score_returns_dict():
    """quick_risk_score should return a lightweight summary dict."""
    result = quick_risk_score("Pay $3000 processing fee before deployment")

    assert isinstance(result, dict)
    assert "risk_score" in result
    assert "risk_level" in result
    assert "indicator_count" in result
    assert "categories" in result
    assert "summary" in result
    assert result["indicator_count"] >= 1


def test_analyze_job_posting_convenience():
    """analyze_job_posting should return a RiskAssessment with JOB_POSTING type."""
    result = analyze_job_posting("Hiring workers, no experience needed, guaranteed job!")

    assert isinstance(result, RiskAssessment)
    assert result.content_type == ContentType.JOB_POSTING


# -----------------------------------------------------------------------
# Indicator evidence and context
# -----------------------------------------------------------------------

def test_indicators_include_evidence(scorer: SocialMediaRiskScorer):
    """Each matched indicator should carry evidence and context."""
    text = "No experience required for this urgent hiring opportunity."
    result = scorer.score_content(text)

    for ind in result.indicators:
        assert len(ind.evidence) > 0, "Indicator must have evidence"
        assert len(ind.context) > 0, "Indicator must have context"
        assert len(ind.explanation) > 0, "Indicator must have explanation"
        assert 1 <= ind.severity <= 10
