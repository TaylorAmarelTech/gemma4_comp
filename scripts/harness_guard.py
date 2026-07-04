#!/usr/bin/env python3
"""Deterministic serving guard -- never deliver a harnessed reply that is WORSE than the baseline.

The grounding harness LIFTS the large majority of replies (it adds the indicator + statute + resource
the bare model omits). On a small tail it HURTS -- the *negative-lift* cases, the instances "where the
harness hurts". This guard runs at serve time on the two candidate texts (no model call, no judge, no
score) and falls back to the baseline ONLY when the harnessed reply carries a deterministic signature of
having LOST safety-relevant content the baseline had.

The signals were chosen from a measurement on the committed grades (``scripts/analyze_harness_guard.py``
-> ``docs/research/harness_guard_analysis.md``), which produced a decisive negative result about the
NAIVE guard and shaped the ones kept here:

  * ``bare_nonanswer``      -- baseline was useful, harnessed is a NON-answer (refusal / empty / too
    short / a reasoning-trace) AND is itself ungrounded (cites no statute section). Requiring ungrounded
    is essential: a *grounded refusal* ("I can't help you trap a worker -- but here is the indicator,
    ILO C29, and the hotline") is the harness working as designed and must NEVER be reverted. Only a
    BARE non-answer is a regression.
  * ``citation_regression`` -- the baseline cited >=1 statute section and the harnessed reply cites
    NONE. Targets the strong-baseline signature: a model like gpt-oss writes a cited legal analysis
    unaided, and a harnessed rewrite that reads fine but silently drops the statute is a real loss.

Explicitly REJECTED as a length signal (kept only as an opt-in analysis signal, never in a default
policy): ``drastic_shortening`` -- "harnessed much shorter than baseline". A verbose baseline (gpt-oss
averages ~9.5k chars) is very often IMPROVED by a shorter, focused, grounded reply, so a length signal
fires overwhelmingly where the harness HELPED. Length is not a proxy for quality loss.

MEASURED RESULT (docs/research/harness_guard_analysis.md, current grades): a guard's worth is entirely
about how tightly it targets the CATASTROPHIC tail. The broad ``min`` policy is net-NEGATIVE: it fired
512 times but MISFIRED on 458 (reverting a harnessed reply that had actually scored ABOVE baseline,
~-19k pts) against 54 catches, because the harness's signature win is a *grounded refusal* that
``refusal_detector`` flags as a "refusal" -- no cheap phrase test separates it from a bare "I can't
help". BUT the tight ``hard`` policy (``hard_collapse``: a >=1k-char baseline turned into a <=150-char
reply) is net-POSITIVE (+1,525 pts; guarded mean 85.3 > 84.9 unguarded): its length cap physically
cannot fire on a grounded refusal (those run to hundreds/thousands of chars), so it catches the ~38-char
catastrophes (51 big recoveries) with few, small misfires (41, small deltas). So
``DEFAULT_GUARD_POLICY`` is ``hard`` -- a cheap serving-time safety net for the catastrophic tail. The
larger lever against "the harness hurts" is still serving ``harness_core`` instead of ``harness_full``
(full <= core for every model); ``hard`` sits on top. (~65% of the MILDER negative-lift tail is
``other`` -- a full-length reply the judge scored slightly lower -- which no text guard should touch.)

Pure stdlib plus two sibling detectors (``refusal_detector``, ``citation_accuracy``); safe to import
anywhere, including the offline analysis path.
"""
from __future__ import annotations

# Threshold for the opt-in (non-default) ``drastic_shortening`` analysis signal only.
MIN_LEN_RATIO = 0.4
MIN_BASELINE_CHARS = 200

# ``hard_collapse``: the catastrophic tail found via the benchmark DB -- a substantive baseline (a long
# gpt-oss legal analysis, 9k-17k chars scoring 83-96) turned into a ~38-char bare refusal scoring ~17
# (a -75 drop). The tight length gate catches ONLY these and NEVER a *grounded* refusal, which runs to
# hundreds/thousands of chars, so a <150-char cap cannot fire on it. That is the separation the broad
# ``min`` guard lacked (it keyed on the refusal PHRASE, which grounded refusals also carry).
HARD_COLLAPSE_MAX_CHARS = 150      # the collapsed reply must be this short (a bare refusal is ~38 chars)
HARD_COLLAPSE_MIN_BASELINE = 1000  # ...and the baseline must have been substantial (so fallback is safe)

GUARD_SIGNALS = ("bare_nonanswer", "citation_regression", "drastic_shortening", "hard_collapse")

# A policy is an ORDERED tuple of signal names; the first that fires attributes the fallback.
# NB: all non-``off`` policies measured net-NEGATIVE on the current grades (see module docstring); they
# exist so the analysis can quantify that, and to be re-measured on other data, not as a recommendation.
GUARD_POLICIES: dict[str, tuple[str, ...]] = {
    "off": (),
    # Minimal grounding-loss guard (bare non-answer + dropped-all-citations). Measured net-negative here.
    "min": ("bare_nonanswer", "citation_regression"),
    # Adds the length signal -- retained ONLY to demonstrate its (worse) measured net-negative effect.
    "len": ("bare_nonanswer", "citation_regression", "drastic_shortening"),
    # Catches ONLY the catastrophic ~38-char collapses of a long baseline; designed to avoid the misfires
    # that sank ``min`` (grounded refusals are long, so the length cap cannot fire on them). Measured.
    "hard": ("hard_collapse",),
}
# ``hard`` by measurement (docs/research/harness_guard_analysis.md): the tight hard-collapse guard is the
# one fallback policy that is net-POSITIVE (+1,525 pts; guarded mean 85.3 > 84.9 unguarded). ``min``/``len``
# are net-negative (they revert grounded refusals). Re-run scripts/analyze_harness_guard.py if the grades
# change materially. The larger lever against "the harness hurts" remains serving ``harness_core``.
DEFAULT_GUARD_POLICY = "hard"


def _require_policy(policy: str) -> tuple[str, ...]:
    if policy not in GUARD_POLICIES:
        raise ValueError(f"unknown guard policy: {policy!r} (expected one of {tuple(GUARD_POLICIES)})")
    return GUARD_POLICIES[policy]


def guard_signals(baseline: str, harnessed: str, *, min_len_ratio: float = MIN_LEN_RATIO,
                  min_baseline_chars: int = MIN_BASELINE_CHARS) -> dict[str, bool]:
    """Return each deterministic harm-signal independently (for the analysis to tabulate).

    Every signal is gated on the baseline being *useful* -- a guard must never fall back FROM a bad
    baseline (there is nothing better to fall back to), only away from a harnessed reply that lost
    something a good baseline had.
    """
    from refusal_detector import classify              # sibling; lazy so importers stay light
    from citation_accuracy import citation_stats        # sibling; lazy

    baseline = baseline if isinstance(baseline, str) else ""
    harnessed = harnessed if isinstance(harnessed, str) else ""
    b_useful, _b_reason = classify(baseline)
    h_useful, _h_reason = classify(harnessed)
    b_cites = citation_stats(baseline)["n_section_refs"] if baseline else 0
    h_cites = citation_stats(harnessed)["n_section_refs"] if harnessed else 0

    # A bare non-answer: harnessed did not answer AND is ungrounded (a grounded refusal has h_cites > 0
    # and is therefore NOT flagged -- it is the harness working, not a regression).
    bare_nonanswer = bool(b_useful and (not h_useful) and h_cites == 0)
    citation_regression = bool(b_useful and b_cites >= 1 and h_cites == 0)
    drastic_shortening = bool(
        b_useful and len(baseline) > min_baseline_chars and len(harnessed) < min_len_ratio * len(baseline))
    # A hard collapse: a substantial baseline turned into an absurdly short reply -- too short to be
    # grounded, so (unlike the refusal phrase) this cannot fire on a grounded refusal.
    hard_collapse = bool(
        b_useful and len(baseline) >= HARD_COLLAPSE_MIN_BASELINE
        and len(harnessed) <= HARD_COLLAPSE_MAX_CHARS)

    return {"bare_nonanswer": bare_nonanswer, "citation_regression": citation_regression,
            "drastic_shortening": drastic_shortening, "hard_collapse": hard_collapse}


def harness_guard(baseline: str, harnessed: str, *, policy: str = DEFAULT_GUARD_POLICY,
                  min_len_ratio: float = MIN_LEN_RATIO,
                  min_baseline_chars: int = MIN_BASELINE_CHARS) -> tuple[str, str | None]:
    """Choose the response to deliver: ``(chosen_response, fell_back_reason | None)``.

    Falls back to the baseline reply on the first signal in ``policy`` that fires; otherwise keeps the
    harnessed reply (the usual grounded improvement). This bounds the harness so the delivered answer is
    never a *detectable* regression: at deployment, generate harnessed, run this cheap check, and serve
    the baseline only on the guarded tail. Pure deterministic text analysis; no model call.
    """
    signals = guard_signals(baseline, harnessed, min_len_ratio=min_len_ratio,
                            min_baseline_chars=min_baseline_chars)
    for name in _require_policy(policy):
        if signals[name]:
            return baseline, name
    return harnessed, None
