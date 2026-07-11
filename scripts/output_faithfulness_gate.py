"""Output-faithfulness gate: flag a generated ANSWER that states an absolute legal rule WITHOUT its exception.

This is the output-side analog of legal_corpus_stage._looks_overbroad (which screens candidate CLAIMS being
appended to the corpus). The adversarial audit (docs/research/adversarial_findings_2026_07_10.md, items A2 /
B5 / owed #3) flagged that the overbroad-no-exception failure mode -- a real convention cited as if it
admitted no exception ("ILO C181 prohibits ANY recruitment fee everywhere, no exceptions") -- is UNGUARDED at
inference: the reasoning contract passes it and nothing downstream catches it. This module is that missing
check, meant to run on actual harness/model OUTPUTS, blinded to arm. Deterministic, offline, propose-only.

check(answer, claims=None) returns:
  * overbroad_sentences         -- sentences pairing an absolute quantifier with an absolute legal verb and
                                   carrying no scoping in that sentence (reuses the hardened corpus detector).
  * mentions_exception          -- whether the answer surfaces ANY exception/qualifier anywhere.
  * cited_claims_with_exceptions-- corpus claims the answer names (by a law signature, e.g. 'No. 181', '1591',
                                   'Palermo') that DO carry recorded exceptions -- so an absolute statement
                                   about them is a faithfulness failure the corpus can prove.
  * verdict                     -- "fail" if overbroad and no exception is surfaced; "warn" if it names an
                                   exception-bearing claim absolutely but does surface some qualifier;
                                   "pass" otherwise.

Run:
    python scripts/output_faithfulness_gate.py     # demo across pass / warn / fail answers
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

# reuse the hardened, sentence-scoped absolutist detector from the corpus guardrail (build-upon, one source)
from legal_corpus_stage import _ABS_QUANT, _ABS_VERB, _SCOPING  # noqa: E402

# an answer surfaces an exception if it uses genuine scoping OR ordinary contrast/qualifier language
_EXCEPTION_MARKERS = re.compile(
    r"\bexcept\b|\bunless\b|\bsubject to\b|\bdepends on\b|\bvaries\b|\bin some\b|\bin certain\b|\bmay permit\b"
    r"|\bwhere ratified\b|\bnot in all\b|\bhowever\b|\bbut not\b|\bcheck (whether|if) it applies\b"
    r"|\bverify (it|whether) applies\b|\bwith (limited |certain )?exceptions?\b|\bqualif\w+\b|\bcaveat\b", re.I)


def _overbroad_sentences(text: str) -> list[str]:
    # Neutralise the number-abbreviation "No."/"Nos." when it precedes a digit, so "Convention No. 181" is not
    # split at "No." and is not misread as the quantifier "no". A genuine "no exceptions" (no trailing digit)
    # is untouched and still caught.
    t = re.sub(r"\bNos?\.\s*(?=\d)", "number ", text or "", flags=re.I)
    out = []
    for s in re.split(r"(?<=[.!?])\s+", t):
        if _ABS_QUANT.search(s) and _ABS_VERB.search(s) and not _SCOPING.search(s):
            out.append(s.strip())
    return out


def _law_signature(claim: dict) -> list[str]:
    """Distinctive tokens for matching an answer to a claim: convention/section numbers + a name word."""
    blob = f"{claim.get('authority','')} {claim.get('text','')}"
    sigs = set(re.findall(r"\bNo\.?\s*\d+\b|\bC0?\d{2,3}\b|\b\d{3,4}\b|\bArticle\s+\d+\b", blob))
    for name in ("Palermo", "UNTOC", "Kafala", "TVPA", "MLC", "UFLPA", "ICRMW", "CEDAW"):
        if name.lower() in blob.lower():
            sigs.add(name)
    return [s for s in sigs if len(s) >= 2]


def check(answer: str, claims: list[dict] | None = None) -> dict:
    """Flag an answer that asserts an absolute legal rule without its exception."""
    text = answer or ""
    overbroad = _overbroad_sentences(text)
    mentions_exc = bool(_EXCEPTION_MARKERS.search(text))
    cited = []
    if claims:
        low = text.lower()
        for c in claims:
            if not c.get("exceptions"):
                continue
            for sig in _law_signature(c):
                if sig.lower() in low:
                    cited.append(c["id"])
                    break
    if overbroad and not mentions_exc:
        verdict = "fail"        # states an absolute legal rule and surfaces no exception at all
    elif cited and overbroad:
        verdict = "warn"        # names an exception-bearing claim absolutely, but does mention some qualifier
    else:
        verdict = "pass"
    return {"verdict": verdict, "overbroad_sentences": overbroad, "mentions_exception": mentions_exc,
            "cited_claims_with_exceptions": sorted(set(cited)),
            "reason": ("absolute legal rule stated with no exception surfaced" if verdict == "fail"
                       else "absolute phrasing about an exception-bearing law" if verdict == "warn"
                       else "no unqualified absolute legal claim detected")}


_DEMO = [
    ("Recruitment fees are prohibited under ILO Convention No. 181, but this is subject to authorised national "
     "exceptions and depends on ratification.", "pass"),
    ("ILO Convention No. 181 absolutely prohibits ANY recruitment fee in every country with no exceptions, so "
     "this is illegal everywhere.", "fail"),
    ("Under Convention No. 29 forced labour is prohibited; note that C29 has defined lawful exceptions such as "
     "military service and prison labour.", "pass"),
]


def main() -> int:
    try:
        from legal_claims import load_claims
        claims = load_claims()
    except Exception:  # noqa: BLE001
        claims = None
    print("output-faithfulness gate -- demo:\n")
    for text, expected in _DEMO:
        r = check(text, claims)
        flag = "ok" if r["verdict"] == expected else f"!! expected {expected}"
        print(f"  [{r['verdict']:4s}] [{flag}] {text[:78]}...")
        if r["overbroad_sentences"]:
            print(f"        overbroad: {r['overbroad_sentences'][0][:80]}")
    print("\nrun on actual harness outputs, blinded to arm; a 'fail' = a real convention stated without its "
          "recorded exception -- the overbroad-no-exception failure the reasoning contract cannot catch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
