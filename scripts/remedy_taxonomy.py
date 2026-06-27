#!/usr/bin/env python3
"""Remedy taxonomy -- the space of remedies available to an exploited / trafficked migrant worker, so we
can detect when advice MISSES a remedy (Taylor: "an NGO doesn't know the right statute or misses a remedy
available to a worker").

A good advisor doesn't just name the violation -- it surfaces every avenue of redress the worker can
actually pursue. This enumerates that space deterministically (term-based) so we can measure remedy
COVERAGE in any advice text and flag gaps. It complements the generic "resources" link in
build_reasoning_targets (which only checks that *some* help was named) by asking *which specific remedies*
were offered vs available.

Remedy families:
  * financial      -- unpaid-wage recovery, recruitment-fee refund, compensation / damages / victim funds
  * criminal/civil -- criminal complaint, civil claim for damages
  * labour         -- labour tribunal / employment claim, labour inspectorate action
  * immigration    -- visa remedies (T-visa, reflection period, residence permit), protection from removal
  * protection     -- non-punishment, legal aid, shelter / medical / psychosocial support
  * return         -- safe repatriation + reintegration assistance
  * administrative -- recruitment-regulator complaint (POEA/BP2MI), licence revocation / blacklisting
  * external       -- embassy / consular assistance, ILO mechanisms / national human-rights institution

Offline + deterministic. No model, no network, no credits.

    python scripts/remedy_taxonomy.py                 # remedy coverage over the gold reasoning set
    python scripts/remedy_taxonomy.py --text "..."    # remedies mentioned in one reply
Design: docs/research/training_methodology.md (advice critique)
"""
from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
REASONING_SFT = _ROOT / "reports" / "training" / "reasoning_sft.jsonl"
OUT = _ROOT / "reports" / "training" / "remedy_coverage.json"

REMEDIES: dict[str, tuple[str, ...]] = {
    "unpaid_wage_recovery": ("unpaid wage", "back pay", "recover your wages", "wage claim", "wages owed",
                             "owed wages", "claim your wages", "recover unpaid"),
    "fee_refund": ("refund", "reimburse", "recover the fee", "fee reimbursement", "return the fee",
                   "recover the recruitment fee", "illegal fee recover"),
    "compensation_damages": ("compensation", "damages", "restitution", "victim compensation",
                             "compensation fund", "compensation scheme"),
    "criminal_complaint": ("criminal complaint", "file a police report", "report the crime", "press charges",
                           "criminal case", "report to the police"),
    "civil_claim": ("civil suit", "civil claim", "sue ", "lawsuit", "civil action", "tort claim",
                    "claim for damages"),
    "labour_tribunal": ("labour tribunal", "labor tribunal", "labour court", "employment tribunal",
                        "labour complaint", "industrial tribunal", "employment claim"),
    "labour_inspection": ("labour inspector", "labor inspector", "labour inspectorate", "workplace inspection",
                          "report to the labour office", "labour office"),
    "visa_immigration_remedy": ("t-visa", "t visa", "reflection period", "residence permit", "regulariz",
                                "visa remedy", "protection from deportation", "stay of removal", "u-visa"),
    "non_punishment": ("non-punishment", "not be prosecuted", "not a criminal", "should not be punished",
                       "victim not offender", "immunity from prosecution"),
    "legal_aid": ("legal aid", "free legal", "pro bono", "legal assistance", "legal representation",
                  "see a lawyer", "consult a lawyer", "consult an attorney"),
    "support_services": ("shelter", "safe house", "medical support", "psychological", "counselling",
                         "counseling", "trauma support", "psychosocial", "interpreter"),
    "repatriation": ("repatriation", "safe return", "return-home assistance", "reintegration",
                     "voluntary return"),
    "regulator_complaint": ("recruitment regulator", "poea", "bp2mi", "license revocation",
                            "licence revocation", "blacklist", "deregister the agency", "report the agency"),
    "embassy_assistance": ("embassy", "consulate", "consular assistance"),
    "ilo_nhri": ("ilo complaint", "national human rights", "nhri", "human rights commission", "ombudsman",
                 "ilo supervisory"),
}


def remedies_present(text: str) -> list[str]:
    low = text.lower()
    return [name for name, terms in REMEDIES.items() if any(t in low for t in terms)]


def remedy_gap(text: str) -> dict[str, Any]:
    """Which remedies the advice offers vs the full space -- the candidate 'missed remedies'."""
    present = remedies_present(text)
    missing = [r for r in REMEDIES if r not in present]
    return {"present": present, "missing": missing, "n_present": len(present),
            "coverage": round(len(present) / len(REMEDIES), 3)}


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


def coverage(texts: list[str]) -> dict[str, Any]:
    """How often each remedy is offered across the advice set -- low rates = systematically missed remedies."""
    n = len([t for t in texts if t])
    if not n:
        return {"n": 0}
    c: Counter = Counter()
    totals = []
    for t in texts:
        if t:
            present = remedies_present(t)
            c.update(present)
            totals.append(len(present))
    return {"n": n, "mean_remedies_per_reply": round(sum(totals) / n, 2),
            "remedy_rate": {k: round(c.get(k, 0) / n, 3) for k in REMEDIES}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", help="list the remedies mentioned in a single reply")
    ap.add_argument("--sft", type=pathlib.Path, default=REASONING_SFT, help="gold reasoning set to score")
    args = ap.parse_args(argv)

    if args.text is not None:
        print(json.dumps(remedy_gap(args.text), indent=2, ensure_ascii=False))
        return 0
    rows = _load_jsonl(args.sft)
    if not rows:
        print(f"[remedy] no reasoning set at {args.sft} -- run build_reasoning_targets.py first")
        return 1
    rep = coverage([_assistant_text(r) for r in rows])
    rep["note"] = ("Remedy coverage over the gold reasoning traces. Low per-remedy rates are remedies the "
                   "advice systematically MISSES -- the 'an NGO misses a remedy' gap. Pairs with the advice "
                   "critique workflow (which finds + verifies missed remedies/statutes and improves the advice).")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    least = sorted(rep["remedy_rate"].items(), key=lambda kv: kv[1])[:5]
    print(f"[remedy] n={rep['n']} mean_remedies/reply={rep['mean_remedies_per_reply']} "
          f"| least-offered: {dict(least)} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
