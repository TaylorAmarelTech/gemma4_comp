#!/usr/bin/env python3
"""Investigation lens -- the INVESTIGATIVE dimension of trafficking reasoning: actors, connections, and
crime-script stage, the way a trained investigator (not just a screener) thinks.

Per Taylor: real trafficking investigations don't stop at "name an indicator" -- they ask who the actors
are, map the NETWORK and the MONEY (trafficking is a profit crime), and locate the case in the crime
script. This module encodes that lens deterministically, complementing the legal/screening layer
(palermo_screening.py) and the indicator->statute->action->resources chain (build_reasoning_targets.py):

  * ACTORS / ROLES    -- recruiter, employer/principal, broker/agent, transporter, harbourer, financier,
                         facilitator (corrupt official / document forger). Who is involved?
  * CONNECTIONS       -- the organisational + financial structure that separates an isolated incident from
                         a network: multiple victims, shared recruiter/agency, sub-contracting / labour
                         laundering, shell / front companies + beneficial owners, and the MONEY FLOW
                         (fees, remittances, hawala, crypto, who profits). "Follow the money."
  * CRIME-SCRIPT STAGE -- recruitment -> transport/transit -> exploitation -> coercion/control -> exit.
                         Where in the lifecycle is this, which informs the right intervention.

A reasoning trace that considers actors + network + money + stage is reasoning like an investigator, not
just flagging a victim's symptoms. Used as a judge-independent quality dimension (esp. for the NGO /
investigator and platform-triage surfaces) and as a future contract enrichment.

Offline + deterministic (term-based). No model, no network, no credits.

    python scripts/investigation_lens.py                 # actor/connection/stage coverage over the gold set
    python scripts/investigation_lens.py --text "..."    # analyse one reply
Design: docs/research/training_methodology.md (reasoning contract)
"""
from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
REASONING_SFT = _ROOT / "reports" / "training" / "reasoning_sft.jsonl"
OUT = _ROOT / "reports" / "training" / "investigation_lens.json"

# Who is involved -- the roles an investigator maps in a trafficking operation.
ACTOR_ROLES: dict[str, tuple[str, ...]] = {
    "recruiter": ("recruiter", "recruitment agent", "broker", "middleman", "labour agent", "labor agent"),
    "employer": ("employer", "the boss", "factory owner", "principal employer", "sponsor", "the company"),
    "transporter": ("transporter", "the driver", "smuggler", "transport operator"),
    "harbourer": ("landlord", "accommodation provider", "the controller", "the keeper", "housed the"),
    "financier": ("financier", "money lender", "moneylender", "the lender", "the creditor",
                  "beneficial owner", "investor"),
    "facilitator": ("corrupt official", "document forger", "the fixer", "facilitator", "complicit",
                    "bribed official"),
}
# Organisational + financial structure -- isolated incident vs network ("look at connections").
CONNECTION_SIGNALS: dict[str, tuple[str, ...]] = {
    "multiple_victims": ("multiple workers", "other workers", "several victims", "group of workers",
                         "others in the same", "many workers", "dozens of"),
    "shared_recruiter": ("same recruiter", "same agency", "same broker", "the same agent", "same network"),
    "subcontracting": ("subcontract", "sub-contract", "labour laundering", "labor laundering", "outsourced",
                       "third-party labour", "layers of contractors"),
    "corporate_structure": ("shell company", "front company", "beneficial owner", "parent company",
                            "holding company", "registered to", "corporate veil"),
    "financial_flow": ("remittance", "wire transfer", "money transfer", "hawala", "crypto", "paid into",
                       "deductions sent", "kickback", "who profits", "the proceeds", "money trail"),
}
# Crime-script lifecycle stages -- where in the operation, which informs the intervention.
CRIME_STAGES: dict[str, tuple[str, ...]] = {
    "recruitment": ("recruit", "job offer", "was promised", "advertis", "before departure", "in the village",
                    "back home"),
    "transport": ("transport", "in transit", "the border", "the journey", "on arrival", "crossed into"),
    "exploitation": ("forced to work", "exploited", "the working conditions", "at the workplace", "on the job",
                     "made to work"),
    "control": ("passport", "the debt", "threat", "confined", "isolated", "monitored", "cannot leave",
                "withheld wages"),
    "exit": ("escape", "rescued", "fled", "got out", "managed to leave", "reported to the"),
}

_NETWORK_KEYS = ("multiple_victims", "shared_recruiter", "subcontracting", "corporate_structure")


def _present(text: str, groups: dict[str, tuple[str, ...]]) -> list[str]:
    low = text.lower()
    return [name for name, terms in groups.items() if any(t in low for t in terms)]


def investigation_analysis(text: str) -> dict[str, Any]:
    """Identify the investigative elements a reply surfaces: actors, connections (network + money), and
    crime-script stage(s)."""
    actors = _present(text, ACTOR_ROLES)
    connections = _present(text, CONNECTION_SIGNALS)
    stages = _present(text, CRIME_STAGES)
    return {"actors": actors, "connections": connections, "stages": stages,
            "considers_actors": bool(actors),
            "considers_network": any(c in connections for c in _NETWORK_KEYS),
            "considers_financial": "financial_flow" in connections,
            "n_actors": len(actors), "n_connections": len(connections), "n_stages": len(stages)}


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
    """Aggregate: how often the reasoning reasons like an investigator (actors / network / money / stage)."""
    n = len([t for t in texts if t])
    if not n:
        return {"n": 0}
    rows = [investigation_analysis(t) for t in texts if t]
    actor_c: Counter = Counter()
    conn_c: Counter = Counter()
    stage_c: Counter = Counter()
    for r in rows:
        actor_c.update(r["actors"])
        conn_c.update(r["connections"])
        stage_c.update(r["stages"])
    return {"n": n,
            "considers_actors_rate": round(sum(r["considers_actors"] for r in rows) / n, 3),
            "considers_network_rate": round(sum(r["considers_network"] for r in rows) / n, 3),
            "considers_financial_rate": round(sum(r["considers_financial"] for r in rows) / n, 3),
            "actor_rate": {k: round(v / n, 3) for k, v in actor_c.most_common()},
            "connection_rate": {k: round(v / n, 3) for k, v in conn_c.most_common()},
            "stage_rate": {k: round(v / n, 3) for k, v in stage_c.most_common()}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", help="analyse a single reply and print its investigation verdict")
    ap.add_argument("--sft", type=pathlib.Path, default=REASONING_SFT, help="gold reasoning set to score")
    args = ap.parse_args(argv)

    if args.text is not None:
        print(json.dumps(investigation_analysis(args.text), indent=2, ensure_ascii=False))
        return 0
    rows = _load_jsonl(args.sft)
    if not rows:
        print(f"[investigation] no reasoning set at {args.sft} -- run build_reasoning_targets.py first")
        return 1
    rep = coverage([_assistant_text(r) for r in rows])
    rep["note"] = ("Investigative-lens coverage over the gold reasoning traces: how often the reasoning maps "
                   "actors, the network, the money, and the crime-script stage -- reasoning like an "
                   "investigator, not just flagging a victim's symptoms. Low network/financial rates show "
                   "where investigator-grade reasoning is thin (a target for the NGO/triage surfaces).")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(f"[investigation] n={rep['n']} actors={rep['considers_actors_rate']} "
          f"network={rep['considers_network_rate']} financial={rep['considers_financial_rate']} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
