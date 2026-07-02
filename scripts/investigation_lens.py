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
import re
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
REASONING_SFT = _ROOT / "reports" / "training" / "reasoning_sft.jsonl"
OUT = _ROOT / "reports" / "training" / "investigation_lens.json"
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")


def _has_sensitive_display_text(text: str) -> bool:
    return bool(
        _EMAIL.search(text)
        or _PHONE.search(text)
        or _LOCAL_PATH_HINT.search(text)
        or re.search(r"\b\d{9,}\b", text)
    )


def _safe_relative_report_path(path: pathlib.PurePath) -> str:
    display = path.as_posix()
    if not display or display.startswith("../") or "/../" in display:
        return "redacted"
    if _has_sensitive_display_text(display):
        return "redacted"
    if not _SAFE_RELATIVE_PATH.fullmatch(display):
        return "redacted"
    return display


def _display_report_path(raw_path: Any) -> str:
    if not raw_path:
        return "n/a"
    raw = str(raw_path)
    try:
        path = pathlib.Path(raw)
        if path.is_absolute():
            try:
                return _safe_relative_report_path(path.relative_to(_ROOT))
            except ValueError:
                return "external"
        return _safe_relative_report_path(pathlib.PurePosixPath(pathlib.PureWindowsPath(raw).as_posix()))
    except (OSError, RuntimeError, ValueError):
        return "redacted"

# PERPETRATOR-side roles -- the operation's actors an investigator maps (with variations).
ACTOR_ROLES: dict[str, tuple[str, ...]] = {
    "recruiter": ("recruiter", "recruitment agent", "broker", "middleman", "labour agent", "labor agent"),
    "sub_agent": ("sub-agent", "subagent", "sub-broker", "local agent", "village broker", "intermediary"),
    "employer": ("employer", "the boss", "factory owner", "principal employer", "sponsor", "the company"),
    "transporter": ("transporter", "the driver", "smuggler", "transport operator"),
    "harbourer": ("landlord", "accommodation provider", "the controller", "the keeper", "housed the"),
    "enforcer": ("enforcer", "the guard", "the minder", "the muscle", "gang member"),
    "buyer_client": ("the buyer", "the client", "the customer", "purchaser", "the john"),
    "financier": ("financier", "money lender", "moneylender", "the lender", "the creditor",
                  "beneficial owner", "investor"),
    "facilitator": ("document forger", "forged documents", "fake passport", "the fixer", "facilitator",
                    "enabler"),
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

# RESPONSE-side actors -- the institutions that are SUPPOSED to protect. Do NOT presume they are benign:
# the analysis must not assume the employer/agency is the only source of harm (Taylor) -- regulators,
# police, and even NGOs can contribute to harm, knowingly or unknowingly.
RESPONSE_ACTORS: dict[str, tuple[str, ...]] = {
    "police": ("police", "law enforcement", "the officers", "constable", "the authorities"),
    "labour_inspector": ("labour inspector", "labor inspector", "labour inspectorate", "workplace inspection"),
    "immigration": ("immigration authorities", "immigration officer", "border force", "border agency"),
    "prosecutor": ("prosecutor", "public prosecutor", "district attorney"),
    "judiciary": ("the court", "tribunal", "the judge", "magistrate"),
    "regulator": ("regulator", "licensing authority", "recruitment regulator", "poea", "bp2mi",
                  "gangmasters", "glaa", "oversight body"),
    "embassy": ("embassy", "consulate", "consular"),
    "ngo": ("ngo", "civil society", "support organisation", "support organization", "charity",
            "the helpline", "the hotline"),
    "financial_intelligence": ("financial intelligence", "the fiu", "aml unit", "suspicious transaction"),
    "union": ("trade union", "labour union", "labor union", "workers union", "workers' union"),
    "social_services": ("social services", "social worker", "victim support", "the shelter"),
}
# GOOD responder behaviour -- the protective stance we want.
RESPONDER_GOOD: dict[str, tuple[str, ...]] = {
    "victim_centered": ("victim-centered", "victim-centred", "trauma-informed", "non-punishment",
                        "not prosecuted", "protect the victim", "safety of the victim"),
    "proactive": ("proactive", "intelligence-led", "opened an investigation", "financial investigation",
                  "follow the money", "parallel investigation"),
    "multi_agency": ("multi-agency", "referral mechanism", "national referral", "task force", "inter-agency"),
    "screening": ("screening", "formally identified", "victim identification", "identified as a victim"),
}
# FAILURE / harm from the response side -- knowing OR unknowing. The exploiter is NOT only the employer.
RESPONDER_FAILURE: dict[str, tuple[str, ...]] = {
    "corruption_complicity": ("corrupt", "bribed", "complicit", "colluding", "turned a blind eye",
                              "paid off", "kickback to", "in the pocket of"),
    "victim_criminalization": ("arrested the victim", "prosecuted the victim", "detained the worker",
                               "charged the victim", "treated as a criminal", "deported the victim",
                               "deportation", "punished the victim"),
    "negligence": ("ignored the", "failed to act", "no investigation", "did not investigate",
                   "dismissed the complaint", "no action was taken", "inadequate response"),
    "non_enforcement": ("not enforced", "unlicensed", "regulatory gap", "no oversight", "unregulated",
                        "regulatory capture", "licence was not checked", "license was not checked"),
    # The user's key point: NGOs/advisors can give bad advice / take the wrong stance, often UNKNOWINGLY.
    "bad_advice_wrong_stance": ("bad advice", "wrong stance", "misadvised", "misguided advice",
                                "inappropriate referral", "well-intentioned but", "unknowingly",
                                "made it worse", "re-traumatiz", "retraumatiz", "paternalistic",
                                "dismissed her concerns", "dismissed his concerns", "wrong advice"),
}


def _present(text: str, groups: dict[str, tuple[str, ...]]) -> list[str]:
    if not isinstance(text, str):
        return []
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


def institutional_review(text: str) -> dict[str, Any]:
    """Review the RESPONSE side: which protective institutions appear, and are they behaving well or
    contributing to harm? The exploiter is not presumed to be the employer -- regulators, police, and even
    NGOs can give bad advice / take the wrong stance / be complicit, knowingly or unknowingly. Surfacing
    a failure means the reasoning must NOT blindly route the worker there (referral safety)."""
    actors = _present(text, RESPONSE_ACTORS)
    good = _present(text, RESPONDER_GOOD)
    failures = _present(text, RESPONDER_FAILURE)
    return {"response_actors": actors, "good_behaviors": good, "failure_behaviors": failures,
            "reviews_institutions": bool(actors or good or failures),
            "flags_institutional_failure": bool(failures),
            "n_response_actors": len(actors)}


def _assistant_text(row: Any) -> str:
    if not isinstance(row, dict):
        return ""
    messages = row.get("messages")
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
    return ""


def _load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
    return out


def coverage(texts: list[str]) -> dict[str, Any]:
    """Aggregate: how often the reasoning reasons like an investigator (actors / network / money / stage)."""
    valid_texts = [t for t in texts if isinstance(t, str) and t]
    n = len(valid_texts)
    if not n:
        return {"n": 0}
    rows = [investigation_analysis(t) for t in valid_texts]
    inst = [institutional_review(t) for t in valid_texts]
    actor_c: Counter = Counter()
    conn_c: Counter = Counter()
    stage_c: Counter = Counter()
    resp_c: Counter = Counter()
    fail_c: Counter = Counter()
    for r in rows:
        actor_c.update(r["actors"])
        conn_c.update(r["connections"])
        stage_c.update(r["stages"])
    for r in inst:
        resp_c.update(r["response_actors"])
        fail_c.update(r["failure_behaviors"])
    return {"n": n,
            "considers_actors_rate": round(sum(r["considers_actors"] for r in rows) / n, 3),
            "considers_network_rate": round(sum(r["considers_network"] for r in rows) / n, 3),
            "considers_financial_rate": round(sum(r["considers_financial"] for r in rows) / n, 3),
            "reviews_institutions_rate": round(sum(r["reviews_institutions"] for r in inst) / n, 3),
            "flags_institutional_failure_rate": round(sum(r["flags_institutional_failure"] for r in inst) / n, 3),
            "actor_rate": {k: round(v / n, 3) for k, v in actor_c.most_common()},
            "connection_rate": {k: round(v / n, 3) for k, v in conn_c.most_common()},
            "stage_rate": {k: round(v / n, 3) for k, v in stage_c.most_common()},
            "response_actor_rate": {k: round(v / n, 3) for k, v in resp_c.most_common()},
            "institutional_failure_rate": {k: round(v / n, 3) for k, v in fail_c.most_common()}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", help="analyse a single reply and print its investigation verdict")
    ap.add_argument("--sft", type=pathlib.Path, default=REASONING_SFT, help="gold reasoning set to score")
    args = ap.parse_args(argv)

    if args.text is not None:
        rep = investigation_analysis(args.text)
        rep["institutional_review"] = institutional_review(args.text)
        print(json.dumps(rep, indent=2, ensure_ascii=False))
        return 0
    rows = _load_jsonl(args.sft)
    if not rows:
        print(f"[investigation] no reasoning set at {_display_report_path(args.sft)} "
              "-- run build_reasoning_targets.py first")
        return 1
    rep = coverage([_assistant_text(r) for r in rows])
    rep["note"] = ("Investigative-lens coverage over the gold reasoning traces: how often the reasoning maps "
                   "actors, the network, the money, and the crime-script stage -- reasoning like an "
                   "investigator, not just flagging a victim's symptoms. Low network/financial rates show "
                   "where investigator-grade reasoning is thin (a target for the NGO/triage surfaces).")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(f"[investigation] n={rep['n']} actors={rep['considers_actors_rate']} "
          f"network={rep['considers_network_rate']} financial={rep['considers_financial_rate']} "
          f"reviews_institutions={rep['reviews_institutions_rate']} "
          f"flags_failure={rep['flags_institutional_failure_rate']} -> {_display_report_path(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
