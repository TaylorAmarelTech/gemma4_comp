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
import re
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
REASONING_SFT = _ROOT / "reports" / "training" / "reasoning_sft.jsonl"
OUT = _ROOT / "reports" / "training" / "remedy_coverage.json"
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

REMEDIES: dict[str, tuple[str, ...]] = {
    "unpaid_wage_recovery": ("back pay", "recover your wages", "recover your unpaid wage",
                             "recover unpaid wage", "claim your wages", "claim unpaid wage",
                             "file a wage claim", "wage claim", "pay claim", "wages you are owed",
                             "wages owed to you", "wage arrears", "recover wage arrears"),
    "fee_refund": ("recover the fee", "recover the recruitment fee", "recover recruitment fee",
                   "refund the recruitment fee", "refund of recruitment fee", "fee reimbursement",
                   "reimbursement of recruitment fee", "return the fee", "get the fee back",
                   "recover fees paid", "illegal fee recover"),
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

CORE_REMEDY_TRIGGERS: dict[str, tuple[str, ...]] = {
    "exploitation_or_forced_labour": ("exploitation", "exploited", "forced labour", "forced labor",
                                      "trafficking", "trafficked", "domestic servitude", "debt bondage",
                                      "forced to work"),
    "wage_harm": ("unpaid wages", "unpaid salary", "salary unpaid", "withheld wages", "wages withheld",
                  "withholding of wages", "wage theft", "not paid", "worked and wasn't paid",
                  "worked and was not paid", "wage arrears", "unlawful deductions", "illegal deductions"),
    "recruitment_fee_debt": ("recruitment fee", "placement fee", "agency fee", "training fee",
                             "worker-paid fee", "recruitment debt", "recruitment-fee debt",
                             "salary deduction", "payroll deduction", "loan repayment", "migration loan"),
    "document_control": ("passport confiscated", "confiscated passport", "held passport", "passport held",
                         "withheld passport", "took her passport", "took his passport",
                         "identity document confiscated", "document retention"),
}
CORE_BASE_REMEDIES = ("compensation_damages", "non_punishment")
CORE_TRIGGER_REMEDIES: dict[str, tuple[str, ...]] = {
    "wage_harm": ("unpaid_wage_recovery",),
    "recruitment_fee_debt": ("fee_refund",),
}


def remedies_present(text: str) -> list[str]:
    if not isinstance(text, str):
        return []
    low = text.lower()
    return [name for name, terms in REMEDIES.items() if any(t in low for t in terms)]


def core_remedy_triggers(text: str) -> list[str]:
    """Harms that make money remedies and non-punishment mandatory in first-contact advice."""
    if not isinstance(text, str):
        return []
    low = text.lower()
    return [name for name, terms in CORE_REMEDY_TRIGGERS.items() if any(t in low for t in terms)]


def core_remedy_gap(text: str) -> dict[str, Any]:
    """Mandatory remedies from the advice-completeness playbook, keyed to harms in the reply/scenario."""
    triggers = core_remedy_triggers(text)
    required: list[str] = []
    if triggers:
        required.extend(CORE_BASE_REMEDIES)
        for trigger in triggers:
            required.extend(CORE_TRIGGER_REMEDIES.get(trigger, ()))
    required = list(dict.fromkeys(required))
    present = remedies_present(text)
    missing = [name for name in required if name not in present]
    return {"triggers": triggers, "required": required, "present": present, "missing": missing,
            "complete": not missing}


def remedy_gap(text: str) -> dict[str, Any]:
    """Which remedies the advice offers vs the full space -- the candidate 'missed remedies'."""
    present = remedies_present(text)
    missing = [r for r in REMEDIES if r not in present]
    core = core_remedy_gap(text)
    return {"present": present, "missing": missing, "n_present": len(present),
            "coverage": round(len(present) / len(REMEDIES), 3),
            "core_triggers": core["triggers"], "core_required": core["required"],
            "core_missing": core["missing"], "core_complete": core["complete"]}


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
    """How often each remedy is offered across the advice set -- low rates = systematically missed remedies."""
    valid_texts = [t for t in texts if isinstance(t, str) and t]
    n = len(valid_texts)
    if not n:
        return {"n": 0}
    c: Counter = Counter()
    core_missing: Counter = Counter()
    triggered = 0
    complete = 0
    totals = []
    for t in valid_texts:
        present = remedies_present(t)
        c.update(present)
        totals.append(len(present))
        core = core_remedy_gap(t)
        if core["required"]:
            triggered += 1
            complete += int(core["complete"])
            core_missing.update(core["missing"])
    core_complete_rate = round(complete / triggered, 3) if triggered else None
    return {"n": n, "mean_remedies_per_reply": round(sum(totals) / n, 2),
            "remedy_rate": {k: round(c.get(k, 0) / n, 3) for k in REMEDIES},
            "core_triggered_n": triggered,
            "core_complete_rate": core_complete_rate,
            "core_missing_rate": {k: round(core_missing.get(k, 0) / triggered, 3)
                                  for k in REMEDIES if k in core_missing} if triggered else {}}


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
        print(f"[remedy] no reasoning set at {_display_report_path(args.sft)} "
              "-- run build_reasoning_targets.py first")
        return 1
    rep = coverage([_assistant_text(r) for r in rows])
    rep["note"] = ("Remedy coverage over the gold reasoning traces. Low per-remedy rates are remedies the "
                   "advice systematically MISSES -- the 'an NGO misses a remedy' gap. Pairs with the advice "
                   "critique workflow (which finds + verifies missed remedies/statutes and improves the advice).")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    least = sorted(rep["remedy_rate"].items(), key=lambda kv: kv[1])[:5]
    print(f"[remedy] n={rep['n']} mean_remedies/reply={rep['mean_remedies_per_reply']} "
          f"core_complete={rep['core_complete_rate']} | least-offered: {dict(least)} "
          f"-> {_display_report_path(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
