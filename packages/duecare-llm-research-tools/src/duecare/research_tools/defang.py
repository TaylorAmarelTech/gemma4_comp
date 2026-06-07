"""Defang untrusted document text before it enters the corpus / reaches the model.

Acquisition scrapes arbitrary public pages, so extracted text is UNTRUSTED. Two
threats from the representation-bottleneck analysis:

  * INJECTION -- content that reads as instruction/structure: chat-template /
    system delimiters (``<|im_end|>``, ``<start_of_turn>``, ``[INST]``) and
    markdown image/link exfil beacons (``![](http...)``).
  * EVASION   -- harmful content hidden as invisible/encoded tokens that slip past
    a human reviewer AND a classifier: zero-width chars, bidi overrides (the
    "Trojan Source" attack), and mixed-script homoglyphs.

Two jobs, not one:
  1. NEUTRALIZE -- strip invisibles/bidi, defuse template delimiters, declaw exfil
     images; and 2. DETECT -- a public gov page that contains an RLO override or a
     ``<|im_end|>`` token is itself a tamper/injection signal (``report.suspicious``).

Principle: DECLARED loss, not silent -- ``defang()`` returns cleaned text PLUS a
report of exactly what was neutralized, so the change is auditable. Deterministic,
offline, stdlib (unicodedata + re).
"""
from __future__ import annotations

import re
import unicodedata

# invisible / zero-width formatting chars (legit text almost never needs these)
_INVISIBLE = {0x200B, 0x200C, 0x200D, 0x2060, 0x2061, 0x2062, 0x2063, 0x2064,
              0xFEFF, 0x00AD, 0x034F, 0x180E}
# bidirectional override/embedding controls -- the Trojan-Source reorder attack
_BIDI = {0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069, 0x061C}
_STRIP = _INVISIBLE | _BIDI

# chat-template / system delimiters across families (channel separation)
_TEMPLATE = re.compile(
    r"<\|(?:im_start|im_end|endoftext|eot_id|start_header_id|end_header_id|system|user|assistant)\|>"
    r"|<\s*/?\s*(?:start_of_turn|end_of_turn)\s*>"          # gemma
    r"|\[/?INST\]|<</?SYS>>",                                # llama-2 / mistral
    re.I)

# markdown image exfil beacon: ![alt](http...) -> keep alt text, drop the URL
_MD_IMG = re.compile(r"!\[([^\]]*)\]\(\s*https?://[^)]+\)")

_WORD = re.compile(r"\S+")
_LATIN = re.compile(r"[A-Za-z]")
_CYR_GRK = re.compile(r"[Ͱ-ϿЀ-ӿ]")       # Greek + Cyrillic homoglyph range


def _neutralize_marker(m: re.Match) -> str:
    # keep it human-visible but un-parseable as a real control token
    return (m.group(0).replace("|", "¦").replace("<", "‹").replace(">", "›")
            .replace("[", "⟦").replace("]", "⟧"))


def defang(text: str) -> dict:
    """Return ``{"text": cleaned, "report": {...}}``. ``report.suspicious`` is True
    when an adversarial signal (bidi override, template delimiter, or mixed-script
    homoglyph word) was present -- a quarantine flag for the curator."""
    t = text or ""
    normalized = unicodedata.normalize("NFKC", t)        # full-width / compat lookalikes
    nfkc_changed = normalized != t
    t = normalized

    bidi = sum(1 for c in t if ord(c) in _BIDI)
    invisible = sum(1 for c in t if ord(c) in _INVISIBLE)
    if bidi or invisible:
        t = "".join(c for c in t if ord(c) not in _STRIP)

    t, n_markers = _TEMPLATE.subn(_neutralize_marker, t)
    t, n_images = _MD_IMG.subn(lambda m: m.group(1) or "[image]", t)

    mixed_script = sum(1 for w in _WORD.findall(t) if _LATIN.search(w) and _CYR_GRK.search(w))

    report = {
        "nfkc_changed": nfkc_changed,
        "bidi_controls_removed": bidi,
        "invisible_chars_removed": invisible,
        "template_markers_neutralized": n_markers,
        "exfil_images_neutralized": n_images,
        "mixed_script_words": mixed_script,
        "suspicious": bool(bidi or n_markers or mixed_script),
    }
    return {"text": t, "report": report}


def defang_text(text: str) -> str:
    """Convenience: return just the cleaned text."""
    return defang(text)["text"]
