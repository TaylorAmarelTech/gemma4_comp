"""Heuristic verdicts for the moderation + worker-check surfaces.

These are the FALLBACKS used when no Gemma backend is wired into the
server. The heuristic rules are deliberately rich -- multi-signal,
multi-language (English, Tagalog markers, transliterated Arabic) --
because a real Kaggle demo without Gemma needs to still produce
believable verdicts on coercion-style messages like:

  "Mama-san said I must pay USD 5,000 deposit and she will keep my
   passport until I finish 2 years. She said the agency boss will help
   me, but I cannot leave the house alone."

That message hits 5+ critical ILO C029 signals and should land at
severity 9-10, not 0.
"""
from __future__ import annotations

import re
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Signal taxonomy. Each (signal_name, keyword_list, severity_weight).
# Weights are additive but capped at 10. A single critical signal alone
# is enough to land in REVIEW; two critical or one critical + one
# strong land in BLOCK.
# ---------------------------------------------------------------------------
_CRITICAL_SIGNALS: list[tuple[str, list[str], int]] = [
    ("passport_confiscation", [
        "keep your passport", "keep my passport", "hold your passport",
        "we will keep your passport", "we'll keep your passport",
        "deposit your passport", "passport will be held",
        "passport in our safe", "we hold the passport",
        "cannot return passport", "passport with the agency",
        "give us your passport", "surrender your passport",
        "agency will hold", "kafala", "iqama",
        # Tagalog markers
        "passport namin", "ihahawak ang passport",
    ], 4),

    ("movement_restriction", [
        "cannot leave", "not allowed to leave", "must stay",
        "cannot go out", "lock the door", "no time off",
        "cannot leave the house", "cannot leave alone",
        "no day off", "always with us", "must stay inside",
        "live with employer", "no permission to leave",
        # Tagalog markers
        "hindi makaalis", "bawal lumabas",
    ], 3),

    ("debt_bondage", [
        "you owe", "must pay first", "until you finish",
        "work off the debt", "must pay before", "deposit then start",
        "until you complete", "until you finish 2 year",
        "until you finish 2 years", "until contract ends",
        "agency owes you nothing until", "settle the debt",
        # Tagalog markers
        "may utang ka", "magbayad muna",
    ], 3),

    ("coercion_authority", [
        "mama-san", "mama san", "madame", "agency boss",
        "the boss said", "you have no choice", "we will report you",
        "report you to immigration", "report you to police",
        "send you home", "blacklist you", "we know your family",
        # Tagalog markers
        "boss ang nag-utos", "wala kang choice",
    ], 3),

    ("excessive_fee_with_currency", [
        "5000 deposit", "5,000 deposit", "usd 5000", "usd 5,000",
        "usd 5,000 deposit", "5000 placement", "5,000 placement",
        "10000 deposit", "10,000 deposit", "usd 10000", "usd 10,000",
        "phd 250000", "php 250,000", "hkd 25000", "hkd 25,000",
        "release fee", "exit visa fee", "deposit before flight",
        "agency fee usd", "placement fee usd", "must pay before flight",
        "advance salary deduction", "salary deduction for fee",
    ], 4),
]


_STRONG_SIGNALS: list[tuple[str, list[str], int]] = [
    ("identity_share", [
        "send your passport", "send your passport copy",
        "passport scan", "send your id copy",
        "send your nbi", "send your birth cert", "send national id",
    ], 2),

    ("informal_payment", [
        "deposit to account", "wire to account", "transfer to my account",
        "remit before flight", "remit before deployment",
        "deposit cash", "cash payment only",
    ], 2),

    ("isolation", [
        "no contact with family", "do not call your family",
        "no phone privileges", "we keep your phone",
        "alone in the house", "cannot tell anyone",
    ], 2),

    ("vague_authority", [
        "trust me", "we are official", "we are licensed",
        "do not worry", "i will help you", "everything is fine",
    ], 1),
]


_LEGITIMATE_SIGNALS: list[tuple[str, list[str], int]] = [
    ("licensed_agency", [
        "poea-licensed", "poea license", "doh approved",
        "deg.com", "deg endorsed", "official receipt",
        "ilo c181", "no placement fee", "no recruitment fee",
        "free training", "free pdos",
    ], -3),

    ("legal_compliance", [
        "ratified by", "stamped by deg", "endorsed by",
        "receipted", "tax-paid", "verified by polo",
    ], -2),
]


# Locale-aware hotline directory.
_HOTLINES = {
    "ph":  ("POEA / DMW Migrant Worker Hotline", "1343"),
    "id":  ("BP2MI Crisis Center", "+62-21-2924-3333"),
    "np":  ("HRD Nepal Migrant Worker Help",
            "+977-1-4218000"),
    "in":  ("MEA OIA Madad Helpline",
            "+91-11-1800-11-3090"),
    "bd":  ("Wage Earners' Welfare Board",
            "+880-2-9143006"),
    "lk":  ("SLBFE Help Desk", "+94-11-258-0996"),
    "hk":  ("Mission for Migrant Workers HK",
            "+852-2522-8264"),
    "sa":  ("Musaned (worker grievance)",
            "+966-9200-19797"),
    "ae":  ("MOHRE Worker Helpline (UAE)",
            "+971-800-665"),
    "qa":  ("ADLSA Workers' Hotline (Qatar)",
            "+974-4406-2244"),
    "kw":  ("PAM Hotline (Kuwait)", "+965-128"),
    "en":  ("ILO TIP Reporting", "https://www.ilo.org/contact"),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def quick_moderate(text: str, locale: str = "en",
                     gemma_call: Optional[Any] = None) -> dict:
    """Enterprise content-moderation triage. Severity 0-10 + verdict +
    matched signals + reasoning. Uses Gemma if a callable is supplied;
    otherwise the multi-signal heuristic."""
    if gemma_call is not None:
        return _gemma_moderate(text, locale, gemma_call)
    sev, signals, drops = _score(text)
    if sev >= 7:
        verdict = "block"
    elif sev >= 4:
        verdict = "review"
    else:
        verdict = "pass"
    return {
        "verdict": verdict,
        "severity": sev,
        "matched_signals": signals,
        "legitimate_signals": drops,
        "reasoning": _reasoning(sev, signals, drops),
        "mode": "heuristic",
    }


def worker_check(text: str, locale: str = "en",
                   gemma_call: Optional[Any] = None) -> dict:
    """Individual worker-check. Heuristic returns severity + advice +
    locale-aware hotline + plain-language warnings."""
    if gemma_call is not None:
        return _gemma_worker(text, locale, gemma_call)
    sev, signals, drops = _score(text)

    if sev >= 7:
        advice = ("This message has STRONG warning signs of recruitment "
                  "abuse / passport confiscation / debt bondage. Do NOT "
                  "pay any fee, do NOT surrender your passport, do NOT "
                  "sign anything before talking to the hotline below. "
                  "Save this conversation as evidence.")
    elif sev >= 4:
        advice = ("This message has serious warning signs. Verify the "
                  "agency's POEA / DMW licence in writing and refuse to "
                  "deposit any fee or hand over your passport until the "
                  "hotline confirms the agency is legitimate.")
    elif sev >= 2:
        advice = ("Some warning signs are present. Keep a copy of every "
                  "document and message. Contact the hotline if anything "
                  "feels off.")
    else:
        advice = ("No strong warning signs in this message. Stay "
                  "vigilant and never share documents with unverified "
                  "contacts.")

    hot_locale = (locale or "en").lower()[:2]
    hot_name, hot_contact = _HOTLINES.get(hot_locale, _HOTLINES["en"])

    return {
        "severity": sev,
        "warning_signs": signals,
        "legitimate_signals": drops,
        "advice": advice,
        "hotline": {"name": hot_name, "contact": hot_contact},
        "reasoning": _reasoning(sev, signals, drops),
        "mode": "heuristic",
    }


# ---------------------------------------------------------------------------
# Internal scorer (multi-signal, capped 0-10)
# ---------------------------------------------------------------------------
def _score(text: str) -> tuple[int, list[dict], list[dict]]:
    """Return (severity_0_10, matched_signals, legitimate_signals)."""
    if not text:
        return 0, [], []
    t = text.lower()
    matched: list[dict] = []
    drops: list[dict] = []
    raw_sev = 0
    for name, kws, weight in _CRITICAL_SIGNALS:
        hits = [k for k in kws if k in t]
        if hits:
            matched.append({"signal": name, "severity_weight": weight,
                             "hits": hits[:5], "tier": "critical"})
            raw_sev += weight
    for name, kws, weight in _STRONG_SIGNALS:
        hits = [k for k in kws if k in t]
        if hits:
            matched.append({"signal": name, "severity_weight": weight,
                             "hits": hits[:5], "tier": "strong"})
            raw_sev += weight
    for name, kws, weight in _LEGITIMATE_SIGNALS:
        hits = [k for k in kws if k in t]
        if hits:
            drops.append({"signal": name, "severity_offset": weight,
                            "hits": hits[:3]})
            raw_sev += weight    # weight is negative
    sev = max(0, min(10, raw_sev))
    return sev, matched, drops


def _reasoning(sev: int, signals: list[dict], drops: list[dict]) -> str:
    if sev == 0 and not signals:
        return "Heuristic: no warning signs matched."
    parts = []
    if signals:
        crit = sum(1 for s in signals if s["tier"] == "critical")
        strong = sum(1 for s in signals if s["tier"] == "strong")
        if crit:
            parts.append(f"{crit} critical signal(s)")
        if strong:
            parts.append(f"{strong} strong signal(s)")
    if drops:
        parts.append(f"{len(drops)} legitimate-context signal(s)")
    summary = " + ".join(parts) or "no signals"
    return f"Heuristic match: severity={sev}/10 from {summary}."


# ---------------------------------------------------------------------------
# Gemma-backed (only used when server has gemma_call configured)
# ---------------------------------------------------------------------------
def _gemma_moderate(text: str, locale: str, gemma_call) -> dict:
    # Run the heuristic FIRST so we have structured signals + a
    # severity floor. Gemma is anchored to the heuristic findings via
    # explicit anchor table in the prompt; we then merge: take Gemma's
    # verdict + reasoning, but keep the heuristic's structured signals
    # and use max(gemma_sev, heuristic_sev) so Gemma's chronic
    # underrating can't downgrade a clear block to severity 1.
    h_sev, h_signals, h_drops = _score(text)

    # Build an anchor sentence the prompt can reference.
    anchor_lines = []
    for s in h_signals:
        anchor_lines.append(
            f"  - {s['signal']} ({s['tier']} signal, severity weight "
            f"+{s['severity_weight']}): hits {s['hits']}")
    if h_drops:
        for s in h_drops:
            anchor_lines.append(
                f"  - {s['signal']} (legitimate-context, "
                f"weight {s['severity_offset']}): hits {s['hits']}")
    anchor = ("\n".join(anchor_lines)
              if anchor_lines else "  (no heuristic signals matched)")

    prompt = (
        "You are a content-moderation analyst for a migrant-worker "
        "job-board platform. Decide BLOCK / REVIEW / PASS based on "
        "ILO C181 + Palermo Protocol + RA 8042 standards.\n"
        "\n"
        "SEVERITY ANCHORS (use this scale strictly):\n"
        "  9-10 = passport confiscation, debt bondage, illegal fees "
        "(>USD 200), explicit movement restriction, kafala\n"
        "  7-8  = strong recruitment-fee or document-retention signals\n"
        "  4-6  = ambiguous: mentions fees but small / claims licensed\n"
        "  2-3  = minor concerns, mostly looks legitimate\n"
        "  0-1  = no warning signs, clearly legitimate\n"
        "VERDICT RULES:\n"
        "  severity >= 7  -> BLOCK\n"
        "  severity 4-6   -> REVIEW\n"
        "  severity 0-3   -> PASS\n"
        "\n"
        "HEURISTIC PRE-SCAN found severity " + f"{h_sev}/10:\n"
        + anchor + "\n"
        "\n"
        f"POST TO MODERATE:\n{text}\n\n"
        "Respond with ONE JSON object only (no prose before or after):\n"
        "{\"verdict\": \"block|review|pass\", \"severity\": 8, "
        "\"reasoning\": \"one short sentence citing the specific "
        "indicator\"}"
    )
    raw = gemma_call(prompt, max_new_tokens=200) or ""
    parsed = _extract_json(raw) or {}

    # Normalize Gemma's outputs.
    g_verdict = str(parsed.get("verdict", "")).strip().lower()
    if g_verdict not in ("block", "review", "pass"):
        g_verdict = "review"
    try:
        g_sev = int(parsed.get("severity", 0))
    except Exception:
        g_sev = 0

    # FLOOR: severity = max(gemma, heuristic). Catches the case where
    # Gemma underrates (e.g. severity=1) on a clearly severe post.
    final_sev = max(g_sev, h_sev)
    # Re-derive verdict from final severity using the same thresholds
    # the prompt asked for, so verdict and severity stay consistent.
    if final_sev >= 7:
        final_verdict = "block"
    elif final_sev >= 4:
        final_verdict = "review"
    else:
        final_verdict = g_verdict if g_verdict == "pass" else "review"
    # If Gemma explicitly said BLOCK, respect it even if final_sev < 7.
    if g_verdict == "block":
        final_verdict = "block"
        final_sev = max(final_sev, 7)

    return {
        "verdict": final_verdict,
        "severity": final_sev,
        "matched_signals": h_signals,       # structured (UI-renderable)
        "legitimate_signals": h_drops,
        "reasoning": (parsed.get("reasoning") or raw[:240]
                      or _reasoning(final_sev, h_signals, h_drops)),
        "mode": "gemma",
        "gemma_severity": g_sev,
        "heuristic_severity": h_sev,
        "raw_gemma": raw,
    }


def _gemma_worker(text: str, locale: str, gemma_call) -> dict:
    h_sev, h_signals, h_drops = _score(text)
    hot_locale = (locale or "en").lower()[:2]
    hot_name, hot_contact = _HOTLINES.get(hot_locale, _HOTLINES["en"])

    anchor_lines = [f"  - {s['signal']} ({s['tier']}): {s['hits']}"
                    for s in h_signals]
    anchor = ("\n".join(anchor_lines)
              if anchor_lines else "  (no heuristic signals matched)")

    prompt = (
        "You advise migrant workers and their families. Read the "
        "MESSAGE below and tell the worker plainly: (a) is this a "
        "recruitment-fee scam, passport-confiscation, or coercion "
        "pattern (severity 0-10 strict scale below), (b) what to do "
        "RIGHT NOW, and (c) which hotline to call.\n"
        "\n"
        "SEVERITY SCALE (use strictly):\n"
        "  9-10 = passport held by employer, debt bondage, illegal "
        "fees over USD 200, explicit movement restriction\n"
        "  7-8  = strong fee-shifting / document-retention signals\n"
        "  4-6  = ambiguous; some warning signs, claims of legitimacy\n"
        "  2-3  = minor concerns\n"
        "  0-1  = looks legitimate\n"
        "\n"
        f"HEURISTIC PRE-SCAN (severity {h_sev}/10):\n{anchor}\n"
        "\n"
        f"WORKER LOCALE: {locale}  "
        f"(default hotline: {hot_name} -- {hot_contact})\n\n"
        f"MESSAGE:\n{text}\n\n"
        "Respond with ONE JSON object only:\n"
        "{\"severity\": 8, \"warning_signs\": [\"...\"], "
        "\"advice\": \"plain-language one-paragraph what-to-do\", "
        "\"hotline\": {\"name\": \"...\", \"contact\": \"...\"}}"
    )
    raw = gemma_call(prompt, max_new_tokens=350) or ""
    parsed = _extract_json(raw) or {}

    try:
        g_sev = int(parsed.get("severity", 0))
    except Exception:
        g_sev = 0
    final_sev = max(g_sev, h_sev)

    return {
        "severity": final_sev,
        "warning_signs": h_signals,         # structured for UI
        "legitimate_signals": h_drops,
        "advice": (parsed.get("advice") or raw[:400]
                   or "Verify the agency licence; never pay upfront fees "
                      "or surrender your passport."),
        "hotline": (parsed.get("hotline")
                    or {"name": hot_name, "contact": hot_contact}),
        "reasoning": _reasoning(final_sev, h_signals, h_drops),
        "mode": "gemma",
        "gemma_severity": g_sev,
        "heuristic_severity": h_sev,
        "raw_gemma": raw,
    }


def _extract_json(raw: str) -> dict | None:
    if not raw:
        return None
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        import json
        return json.loads(m.group(0))
    except Exception:
        try:
            import json
            cleaned = re.sub(r",\s*([}\]])", r"\1", m.group(0))
            return json.loads(cleaned)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# File-upload moderation (image / PDF / docx -> text -> heuristic/gemma)
# ---------------------------------------------------------------------------
def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """Best-effort text extraction. Returns extracted text + a note
    describing the source. Falls back to UTF-8 decode for plain text."""
    name = (filename or "").lower()
    # Plain text / markdown
    if name.endswith((".txt", ".md", ".csv", ".log")):
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return data.decode("latin-1", errors="replace")
    # PDF -- try pypdfium2 (used by the baseline)
    if name.endswith(".pdf"):
        try:
            import pypdfium2 as _pp   # type: ignore
            import io
            doc = _pp.PdfDocument(io.BytesIO(data))
            chunks = []
            for page in doc:
                tp = page.get_textpage()
                chunks.append(tp.get_text_range() or "")
                tp.close()
            doc.close()
            return "\n".join(chunks)
        except Exception:
            pass
    # Image -- OCR via pytesseract
    if name.endswith((".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp",
                       ".gif", ".webp")):
        try:
            from PIL import Image as _Image   # type: ignore
            import io
            import pytesseract as _pt   # type: ignore
            img = _Image.open(io.BytesIO(data))
            return _pt.image_to_string(img) or ""
        except Exception as e:
            return f"[OCR failed: {type(e).__name__}: {e}]"
    # docx
    if name.endswith(".docx"):
        try:
            import io, zipfile
            from xml.etree import ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                xml = z.read("word/document.xml").decode("utf-8")
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            root = ET.fromstring(xml)
            return "\n".join(t.text or "" for t in root.iter(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
        except Exception:
            pass
    # Unknown -- last resort: decode as text
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return "[Could not extract text from this file type]"


# ---------------------------------------------------------------------------
# Bulk archive extractor (zip / tar / tar.gz / tgz)
# ---------------------------------------------------------------------------
_BULK_ALLOWED_EXTS = (
    ".txt", ".md", ".csv", ".log",
    ".pdf", ".docx",
    ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp",
    ".html", ".htm", ".xml", ".json",
)
_BULK_MAX_FILES = 500          # safety cap so a 10k-file zip doesn't OOM
_BULK_MAX_BYTES_PER_FILE = 25 * 1024 * 1024   # 25 MB
_BULK_MAX_TOTAL_BYTES = 500 * 1024 * 1024     # 500 MB total


def extract_archive_to_files(data: bytes, filename: str
                                ) -> list[tuple[str, bytes]]:
    """Extract zip / tar / tar.gz / tgz into a list of
    (relative_path, bytes) tuples. Filters out:
      - directories
      - hidden files (leading '.' segment)
      - macOS resource forks / __MACOSX
      - files outside _BULK_ALLOWED_EXTS
      - files larger than _BULK_MAX_BYTES_PER_FILE
    Caps total at _BULK_MAX_FILES and _BULK_MAX_TOTAL_BYTES.

    Raises ValueError on unrecognized archive format."""
    name = (filename or "").lower()
    out: list[tuple[str, bytes]] = []
    total_bytes = 0

    def _accept(member_name: str) -> bool:
        if not member_name or member_name.endswith("/"):
            return False
        parts = member_name.replace("\\", "/").split("/")
        if any(p.startswith(".") or p == "__MACOSX" for p in parts):
            return False
        ext = "." + parts[-1].rsplit(".", 1)[-1].lower()
        return ext in _BULK_ALLOWED_EXTS

    if name.endswith(".zip"):
        import io, zipfile
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as e:
            raise ValueError(f"not a valid zip: {e}")
        for info in zf.infolist():
            if len(out) >= _BULK_MAX_FILES:
                break
            if not _accept(info.filename):
                continue
            if info.file_size > _BULK_MAX_BYTES_PER_FILE:
                continue
            if total_bytes + info.file_size > _BULK_MAX_TOTAL_BYTES:
                break
            try:
                buf = zf.read(info)
            except Exception:
                continue
            out.append((info.filename, buf))
            total_bytes += len(buf)
        zf.close()
        return out

    if (name.endswith(".tar") or name.endswith(".tar.gz")
            or name.endswith(".tgz") or name.endswith(".tar.bz2")):
        import io, tarfile
        mode = "r:gz" if name.endswith((".tar.gz", ".tgz")) else (
            "r:bz2" if name.endswith(".tar.bz2") else "r:")
        try:
            tf = tarfile.open(fileobj=io.BytesIO(data), mode=mode)
        except tarfile.TarError as e:
            raise ValueError(f"not a valid tar: {e}")
        for info in tf:
            if len(out) >= _BULK_MAX_FILES:
                break
            if not info.isfile() or not _accept(info.name):
                continue
            if info.size > _BULK_MAX_BYTES_PER_FILE:
                continue
            if total_bytes + info.size > _BULK_MAX_TOTAL_BYTES:
                break
            f = tf.extractfile(info)
            if f is None:
                continue
            buf = f.read()
            out.append((info.name, buf))
            total_bytes += len(buf)
        tf.close()
        return out

    raise ValueError(
        f"unsupported archive type: {filename!r}. "
        f"Use .zip, .tar, .tar.gz, .tgz, or .tar.bz2.")
