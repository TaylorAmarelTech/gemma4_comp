#!/usr/bin/env python3
"""code_neighbors.py -- when you touch one file, see its neighbours across three modes.

DueCare already has a strong DETERMINISTIC / STRUCTURAL code graph: the CodeGraph MCP
(``.codegraph/`` -- ~1,200 files / ~32k edges, tree-sitter) for callers, callees, blast
radius, and trace (``codegraph_callers`` / ``_callees`` / ``_impact`` / ``_trace`` /
``_context``), plus 75 generated ``HIERARCHY.md`` meta files (deps / dependents / siblings
per module). What it does NOT have is a *similarity* layer.

This tool adds exactly that gap -- a **lexical-semantic "similar files"** ranking
(TF-IDF cosine over identifier/term tokens; pure stdlib, no model download) -- alongside a
quick imports / imported-by view, so one command answers "what else should I look at when I
edit this file?". It is intentionally complementary: for authoritative callers/callees/
impact/trace and LLM-composed context, use the CodeGraph MCP (sub-millisecond).

Honest scope: "semantic" here means lexical similarity (shared vocabulary), NOT neural
embeddings. Files about the same thing share identifiers, so TF-IDF is a strong, free
proxy; a true-embedding mode (a small local code model in the recovery venv) is the
documented upgrade path, not built here.

Usage:
    python scripts/code_neighbors.py packages/duecare-llm-chat/src/duecare/chat/harnesses/triage/handler.py
    python scripts/code_neighbors.py <file> --top 10 --roots packages scripts apps src
"""
from __future__ import annotations

import argparse
import ast
import math
import re
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_ROOTS = ("packages", "scripts", "apps", "src", "configs")
_SKIP = ("__pycache__", "_archive", "node_modules", ".codegraph", "reports", ".git", ".venv")
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
# very common python/identifier noise that carries no signal for similarity
_STOP = frozenset((
    "self", "def", "return", "import", "from", "the", "for", "and", "not", "none", "true",
    "false", "args", "kwargs", "str", "int", "list", "dict", "set", "type", "value", "data",
    "name", "path", "file", "test", "init", "main", "print", "raise", "except", "class",
))


def tokenize(text: str) -> Counter:
    """Identifier / term tokens (lowercased, stopwords + tiny tokens dropped)."""
    return Counter(t for t in (m.group(0).lower() for m in _TOKEN.finditer(text)) if t not in _STOP)


def _iter_files(roots, exts=(".py",)) -> list[Path]:
    out: list[Path] = []
    for r in roots:
        base = _ROOT / r
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.suffix in exts and not any(s in p.parts for s in _SKIP):
                out.append(p)
    return out


def build_tfidf(files: list[Path]) -> tuple[dict[Path, dict[str, float]], dict[str, float]]:
    """Return (per-file tf-idf vectors, idf). Pure stdlib."""
    tfs: dict[Path, Counter] = {}
    df: Counter = Counter()
    for p in files:
        try:
            tf = tokenize(p.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        if tf:
            tfs[p] = tf
            df.update(tf.keys())
    n = max(1, len(tfs))
    idf = {term: math.log(n / (1 + d)) + 1.0 for term, d in df.items()}
    vecs: dict[Path, dict[str, float]] = {}
    for p, tf in tfs.items():
        total = sum(tf.values()) or 1
        vecs[p] = {t: (c / total) * idf.get(t, 0.0) for t, c in tf.items()}
    return vecs, idf


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def similar_files(target: Path, vecs: dict[Path, dict[str, float]], top: int = 8) -> list[tuple[Path, float]]:
    """Top-N files most similar to `target` by TF-IDF cosine (target excluded)."""
    tv = vecs.get(target)
    if tv is None:
        return []
    scored = [(p, cosine(tv, v)) for p, v in vecs.items() if p != target]
    scored.sort(key=lambda x: -x[1])
    return [(p, s) for p, s in scored[:top] if s > 0]


def _module_of(path: Path) -> str:
    """Best-effort dotted module for a packaged file (…/src/duecare/x/y.py -> duecare.x.y)."""
    parts = path.with_suffix("").parts
    if "src" in parts:
        parts = parts[parts.index("src") + 1:]
    return ".".join(parts)


def imports_of(path: Path) -> list[str]:
    """Modules this file imports (AST; regex fallback for unparseable files)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, SyntaxError):
        return []
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            # relative imports (the package idiom, e.g. `from ..model_interface`) carry
            # the most local signal -- keep them, prefixed with their dots.
            if node.level:
                mods.add("." * node.level + (node.module or ""))
            elif node.module:
                mods.add(node.module)
    return sorted(m for m in mods if m.startswith(".") or "duecare" in m
                  or m.split(".")[0] in {"scripts"})


def dependents_of(target: Path, files: list[Path]) -> list[Path]:
    """Files that import the target's module, or sibling-load it by stem (the repo's
    `_sibling("name")` / `_load("name", …)` idiom for scripts)."""
    stem = target.stem
    dotted = _module_of(target)
    pats = [re.compile(rf"\b(import|from)\s+{re.escape(dotted)}\b") if dotted else None,
            re.compile(rf'_sibling\(["\']{re.escape(stem)}["\']'),
            re.compile(rf'_load\(["\']{re.escape(stem)}["\']'),
            re.compile(rf'spec_from_file_location\([^)]*["\']{re.escape(stem)}["\']')]
    pats = [p for p in pats if p]
    hits: list[Path] = []
    for p in files:
        if p == target:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(pat.search(txt) for pat in pats):
            hits.append(p)
    return hits


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(_ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="the file you are editing")
    ap.add_argument("--top", type=int, default=8, help="number of similar files (default 8)")
    ap.add_argument("--roots", nargs="*", default=list(_DEFAULT_ROOTS), help="dirs to scan")
    args = ap.parse_args(argv)

    target = Path(args.file)
    if not target.is_absolute():
        target = (_ROOT / target)
    target = target.resolve()
    if not target.exists():
        print(f"no such file: {args.file}", file=sys.stderr)
        return 2

    files = _iter_files(args.roots)
    if target not in files:
        files.append(target)

    print(f"# neighbours of {_rel(target)}\n")
    deps = imports_of(target)
    print("## imports (this file depends on)")
    print("\n".join(f"  - {d}" for d in deps) if deps else "  (none in duecare.*/scripts.*)")
    dependents = dependents_of(target, files)
    print(f"\n## imported / sibling-loaded by ({len(dependents)} file(s))")
    print("\n".join(f"  - {_rel(p)}" for p in dependents[:25]) if dependents else "  (none found)")
    vecs, _ = build_tfidf(files)
    sims = similar_files(target, vecs, args.top)
    print("\n## similar files (lexical-semantic, TF-IDF cosine)")
    print("\n".join(f"  {s:.3f}  {_rel(p)}" for p, s in sims) if sims else "  (none)")
    print("\nFor callers/callees/impact/trace + LLM context, use the CodeGraph MCP "
          "(codegraph_callers / _callees / _impact / _trace / _context).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
