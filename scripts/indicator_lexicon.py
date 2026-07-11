"""Multilingual + synonym lexicon for the ILO forced-labour indicators -- closes the paraphrase and
non-English evasion gaps an adversarial audit verified (see docs/research/adversarial_findings_2026_07_10.md,
items 1 & 2).

The deterministic indicator matcher in legal_reasoning.py keyed on a handful of EXACT English surface forms,
so a worker who wrote "the office is keeping my travel booklet and I have a cash advance I must earn back"
matched NOTHING, and a Tagalog report fired nothing at all. Migrant workers overwhelmingly report in origin
and host languages and rarely in the exact benchmark phrasing. This module supplies, per indicator:

  * SYNONYM_EN  -- English PARAPHRASES of the same concept (high confidence): 'travel booklet/papers' ->
    document retention, 'cash advance / earn it back / owe them' -> debt bondage, "won't let me leave /
    stuck / trapped" -> restriction of movement, etc. This is the part that closes the verified paraphrase
    attack and it is expanded conservatively.
  * MULTILINGUAL  -- a STARTER seed of high-confidence terms in key corridor languages (Tagalog, Indonesian,
    Spanish loanwords, plus a few widely-used terms). It is deliberately small and HONEST: it is a scaffold,
    not a complete dictionary. Real coverage needs native-speaker + primary-source expansion (tracked in
    configs/duecare/legal_research_queue.json). Nothing here is fabricated; uncertain translations are omitted
    rather than guessed.

Terms feed legal_reasoning.match_indicators through the same whole-word/stem matcher, so precision behaves
the same as the English keywords. Deterministic, no model, no network, propose-only.

Run:
    python scripts/indicator_lexicon.py     # coverage summary per indicator
"""
from __future__ import annotations

# English paraphrase synonyms (the confident, verified-attack-closing layer). Keyed to the exact indicator
# names used by legal_reasoning._INDICATOR_KEYWORDS. A trailing '*' is a stem (matches suffixes).
SYNONYM_EN: dict[str, list[str]] = {
    "retention of identity documents": [
        "travel booklet", "travel document*", "travel papers", "my papers", "id booklet", "identity booklet",
        "held my document*", "took my document*", "keeping my document*", "kept my id", "has my passport",
        "won't give my passport", "will not give my passport", "won't return my passport", "keeps my passport",
        "holding my paper*"],
    "debt bondage": [
        "cash advance", "an advance", "earn it back", "earn back", "work it off", "work off", "pay it back before",
        "owe them", "owe the agency", "owe the boss", "i owe", "still owe", "until i pay", "until it is paid",
        "money i borrowed", "the loan i took", "clear the debt"],
    "restriction of movement": [
        "won't let me leave", "will not let me leave", "won't let me go", "not allowed to leave",
        "can't get out", "cannot get out", "not allowed out", "stuck here", "i am trapped", "trapped here",
        "keep me here", "kept inside", "locked inside", "cannot go outside", "not free to leave", "let me go"],
    "withholding of wages": [
        "holding my pay", "keeping my salary", "not giving my wage*", "haven't been paid", "have not been paid",
        "keeping my money", "hold my pay", "salary not given", "not paying me", "months without pay",
        "no pay for month*", "keeps my earning*"],
    "intimidation and threats": [
        "threatened to call immigration", "threatened to send me home", "said they would report me",
        "said they'd report me", "scared to leave", "afraid to complain", "afraid to leave",
        "threatened to cancel", "threatened my family", "if i complain they"],
    "excessive overtime": [
        "work all day and night", "work day and night", "never a day off", "no day off ever", "work every day",
        "no break*", "sixteen hours", "no rest at all"],
    "deception": [
        "not the job promised", "different job", "job was not what", "lied about the", "promised something else",
        "contract i signed was different", "tricked me"],
    "isolation": [
        "phone was taken", "took my phone", "can't call anyone", "cannot contact my family", "no way to contact",
        "not allowed a phone", "cut off from"],
    "abuse of vulnerability": [
        "i am undocumented", "no papers here", "don't speak the language", "cannot read the contract",
        "far from home and", "nobody to help me here"],
}

# STARTER multilingual seed -- high-confidence terms only; expand with native speakers. tl=Tagalog, id=Indonesian,
# es=Spanish (loanwords also used in several corridors). Uncertain terms are intentionally omitted.
MULTILINGUAL: dict[str, list[str]] = {
    "retention of identity documents": ["pasaporte", "paspor", "kinuha ang aking pasaporte", "hawak ang pasaporte"],
    "debt bondage": ["utang", "deuda", "may utang ako", "hutang"],
    "restriction of movement": ["hindi ako makaalis", "tidak boleh keluar", "no puedo salir", "hindi pinapayagang umalis"],
    "withholding of wages": ["hindi ako binabayaran", "tidak dibayar", "no me pagan", "sahod hindi ibinigay"],
    "intimidation and threats": ["tinatakot ako", "diancam", "me amenazan"],
}


def terms_for(indicator: str) -> list[str]:
    """All extra lexicon terms (English synonyms + multilingual seed) for one indicator."""
    return SYNONYM_EN.get(indicator, []) + MULTILINGUAL.get(indicator, [])


def all_terms() -> dict[str, list[str]]:
    """indicator -> combined extra terms, for every indicator this lexicon covers."""
    keys = set(SYNONYM_EN) | set(MULTILINGUAL)
    return {k: terms_for(k) for k in keys}


def coverage() -> dict[str, dict[str, int]]:
    return {k: {"synonym_en": len(SYNONYM_EN.get(k, [])), "multilingual": len(MULTILINGUAL.get(k, []))}
            for k in (set(SYNONYM_EN) | set(MULTILINGUAL))}


def main() -> int:
    print("indicator lexicon -- extra terms per indicator (synonym_en + multilingual seed):")
    total = 0
    for ind, c in sorted(coverage().items()):
        n = c["synonym_en"] + c["multilingual"]
        total += n
        print(f"  {ind:38s} en={c['synonym_en']:>2}  ml={c['multilingual']:>2}  (total {n})")
    print(f"\n{total} extra terms across {len(coverage())} indicators. Multilingual is a STARTER seed -- "
          "expand with native speakers + primary sources (do not guess translations).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
