"""Redact PII from raw content (social media posts, messages, documents)
to produce safe-to-publish examples for the Duecare hackathon submission.

Per `.claude/rules/10_safety_gate.md`, the submission ships these to the
public, so leaks are P0. This tool:

  1. Detects PII via deterministic regex + heuristic patterns (no ML, no
     network calls, no embedding model — defensible and reproducible).
  2. Replaces with stable composite-tag placeholders ([NAME-A],
     [PHONE-1], [PASSPORT-PH-1], etc.).
  3. Optionally fills the placeholders with composite content (Maria
     Santos (composite), +63-555-0123 (synthetic 555 prefix), etc.) for
     a publish-ready example.
  4. Emits an audit log with sha256 of every original substring it
     redacted — never the plaintext.

Usage:
    # Redact a single string (stdin)
    echo "Maria Santos +63 917 555 1234 lost her passport AB1234567" \\
        | python scripts/redact_pii.py

    # Redact a file
    python scripts/redact_pii.py --input raw_post.txt --output redacted.txt

    # Generate publish-ready synthetic equivalent
    python scripts/redact_pii.py --input raw.txt --synthesize

    # Dry run: show what WOULD be redacted, but don't write
    python scripts/redact_pii.py --input raw.txt --dry-run

    # Bulk: scan all .json + .py + .md in a tree, report any PII
    python scripts/redact_pii.py --scan path/to/dir
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


# ------------------------------------------------------------------
# Detection patterns (deterministic regex; precision over recall —
# false negatives are OK because this is a triage tool not a final
# gate, and false positives are noise).
# ------------------------------------------------------------------

# Order matters: more-specific patterns must run BEFORE more-general
# ones so a passport like "AB1234567" isn't half-eaten by the phone
# regex. Insertion order is preserved in py3.7+.
PATTERNS: dict[str, str] = {
    # Email addresses — most specific, run first
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    # Passport numbers — alphabetic prefix + digits, OR standalone in
    # passport-context. Run before phone/national_id to avoid stealing.
    "passport": (
        r"\b[A-Z]{1,3}\d{6,9}\b"
        r"|\b(?:passport|paspor|paspoort|pasaporte)[\s:#]*\d{7,9}\b"
    ),
    # National IDs — only matched in explicit context (NID:, KTP:, etc.)
    # to avoid capturing arbitrary long digit runs.
    "national_id": (
        r"\b(?:NID|KTP|SSS|UMID|TIN|PhilSys)[\s:#]*\d{8,17}\b"
    ),
    # Bank / IBAN — must start with country code + 2 digits
    "iban": r"\b[A-Z]{2}\d{2}[A-Z0-9]{8,30}\b",
    # Credit-card-shaped — explicit 16-digit pattern with separators
    "credit_card": r"\b(?:\d{4}[-\s]){3}\d{4}\b",
    # Dates of birth — only when contextual ('DOB:', 'born:', etc.)
    "dob": (
        r"\b(?:DOB|D\.O\.B|date\s+of\s+birth|born)[\s:]+"
        r"\d{1,2}[\-/\.]\d{1,2}[\-/\.](?:19|20)\d{2}\b"
    ),
    # Specific street addresses (number + street suffix)
    "address": (
        r"\b\d{1,5}\s+[A-Z][a-zA-Z]+\s+(?:Rd|Road|St|Street|Ave|"
        r"Avenue|Blvd|Boulevard|Lane|Ln|Way|Drive|Dr|Terrace|"
        r"Ter|Court|Ct|Place|Pl|Highway|Hwy)\b"
    ),
    # URLs to specific cases/profiles (filter common public sites)
    "specific_url": (
        r"https?://(?!(?:www\.)?(?:ilo\.org|poea\.gov\.ph|"
        r"bp2mi\.go\.id|dofe\.gov\.np|bmet\.gov\.bd|slbfe\.lk|"
        r"polarisproject\.org|ijm\.org|mfmw\.com\.hk|wikipedia\.org|"
        r"hk\.lexum\.com|elaws\.gov\.ph|hklii\.hk))"
        r"[A-Za-z0-9./_\-?=&%#]+/(?:case|profile|user|status|post|p)/[A-Za-z0-9_\-]+"
    ),
    # Social media handles (@username)
    "social_handle": (
        r"(?<![A-Za-z0-9_./])@([A-Za-z0-9_]{3,30})(?![A-Za-z0-9_])"
    ),
    # Phone numbers — runs LAST so passports/IBANs/NIDs already gone.
    # Requires either a leading + (intl) or sentence-boundary-isolated
    # 10-digit US-format. Min 9 digits total to avoid 4-digit years.
    "phone": (
        r"\+\d{1,3}[\s\-\(\)]*\d{1,4}[\s\-\(\)]*\d{2,4}[\s\-\(\)]*\d{2,5}"
        r"|(?<![\d-])\b\d{3}[-\s]\d{3}[-\s]\d{4}\b(?![\d-])"
    ),
}

# Names: list of common given names + surnames in target countries.
# A real PII detector would use spaCy NER; this list-based approach is
# defensible (false positives reviewable) and dependency-free.
COMMON_GIVEN_NAMES = {
    # Filipino/Filipina (most common per PSA)
    "Maria", "Marie", "Anna", "Sarah", "Angel", "Joy", "Ana", "Luz",
    "Mary", "Rosa", "Carmen", "Cristina", "Jocelyn", "Joanne",
    "Juan", "Jose", "Mark", "John", "Michael", "Joshua", "Christian",
    # Indonesian
    "Siti", "Nur", "Sri", "Dewi", "Indah", "Rini", "Wati", "Yuni",
    "Budi", "Agus", "Bambang", "Ahmad", "Muhammad", "Andi",
    # Nepalese
    "Sita", "Gita", "Maya", "Sushila", "Kamala", "Bishnu", "Ram",
    "Ramesh", "Bishnu", "Krishna", "Hari", "Kumar",
    # Bangladeshi
    "Rafiqul", "Abdul", "Mohammed", "Md", "Khaleda", "Fatima",
    "Rashida", "Nasreen", "Salma", "Karim", "Rahim",
    # Sri Lankan
    "Kumari", "Rani", "Pradeep", "Saman", "Ranjan", "Nimal",
    # Common international
    "Anna", "Sara", "Tom", "James", "David", "Alex",
}

COMMON_SURNAMES = {
    # Filipino
    "Santos", "Reyes", "Cruz", "Bautista", "Garcia", "Aquino",
    "Mendoza", "Lopez", "Ramos", "Perez",
    # Indonesian
    "Wijaya", "Susanto", "Kurniawan", "Setiawan", "Pratama",
    # Nepalese
    "Tamang", "Sherpa", "Gurung", "Magar", "Rai", "Limbu",
    # Bangladeshi
    "Islam", "Ahmed", "Khan", "Rahman", "Chowdhury", "Hossain",
    # Sri Lankan
    "Silva", "Perera", "Fernando", "Wickramasinghe",
    # HK Chinese (common)
    "Wong", "Lee", "Chan", "Cheung", "Lam", "Lim", "Liu", "Wu",
    # Other
    "Smith", "Brown", "Lopez",
}

# Allowed phone prefixes that are PUBLIC NGO/regulator hotlines.
# If a number starts with one of these, do NOT redact (it's intended).
PUBLIC_HOTLINE_PREFIXES = (
    "+63-2-8721-1144",      # POEA
    "+852-2522-8264",       # MfMW HK
    "+852-2823-8500",       # PH Consul HK
    "+62-21-2924-4800",     # BP2MI
    "+852-2997-2832",       # IMWU HK
    "+977-1-4-433-401",     # DoFE Nepal
    "+977-1-4441-122",      # PNCC
    "+977-1-4-440-141",     # HRD Nepal
    "+966-11-450-5555",     # PH Embassy Riyadh
    "+966-50-303-7110",     # Migrante Saudi
    "+965-2253-0871",       # PH Embassy Kuwait
    "+965-2245-3636",       # KSHR
    "+961-1-983-100",       # PH Embassy Beirut
    "+961-71-700-844",      # ARM Beirut
    "+966-11-488-2800",     # ID Embassy Riyadh
    "+62-21-7984-735",      # SBMI
    "+961-5-924-682",       # ID Embassy Beirut
    "+62-21-228-29-22",     # Migrant Care
    "+94-11-263-9277",      # SLBFE
    "+961-5-959-925",       # SL Embassy Beirut
    "+880-2-984-9925",      # BMET
    "+966-11-419-7600",     # BD Embassy Riyadh
    "+880-2-9117-101",      # WARBE
    "+965-2531-7203",       # BD Embassy Kuwait
    "1-866-487-9243",       # Polaris (US National Trafficking Hotline)
    "+66 2 245 2380",       # Issara Institute
)

# RFC 2606 / RFC 5737 / E.164 reserved test ranges (clearly synthetic)
SYNTHETIC_PHONE_RANGES = (
    "+1-555-0",   # US 555-01XX reserved range
    "555-555-",
    "+63-555-",   # arbitrary synthetic with 555
)


def _is_public_hotline(phone: str) -> bool:
    """Check if a phone number matches a known public hotline prefix."""
    normalized = re.sub(r"[\s\-\(\)]", "", phone)
    for prefix in PUBLIC_HOTLINE_PREFIXES:
        prefix_norm = re.sub(r"[\s\-\(\)]", "", prefix)
        if normalized.startswith(prefix_norm[:8]):  # match first 8 digits
            return True
    return False


def _is_synthetic_phone(phone: str) -> bool:
    """Check if the phone is clearly in a reserved synthetic range."""
    return any(syn in phone for syn in SYNTHETIC_PHONE_RANGES)


def _hash_short(s: str) -> str:
    """Return a short SHA-256 prefix for the audit log."""
    return hashlib.sha256(s.encode()).hexdigest()[:12]


# ------------------------------------------------------------------
# Composite synthetic data — used when --synthesize replaces tags
# ------------------------------------------------------------------

SYNTHETIC_FILL = {
    "name": [
        "Maria Santos (composite)",
        "Sita Tamang (composite)",
        "Ramesh Khadka (composite)",
        "Nur Aini (composite)",
        "Mohammed Hossain (composite)",
        "Anna Reyes (composite)",
    ],
    "phone": [
        "+63-555-0123 (synthetic)",
        "+852-555-0246 (synthetic)",
        "+62-555-0357 (synthetic)",
        "+977-555-0468 (synthetic)",
    ],
    "email": [
        "worker@example.invalid",
        "ngo-intake@example.invalid",
    ],
    "passport": [
        "AB1234567 (synthetic)",
        "CD7654321 (synthetic)",
    ],
    "national_id": [
        "1234567890123 (synthetic)",
    ],
    "address": [
        "[redacted street], Mid-Levels, HK (composite)",
        "[redacted barangay], Manila, PH (composite)",
        "[redacted street], Beirut, LB (composite)",
    ],
    "social_handle": [
        "@example_handle_1",
        "@example_handle_2",
    ],
    "specific_url": [
        "https://example.invalid/case/redacted",
    ],
    "iban": ["XX00 0000 0000 0000 (synthetic)"],
    "credit_card": ["4242-4242-4242-4242 (test card)"],
    "dob": ["DOB: [year only redacted, e.g., 1990]"],
}


# ------------------------------------------------------------------
# Core redaction
# ------------------------------------------------------------------

def redact(text: str, *, synthesize: bool = False) -> tuple[str, list[dict]]:
    """Redact PII from `text`. Returns (redacted_text, audit_log).

    audit_log entries: {category, sha256_short, position, length, action}
    Never includes the plaintext of the redacted span.
    """
    audit: list[dict] = []
    counters: dict[str, int] = defaultdict(int)
    fill_idx: dict[str, int] = defaultdict(int)
    out = text

    def _replacement(category: str, match_text: str) -> str:
        counters[category] += 1
        if synthesize:
            options = SYNTHETIC_FILL.get(category, [f"[{category.upper()}-{counters[category]}]"])
            v = options[fill_idx[category] % len(options)]
            fill_idx[category] += 1
            return v
        # Default: stable composite tag
        return f"[{category.upper()}-{counters[category]}]"

    # Apply patterns in order. Use sub with a function so we can audit.
    for category, pattern in PATTERNS.items():
        def _sub(m: re.Match, _cat=category) -> str:
            matched = m.group(0)
            # Whitelist exceptions
            if _cat == "phone":
                if _is_public_hotline(matched) or _is_synthetic_phone(matched):
                    return matched
            audit.append({
                "category":      _cat,
                "sha256_short":  _hash_short(matched),
                "position":      m.start(),
                "length":        len(matched),
                "action":        "synthesize" if synthesize else "redact",
            })
            return _replacement(_cat, matched)
        out = re.sub(pattern, _sub, out)

    # Names: detect "FirstName LastName" pairs where both parts are in
    # COMMON_GIVEN_NAMES / COMMON_SURNAMES. Skip if already labeled
    # (composite). Not perfect, but defensible for triage.
    name_re = re.compile(
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+([A-Z][a-z]+)\b"
    )
    def _name_sub(m: re.Match) -> str:
        full = m.group(0)
        # Skip if already-composite
        if "(composite)" in out[m.start(): m.end() + 20].lower():
            return full
        first = m.group(1).split()[0]
        last = m.group(2)
        if first in COMMON_GIVEN_NAMES and last in COMMON_SURNAMES:
            audit.append({
                "category":      "name",
                "sha256_short":  _hash_short(full),
                "position":      m.start(),
                "length":        len(full),
                "action":        "synthesize" if synthesize else "redact",
            })
            return _replacement("name", full)
        return full
    out = name_re.sub(_name_sub, out)
    return out, audit


# ------------------------------------------------------------------
# Bulk scan mode
# ------------------------------------------------------------------

def scan_tree(root: Path) -> dict:
    """Walk a directory tree, scan every text file for PII, return
    a summary dict {filepath: [audit entries]}."""
    EXTENSIONS = {".py", ".md", ".json", ".jsonl", ".html", ".txt", ".yaml", ".yml"}
    findings: dict[str, list[dict]] = {}
    for f in root.rglob("*"):
        if not f.is_file() or f.suffix not in EXTENSIONS:
            continue
        # Skip vendor / cache / build artifacts
        if any(part in {"__pycache__", "node_modules", ".git",
                          "_archive", "dist", "build"}
               for part in f.parts):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        _, audit = redact(text)
        if audit:
            findings[str(f.relative_to(root))] = audit
    return findings


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path,
                          help="Input text file (use stdin if omitted)")
    parser.add_argument("--output", type=Path,
                          help="Output file for redacted content (default: stdout)")
    parser.add_argument("--audit", type=Path,
                          help="Write audit log JSON to this path")
    parser.add_argument("--synthesize", action="store_true",
                          help="Replace tags with composite synthetic content")
    parser.add_argument("--dry-run", action="store_true",
                          help="Don't write anything; just show what would be redacted")
    parser.add_argument("--scan", type=Path,
                          help="Bulk-scan a directory; report findings per file")
    args = parser.parse_args()

    if args.scan:
        if not args.scan.is_dir():
            print(f"ERROR: --scan target is not a directory: {args.scan}", file=sys.stderr)
            return 2
        findings = scan_tree(args.scan)
        if not findings:
            print(f"OK — no PII signals found across {args.scan}")
            return 0
        print(f"Found PII signals in {len(findings)} files under {args.scan}:\n")
        for path, audit in sorted(findings.items()):
            cats = defaultdict(int)
            for entry in audit:
                cats[entry["category"]] += 1
            cats_str = ", ".join(f"{k}={v}" for k, v in sorted(cats.items()))
            print(f"  {path}  ({len(audit)} hits: {cats_str})")
        return 1

    if args.input:
        text = args.input.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    redacted, audit = redact(text, synthesize=args.synthesize)

    if args.dry_run:
        print(f"=== DRY RUN: would redact {len(audit)} item(s) ===")
        for entry in audit:
            print(f"  {entry['category']:14s} pos={entry['position']:6d} "
                    f"len={entry['length']:3d} sha={entry['sha256_short']} "
                    f"action={entry['action']}")
        return 0

    if args.output:
        args.output.write_text(redacted, encoding="utf-8")
        print(f"Wrote redacted content to {args.output} ({len(audit)} items redacted)",
                file=sys.stderr)
    else:
        sys.stdout.write(redacted)

    if args.audit:
        args.audit.write_text(json.dumps(audit, indent=2), encoding="utf-8")
        print(f"Wrote audit log to {args.audit}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
