"""Validate every workbench HTML page against the rules in
`.claude/rules/70_workbench_ui_primitives.md`.

Catches drift like:
 - mutation pages without the shared activity-log helper
 - bespoke `wbLog()` re-implementations that should migrate
 - mutation pages with no trust-boundary disclosure
 - pages that POST/PUT/DELETE without an activity log host

Exits non-zero if any finding has level=blocking. Designed to run
inside `make verify-all` alongside `validate_public_surface.py`.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / (
    "packages/duecare-llm-chat/src/duecare/chat/static"
)


# Files intentionally excluded from the rules:
#   - partials/helpers (prefixed _)
#   - http-equiv redirect stubs
#   - pure marketing/showcase pages (read-only, no mutation)
EXCLUDE_PREFIXES = ("_",)
SHOWCASE_PREFIXES = ("showcase-",)

# Pages that are inherently read-only viewers (lists / dumps / static
# information) and therefore exempt from "must have activity log".
# When promoting one of these to do mutations, remove it from this set
# AND wire the helper.
READ_ONLY_PAGES = {
    "all-tools.html",
    "getting-started.html",
    "hotlines.html",
    "harness.html",
    "logs.html",
    "rag-corpus.html",
    "rag-graph.html",
    "grep-rules.html",
    "tools.html",
    "online.html",
    "persona.html",
    "status.html",
}


@dataclass
class Finding:
    path: Path
    rule: str
    level: str  # "blocking" | "warn" | "info"
    message: str


@dataclass
class Audit:
    findings: list[Finding] = field(default_factory=list)

    def add(self, path: Path, rule: str, level: str, msg: str) -> None:
        self.findings.append(Finding(path, rule, level, msg))

    def by_level(self, level: str) -> list[Finding]:
        return [f for f in self.findings if f.level == level]


def _is_redirect_stub(text: str) -> bool:
    return 'http-equiv="refresh"' in text or "http-equiv='refresh'" in text


def _is_marketing(name: str) -> bool:
    return any(name.startswith(p) for p in SHOWCASE_PREFIXES)


def _has_mutation(text: str) -> bool:
    """Page makes at least one POST/PUT/DELETE."""
    return any(
        f"method:'{m}'" in text
        or f'method: "{m}"' in text
        or f'method:"{m}"' in text
        for m in ("POST", "PUT", "DELETE")
    )


def _checks(path: Path, audit: Audit) -> None:
    name = path.name
    if any(name.startswith(p) for p in EXCLUDE_PREFIXES):
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if _is_redirect_stub(text):
        return
    if _is_marketing(name):
        return

    # Rule 6: shared chrome MUST be present
    if "_chrome.css" not in text:
        audit.add(path, "rule_6_chrome", "blocking",
                   "page does not link /static/_chrome.css")

    # Rule 6: shared nav MUST be loaded
    if "_nav.js" not in text:
        audit.add(path, "rule_6_chrome", "blocking",
                   "page does not load /static/_nav.js")

    has_mutation = _has_mutation(text)
    has_actlog = "_activity_log.js" in text

    # Rule 1: every mutation page MUST load the shared
    # activity-log helper.
    if has_mutation and not has_actlog and name not in READ_ONLY_PAGES:
        audit.add(path, "rule_1_activity_log", "blocking",
                   "mutation page missing <script src=\"/static/_activity_log.js\">")

    # Bespoke wbLog/logEvent: warn-level (migration target).
    if re.search(r"function\s+(wbLog|logEvent)\b", text):
        audit.add(path, "rule_1_activity_log", "warn",
                   "bespoke wbLog/logEvent function -- migrate to "
                   "window.dcActivityLog.attach")

    # Rule 7: pages that mutate MUST surface a trust-boundary banner.
    if has_mutation and "wb-trust" not in text and "Trust boundary" not in text:
        if name not in READ_ONLY_PAGES:
            audit.add(path, "rule_7_trust_boundary", "warn",
                       "mutation page missing trust-boundary banner")

    # innerHTML on network/user content is a smell. Only flag when the
    # RHS contains string concatenation or a template literal (the
    # XSS surface), not bare clearing assignments like `host.innerHTML = ''`.
    inner_writes = re.findall(r"\.innerHTML\s*=\s*([^;]+)", text)
    suspicious = 0
    for w in inner_writes:
        w = w.strip()
        if w in ("''", '""'):
            continue
        if "+" in w or "${" in w or w.startswith("`"):
            suspicious += 1
    if suspicious >= 5:
        audit.add(path, "rule_1_activity_log", "warn",
                   f"{suspicious} innerHTML writes with concatenation/template "
                   "-- prefer DOM construction")

    # Rule 8: status.html MUST NOT actually CALL Gemma on page load.
    # Look for fetch() invocations of heavy endpoints, not display text.
    if name == "status.html":
        heavy_fetches = re.findall(
            r"""fetch\(\s*['"`](/api/chat/send|/api/grade-deep[^'"`]*)['"`]""",
            text,
        )
        if heavy_fetches:
            audit.add(path, "rule_8_status_lightweight", "blocking",
                       f"status.html issues fetch() to heavy endpoint(s): "
                       f"{heavy_fetches}")


def main() -> int:
    audit = Audit()
    files = sorted(STATIC.glob("*.html"))
    for f in files:
        _checks(f, audit)
    blocking = audit.by_level("blocking")
    warn = audit.by_level("warn")
    info = audit.by_level("info")

    print(f"=== Workbench UI primitives audit ===")
    print(f"Scanned {len(files)} HTML files under {STATIC}")
    print(f"  blocking={len(blocking)}  warn={len(warn)}  info={len(info)}")
    print()

    by_rule: dict[str, list[Finding]] = {}
    for f in audit.findings:
        by_rule.setdefault(f.rule, []).append(f)

    for rule in sorted(by_rule):
        bucket = by_rule[rule]
        b = sum(1 for f in bucket if f.level == "blocking")
        w = sum(1 for f in bucket if f.level == "warn")
        i = sum(1 for f in bucket if f.level == "info")
        print(f"[{rule}]  blocking={b}  warn={w}  info={i}")
        for f in bucket:
            marker = "X" if f.level == "blocking" else (
                "!" if f.level == "warn" else "-"
            )
            print(f"  {marker} {f.path.name:40s}  {f.message}")
        print()

    if blocking:
        print(f"FAIL: {len(blocking)} blocking finding(s)")
        return 1
    if warn:
        print(f"WARN-ONLY: {len(warn)} warn finding(s) (non-blocking)")
        return 0
    print("OK: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
