"""Tests for the DueCare indicator engine port."""
from __future__ import annotations

from duecare.kit.engine import generate_chain, risk_level, scan

# Composite/synthetic worker account (no real PII) that stacks several ILO indicators.
HARMFUL = (
    "The recruitment agency took my passport when I arrived. I still have not been paid my "
    "salary, and they say I must work off the placement fee debt before I can leave. I am not "
    "allowed to leave the compound and my phone was taken."
)
BENIGN = (
    "I started a new job at a local cafe downtown. The pay is fair and arrives on time every "
    "week, my manager is supportive, and my hours are reasonable with weekends free. I feel safe "
    "and can come and go as I like."
)


def test_scan_detects_at_least_four_indicators_on_harmful_example():
    hits = scan(HARMFUL)
    indicators = {h["indicator"] for h in hits}
    assert len(indicators) >= 4, f"expected >=4 distinct indicators, got {sorted(indicators)}"


def test_harmful_example_is_high_risk():
    level, _ = risk_level(scan(HARMFUL))
    assert level == "HIGH"


def test_benign_example_is_not_high_risk():
    level, _ = risk_level(scan(BENIGN))
    assert level != "HIGH"


def test_scan_returns_grounded_hit_shape():
    hits = scan(HARMFUL)
    assert hits, "harmful text should produce hits"
    for h in hits:
        assert set(h) == {"indicator", "label", "snippet", "ilo_ref"}
        assert h["ilo_ref"], "every hit cites an ILO reference"


def test_risk_level_thresholds():
    assert risk_level([])[0] == "LOW"
    assert risk_level([{"indicator": "x"}])[0] == "WATCH"
    assert risk_level([{"indicator": "x"}, {"indicator": "y"}])[0] == "ELEVATED"
    four = [{"indicator": i} for i in "abcd"]
    assert risk_level(four)[0] == "HIGH"


def test_generate_chain_reasons_and_concludes():
    steps = generate_chain(HARMFUL)
    assert steps, "chain should not be empty"
    assert all(isinstance(n, int) and isinstance(text, str) for n, text in steps)
    # numbered contiguously from 1
    assert [n for n, _ in steps] == list(range(1, len(steps) + 1))
    conclusion = steps[-1][1]
    assert "Conclusion" in conclusion and "risk = HIGH" in conclusion


def test_generate_chain_marks_present_indicators():
    steps = generate_chain(HARMFUL)
    present = [t for _, t in steps if "PRESENT" in t]
    assert present, "at least one indicator question should resolve to PRESENT"


# --- recall: contract legalese and South Asian fee amounts (closed 2026-07-26) -----------------
# The compact engine previously matched only first-person narrative phrasing, so a written contract
# clause naming the worker in the third person -- the single most common documentary red flag -- and
# lakh/crore fee amounts went undetected. Measured additive on 15,600 real texts: +442 rows, 0 lost.

def _inds(text):
    return {h["indicator"] for h in scan(text)}


def test_possessive_contract_clause_is_document_retention():
    assert "document_retention" in _inds(
        "The Employer shall retain the Employee's passport for the contract duration.")
    assert "document_retention" in _inds(
        "Management holds all workers' passports in the site safe.")


def test_third_party_custody_phrasing_is_document_retention():
    assert "document_retention" in _inds(
        "The passport stays with the employer until the contract ends.")
    assert "document_retention" in _inds("Your documents remain with the company office.")


def test_worker_keeping_own_documents_is_still_not_flagged():
    # The precision guard must survive the recall broadening (ILO C189 Art. 9 is the benign case).
    assert "document_retention" not in _inds("I keep my own passport in my room.")
    assert "document_retention" not in _inds(
        "The passport stays with the employee at all times.")
    assert "document_retention" not in _inds(
        "Workers keep their own passports at all times under C189.")


def test_south_asian_fee_amounts_are_recruitment_fees():
    assert "recruitment_fee" in _inds("The broker demanded 1.5 crore rupees as placement money.")
    assert "recruitment_fee" in _inds("I paid 2 lakh to the agent for the job in Dubai.")


def test_ordinary_salary_in_lakh_is_not_a_recruitment_fee():
    # A lakh/crore amount only counts near a recruiter/placement context, not any large number.
    assert "recruitment_fee" not in _inds(
        "My annual salary is 8 lakh rupees and I am paid on time.")


def test_response_naming_the_prohibition_still_counts_as_the_indicator():
    # scan() serves BOTH roles: screening an incoming account AND checking whether a model RESPONSE
    # names the indicator. A response that cites the prohibition is correctly naming it, so it must
    # not be suppressed -- a prohibition-aware guard was measured to drop 6.3% of real detections.
    assert "document_retention" in _inds(
        "Under ICRMW Art. 21 your employer may not confiscate your passport.")
