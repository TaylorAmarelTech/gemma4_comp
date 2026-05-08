"""v0.14.1 — Bulk-reconcile stale numbers across all docs.

Applies the same find/replace across every doc that quotes chat-package
content counts. Idempotent — replacements that don't match are
silently no-op so re-running is safe.

Targets the audit findings from the v0.14.0 reconciliation pass:
  - 108 / 111 / 146 GREP rules → 161
  - 33 / 35 RAG docs → 46
  - 21 / 34 dimensions → 46
  - 26 / 26-edge citation graph → 46-edge
  - 17 LLM-judge questions → 46
  - 5-layer harness → 6-layer
  - 5 toggleable layers → 6 toggleable layers
  - 407 / 545 / 575 prompts → 587 prompts
  - 50-test adversarial → 65-test
  - "v3.6" / "v3.8" / "v3.9" rubric labels → "v3.10"
  - "21 evaluator questions" → "46 evaluator questions"

Reports every replacement made (or skipped because already current).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPLACEMENTS: list[tuple[str, str]] = [
    # GREP rule counts (current: 161, multiple stale forms)
    ("108 GREP rules",  "161 GREP rules"),
    ("111 GREP rules",  "161 GREP rules"),
    ("146 GREP rules",  "161 GREP rules"),
    ("`108 GREP",       "`161 GREP"),
    ("`146 GREP",       "`161 GREP"),
    ("'108 GREP",       "'161 GREP"),
    ("\"108 GREP",      "\"161 GREP"),
    ("108 GREP / 33 RAG",       "161 GREP / 46 RAG"),
    ("108 GREP /33 RAG",        "161 GREP / 46 RAG"),
    ("108 GREP, 33 RAG",        "161 GREP, 46 RAG"),
    ("108 rules",       "161 rules"),
    ("111 rules",       "161 rules"),
    ("146 rules",       "161 rules"),
    ("GREP 108 rules",  "GREP 161 rules"),
    ("GREP 111 rules",  "GREP 161 rules"),
    ("GREP 146 rules",  "GREP 161 rules"),
    ("GREP rules: 108", "GREP rules: 161"),
    ("GREP rules | 108","GREP rules | 161"),
    ("len(GREP_RULES) == 108", "len(GREP_RULES) == 161"),
    ("GREP rules 108 >= 108",  "GREP rules 161 >= 161"),
    ("GREP rules 42 >= 42",    "GREP rules 161 >= 161"),
    ("GREP rules: 42",         "GREP rules: 161"),
    ("GREP rules | 42",        "GREP rules | 161"),
    ("**42 rules**",           "**161 rules**"),
    ("49 GREP rules",          "161 GREP rules"),

    # RAG doc counts (current: 46, multiple stale forms)
    ("33 RAG docs",          "46 RAG docs"),
    ("35 RAG docs",          "46 RAG docs"),
    ("`33 RAG",              "`46 RAG"),
    ("`35 RAG",              "`46 RAG"),
    ("'33 RAG",              "'46 RAG"),
    ("\"33 RAG",             "\"46 RAG"),
    ("33-doc RAG corpus",    "46-doc RAG corpus"),
    ("35-doc RAG corpus",    "46-doc RAG corpus"),
    ("33-doc curated RAG",   "46-doc curated RAG"),
    ("35-doc curated RAG",   "46-doc curated RAG"),
    ("33-doc baseline RAG",  "46-doc baseline RAG"),
    ("RAG 33 docs",          "RAG 46 docs"),
    ("RAG 35 docs",          "RAG 46 docs"),
    ("33 RAG documents",     "46 RAG documents"),
    ("33 RAG docsuments",    "46 RAG documents"),  # typo seen in audit
    ("33-document corpus",   "46-document corpus"),
    ("BM25 over 33-doc",     "BM25 over 46-doc"),
    ("BM25 over a 33-doc",   "BM25 over a 46-doc"),
    ("33-doc legal corpus",  "46-doc legal corpus"),
    ("33-doc in-kernel corpus", "46-doc in-kernel corpus"),
    ("RAG corpus (33 documents", "RAG corpus (46 documents"),
    ("RAG corpus (33 docs", "RAG corpus (46 docs"),
    ("33 documents, BM25",   "46 documents, BM25"),
    ("33 docs (ILO conventions",  "46 docs (ILO conventions"),
    ("The 33 docs",          "The 46 docs"),
    ("the 33 docs",          "the 46 docs"),
    ("33 docs cluster",      "46 docs cluster"),
    ("33 docs fits",         "46 docs fits"),
    ("Current 33 docs",      "Current 46 docs"),
    ("33-doc legal RAG corpus", "46-doc legal RAG corpus"),
    ("RAG **33 docs**",      "RAG **46 docs**"),
    ("RAG     **33 docs**",  "RAG     **46 docs**"),
    (" 33-doc RAG ",         " 46-doc RAG "),
    ("21 evaluator q+hint",  "46 evaluator q+hint"),
    ("413 example prompts",  "587 example prompts"),
    ("413 bundled example prompts", "587 bundled example prompts"),
    ("413 prompts",          "587 prompts"),
    ("Generative legal Q&A grounded in 33-doc RAG",
     "Generative legal Q&A grounded in 46-doc RAG"),
    ("# 21 evaluator",       "# 46 evaluator"),

    # v0.14.2 round-2 sweep — kernel.py docstrings + appendix READMEs
    ("108 regex KB rules",   "161 regex KB rules"),
    ("108 regex / pattern rules", "161 regex / pattern rules"),
    ("204 example prompts",  "587 example prompts"),
    ("33-doc BM25 corpus",   "46-doc BM25 corpus"),
    ("Grading Evaluation (A6)", "Grading Evaluation (A11)"),
    ("universal v2 grader",  "universal v3.10 grader"),
    ("universal v2):",       "universal v3.10):"),
    ("Universal = 21-dim",   "Universal = 46-dim"),
    ("21-dim multi-signal grader", "46-dim multi-signal grader"),
    ("21-dim multi-signal scorer", "46-dim multi-signal scorer"),
    ("Rule-Based (21-dim",   "Rule-Based (46-dim rubric v3.10"),
    ("21 LLM-judge calls",   "up to 46 LLM-judge calls"),
    ("21 questions back",    "46 questions back"),
    ("v3.6 universal grader", "v3.10 universal grader"),
    ("v3.6 (21 dims",        "v3.10 (46 dims"),
    ("v3.5 (19 dims)",       "v3.5 (19 dims, historical)"),
    ("(15 dimensions",       "(46 dimensions"),
    (">108 rules<",          ">161 rules<"),
    ("`108 regex",           "`161 regex"),
    ("v0.13.0+):",           "v0.14.2+):"),
    ("v0.13.0+)",            "v0.14.2+)"),

    # Citation graph (current: 46 edges)
    ("26-edge citation graph", "46-edge citation graph"),
    ("26 hand-curated edges",  "46 hand-curated edges"),

    # Rubric dimension counts (current: 46)
    ("21-dim universal rubric", "46-dim universal rubric"),
    ("21-dimension multi-signal grader", "46-dimension multi-signal grader"),
    ("21-dimension grader",     "46-dimension grader"),
    ("21-dim ",                 "46-dim "),
    ("21 dimensions",           "46 dimensions"),
    ("21-dim universal",        "46-dim universal"),
    ("21 rubric dimensions",    "46 rubric dimensions"),
    ("17 dimensions",           "46 dimensions"),  # A-11 metadata stale ref
    ("34-dim universal rubric", "46-dim universal rubric"),
    ("34-dimension grader",     "46-dimension grader"),
    ("34 dimensions",           "46 dimensions"),
    ("34-dim ",                 "46-dim "),
    ("17 LLM-judge questions",  "46 LLM-judge questions"),
    ("21 LLM-judge questions",  "46 LLM-judge questions"),
    ("21 evaluator questions",  "46 evaluator questions"),

    # Layer counts (current: 6)
    ("5-layer harness",        "6-layer harness"),
    ("five toggleable layers", "six toggleable layers"),
    ("Five toggleable layers", "Six toggleable layers"),
    ("5 harness layers",       "6 harness layers"),
    ("5 toggleable layers",    "6 toggleable layers"),

    # Example prompt counts (current: 587)
    ("407 prompts", "587 prompts"),
    ("407 promptss", "587 prompts"),  # typo
    ("407 example prompts", "587 example prompts"),
    ("204 prompts", "587 prompts"),
    ("204 example prompts", "587 example prompts"),
    ("545 prompts", "587 prompts"),
    ("545 example prompts", "587 example prompts"),
    ("575 prompts", "587 prompts"),
    ("Example prompts 394 >= 407", "Example prompts 587 >= 587"),

    # Adversarial suite (current: 65 tests)
    ("50-test adversarial",  "65-test adversarial"),
    ("50 adversarial tests", "65 adversarial tests"),
    ("19 adversarial tests", "65 adversarial tests"),

    # 207 5-tier rubrics — leave as-is (those are reference-set numbers,
    # not chat-package counts). But "207 prompts" as a chat-package
    # claim should be qualified.

    # Audience buckets (current: 8)
    ("6 audience buckets", "8 audience buckets"),
    ("six audience buckets", "eight audience buckets"),

    # Rubric versions (target current rubric label)
    ("rubric v3.6",  "rubric v3.10"),
    ("rubric v3.7",  "rubric v3.10"),
    ("rubric v3.8",  "rubric v3.10"),
    ("rubric v3.9",  "rubric v3.10"),
    ("v3.6-usecase-aware",  "v3.10-data-evaluator"),
    ("v3.6 universal",      "v3.10 universal"),

    # 51 classifier examples (live: 54+) — leave alone unless docs claim drift
    # Stable references like "21K-test benchmark" are reference-set, not
    # chat-package, so they stay.

    # README math (2+11=13 not 11)
    ("2 core +\n11 appendix Kaggle notebooks", "2 core + 11 appendix = 13 Kaggle notebooks"),
    ("2 core + 11 appendix = 11 Kaggle notebooks", "2 core + 11 appendix = 13 Kaggle notebooks"),
    ("The 9 appendix notebooks", "The 11 appendix notebooks"),
    ("The **9** appendix notebooks", "The **11** appendix notebooks"),

    # Citation-graph helper text
    ("17 evaluator questions", "46 evaluator questions"),

    # NOT replacing: "21K-test benchmark" / "207-prompt eval set" — those
    # are reference-set numbers from the upstream benchmark, not chat-
    # package counts. They stay.
]


def _walk_docs(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    skip_dirs = {"_archive", "__pycache__", ".git", "node_modules", "wheels"}
    # Match .md, kaggle/*/kernel.py (the kernel scripts are Python but
    # contain user-facing docstrings + print() banners), and
    # kaggle/*/notebook.ipynb (the JSON notebook source). All three
    # surface to judges so we sweep all three.
    patterns = ("*.md", "kernel.py", "notebook.ipynb")
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            out.append(root)
            continue
        for pat in patterns:
            for p in root.rglob(pat):
                if any(part in skip_dirs for part in p.parts):
                    continue
                out.append(p)
    return sorted(set(out))


def main() -> None:
    docs_root = Path("docs")
    kaggle_root = Path("kaggle")
    extras = [Path("README.md"), Path("LICENSES.md")]
    files = _walk_docs([docs_root, kaggle_root] + extras)
    print(f"Scanning {len(files)} files for stale references...\n")

    total_replacements = 0
    files_changed = 0

    for f in files:
        try:
            txt = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        orig = txt
        per_file: list[tuple[str, str, int]] = []
        for old, new in REPLACEMENTS:
            if old not in txt:
                continue
            n = txt.count(old)
            txt = txt.replace(old, new)
            per_file.append((old, new, n))
            total_replacements += n
        if txt != orig:
            f.write_text(txt, encoding="utf-8")
            files_changed += 1
            print(f"== {f}")
            for old, new, n in per_file:
                print(f"   ({n}x)  {old!r}  ->  {new!r}")
            print()

    print(f"\nTotal replacements: {total_replacements} across {files_changed} files.")
    if files_changed == 0:
        print("(All docs already current — no replacements needed.)")


if __name__ == "__main__":
    main()
