"""Gated staging step for the legal-corpus enrichment loop: guardrails + multi-prompt convergence vet.

Per the design in docs/research/corpus_enrichment_and_cot_training.md. A candidate EvidenceClaim (drafted
by the agent from WebSearch research) is put through defence-in-depth guardrails AND a multi-prompt
CONVERGENCE vet (several distinct framings via mistral, accepted only on a majority), then STAGED to a
propose-only review queue. It NEVER appends to the vetted corpus (configs/duecare/legal_claims.json) --
promotion is a human, append-only step (supersede, never overwrite). Economical: 3 mistral calls/candidate.

Run:
    python scripts/legal_corpus_stage.py --candidate reports/legal_corpus_candidates/<id>.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

from legal_claims import DEFAULT_PATH as CORPUS_PATH  # noqa: E402
from legal_claims import load_claims, validate_schema  # noqa: E402
import llm_generate as lg  # noqa: E402

STAGING = _ROOT / "reports" / "legal_corpus_staging.json"

# Absolute-claim heuristic, evaluated PER SENTENCE and ORDER-INDEPENDENTLY: a sentence that pairs an
# absolute quantifier (any/all/every/no) with an absolute legal verb (prohibited/banned/illegal/unlawful/
# never / "no exception(s)") is overbroad UNLESS that same sentence carries genuine scoping language. Three
# evasions the old single-regex version missed are now closed: (a) reversed word order ("illegal in all
# cases"), (b) an unrelated hedge word elsewhere in the text ("generally" in a different sentence), and
# (c) the plural "no exceptions". A hedge in a DIFFERENT sentence no longer rescues an absolutist claim.
_ABS_QUANT = re.compile(r"\b(any|all|every|no)\b", re.I)
# verbs that assert an absolute legal bar. Inflections matter: 'ban' must also catch 'bans'/'banned', and
# an adversarial audit showed 'outlaws'/'forbids' slipped an unscoped absolutist claim past the old list.
_ABS_VERB = re.compile(r"\b(prohibit(?:s|ed)?|ban(?:s|ned)?|outlaw(?:s|ed)?|forbid(?:s|den)?|"
                       r"illegal|unlawful|never|no\s+exceptions?)\b", re.I)
_SCOPING = re.compile(r"subject to|depends on|where ratified|unless|only where|not exceeding|"
                      r"authoris\w+ exception|per national law|except (?:where|for|in|as)|"
                      r"in (?:certain|some) (?:cases|jurisdictions)|may (?:be )?permit", re.I)


def _looks_overbroad(text: str) -> bool:
    """True if any single sentence pairs an absolute quantifier with an absolute legal verb and lacks its own
    scoping language. Sentence-scoped so a hedge elsewhere cannot launder an unscoped absolutist clause."""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if _ABS_QUANT.search(sentence) and _ABS_VERB.search(sentence) and not _SCOPING.search(sentence):
            return True
    return False

_FRAMINGS = (
    'Judge ONLY this legal claim for ACCURACY against its cited source. Reply compact JSON {"accurate": true|false, "why": "<short>"}.',
    'What is the STRONGEST objection to this legal claim (missing exception, wrong scope, out of date)? Reply JSON {"fatal": true|false, "objection": "<short>"}.',
    'Does this claim properly SCOPE its applicability and exceptions (i.e. it is NOT overbroad)? Reply JSON {"scoped": true|false, "missing": "<short>"}.',
)


def guardrail_check(candidate: dict, existing: list[dict]) -> tuple[bool, list[str]]:
    """Defence-in-depth structural gate (no model): schema, real source, exceptions present, not a
    duplicate (build-upon: a match must propose a supersede, not overwrite), not obviously overbroad."""
    if not isinstance(candidate, dict):
        return (False, [f"candidate is not a JSON object (got {type(candidate).__name__})"])
    issues = list(validate_schema([candidate]))
    if not str(candidate.get("source_url", "")).startswith("http"):
        issues.append("no real source_url (primary/official required)")
    if not candidate.get("exceptions"):
        issues.append("no exceptions/applicability recorded (bare absolute claims are rejected)")
    existing_ids = {c.get("id") for c in existing if isinstance(c, dict)}   # .get: tolerate a legacy record w/o id
    if candidate.get("id") in existing_ids:
        issues.append(f"duplicate id {candidate.get('id')!r} -- build-upon: propose supersede, do not overwrite")
    if _looks_overbroad(candidate.get("text", "")):
        issues.append("looks OVERBROAD (an absolute claim without scoping/exception in the same sentence)")
    return (not issues, issues)


def _vote(data: dict) -> bool | None:
    if "accurate" in data:
        return bool(data["accurate"])
    if "fatal" in data:
        return data["fatal"] is False
    if "scoped" in data:
        return bool(data["scoped"])
    return None


def convergence_vet(candidate: dict, *, caller=None, model: str = "mistral:mistral-small-latest",
                    framings=_FRAMINGS) -> tuple[bool, list]:
    """Ask several DISTINCT framings and accept only on a majority of the valid votes -- no claim enters on
    one model's single say-so. Returns (accepted, votes)."""
    call = caller or (lambda p, **kw: lg.provider_chat(p, **kw))
    ctx = (f"CLAIM: {candidate.get('text','')}\nJURISDICTION: {candidate.get('jurisdiction')}\n"
           f"SOURCE: {candidate.get('source_url')}\nEXCEPTIONS: {candidate.get('exceptions')}")
    votes = []
    for f in framings:
        try:
            data = lg.extract_json(call(f"{ctx}\n\n{f}", model=model, max_tokens=300, temperature=0.0)) or {}
            votes.append(_vote(data))
        except Exception:  # noqa: BLE001
            votes.append(None)
    valid = [v for v in votes if v is not None]
    accepted = len(valid) >= 2 and sum(1 for v in valid if v) > len(valid) / 2
    return accepted, votes


def stage(candidate: dict, *, guardrails_ok: bool, guardrail_issues: list[str],
          convergence_ok: bool, votes: list, staging_path: Path = STAGING) -> dict:
    """Append a staged record to the propose-only review queue. ready_for_review only if BOTH gates pass;
    it is NEVER auto-promoted -- a human appends it to the corpus."""
    record = {"candidate": candidate, "guardrails_ok": guardrails_ok, "guardrail_issues": guardrail_issues,
              "convergence_ok": convergence_ok, "convergence_votes": votes,
              "ready_for_review": bool(guardrails_ok and convergence_ok), "status": "staged",
              "_propose_only": True, "_not_auto_promoted": True}
    existing = []
    if staging_path.exists():
        try:
            existing = json.loads(staging_path.read_text(encoding="utf-8")).get("staged", [])
        except (json.JSONDecodeError, OSError):
            existing = []
    existing = [r for r in existing if r.get("candidate", {}).get("id") != candidate.get("id")]  # replace same id
    existing.append(record)
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path.write_text(json.dumps({"_propose_only": True, "staged": existing}, indent=2), encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Guardrail + convergence-vet + stage one candidate legal claim.")
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--model", default="mistral:mistral-small-latest")
    args = ap.parse_args(argv)
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    g_ok, g_issues = guardrail_check(candidate, load_claims(CORPUS_PATH))
    print(f"guardrails: {'PASS' if g_ok else 'FAIL'}" + ("" if g_ok else " -- " + "; ".join(g_issues)))
    if not g_ok:
        stage(candidate, guardrails_ok=False, guardrail_issues=g_issues, convergence_ok=False, votes=[])
        print("staged as NOT ready (guardrails failed); fix and re-stage.")
        return 0
    c_ok, votes = convergence_vet(candidate, model=args.model)
    print(f"convergence vet ({args.model}): votes={votes} -> {'ACCEPT' if c_ok else 'HOLD'}")
    rec = stage(candidate, guardrails_ok=True, guardrail_issues=[], convergence_ok=c_ok, votes=votes)
    print(f"staged: ready_for_review={rec['ready_for_review']} -> {STAGING}")
    print("NOT auto-promoted; a human appends it to configs/duecare/legal_claims.json (append-only).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
