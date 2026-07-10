"""Is the harness sitting on a fragile SEMANTIC PEAK? — GREP fire-rate under realistic input noise.

Taylor's concern: "make sure we aren't just maximizing a semantic peak in the feature space" — if a few
typos or extra words collapse the harness's detection, the lift is overfit to an exact surface form, not
robust. Migrant workers type on phones, in a second language, under stress: misspellings, keyboard typos,
filler words, and dropped words are the NORMAL input, not the exception.

This measures how the deterministic GREP indicator layer's fire-rate degrades as escalating noise is
injected into worker prompts (no LLM, no network, no Ollama — cheap and reproducible). Nine noise types:
keyboard TYPOS, common MISSPELLINGS, EXTRA words (filler), DROPPED words (content-word subtraction),
DROP_STOPWORDS (subtract only stopwords — the clean overfitting test), SPLIT_MERGE (whitespace noise:
'passport'->'pass port'), CHAR_REPEAT (elongation: 'pleaseee'), PUNCT_INJECT (separator evasion:
'p.a.s.s.p.o.r.t'), and WORD_SWAP (local reorder). The
metric is fire RETENTION = rules_fired(noisy) / rules_fired(clean); retention well below 1.0 under mild
noise means GREP is brittle to that noise and should gain typo/misspelling-tolerant matching (an actionable
harness improvement, propose-only — this script never edits the harness). Complements
``grep_multilingual_coverage.py`` (language axis) and ``prompt_remixer.py`` (which GENERATES perturbations;
this MEASURES robustness). Propose-only.

Run:
    python scripts/noise_robustness.py                 # over the embedded composite worker scenarios
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
from pathlib import Path
from typing import Callable

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
for _s in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_s))

from grep_multilingual_coverage import _default_grep_call, n_fired  # noqa: E402

OUT = _ROOT / "reports" / "noise_robustness.json"
LEVELS = (0.05, 0.10, 0.20)   # fraction of eligible words perturbed

# COMPOSITE / SYNTHETIC worker scenarios rich in indicator terms the GREP layer targets (no real PII).
WORKER_SCENARIOS = [
    "The recruitment agency took my passport and says I must repay the placement fee before I can leave.",
    "My employer withholds two months of wages as security and pays less than the contract promised.",
    "I paid a large recruitment fee and now they say I am in debt bondage until it is cleared.",
    "The boss locked the accommodation and confiscated our phones so we cannot contact anyone.",
    "They switched my contract after I arrived and threaten to cancel my visa if I complain.",
    "The agent charged a processing fee equal to three months salary before releasing the job offer.",
    "I work eighteen hours a day with no rest day and they deduct money for food and housing.",
    "My passport is held by the sponsor and I cannot change jobs or go home without permission.",
    "The broker promised factory work but I was sent to a fishing boat and never paid.",
    "They say I owe them for travel and training so all my salary goes to repay the loan.",
]

_QWERTY_ADJ = {
    "a": "sqwz", "b": "vghn", "c": "xdfv", "d": "sferc", "e": "wrsdf", "f": "dgrtcv", "g": "fhtybv",
    "h": "gjyubn", "i": "ujko", "j": "hknmu", "k": "jlmi", "l": "kop", "m": "njk", "n": "bhjm",
    "o": "iklp", "p": "ol", "q": "wa", "r": "etdf", "s": "adwxz", "t": "rygf", "u": "yihj",
    "v": "cfgb", "w": "qeas", "x": "zsdc", "y": "tugh", "z": "asx",
}
# common real-world misspellings (worker-plausible), keyed on the correctly-spelled word
_MISSPELL = {
    "recruitment": "recruitement", "receive": "recieve", "passport": "pasport", "salary": "salery",
    "agency": "agancy", "employer": "employeer", "separate": "seperate", "government": "goverment",
    "contract": "contrct", "because": "becuase", "money": "mony", "police": "polise", "wages": "wagaes",
    "immigration": "imigration", "foreign": "foriegn", "accommodation": "accomodation",
    "confiscated": "confiscted", "threaten": "threathen", "processing": "procesing", "security": "securty",
}
_FILLERS = ["um", "like", "please", "sir", "actually", "you know", "i think", "maybe", "so", "kind of"]


def _typo_word(w: str, rng: random.Random) -> str:
    """One keyboard-style typo on a word (transpose / adjacent-key sub / drop); short words untouched."""
    if len(w) < 4:
        return w
    i = rng.randrange(len(w) - 1)
    r = rng.random()
    if r < 0.4:                                   # transpose adjacent chars
        return w[:i] + w[i + 1] + w[i] + w[i + 2:]
    if r < 0.75:                                  # substitute a keyboard-adjacent char
        adj = _QWERTY_ADJ.get(w[i].lower())
        return w[:i] + rng.choice(adj) + w[i + 1:] if adj else w
    return w[:i] + w[i + 1:]                       # drop a char


def keyboard_typo(text: str, *, rate: float, rng: random.Random) -> str:
    return " ".join(_typo_word(w, rng) if rng.random() < rate else w for w in text.split())


def misspell(text: str, *, rate: float, rng: random.Random) -> str:
    def repl(m: re.Match) -> str:
        w = m.group(0)
        ms = _MISSPELL.get(w.lower())
        if ms and rng.random() < rate:
            return ms.capitalize() if w[:1].isupper() else ms
        return w
    return re.sub(r"[A-Za-z]+", repl, text)


def insert_filler(text: str, *, rate: float, rng: random.Random) -> str:
    out: list[str] = []
    for w in text.split():
        out.append(w)
        if rng.random() < rate:
            out.append(rng.choice(_FILLERS))
    return " ".join(out)


def delete_words(text: str, *, rate: float, rng: random.Random) -> str:
    """Word SUBTRACTION: drop content words (>2 chars). Info loss is expected; the question is how fast
    firing degrades (low retention under mild deletion = low trigger redundancy)."""
    kept = [w for w in text.split() if not (len(w) > 2 and rng.random() < rate)]
    return " ".join(kept) or text


_STOPWORDS = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "to", "of", "in", "on",
              "for", "with", "my", "i", "me", "we", "they", "he", "she", "it", "that", "this", "so", "at",
              "as", "by", "from", "before", "after", "than", "then", "now", "has", "have", "had", "will"}


def drop_stopwords(text: str, *, rate: float, rng: random.Random) -> str:
    """Subtract ONLY stopwords -- the CLEAN overfitting test. Removing 'the'/'to'/'my' must not change a
    trafficking indicator; if GREP firing drops, a rule is matching an exact multi-word phrase that
    includes a stopword (overfit to surface form, not to the indicator)."""
    kept = [w for w in text.split() if not (w.lower().strip(".,!?;:") in _STOPWORDS and rng.random() < rate)]
    return " ".join(kept) or text


def split_merge(text: str, *, rate: float, rng: random.Random) -> str:
    """WHITESPACE noise: split some long words with a space ('passport'->'pass port') and merge some
    adjacent pairs ('recruitment fee'->'recruitmentfee'). Phone autocorrect / OCR do this constantly and
    it directly breaks token/keyword matching."""
    words = text.split()
    out: list[str] = []
    i = 0
    while i < len(words):
        w = words[i]
        r = rng.random()
        if r < rate / 2 and len(w) >= 6:                      # split a long word
            k = rng.randrange(2, len(w) - 1)
            out.extend([w[:k], w[k:]])
        elif r < rate and i + 1 < len(words):                 # merge with the next word
            out.append(w + words[i + 1]); i += 1
        else:
            out.append(w)
        i += 1
    return " ".join(out)


def char_repeat(text: str, *, rate: float, rng: random.Random) -> str:
    """Character ELONGATION ('pleaseee', 'helppp') -- stressed / emotional phone text."""
    def rep(w: str) -> str:
        if len(w) < 3 or rng.random() >= rate:
            return w
        i = rng.randrange(len(w))
        return w[:i + 1] + w[i] * rng.randint(1, 2) + w[i + 1:]
    return " ".join(rep(w) for w in text.split())


def punct_inject(text: str, *, rate: float, rng: random.Random) -> str:
    """Separator EVASION ('p.a.s.s.p.o.r.t', 'fe-e') -- the technique bad actors use to slip past keyword
    filters, and that stylised text produces by accident. Splits a selected word with a separator char."""
    seps = (".", "-", "*", " ")
    def inj(w: str) -> str:
        if len(w) < 4 or rng.random() >= rate:
            return w
        return rng.choice(seps).join(w)
    return " ".join(inj(w) for w in text.split())


def word_swap(text: str, *, rate: float, rng: random.Random) -> str:
    """Local word REORDER (swap adjacent pairs) -- ungrammatical second-language / stress ordering. The
    word SET is preserved, so a bag-of-words rule should be invariant; a phrase rule will miss."""
    words = text.split()
    i = 0
    while i < len(words) - 1:
        if rng.random() < rate:
            words[i], words[i + 1] = words[i + 1], words[i]
            i += 2
        else:
            i += 1
    return " ".join(words)


NOISE_FUNCS: dict[str, Callable[..., str]] = {
    "typo": keyboard_typo, "misspell": misspell, "extra_words": insert_filler, "dropped_words": delete_words,
    "drop_stopwords": drop_stopwords, "split_merge": split_merge, "char_repeat": char_repeat,
    "punct_inject": punct_inject, "word_swap": word_swap,
}


def measure(prompts: list[str], grep_call: Callable[[str], object], *, levels=LEVELS) -> dict:
    """Per (noise_type, level): mean rules fired clean vs noisy and the fire-retention ratio, over the
    prompts whose CLEAN text fired at least one rule (so retention is well-defined)."""
    clean = {i: n_fired(grep_call, p) for i, p in enumerate(prompts)}
    fired_idx = [i for i, c in clean.items() if c > 0]
    clean_mean = round(statistics.mean(clean[i] for i in fired_idx), 2) if fired_idx else 0.0
    rows = []
    for ntype, fn in NOISE_FUNCS.items():
        for lvl in levels:
            noisy, ratios = [], []
            for i in fired_idx:
                rng = random.Random(f"{ntype}:{lvl}:{i}")     # deterministic, reproducible
                nf = n_fired(grep_call, fn(prompts[i], rate=lvl, rng=rng))
                noisy.append(nf)
                ratios.append(nf / clean[i])
            rows.append({
                "noise_type": ntype, "level": lvl, "n": len(fired_idx),
                "mean_fired_noisy": round(statistics.mean(noisy), 2) if noisy else 0.0,
                "fire_retention": round(statistics.mean(ratios), 3) if ratios else None,
            })
    return {"n_prompts": len(prompts), "n_prompts_fired_clean": len(fired_idx),
            "clean_mean_fired": clean_mean, "levels": list(levels), "by_noise": rows}


def format_report(res: dict) -> str:
    lines = [f"GREP fire-rate under input noise (clean mean fired = {res['clean_mean_fired']} over "
             f"{res['n_prompts_fired_clean']}/{res['n_prompts']} prompts that fire clean)",
             "(fire_retention = rules fired on the NOISY prompt / rules fired on the clean prompt; "
             "1.0 = fully robust, <1 = brittle to that noise)", "",
             f"{'noise_type':14s} {'level':>6s} {'mean_fired':>11s} {'retention':>10s}"]
    for r in res["by_noise"]:
        ret = "n/a" if r["fire_retention"] is None else f"{r['fire_retention']:.2f}"
        lines.append(f"{r['noise_type']:14s} {r['level']:>6.2f} {r['mean_fired_noisy']:>11.2f} {ret:>10s}")
    # headline: worst retention at the lightest level (the fragility signal)
    light = [r for r in res["by_noise"] if r["level"] == min(res["levels"]) and r["fire_retention"] is not None]
    if light:
        worst = min(light, key=lambda r: r["fire_retention"])
        lines += ["", f"at the lightest noise ({worst['level']:.0%}), worst-hit = {worst['noise_type']} "
                  f"-> {worst['fire_retention']:.0%} of indicator rules still fire.",
                  "  low retention on typo/misspell => GREP overfits exact spelling; add "
                  "misspelling/typo-tolerant matching (propose-only)."]
    return "\n".join(lines)


def load_batch_prompts(path: Path, sample: int) -> list[str]:
    """First ``sample`` prompt texts from a promptset JSON (``{"prompts":[{"text":..}]}`` or a bare list),
    so the noise probe can run on the REAL benchmark distribution instead of the embedded scenarios."""
    d = json.loads(path.read_text(encoding="utf-8"))
    items = d.get("prompts") if isinstance(d, dict) else d
    out = []
    for p in (items or []):
        t = p.get("text") or p.get("source_text_en") or p.get("prompt") if isinstance(p, dict) else None
        if t:
            out.append(t)
        if len(out) >= sample:
            break
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GREP fire-rate robustness under input noise (typos/misspell/etc).")
    ap.add_argument("--levels", default=",".join(str(x) for x in LEVELS),
                    help="comma-separated perturbation rates")
    ap.add_argument("--batch", type=Path, default=None,
                    help="promptset JSON to draw real prompts from (default: embedded worker scenarios)")
    ap.add_argument("--sample", type=int, default=300, help="max prompts to draw from --batch")
    args = ap.parse_args(argv)
    levels = tuple(float(x) for x in args.levels.split(",") if x.strip())
    prompts = load_batch_prompts(args.batch, args.sample) if args.batch else WORKER_SCENARIOS
    if not prompts:
        print(f"no prompts loaded from {args.batch}"); return 1
    res = measure(prompts, _default_grep_call(), levels=levels)
    res["_synthetic"] = True
    res["_propose_only"] = True
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(format_report(res))
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
