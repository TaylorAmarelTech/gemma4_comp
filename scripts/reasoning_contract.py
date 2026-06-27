#!/usr/bin/env python3
"""Reasoning contract -- a formal, deterministic spec of the WAY OF THINKING a migrant-worker-safety
answer must follow, so a Gemma 4 reasoning LoRA can be trained to internalise a *procedure* (not facts)
and have that procedure ENFORCED at inference instead of merely hoped for.

The idea (per Taylor): rather than a LoRA that memorises facts (brittle, low-rank capacity, goes stale),
a LoRA that stores a *way of thinking* -- a fixed reasoning scaffold, jurisdiction-independent and free
of volatile specifics -- with contracts + verifications enforcing the chain of thought. This module is
that contract. It is used THREE ways:

  1. TRAINING FILTER   -- keep only reasoning traces that SATISFY the contract (the LoRA learns the
                          scaffold). build_reasoning_targets.py already gates on link presence; this is
                          the stricter, enforceable form (order + valid citation + no fragile facts).
  2. INFERENCE ENFORCE -- parse a model's thinking trace, verify each step deterministically, and emit a
                          REPAIR DIRECTIVE when a step is missing/wrong -> a verify-and-repair loop that
                          enforces the CoT (the harness re-prompts with the repair hint).
  3. EVAL METRIC       -- % of responses whose CoT satisfies the contract: a judge-INDEPENDENT quality
                          signal (a candidate additive board column alongside the LLM-panel lift).

The contract -- the scaffold the LoRA should think in:

    indicator  ->  statute  ->  action  ->  resources
    (name the ILO  (cite the     (concrete    (route the worker
     indicator)    controlling   protective    to protective help)
                   law)          step)

Each step has a DETERMINISTIC verifier reusing the project's own tools (build_reasoning_targets'
chain detectors built on migrant_taxonomy ILO indicators + citation_accuracy + refusal_detector). Two
enforcements beyond mere presence make it a contract, not a checklist:

  * CITATION VALIDITY -- a cited statute must not be hallucinated (citation_stats.n_section_implausible
    == 0). The model may not invent a section number to satisfy the "statute" step.
  * FRAGILE-FACT PROHIBITION -- the reasoning must not assert volatile specifics (phone/hotline numbers
    especially; fee amounts / dates are flagged). Those belong in tools/RAG; forbidding them in the
    reasoning is what keeps the LoRA storing a way of THINKING, not memorised facts.

Offline + deterministic. No model, no network, no credits -- so the contract is reproducible and runs
during the credit outage.

    python scripts/reasoning_contract.py                 # contract pass-rate over the gold reasoning set
    python scripts/reasoning_contract.py --text "..."    # verify one reply, print the verdict + repair hint
Design: docs/research/training_methodology.md (reasoning contract); training_regimes_and_systems.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass, asdict
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))   # sibling-script imports
# Reuse the chain detectors (DRY) -- migrant_taxonomy ILO indicators + citation_accuracy + refusal_detector.
from build_reasoning_targets import (  # noqa: E402
    chain_links, _INDICATOR_TERMS, _ACTION_TERMS, _RESOURCE_TERMS,
)
from citation_accuracy import citation_stats as _citation_stats  # noqa: E402
from refusal_detector import classify as _classify, FORMAT_FAILURE  # noqa: E402
from palermo_screening import palermo_analysis  # noqa: E402  -- Act-Means-Purpose triad + screening signals

REASONING_SFT = _ROOT / "reports" / "training" / "reasoning_sft.jsonl"
OUT = _ROOT / "reports" / "training" / "reasoning_contract.json"

STEPS = ("indicator", "statute", "action", "resources")
# Fragile facts forbidden IN THE REASONING (mirror of audit_training_quality; here phone is a hard fail --
# the way-of-thinking must not encode a volatile contact). Money/date are flagged but not hard fails
# (a statute's enactment year is stable; an in-scenario amount is description, not an asserted rule).
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_MONEY = re.compile(r"(?:\$|usd|eur|php|aed|sar)\s?\d[\d,]*", re.I)
_DATE = re.compile(r"\b(?:20\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
# Thinking-trace delimiters Gemma-4-thinking / common templates may emit; if none, the whole text is used.
_THINK_SPLIT = re.compile(r"</think>|<end_of_thinking>|<end_working>|\n\s*(?:final answer|answer)\s*:",
                          re.IGNORECASE)


def split_thinking(text: str) -> tuple[str, str]:
    """(reasoning, answer). If a thinking delimiter is present, split on it; otherwise the whole text is
    treated as both (the chain may appear anywhere -- we verify the full text by default)."""
    m = _THINK_SPLIT.search(text or "")
    if not m:
        return text or "", text or ""
    return (text[: m.start()], text[m.end():])


def _first_pos(text: str, terms: tuple[str, ...]) -> "int | None":
    low = text.lower()
    hits = [low.find(t) for t in terms if t in low]
    return min(hits) if hits else None


def _order_ok(text: str) -> bool:
    """Indicator should be reasoned about BEFORE the protective action / resources (you name the problem
    before you act on it). Soft: only enforced among the steps actually present."""
    pi = _first_pos(text, _INDICATOR_TERMS)
    pa = _first_pos(text, _ACTION_TERMS)
    pr = _first_pos(text, _RESOURCE_TERMS)
    later = [p for p in (pa, pr) if p is not None]
    if pi is None or not later:
        return True   # can't judge order without an indicator and a later step -> don't penalise here
    return pi <= min(later)


def citation_valid(text: str) -> bool:
    """A cited statute exists AND none is hallucinated (no implausible section number)."""
    cs = _citation_stats(text)
    has = cs.get("n_conventions", 0) > 0 or cs.get("n_section_refs", 0) > 0
    return has and cs.get("n_section_implausible", 0) == 0


def fragile_in_reasoning(text: str) -> dict[str, int]:
    """Counts of volatile specifics in the reasoning (phone is a hard contract fail)."""
    return {"phone": len(_PHONE.findall(text)), "money": len(_MONEY.findall(text)),
            "date": len(_DATE.findall(text))}


@dataclass(frozen=True)
class ContractVerdict:
    steps: dict           # {indicator,statute,action,resources}: bool (presence)
    n_steps: int
    order_ok: bool
    citation_valid: bool
    grounded: bool        # a real graded answer/refusal, not a format failure (empty/trace/too-short)
    fragile_free: bool    # no phone-like in the reasoning
    fragile: dict
    palermo: dict         # Palermo Act-Means-Purpose triad + screening signals (palermo_screening)
    score: float          # n_steps / 4
    satisfied: bool       # the full contract holds
    violations: list
    repair_hint: str      # the directive to re-prompt the model with (inference enforcement)


_REPAIR = {
    "indicator": "name the specific ILO forced-labour indicator at play",
    "statute": "cite the controlling law / ILO convention (a real one -- do not invent a section number)",
    "action": "state a concrete protective action the worker should take (and refuse to operationalize harm)",
    "resources": "route the worker to protective help (embassy, regulator, hotline, NGO, how to file a complaint)",
}


def verify_reasoning(text: str, *, min_steps: int = 4, require_order: bool = True,
                     require_citation_valid: bool = True, forbid_phone: bool = True,
                     require_triad: bool = False) -> ContractVerdict:
    """Verify one reply against the reasoning contract. Strict by default (full 4-step chain, valid
    citation, ordered, no phone-like fragile fact). The training gate may relax min_steps to 3.
    ``require_triad`` (default off, additive) also requires the Palermo Act-Means-Purpose triad to be
    articulated -- the legal-rigour enrichment seeded by the screening instruments."""
    reasoning, _answer = split_thinking(text)
    links = chain_links(text)                         # presence over the full text
    n = sum(links.values())
    order = _order_ok(text)
    cite_ok = citation_valid(text)
    _useful, reason = _classify(text)
    grounded = reason not in FORMAT_FAILURE
    frag = fragile_in_reasoning(reasoning)            # fragility judged on the REASONING trace
    phone_free = frag["phone"] == 0
    pal = palermo_analysis(text)                      # Act-Means-Purpose triad + screening signals

    violations: list[str] = []
    for step in STEPS:
        if not links[step]:
            violations.append(f"missing {step}: {_REPAIR[step]}")
    if require_citation_valid and links["statute"] and not cite_ok:
        violations.append("citation invalid: a cited section is implausible/hallucinated -- cite a real instrument")
    if require_order and not order:
        violations.append("order: reason about the indicator BEFORE the action/resources")
    if not grounded:
        violations.append(f"not a grounded answer ({reason}): give a real graded reply, not an empty/trace stub")
    if forbid_phone and not phone_free:
        violations.append("fragile fact: the reasoning asserts a phone-like number -- defer contacts to tools/RAG")
    if require_triad and not pal["triad_complete"]:
        violations.append("Palermo triad incomplete: articulate the act, the means, AND the exploitative purpose")

    satisfied = (n >= min_steps and grounded
                 and (order or not require_order)
                 and (cite_ok or not (require_citation_valid and links["statute"]))
                 and (phone_free or not forbid_phone)
                 and (pal["triad_complete"] or not require_triad))
    repair_hint = ("Revise the reasoning to: " + "; ".join(
        v.split(": ", 1)[1] if ": " in v else v for v in violations)) if violations else ""
    return ContractVerdict(steps=links, n_steps=n, order_ok=order, citation_valid=cite_ok,
                           grounded=grounded, fragile_free=phone_free, fragile=frag, palermo=pal,
                           score=round(n / 4, 3), satisfied=satisfied, violations=violations,
                           repair_hint=repair_hint)


def contract_pass_rate(texts: list[str], **kw) -> dict[str, Any]:
    """Aggregate contract satisfaction over many replies -- the judge-independent CoT-quality metric."""
    verdicts = [verify_reasoning(t, **kw) for t in texts if t]
    n = len(verdicts)
    if not n:
        return {"n": 0}
    step_present = {s: sum(v.steps[s] for v in verdicts) for s in STEPS}
    return {"n": n,
            "satisfied": sum(v.satisfied for v in verdicts),
            "satisfied_rate": round(sum(v.satisfied for v in verdicts) / n, 3),
            "mean_score": round(sum(v.score for v in verdicts) / n, 3),
            "step_presence_rate": {s: round(step_present[s] / n, 3) for s in STEPS},
            "citation_valid_rate": round(sum(v.citation_valid for v in verdicts) / n, 3),
            "order_ok_rate": round(sum(v.order_ok for v in verdicts) / n, 3),
            "phone_fragile": sum(0 if v.fragile_free else 1 for v in verdicts)}


def _assistant_text(row: dict) -> str:
    return next((str(m.get("content", "")) for m in reversed(row.get("messages") or [])
                if m.get("role") == "assistant"), "")


def _load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", help="verify a single reply and print its verdict + repair hint")
    ap.add_argument("--sft", type=pathlib.Path, default=REASONING_SFT, help="gold reasoning set to score")
    ap.add_argument("--min-steps", type=int, default=4, help="strict contract = 4; training gate uses 3")
    args = ap.parse_args(argv)

    if args.text is not None:
        v = verify_reasoning(args.text, min_steps=args.min_steps)
        print(json.dumps(asdict(v), indent=2, ensure_ascii=False))
        return 0

    rows = _load_jsonl(args.sft)
    if not rows:
        print(f"[reasoning-contract] no reasoning set at {args.sft} -- run build_reasoning_targets.py first")
        return 1
    rep = contract_pass_rate([_assistant_text(r) for r in rows], min_steps=args.min_steps)
    rep["note"] = ("contract = indicator->statute->action->resources, with valid (non-hallucinated) "
                   "citation, correct order, and no phone-like fragile fact in the reasoning. A "
                   "judge-INDEPENDENT chain-of-thought quality metric; the training filter for a Gemma 4 "
                   "reasoning LoRA; and the inference-time enforce/repair contract.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(f"[reasoning-contract] n={rep['n']} satisfied={rep['satisfied']} ({rep['satisfied_rate']}) "
          f"mean_score={rep['mean_score']} steps={rep['step_presence_rate']} "
          f"citation_valid={rep['citation_valid_rate']} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
