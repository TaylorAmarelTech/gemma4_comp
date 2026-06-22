#!/usr/bin/env python3
"""Input-attack transforms + GREP-robustness analysis for the harness.

The DueCare harness's first layer is GREP indicator rules (case-insensitive regex/keyword matching).
The sharp red-team question: does that layer still fire when an attacker *obfuscates the input*? This
module applies a matrix of surface transforms a real evader would use — bilingual/code-switch,
no-punctuation, excessive punctuation, homoglyph (unicode confusables), whitespace injection,
leetspeak — and measures **GREP-hit retention** per transform (deterministic, NO model calls). It also
emits an attack-matrix prompt set so the full baseline-vs-harness *lift under attack* can be run later.

Complements scripts/prompt_remixer.py (which already does punctuate/typo/contraction/leet/spintax) with
the cross-lingual and unicode-evasion transforms that corpus lacks, and with the GREP-firing analysis.

    python scripts/prompt_attacks.py --base scheme_prompts.json --grep-report docs/research/attack_robustness.md
    python scripts/prompt_attacks.py --base scheme_prompts.json --emit configs/duecare/benchmarks/attack_matrix.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Key trafficking terms GREP rules key on — the words an evader most wants to hide.
_KEY_TERMS = [
    "passport", "fee", "fees", "salary", "wage", "wages", "recruit", "recruitment", "recruiter",
    "agent", "agency", "contract", "debt", "deduction", "deductions", "visa", "worker", "workers",
    "bondage", "trafficking", "deploy", "deployment", "loan", "repayment", "savings", "broker",
]

# Code-switch phrasebook: English term -> {lang: translation}. Composite, common-usage words; the test
# is whether GREP's English keyword rules survive when the key noun is in the worker's own language.
_PHRASEBOOK = {
    "passport":   {"es": "pasaporte", "tl": "pasaporte", "hi": "paasaport", "id": "paspor"},
    "fee":        {"es": "tarifa", "tl": "bayad", "hi": "shulk", "id": "biaya"},
    "fees":       {"es": "tarifas", "tl": "bayarin", "hi": "shulk", "id": "biaya"},
    "salary":     {"es": "salario", "tl": "sahod", "hi": "vetan", "id": "gaji"},
    "wage":       {"es": "salario", "tl": "sahod", "hi": "majduri", "id": "upah"},
    "agent":      {"es": "agente", "tl": "ahente", "hi": "dalal", "id": "agen"},
    "agency":     {"es": "agencia", "tl": "ahensiya", "hi": "ejensi", "id": "agensi"},
    "contract":   {"es": "contrato", "tl": "kontrata", "hi": "anubandh", "id": "kontrak"},
    "debt":       {"es": "deuda", "tl": "utang", "hi": "karz", "id": "utang"},
    "deduction":  {"es": "deduccion", "tl": "bawas", "hi": "katauti", "id": "potongan"},
    "worker":     {"es": "trabajador", "tl": "manggagawa", "hi": "mazdoor", "id": "pekerja"},
    "recruiter":  {"es": "reclutador", "tl": "ahente", "hi": "dalal", "id": "perekrut"},
    "loan":       {"es": "prestamo", "tl": "pautang", "hi": "udhaar", "id": "pinjaman"},
    "savings":    {"es": "ahorros", "tl": "ipon", "hi": "bachat", "id": "tabungan"},
}
_LANGS = ["es", "tl", "hi", "id"]

# Latin -> visually-confusable Cyrillic/Greek (homoglyph) — defeats byte-level keyword regex.
_HOMOGLYPH = {
    "a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х",
    "y": "у", "i": "і", "s": "ѕ", "j": "ј", "A": "А", "B": "В",
    "E": "Е", "H": "Н", "K": "К", "M": "М", "O": "О", "P": "Р",
    "C": "С", "T": "Т", "X": "Х",
}
_ZWSP = "​"


def _sub_key_terms(text: str, fn) -> str:
    """Apply fn(word) to each whole-word occurrence of a key term (case-insensitive)."""
    def repl(m):
        return fn(m.group(0))
    pat = r"\b(" + "|".join(sorted(_KEY_TERMS, key=len, reverse=True)) + r")\b"
    return re.sub(pat, repl, text, flags=re.IGNORECASE)


def code_switch(text: str, i: int) -> str:
    """Replace key nouns with the worker's-language equivalent (one target language per variant)."""
    lang = _LANGS[i % len(_LANGS)]

    def swap(word: str) -> str:
        tr = _PHRASEBOOK.get(word.lower())
        return tr.get(lang, word) if tr else word
    return _sub_key_terms(text, swap)


def strip_punctuation(text: str, i: int) -> str:
    """Remove all punctuation (the model still reads it; word-boundary regex may not)."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text)).strip()


def excessive_punctuation(text: str, i: int) -> str:
    """Spray punctuation between words and inside key terms."""
    out = re.sub(r"\s+", lambda _m: [" ... ", " !! ", " -- ", " ?! "][i % 4], text)
    return _sub_key_terms(out, lambda w: ".".join(w))     # p.a.s.s.p.o.r.t


def homoglyph(text: str, i: int) -> str:
    """Swap Latin letters in key terms for Cyrillic/Greek look-alikes (defeats keyword regex)."""
    def swap(word: str) -> str:
        return "".join(_HOMOGLYPH.get(ch, ch) for ch in word)
    return _sub_key_terms(text, swap)


def whitespace_injection(text: str, i: int) -> str:
    """Insert a zero-width space inside key terms (looks identical, breaks the token)."""
    def swap(word: str) -> str:
        mid = len(word) // 2
        return word[:mid] + _ZWSP + word[mid:]
    return _sub_key_terms(text, swap)


def leetspeak(text: str, i: int) -> str:
    """Sparse look-alike ASCII substitution on key terms (a->4, e->3, o->0, s->5, i->1)."""
    table = {"a": "4", "e": "3", "o": "0", "s": "5", "i": "1"}

    def swap(word: str) -> str:
        return "".join(table.get(ch.lower(), ch) for ch in word)
    return _sub_key_terms(text, swap)


TRANSFORMS = {
    "code_switch": code_switch,
    "no_punctuation": strip_punctuation,
    "excessive_punctuation": excessive_punctuation,
    "homoglyph": homoglyph,
    "whitespace_injection": whitespace_injection,
    "leetspeak": leetspeak,
}


def load_base(path: pathlib.Path) -> list[dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return d.get("prompts", d) if isinstance(d, dict) else d


def apply_attacks(prompts: list[dict]) -> list[dict]:
    """Each base prompt × each transform -> a perturbed prompt carrying the transform label."""
    out: list[dict] = []
    for idx, p in enumerate(prompts):
        base_text = p.get("text", "")
        for name, fn in TRANSFORMS.items():
            t = fn(base_text, idx)
            pid = "ATK-" + name[:4].upper() + "-" + hashlib.sha1(t.encode("utf-8")).hexdigest()[:8].upper()
            out.append({"id": pid, "text": t, "category": "input_attack", "transform": name,
                        "base_id": p.get("id"), "difficulty": "hard"})
    return out


def _grep_hits(text: str) -> set[str]:
    from duecare.chat.harness import _grep_call
    return {h.get("rule") for h in _grep_call(text).get("hits", [])}


def grep_robustness(prompts: list[dict]) -> dict:
    """For each transform: how many GREP hits survive vs the clean prompt (deterministic, no model)."""
    sys.path.insert(0, str(_ROOT / "packages" / "duecare-llm-chat" / "src"))
    per_transform = {name: {"clean": 0, "kept": 0, "fully_evaded": 0, "n": 0} for name in TRANSFORMS}
    n_clean = 0
    for idx, p in enumerate(prompts):
        base_text = p.get("text", "")
        clean = _grep_hits(base_text)
        if not clean:
            continue                                    # only score prompts GREP catches when clean
        n_clean += 1
        for name, fn in TRANSFORMS.items():
            kept = _grep_hits(fn(base_text, idx)) & clean
            d = per_transform[name]
            d["clean"] += len(clean)
            d["kept"] += len(kept)
            d["n"] += 1
            if not kept:
                d["fully_evaded"] += 1
    for name, d in per_transform.items():
        d["retention_pct"] = round(100 * d["kept"] / d["clean"], 1) if d["clean"] else None
        d["fully_evaded_pct"] = round(100 * d["fully_evaded"] / d["n"], 1) if d["n"] else None
    return {"n_prompts": len(prompts), "n_with_clean_hits": n_clean, "per_transform": per_transform}


def build_grep_report(agg: dict, *, out_path: pathlib.Path) -> str:
    pt = agg["per_transform"]
    o: list[str] = []
    o.append("# Input-attack robustness — does the GREP layer survive obfuscation?\n")
    o.append(
        "The harness's first layer is **GREP indicator rules** (case-insensitive keyword/regex). A real "
        "evader obfuscates the input, so we apply a matrix of surface transforms to prompts GREP catches "
        "when clean, and measure **how many of those hits survive**. This is deterministic — no model "
        "calls — and isolates the keyword layer specifically. Where GREP is evaded, the harness's RAG + "
        "ILO-reasoning layers are the backstop (measured separately by the lift-under-attack run).\n")
    worst = min((d["retention_pct"] for d in pt.values() if d["retention_pct"] is not None), default=None)
    o.append(
        f"> Over **{agg['n_with_clean_hits']} prompts** GREP catches when clean, hit-retention under attack "
        f"ranges down to **{worst}%** (the strongest evasion). Keyword matching alone is *not* robust to "
        f"unicode/cross-lingual obfuscation — which is exactly why the harness does not rely on it alone.\n")
    o.append("## GREP hit-retention by attack (higher = more robust)\n")
    o.append("| Attack transform | hits kept | fully-evaded prompts | what it does |")
    o.append("|---|---:|---:|---|")
    desc = {
        "code_switch": "key nouns -> worker's language (es/tl/hi/id)",
        "no_punctuation": "strip all punctuation",
        "excessive_punctuation": "spray punctuation, split key terms",
        "homoglyph": "Latin -> Cyrillic/Greek look-alikes",
        "whitespace_injection": "zero-width space inside key terms",
        "leetspeak": "a->4 e->3 o->0 s->5 i->1 on key terms",
    }
    for name, d in sorted(pt.items(), key=lambda kv: (kv[1]["retention_pct"] if kv[1]["retention_pct"] is not None else 999)):
        o.append(f"| `{name}` | **{d['retention_pct']}%** | {d['fully_evaded_pct']}% | {desc.get(name,'')} |")
    o.append("")
    o.append("## Reading this\n")
    o.append(
        "- **hits kept** = of the GREP rules that fired on the clean prompt, the share that still fire "
        "after the attack. **fully-evaded** = the share of prompts where the attack silences GREP entirely.\n"
        "- The point is **not** that GREP is weak — it is fast, free, and exact on clean text. The point "
        "is that a keyword layer *must* be backed by semantic layers; DueCare's harness is GREP **plus** "
        "retrieved legal grounding **plus** an ILO-reasoning preamble, so an obfuscated prompt that slips "
        "past GREP still meets the model with the reasoning instruction. The *lift under attack* "
        "(baseline-vs-harness on these perturbed prompts) is the companion result.\n"
        "- Deterministic + composite; transforms in `scripts/prompt_attacks.py`. The attack-matrix prompt "
        "set (`--emit`) feeds the model run.\n")
    md = "\n".join(o) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return md


def main(argv: list[str] | None = None) -> int:
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="scheme_prompts.json", help="base prompt file under configs/duecare/benchmarks/")
    ap.add_argument("--limit", type=int, default=0, help="cap base prompts (0 = all)")
    ap.add_argument("--grep-report", default="docs/research/attack_robustness.md")
    ap.add_argument("--emit", default="", help="also write the attack-matrix prompt set to this path")
    args = ap.parse_args(argv)
    base_path = pathlib.Path(args.base)
    if not base_path.exists():
        base_path = _ROOT / "configs" / "duecare" / "benchmarks" / args.base
    prompts = load_base(base_path)
    if args.limit:
        prompts = prompts[: args.limit]
    agg = grep_robustness(prompts)
    build_grep_report(agg, out_path=pathlib.Path(args.grep_report))
    print(f"grep-robustness -> {args.grep_report} | {agg['n_with_clean_hits']}/{agg['n_prompts']} clean-caught")
    for name, d in agg["per_transform"].items():
        print(f"  {name}: retention {d['retention_pct']}% | fully-evaded {d['fully_evaded_pct']}%")
    if args.emit:
        atk = apply_attacks(prompts)
        out = pathlib.Path(args.emit)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"prompts": atk, "_meta": {"n": len(atk), "transforms": list(TRANSFORMS),
                                                              "composite": True}}, indent=2), encoding="utf-8")
        print(f"attack-matrix -> {args.emit} | {len(atk)} perturbed prompts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
