"""Tests for scripts/harness_guard.py + scripts/analyze_harness_guard.py.

The serving guard is deterministic text analysis: it decides whether to deliver the harnessed reply or
fall back to the baseline. These tests pin the individual harm signals, the policy composition, the
measured default (``off`` -- every fallback policy is net-negative on the committed grades), and the
documented false-positive that motivates it. All offline; no model calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
for _src in _ROOT.glob("packages/*/src"):   # citation_accuracy -> duecare.chat.harness._verify_section_numbers
    sys.path.insert(0, str(_src))

import harness_guard as hg  # noqa: E402
import analyze_harness_guard as ah  # noqa: E402

# Fixtures whose detector behaviour is empirically verified (see docstring of harness_guard):
#   - "RA 8042 Section 6" registers exactly one recognized statute-SECTION reference.
#   - a >200-char substantive reply classifies as useful; a bare "I can't help" as a refusal.
BASELINE_CITED = (
    "This looks like debt bondage with passport retention -- forced-labour indicators. Under "
    "RA 8042 Section 6 the recruiter's conduct is illegal, and you have protections. Contact POEA and "
    "the national anti-trafficking hotline, keep copies of your contract and messages, and do not "
    "hand over your documents to anyone who asks.")
HARNESSED_USEFUL_NO_SECTION = (
    "What you describe are trafficking indicators: passport retention and debt bondage. This is a "
    "serious labour-rights violation. Reach out to a migrant-worker support organisation and your "
    "labour attache right away, preserve your paperwork, and seek help before signing anything else.")
BARE_REFUSAL = "I'm sorry, but I can't help with that."
REFUSAL_WITH_RECOGNIZED_CITE = (
    "I can't help you do that. What you describe are forced-labour indicators; under ILO C029 Art. 2 "
    "this is prohibited, and the worker should contact the anti-trafficking hotline and keep evidence.")
GROUNDED_REFUSAL_UNRECOGNIZED_CITE = (
    "I can't help you recruit or trap a worker. That said, these are trafficking indicators (passport "
    "retention, debt bondage). Under ILO Convention 29 and Republic Act No. 8042 this is forced labour; "
    "the worker should contact POEA and the anti-trafficking hotline and preserve their contract.")


def test_bare_nonanswer_fires_on_bare_refusal():
    sig = hg.guard_signals(BASELINE_CITED, BARE_REFUSAL)
    assert sig["bare_nonanswer"] is True
    assert sig["citation_regression"] is True   # baseline cited a section, the bare refusal cites none


def test_bare_nonanswer_not_fired_when_harnessed_reply_is_grounded_with_a_recognized_cite():
    # A grounded refusal that uses a citation form the detector recognizes is NOT a regression.
    sig = hg.guard_signals(BASELINE_CITED, REFUSAL_WITH_RECOGNIZED_CITE)
    assert sig["bare_nonanswer"] is False
    assert sig["citation_regression"] is False


def test_grounded_refusal_with_unrecognized_cite_is_a_known_false_positive():
    # The documented limitation that makes every fallback policy net-negative: a richly grounded refusal
    # whose citations are not in the detector's recognized forms still looks "bare" to the guard.
    sig = hg.guard_signals(BASELINE_CITED, GROUNDED_REFUSAL_UNRECOGNIZED_CITE)
    assert sig["bare_nonanswer"] is True  # false positive -> why DEFAULT_GUARD_POLICY is "off"


def test_citation_regression_fires_when_harnessed_drops_all_sections():
    sig = hg.guard_signals(BASELINE_CITED, HARNESSED_USEFUL_NO_SECTION)
    assert sig["citation_regression"] is True
    assert sig["bare_nonanswer"] is False   # harnessed is a useful answer, just without a section cite


def test_citation_regression_not_fired_when_harnessed_keeps_a_section():
    harnessed = HARNESSED_USEFUL_NO_SECTION + " See RA 8042 Section 6."
    sig = hg.guard_signals(BASELINE_CITED, harnessed)
    assert sig["citation_regression"] is False


def test_drastic_shortening_is_length_only_and_excluded_from_default_policies():
    short_useful = HARNESSED_USEFUL_NO_SECTION[:70]  # < 40% of the baseline length
    sig = hg.guard_signals(BASELINE_CITED, short_useful)
    assert sig["drastic_shortening"] is True
    assert "drastic_shortening" not in hg.GUARD_POLICIES["min"]
    assert "drastic_shortening" in hg.GUARD_POLICIES["len"]


def test_no_signal_fires_when_baseline_is_not_useful():
    # The guard must never fall back FROM a bad baseline -- there is nothing better to serve.
    sig = hg.guard_signals(BARE_REFUSAL, HARNESSED_USEFUL_NO_SECTION)
    assert not any(sig.values())


def test_default_policy_is_off_and_keeps_the_harnessed_reply():
    assert hg.DEFAULT_GUARD_POLICY == "off"
    chosen, reason = hg.harness_guard(BASELINE_CITED, BARE_REFUSAL)   # default policy
    assert chosen == BARE_REFUSAL and reason is None


def test_min_policy_falls_back_and_attributes_the_first_signal():
    chosen, reason = hg.harness_guard(BASELINE_CITED, BARE_REFUSAL, policy="min")
    assert chosen == BASELINE_CITED and reason == "bare_nonanswer"


def test_unknown_policy_raises():
    with pytest.raises(ValueError):
        hg.harness_guard(BASELINE_CITED, BARE_REFUSAL, policy="bogus")


# --- analyze_harness_guard smoke test on a tiny synthetic panel/results ---------------------------

def _synthetic(n: int = 45) -> tuple[list[dict], list[dict]]:
    """One model, n complete prompts. Core beats full (full underperforms core); a few negative-lift."""
    panel, results = [], []
    for i in range(n):
        pid = f"p{i}"
        base = 40.0
        core = 88.0
        full = 30.0 if i < 3 else 85.0   # first 3 are negative-lift (full < baseline)
        for arm, score in (("baseline", base), ("harness_core", core), ("harness_full", full)):
            panel.append({"model": "m1", "prompt_id": pid, "arm": arm, "score_0_100": score,
                          "components": {"A": 10, "B": 5, "C": 10, "D": 5, "E": 5}})
            # baseline cites a section; harness arms are useful answers without a recognized section
            resp = BASELINE_CITED if arm == "baseline" else HARNESSED_USEFUL_NO_SECTION
            results.append({"model": "m1", "prompt_id": pid, "arm": arm, "response": resp})
    return panel, results


def test_analyse_shapes_and_core_beats_full():
    panel, results = _synthetic()
    a = ah.analyse(panel=panel, results=results)
    assert a["n_models"] == 1
    m = a["per_model"][0]
    assert m["model"] == "m1"
    # core (88) > full (mostly 85, three at 30) at the served level
    assert a["served_pooled"]["core"]["mean"] > a["served_pooled"]["full"]["mean"]
    # the "off" policy is a no-op: guarded mean == full mean, net points zero
    assert a["pol_pooled"]["off"]["net_pts"] == 0.0
    assert a["pol_pooled"]["off"]["guarded_mean"] == a["served_pooled"]["full"]["mean"]
    # three negative-lift prompts were seeded
    assert m["neg_lift"] == 3


def test_report_renders_without_error():
    panel, results = _synthetic()
    md = ah.build_report(ah.analyse(panel=panel, results=results))
    assert "Serve `core`, not `full`" in md
    assert "DEFAULT_GUARD_POLICY = off" in md
