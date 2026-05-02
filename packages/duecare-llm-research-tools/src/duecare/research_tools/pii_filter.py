"""PII filter for external-research tool queries.

Hard rule: nothing identifying an individual leaves the local process.
Allowed: organisation names, jurisdictions, ISO country codes, statute
numbers, currency amounts, generic policy terms.
Rejected: person names (heuristic), passport numbers, phone numbers,
email addresses, financial account numbers.

Implementations MUST call `PIIFilter.validate(query_dict)` before any
upstream HTTP request. Violations raise `PIIRejectionError` which the
harness catches and logs as a finding.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable


class PIIRejectionError(ValueError):
    """Raised when a research-tool query contains PII the filter
    refuses to release to an external service."""


# Patterns that are CLEARLY PII -- reject outright.
_PII_PATTERNS = [
    ("email",
     re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("passport_number",
     re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")),
    ("phone_intl",
     re.compile(r"\+\d{1,3}[\s\-.]?\(?\d{1,4}\)?[\s\-.]?"
                 r"\d{2,4}[\s\-.]?\d{2,4}")),
    ("phone_ph_mobile",
     re.compile(r"(?<!\d)0?9\d{9}(?!\d)")),
    ("financial_account",
     re.compile(r"(?:account|acct|a/c|iban)[:#\s]*[A-Z0-9\-]{6,}",
                 re.IGNORECASE)),
]

# Honorifics that strongly signal a person name follows.
_HONORIFICS = (
    "mr ", "mrs ", "ms ", "miss ", "dr ", "atty ", "engr ",
    "hajj ", "haji ", "sister ", "brother ", "father ",
)


@dataclass
class PIIFilter:
    """Configurable PII filter. Pass a list of allowed organisation
    names if you want to whitelist specific entities (e.g. publicly-
    named recruitment agencies in a government registry)."""

    allow_org_names: list[str] = field(default_factory=list)
    """Org names that bypass the person-name heuristic. Useful for
    publicly-named recruitment agencies that happen to look like
    person names."""

    reject_capitalised_pairs: bool = True
    """If True, reject 'First Last' style pairs by default. Set to
    False if your queries deliberately include public org names that
    look like person names AND none of those names are in
    allow_org_names."""

    def validate(self, query: dict) -> dict:
        """Run every value through the filter. Returns the query dict
        unchanged on success; raises PIIRejectionError on failure."""
        if not isinstance(query, dict):
            raise PIIRejectionError("query must be a dict")
        for k, v in query.items():
            if v is None:
                continue
            if isinstance(v, (list, tuple, set)):
                for item in v:
                    self._check_value(str(k), str(item))
            elif isinstance(v, dict):
                self.validate(v)
            else:
                self._check_value(str(k), str(v))
        return query

    def _check_value(self, field_name: str, value: str) -> None:
        if not value or len(value) < 2:
            return
        v = value.strip()
        for kind, rx in _PII_PATTERNS:
            if rx.search(v):
                raise PIIRejectionError(
                    f"field {field_name!r} contains "
                    f"{kind}-shaped value: {v[:30]!r}")
        # Honorific check
        v_low = " " + v.lower() + " "
        for hon in _HONORIFICS:
            if hon in v_low:
                raise PIIRejectionError(
                    f"field {field_name!r} contains honorific "
                    f"({hon.strip()!r}) -- looks like a person name")
        # Capitalised-pair heuristic for plausible person names.
        if self.reject_capitalised_pairs:
            if self._looks_like_person_name(v):
                if v.lower() not in {n.lower() for n in self.allow_org_names}:
                    raise PIIRejectionError(
                        f"field {field_name!r} value {v[:30]!r} looks "
                        f"like a person name. Add it to "
                        f"PIIFilter.allow_org_names if it's actually "
                        f"a public org.")

    def _looks_like_person_name(self, v: str) -> bool:
        """Two- or three-word run of capitalised tokens with NO suffix
        like Inc / Corp / LLC / Ltd / Manpower / Recruitment."""
        tokens = v.split()
        if not (2 <= len(tokens) <= 4):
            return False
        if not all(t[:1].isupper() for t in tokens if t):
            return False
        # Org markers
        org_markers = {"inc", "inc.", "corp", "corp.", "corporation",
                       "llc", "ltd", "ltd.", "limited", "pte", "co",
                       "manpower", "recruitment", "recruiters",
                       "services", "agency", "agencies", "group",
                       "holdings", "international", "intl", "global",
                       "enterprise", "enterprises", "solutions"}
        if any(t.lower().rstrip(",.") in org_markers for t in tokens):
            return False
        return True
