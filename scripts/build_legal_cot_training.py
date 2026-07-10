"""Chain-of-thought training pairs that teach the model to PREFER the reasoning procedure over each way
simple fine-tuning makes it think wrong.

Taylor: "simple fine-tuning may cause the model to think wrong; we need significant chain-of-thought
improvements." This is the concrete, ADDITIVE implementation of the failure-mode taxonomy in
docs/research/corpus_enrichment_and_cot_training.md. For each legal_reasoning.py walkthrough it builds:
  * CHOSEN  -- a full-chain worker-facing answer (indicator -> statute-with-exception -> protective action
    -> resources -> Palermo reading -> uncertainty + "risk pattern, not a finding"; volatile facts left as
    VERIFY slots, never memorised). It is GATED: it must PASS reasoning_contract.verify_reasoning.
  * REJECTED[mode] -- one response per failure mode, each encoding exactly ONE wrong-thinking pattern.

It emits DPO pairs (chosen > rejected) + SFT rows (chosen only), and a GATE REPORT showing which failure
modes the STRUCTURAL reasoning contract catches (conclusion-only, refusal-collapse, fabricated citation,
stale memorised fact, missing resources) vs which need the SEMANTIC faithfulness/exception layer
(overbroad-no-exception, jurisdiction-blind, overconfident) -- which is exactly why both layers exist.
Reuses reasoning_contract.py (the gate) + legal_reasoning.py (the scaffold) + legal_claims.json (freshness).
Propose-only, staged to reports/training/; NOT fine-tuned (gated: needs hidden lineage splits first).

Run:
    python scripts/build_legal_cot_training.py --today 2026-07-10
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

import legal_reasoning as lr  # noqa: E402
from reasoning_contract import verify_reasoning  # noqa: E402

SFT_OUT = _ROOT / "reports" / "training" / "legal_cot_sft.jsonl"
DPO_OUT = _ROOT / "reports" / "training" / "legal_cot_dpo.jsonl"


def worker_prompt(scenario: dict) -> str:
    return " ".join(scenario.get("facts", []))


def build_chosen(analysis: dict) -> str:
    """A full-chain worker-facing answer built deterministically from the reasoning walkthrough. Structured
    indicator -> statute(with exception) -> action -> resources -> Palermo -> uncertainty, so it satisfies
    the reasoning contract; volatile specifics are deferred to VERIFY, never asserted as fixed facts."""
    inds = ", ".join(analysis["indicators_matched"].keys()) or "possible exploitation indicators"
    statutes = []
    # applicable_claims is already ranked current+binding+jurisdiction-specific first; skip any claim marked
    # historical/superseded so the gold answer never trains the model to cite a superseded statute as current.
    for c in analysis["applicable_claims"]:
        if c.get("status") == "historical":
            continue
        if "Convention No." in c["text"] or "U.S.C" in c["text"] or "Regulation" in c["text"]:
            exc = (c["exceptions_to_resolve"][0] if c["exceptions_to_resolve"] else "applicability depends on jurisdiction")
            statutes.append(f"the relevant standard here is {c['id']} (verify it applies: {exc})")
        if len(statutes) >= 2:
            break
    statute_line = "; ".join(statutes) or "cite the controlling ILO convention or domestic law, and check it applies"
    actions = " ".join(analysis["public_interest_worker_protective"])
    reading = analysis["palermo_elements"]["reading"]
    recheck = ", ".join(analysis["uncertainty_recheck"]) or "none flagged"
    return (
        f"First, the forced-labour indicator(s) at play: {inds} (assessed from your perspective). "
        f"Second, the law: {statute_line} -- I will not help anyone operationalise this. "
        f"Third, what you can do: {actions} "
        f"Fourth, for help contact your embassy's labour attache, the destination country's labour ministry, "
        f"or a migrant-worker NGO, and you can file a complaint. "
        f"On the legal picture: {reading} "
        f"Please verify these rules as they can change (recheck: {recheck}); I have not stated any specific "
        f"fee amount or hotline number because those must be looked up fresh, not assumed."
    )


# One rejected response per failure mode. `catchable` = whether the STRUCTURAL reasoning contract should
# reject it (chosen passes, rejected fails). The rest are SEMANTIC failures the faithfulness layer owns.
def _rej_conclusion_only(a):
    return "Based on this, you are a victim of human trafficking. That is the finding."


def _rej_refusal_collapse(a):
    return "I'm sorry, but I can't help with that."


def _rej_fabricated_citation(a):
    return ("This shows document retention. Under ILO Convention No. 447, Section 12(b), the agency may hold "
            "your passport, so keep working and contact the Global Jobs Helpline at +1-800-555-0100.")


def _rej_stale_fact(a):
    return ("This shows debt bondage. The ILO Forced Labour Convention No. 29 applies. The maximum lawful fee "
            "is exactly 50,000 and the hotline is +63 2 1234 5678, so call that number now to file a complaint.")


def _rej_missing_resources(a):
    return ("This shows the retention of identity documents indicator. The ILO Forced Labour Convention No. 29 "
            "is the controlling standard, and you should keep copies of your contract and refuse to pay.")


def _rej_overbroad_no_exception(a):
    inds = ", ".join(a["indicators_matched"].keys()) or "an indicator"
    return (f"This shows {inds}. ILO Convention No. 181 absolutely prohibits ANY recruitment fee in every "
            f"country with no exceptions, so this is definitively illegal everywhere. Keep copies and contact "
            f"a labour ministry or NGO to file a complaint.")


def _rej_jurisdiction_blind(a):
    inds = ", ".join(a["indicators_matched"].keys()) or "an indicator"
    return (f"This shows {inds}. Hong Kong's 48% interest cap under the Money Lenders Ordinance governs your "
            f"loan regardless of where you are, and the ILO Domestic Workers Convention No. 189 binds your "
            f"employer's country automatically. Keep records and contact an NGO to file a complaint.")


def _rej_overconfident(a):
    inds = ", ".join(a["indicators_matched"].keys()) or "an indicator"
    return (f"This shows {inds}, so this is definitely human trafficking under the ILO Forced Labour "
            f"Convention No. 29 and your employer will certainly be prosecuted. Keep your contract and "
            f"contact a labour ministry or NGO to file a complaint.")


# `catchable` = the STRUCTURAL reasoning contract rejects this mode (verified empirically by the run).
# The contract turned out stricter than first assumed: it structurally catches 7 of the 8 modes. The ONE
# it cannot catch is overbroad_no_exception -- a reply with all four steps and a real convention that is
# merely OVERBROAD ("prohibits ANY fee, no exceptions"). That is precisely the specificity-overfit failure
# and precisely what the legal-claims faithfulness + exception layer catches: the two layers are
# complementary and both necessary. (test_build_legal_cot_training pins this empirical split.)
FAILURE_MODES = {
    "conclusion_only": (_rej_conclusion_only, True),
    "refusal_collapse": (_rej_refusal_collapse, True),
    "fabricated_citation": (_rej_fabricated_citation, True),
    "stale_fact_memorized": (_rej_stale_fact, True),
    "missing_resources": (_rej_missing_resources, True),
    "jurisdiction_blind": (_rej_jurisdiction_blind, True),
    "overconfident_no_uncertainty": (_rej_overconfident, True),
    "overbroad_no_exception": (_rej_overbroad_no_exception, False),   # the sole SEMANTIC-only gap
}


def generate(scenarios: list[dict], claims: list[dict], today: date) -> dict:
    sft, dpo = [], []
    gate = {"chosen_pass": 0, "chosen_fail": 0, "catchable_ok": 0, "catchable_missed": 0,
            "semantic_only": 0, "by_mode": {}}
    for sc in scenarios:
        analysis = lr.analyze(sc, claims, today)
        prompt = worker_prompt(sc)
        chosen = build_chosen(analysis)
        chosen_ok = verify_reasoning(chosen).satisfied
        gate["chosen_pass" if chosen_ok else "chosen_fail"] += 1
        if not chosen_ok:
            continue                                  # never emit an SFT target that fails the contract
        sft.append({"messages": [{"role": "user", "content": prompt},
                                 {"role": "assistant", "content": chosen}],
                    "_scenario": sc["id"], "_contract_ok": True})
        for mode, (builder, catchable) in FAILURE_MODES.items():
            rejected = builder(analysis)
            rej_ok = verify_reasoning(rejected).satisfied
            gate["by_mode"].setdefault(mode, {"catchable": catchable, "rejected_failed_contract": 0, "n": 0})
            gate["by_mode"][mode]["n"] += 1
            if not rej_ok:
                gate["by_mode"][mode]["rejected_failed_contract"] += 1
            if catchable:
                gate["catchable_ok" if not rej_ok else "catchable_missed"] += 1
            else:
                gate["semantic_only"] += 1
            dpo.append({"prompt": prompt, "chosen": chosen, "rejected": rejected,
                        "failure_mode": mode, "contract_catchable": catchable,
                        "chosen_contract_ok": True, "rejected_contract_ok": rej_ok,
                        "_scenario": sc["id"]})
    return {"sft": sft, "dpo": dpo, "gate": gate}


def format_gate(gate: dict) -> str:
    lines = [f"CoT training gate: chosen passed contract {gate['chosen_pass']}, failed {gate['chosen_fail']}",
             f"catchable failure modes rejected by the STRUCTURAL contract: {gate['catchable_ok']} ok, "
             f"{gate['catchable_missed']} missed", "", "per failure mode (rejected should FAIL the contract if catchable):"]
    for mode, m in gate["by_mode"].items():
        tag = "structural" if m["catchable"] else "SEMANTIC (needs faithfulness/exception layer)"
        lines.append(f"  {mode:26s} [{tag}] rejected_failed_contract={m['rejected_failed_contract']}/{m['n']}")
    lines += ["", "the STRUCTURAL reasoning contract catches 7/8 wrong-thinking modes; the sole gap is",
              "overbroad_no_exception (a real convention cited WITHOUT its exception) -- caught instead by the",
              "legal-claims faithfulness + exception layer. Two complementary layers, both necessary."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build gated legal chain-of-thought SFT/DPO training pairs.")
    ap.add_argument("--today", default=None)
    args = ap.parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else date.today()
    out = generate(lr.SCENARIOS, lr.load_claims(), today)
    SFT_OUT.parent.mkdir(parents=True, exist_ok=True)
    SFT_OUT.write_text("\n".join(json.dumps(r) for r in out["sft"]) + ("\n" if out["sft"] else ""), encoding="utf-8")
    DPO_OUT.write_text("\n".join(json.dumps(r) for r in out["dpo"]) + ("\n" if out["dpo"] else ""), encoding="utf-8")
    print(format_gate(out["gate"]))
    print(f"\n-> {SFT_OUT} ({len(out['sft'])} SFT rows)\n-> {DPO_OUT} ({len(out['dpo'])} DPO pairs)")
    print("propose-only; gated: do NOT fine-tune before hidden lineage splits + direct factual grading.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
