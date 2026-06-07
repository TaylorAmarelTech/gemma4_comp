"""Knowledge synthesizer + trend miner -- turn gated acquired chunks into the
FULL envelope taxonomy (not just rag_doc) and surface EMERGING signals.

More envelopes: each fired trend signal becomes a ``grep_rule`` (detection
pattern) or ``context_snippet`` (structured fact); novel recruitment-fee
euphemisms become fee-camouflage labels; uncharted corridors become
``corridor_record`` stubs.

More trend finding: aggregate which tactics appear, how often, and -- crucially --
what is NOVEL versus the existing corpus (a euphemism/corridor/method present in
the harvest but absent from what we already know is the signal worth surfacing).

Detectors implement the operational trend taxonomy (emerging corridors, fee
camouflage, digital coercion, recruitment-tech abuse, scam compounds, crisis
flows, enforcement actions, financial typologies). Deterministic + offline; an
optional LLM pass can deepen extraction. Propose-only: outputs are stubs for the
curator, never auto-promoted.
"""
from __future__ import annotations

import re

# trend_category -> detection patterns (case-insensitive). Condensed from the
# research-grounded taxonomy; conservative phrasings to limit false positives.
TREND_SIGNALS: dict[str, list[str]] = {
    "digital_coercion": [
        r"wages?\s+(?:held|locked|frozen)\s+(?:in|on|inside)\s+(?:the\s+)?app",
        r"(?:fingerprint|facial|iris|biometric)\s+(?:scan\s+)?(?:required|needed)\s+(?:to|before)\s+(?:withdraw|release|access)",
        r"passport\s+(?:stored|uploaded|held)\s+(?:in|on)\s+(?:an?\s+)?app",
        r"debt\s+(?:tracker|tracking|balance)\s+app",
        r"(?:salary|wages?)\s+(?:paid|loaded)\s+(?:only\s+)?(?:to|onto)\s+(?:a\s+)?(?:company|employer)\s+(?:card|wallet|app)",
        r"(?:can(?:not|'t)|unable\s+to)\s+(?:log\s*out|uninstall|delete)\s+(?:the\s+)?app",
    ],
    "scam_compound": [
        r"\b(?:myawaddy|shwe\s*kokko|kk\s*park|sihanoukville|bavet|poipet|golden\s+triangle|laukkai|mong\s*la)\b",
        r"(?:scam|fraud|cyber|crypto)\s+(?:compound|park|centre|center|farm|hub)",
        r"pig[-\s]?butchering|sha\s*zhu\s*pan",
        r"forced\s+to\s+(?:scam|defraud|run\s+scams?)",
        r"(?:sold|resold|transferred)\s+to\s+another\s+(?:compound|company|boss)",
    ],
    "recruitment_tech": [
        r"job\s+(?:offer|opportunity|vacancy)\s+(?:via|on|through)\s+(?:facebook|tiktok|telegram|whatsapp|instagram|wechat|viber|messenger)",
        r"(?:fake|fraudulent|cloned|spoofed)\s+(?:job|recruitment|agency)\s+(?:website|platform|portal|page)",
        r"(?:ai[-\s]?generated|deepfake|synthetic)\s+(?:job\s+ad|recruiter|video|interview|profile)",
        r"verification\s+(?:fee|deposit)\s+(?:to\s+)?(?:confirm|secure)\s+(?:the\s+)?(?:job|position|visa)",
        r"pay\s+(?:via|through|using)\s+(?:gift\s+card|crypto|usdt|mobile\s+money)",
    ],
    "crisis_flow": [
        r"(?:displaced|fleeing|refugees?|idps?)\b.{0,80}\b(?:vulnerable\s+to|targeted\s+by|at\s+risk\s+of)\s+(?:trafficking|exploitation|forced\s+labou?r)",
        r"(?:earthquake|flood|cyclone|drought|famine|conflict|war|coup)\b.{0,70}\b(?:traffick|exploit|forced\s+labou?r)",
        r"(?:stranded|abandoned)\s+(?:workers?|migrants?)\b.{0,50}\b(?:wage\s+theft|unpaid|repatriat)",
    ],
    "enforcement": [
        r"withhold\s+release\s+order|\bWRO\b",
        r"\bUFLPA\b|uyghur\s+forced\s+labor",
        r"convicted\s+(?:of|for)\s+(?:human\s+)?trafficking",
        r"(?:recruitment|placement)\s+(?:agenc\w+|licen[cs]e)\b.{0,25}\b(?:revoked|suspended|blacklisted|cancelled)",
        r"tier\s+[123]\b.{0,30}(?:downgrad|upgrad|watch\s*list)",
        r"(?:new|amended|enacted|came\s+into\s+force)\s+(?:anti[-\s]?trafficking|forced\s+labou?r|modern\s+slavery)\s+(?:law|act|bill)",
    ],
    "financial_typology": [
        r"\bhawala\b|\bhundi\b|informal\s+(?:value|money)\s+transfer",
        r"(?:salary|wages?)\s+(?:paid|sent|routed)\s+(?:to|into)\s+(?:a\s+)?(?:third[-\s]?party|recruiter'?s?|agent'?s?)\s+account",
        r"\b(?:usdt|tether|crypto(?:currency)?|bitcoin)\b.{0,40}\b(?:ransom|deposit|fee|wallet|launder)",
        r"\b(?:mule|smurfing|structuring|layering|shell\s+(?:company|account))\b",
    ],
}
_COMPILED = {cat: [re.compile(p, re.I) for p in pats] for cat, pats in TREND_SIGNALS.items()}

# novel-euphemism miner: "<modifier> <money-noun>" not in the known label set.
# 'commission'/'guarantee' dropped -- too ambiguous (European Commission, Human
# Rights Commission are bodies, not fees -> false positives on gov/NGO text).
_FEE_EUPH = re.compile(r"\b([a-z][a-z]{2,})\s+(bond|deposit|deduction|fee|charge|levy)\b", re.I)
_EUPH_STOP = {"the", "a", "an", "any", "no", "this", "that", "such", "said", "these", "those",
              "application", "registration", "membership", "entrance", "annual", "monthly",
              "late", "small", "full", "total", "additional", "extra", "same", "other", "first",
              "visa", "court", "filing", "user", "licence", "license", "admission", "tuition",
              "in", "on", "of", "and", "or", "for", "with", "without", "free"}


def trend_signals(text: str) -> dict[str, list[str]]:
    """Per-chunk: which trend categories fire, with the matched snippet(s)."""
    t = text or ""
    out: dict[str, list[str]] = {}
    for cat, pats in _COMPILED.items():
        hits = [m.group(0).strip() for p in pats for m in p.finditer(t)]
        if hits:
            out[cat] = sorted(set(hits))[:5]
    return out


def mine_fee_euphemisms(text: str, *, known: set[str] | None = None) -> set[str]:
    """Novel '<modifier> fee/bond/deduction' phrasings not already known -- the
    continuously-evolving recruitment-fee camouflage catalog."""
    known_l = {k.lower() for k in (known or set())}
    found: set[str] = set()
    for m in _FEE_EUPH.finditer(text or ""):
        mod = m.group(1).lower()
        if mod in _EUPH_STOP:
            continue
        label = f"{mod} {m.group(2).lower()}"
        if label not in known_l:
            found.add(label)
    return found


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "x"


def to_grep_rule_envelope(category: str, patterns: list[str], *, created_at: str,
                          severity: str = "high") -> dict:
    """A ``grep_rule`` detection envelope for a fired trend category (curator
    activates after review)."""
    return {
        "schema_version": "1.0", "knowledge_object_type": "grep_rule",
        "id": f"acqrule-{_slug(category)}", "version": "v1",
        "provenance": {"kind": "acquired_trend_signal",
                       "created_by": "scripts/synthesize_acquisition.py",
                       "created_at": created_at,
                       "notes": "Auto-drafted detection rule from acquired-content "
                                "trend mining; review before activation."},
        "content": {"rule": f"acquired_{category}", "category": category,
                    "patterns": patterns, "all_required": False,
                    "severity": severity, "indicator": category.replace("_", " ")},
        "tags": ["acquired", "trend", category],
    }


def fee_label_envelope(label: str, *, created_at: str) -> dict:
    """A ``context_snippet`` envelope mapping a mined euphemism -> fee_camouflage."""
    return {
        "schema_version": "1.0", "knowledge_object_type": "context_snippet",
        "id": f"acqfee-{_slug(label)}", "version": "v1",
        "provenance": {"kind": "acquired_trend_signal",
                       "created_by": "scripts/synthesize_acquisition.py",
                       "created_at": created_at,
                       "notes": "Candidate recruitment-fee euphemism mined from "
                                "acquired content; map to canonical label after review."},
        "content": {"label": label, "canonical": "fee_camouflage", "kind": "fee_euphemism"},
        "tags": ["acquired", "fee-camouflage", "trend"],
    }


def synthesize(chunks: list[dict], *, known_fee_labels: set[str] | None = None,
               created_at: str = "") -> dict:
    """Aggregate trend mining across chunks -> ``{report, envelopes}``. Emits one
    ``grep_rule`` per fired trend category + a ``context_snippet`` per novel fee
    euphemism. Each chunk needs ``text`` (+ optional ``url``/``doc_id``)."""
    from collections import Counter
    cat_chunks: Counter = Counter()
    cat_example: dict[str, str] = {}
    cat_sources: dict[str, set] = {}
    fee: Counter = Counter()
    for c in chunks:
        text = c.get("text", "")
        for cat, hits in trend_signals(text).items():
            cat_chunks[cat] += 1
            cat_example.setdefault(cat, hits[0] if hits else "")
            cat_sources.setdefault(cat, set()).add(c.get("url") or c.get("doc_id"))
        for lab in mine_fee_euphemisms(text, known=known_fee_labels):
            fee[lab] += 1

    envelopes: list[dict] = []
    for cat in cat_chunks:
        envelopes.append(to_grep_rule_envelope(cat, TREND_SIGNALS[cat], created_at=created_at))
    for lab, _ in fee.most_common(50):
        envelopes.append(fee_label_envelope(lab, created_at=created_at))

    report = {
        "chunks_scanned": len(chunks),
        "trend_categories": {
            cat: {"chunks": cat_chunks[cat], "sources": len(cat_sources.get(cat, set())),
                  "example": cat_example.get(cat, "")}
            for cat in sorted(cat_chunks, key=lambda k: -cat_chunks[k])},
        "novel_fee_euphemisms": fee.most_common(40),
        "grep_rules_generated": len(cat_chunks),
        "fee_labels_generated": min(50, len(fee)),
        "envelopes_generated": len(envelopes),
    }
    return {"report": report, "envelopes": envelopes}
