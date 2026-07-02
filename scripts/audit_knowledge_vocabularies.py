#!/usr/bin/env python3
"""Read-only audit for saved KnowledgeObject vocabulary drift.

The app creates the local knowledge root on demand. This script deliberately
does not: it only reads an existing store and reports tokens that saved
envelopes use for indicators, corridors, and journey stages.

Run:
    python scripts/audit_knowledge_vocabularies.py
    python scripts/audit_knowledge_vocabularies.py --strict
    python scripts/audit_knowledge_vocabularies.py --store-path .duecare-knowledge
"""

from argparse import ArgumentParser
from ast import AST, AnnAssign, Assign, Module, Name, literal_eval, parse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from json import loads as json_loads
from os import getenv
from pathlib import Path
from re import match as re_match
from re import sub as re_sub
from sys import exit as sys_exit
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SAFE_TEXT_PY = (
    REPO_ROOT
    / "packages/duecare-llm-chat/src/duecare/chat/harnesses/_safe_text.py"
)
DEFAULT_STORE = REPO_ROOT / ".duecare-knowledge"
KAGGLE_STORE = Path("/kaggle/working/knowledge")

INDICATOR_FIELDS = frozenset({
    "indicators",
    "applies_to_indicators",
    "risk_indicators",
    "signal_types",
    "ilo_indicators",
})
CORRIDOR_FIELDS = frozenset({
    "corridor",
    "corridors",
    "applicable_corridors",
    "applies_to_corridors",
})
STAGE_FIELDS = frozenset({
    "journey_stage",
    "stages",
})
TOKEN_FIELDS = INDICATOR_FIELDS | CORRIDOR_FIELDS | STAGE_FIELDS
MAX_UNKNOWN_PATHS = 10


@dataclass(frozen=True)
class Vocabulary:
    indicators: frozenset[str]
    stages: frozenset[str]
    indicator_aliases: dict[str, str]
    stage_aliases: dict[str, str]


@dataclass
class TokenRecord:
    token: str
    canonical: str | None
    field: str
    path: str


@dataclass
class AuditResult:
    store_path: Path
    envelopes_scanned: int = 0
    invalid_json: list[str] = field(default_factory=list)
    canonical: Counter[str] = field(default_factory=Counter)
    known_alias: Counter[str] = field(default_factory=Counter)
    alias_targets: dict[str, str] = field(default_factory=dict)
    unknown: Counter[str] = field(default_factory=Counter)
    unknown_hits: dict[str, list[TokenRecord]] = field(default_factory=lambda: defaultdict(list))

    @property
    def found_envelopes(self) -> bool:
        return self.envelopes_scanned > 0

    @property
    def has_unknown(self) -> bool:
        return bool(self.unknown)


def _literal_assignment(tree: Module, name: str) -> Any:
    for node in tree.body:
        value: AST | None = None
        if isinstance(node, Assign):
            if any(isinstance(target, Name) and target.id == name for target in node.targets):
                value = node.value
        elif isinstance(node, AnnAssign):
            if isinstance(node.target, Name) and node.target.id == name:
                value = node.value
        if value is not None:
            return literal_eval(value)
    raise KeyError(f"could not find assignment for {name}")


def load_vocabulary(path: Path = SAFE_TEXT_PY) -> Vocabulary:
    tree = parse(path.read_text(encoding="utf-8"))
    indicators = frozenset(_literal_assignment(tree, "STANDARD_FACT_INDICATORS"))
    stages = frozenset(_literal_assignment(tree, "STANDARD_FACT_STAGES"))
    indicator_aliases = dict(_literal_assignment(tree, "_INDICATOR_ALIASES"))
    stage_aliases = dict(_literal_assignment(tree, "_STAGE_ALIASES"))
    return Vocabulary(
        indicators=indicators,
        stages=stages,
        indicator_aliases=indicator_aliases,
        stage_aliases=stage_aliases,
    )


def _candidate_store_paths() -> list[Path]:
    paths: list[Path] = []
    env_root = getenv("DUECARE_KNOWLEDGE_ROOT")
    if env_root:
        paths.append(Path(env_root))
    paths.extend([KAGGLE_STORE, DEFAULT_STORE])
    return paths


def detect_store_path() -> Path:
    for path in _candidate_store_paths():
        if path.exists():
            return path
    return DEFAULT_STORE


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _iter_token_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            out.extend(_iter_token_values(item))
        return out
    return []


def _indicator_key(token: str) -> str:
    return re_sub(r"\s+", "", token.strip()).lower()


def _stage_key(token: str) -> str:
    return re_sub(r"\s+", "_", token.strip()).lower()


def _normalize_corridor(token: str) -> str | None:
    compact = re_sub(r"\s+", "", token.strip().upper())
    corridor_match = re_match(r"^([A-Z]{2})[-_/]([A-Z]{2})$", compact)
    if corridor_match:
        return f"{corridor_match.group(1)}-{corridor_match.group(2)}"
    return None


def _classify_token(field_name: str, token: str, vocab: Vocabulary) -> tuple[str, str | None]:
    if field_name in INDICATOR_FIELDS:
        if token in vocab.indicators:
            return "CANONICAL", token
        key = _indicator_key(token)
        target = vocab.indicator_aliases.get(key)
        if target:
            return "KNOWN_ALIAS", target
        if key in vocab.indicators:
            return "KNOWN_ALIAS", key
        return "UNKNOWN", None
    if field_name in STAGE_FIELDS:
        if token in vocab.stages:
            return "CANONICAL", token
        key = _stage_key(token)
        target = vocab.stage_aliases.get(key)
        if target:
            return "KNOWN_ALIAS", target
        if key in vocab.stages:
            return "KNOWN_ALIAS", key
        return "UNKNOWN", None
    if field_name in CORRIDOR_FIELDS:
        target = _normalize_corridor(token)
        if target is None:
            return "UNKNOWN", None
        if token == target:
            return "CANONICAL", target
        return "KNOWN_ALIAS", target
    return "UNKNOWN", None


def _iter_envelope_files(store_path: Path) -> list[Path]:
    if not store_path.exists() or not store_path.is_dir():
        return []
    return sorted(path for path in store_path.rglob("*.json") if path.is_file())


def audit_store(store_path: Path, vocab: Vocabulary) -> AuditResult:
    result = AuditResult(store_path=store_path)
    for path in _iter_envelope_files(store_path):
        display_path = _display_path(path)
        try:
            envelope = json_loads(path.read_text(encoding="utf-8"))
        except Exception:
            result.invalid_json.append(display_path)
            continue
        if not isinstance(envelope, dict):
            continue
        content = envelope.get("content")
        if not isinstance(content, dict):
            continue
        result.envelopes_scanned += 1
        for field_name in sorted(TOKEN_FIELDS):
            for token in _iter_token_values(content.get(field_name)):
                bucket, canonical = _classify_token(field_name, token, vocab)
                if bucket == "CANONICAL":
                    result.canonical[canonical or token] += 1
                elif bucket == "KNOWN_ALIAS":
                    result.known_alias[token] += 1
                    result.alias_targets[token] = canonical or ""
                else:
                    result.unknown[token] += 1
                    if len(result.unknown_hits[token]) < MAX_UNKNOWN_PATHS:
                        result.unknown_hits[token].append(TokenRecord(
                            token=token,
                            canonical=None,
                            field=field_name,
                            path=display_path,
                        ))
    return result


def _format_counter(counter: Counter[str]) -> list[str]:
    if not counter:
        return ["  (none)"]
    return [f"  {token}: {count}" for token, count in counter.most_common()]


def format_report(result: AuditResult) -> str:
    lines = [
        "Knowledge vocabulary audit",
        f"Store: {_display_path(result.store_path)}",
    ]
    if not result.found_envelopes:
        lines.append(f"No envelopes found at {_display_path(result.store_path)}")
        if result.invalid_json:
            lines.append(f"Invalid JSON files skipped: {len(result.invalid_json)}")
        return "\n".join(lines)

    lines.extend([
        f"Envelopes scanned: {result.envelopes_scanned}",
        (
            "Unique tokens: "
            f"CANONICAL={len(result.canonical)} "
            f"KNOWN_ALIAS={len(result.known_alias)} "
            f"UNKNOWN={len(result.unknown)}"
        ),
    ])
    if result.invalid_json:
        lines.append(f"Invalid JSON files skipped: {len(result.invalid_json)}")

    lines.extend(["", "CANONICAL"])
    lines.extend(_format_counter(result.canonical))

    lines.extend(["", "KNOWN_ALIAS"])
    if result.known_alias:
        for token, count in result.known_alias.most_common():
            lines.append(f"  {token} -> {result.alias_targets.get(token, '')}: {count}")
    else:
        lines.append("  (none)")

    lines.extend(["", "UNKNOWN"])
    if result.unknown:
        for token, count in result.unknown.most_common():
            lines.append(f"  {token}: {count}")
            for hit in result.unknown_hits.get(token, []):
                lines.append(f"    {hit.path} ({hit.field})")
            if count > MAX_UNKNOWN_PATHS:
                lines.append(f"    ... {count - MAX_UNKNOWN_PATHS} more")
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--store-path", type=Path, default=None,
                        help="override the detected local knowledge store")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when any UNKNOWN token is found")
    args = parser.parse_args(argv)

    store_path = args.store_path or detect_store_path()
    vocab = load_vocabulary()
    result = audit_store(store_path, vocab)
    print(format_report(result))
    return 1 if args.strict and result.has_unknown else 0


if __name__ == "__main__":
    sys_exit(main())
