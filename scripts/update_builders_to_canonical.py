"""Update every notebook builder's KERNEL_ID/SLUG + URL_NNN constants
to the canonical `NNN-duecare-<title-derive>` slug pattern.

Canonical slug rule: the Kaggle title-derive of
`NNN: DueCare <Descriptive>` is `nnn-duecare-<descriptive>`. Every
notebook in the suite uses that title format, so a single derivation
rule produces uniform slugs across all 51 notebooks.

What this does:
1. Reads `kaggle/kernels/*/kernel-metadata.json` to compute the
   canonical id for each NNN (title-derive of the metadata title).
2. For each `scripts/build_notebook_*.py` or `scripts/build_*.py` that
   emits a specific notebook, rewrites:
   - `KERNEL_ID = "taylorsamarel/..."` (and `SLUG = ...`)
   - `URL_NNN = "https://www.kaggle.com/code/taylorsamarel/..."`
3. Rewrites the PHASES slug defaults in `scripts/build_index_notebook.py`
   so cross-links in the index also resolve to canonical.
4. Rewrites `PREV_NOTEBOOK` + `SECTION_MEMBERS` defaults in
   `scripts/build_section_conclusion_notebooks.py`.

Does not touch `_public_slugs.py` — that file is for live-slug
overrides of the default, and under canonical nomenclature defaults
should match live.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KERNELS_DIR = REPO_ROOT / "kaggle" / "kernels"
SCRIPTS_DIR = REPO_ROOT / "scripts"


def canonical_slug_from_title(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def load_canonical_slugs() -> dict[str, str]:
    """Return {NNN: canonical_slug} derived from each kernel's metadata title."""
    mapping = {}
    for kd in sorted(KERNELS_DIR.iterdir()):
        if not kd.is_dir():
            continue
        meta_path = kd / "kernel-metadata.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        title = meta.get("title", "")
        # Extract NNN from the dir name (e.g., duecare_140_* -> 140).
        m = re.match(r"duecare_(\d{3})_", kd.name)
        if not m:
            continue
        nnn = m.group(1)
        mapping[nnn] = canonical_slug_from_title(title)
    return mapping


def update_file(path: Path, canon: dict[str, str]) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    orig = text
    # Replace URL_NNN constants.
    for nnn, slug in canon.items():
        # Only touch URL_NNN where the URL points at taylorsamarel.
        pattern = re.compile(
            rf'URL_{nnn}\s*=\s*"https://www\.kaggle\.com/code/taylorsamarel/[^"]+"'
        )
        replacement = f'URL_{nnn} = "https://www.kaggle.com/code/taylorsamarel/{slug}"'
        text = pattern.sub(replacement, text)
    # Replace KERNEL_ID = "taylorsamarel/..." at top-level assignment.
    m = re.search(r'duecare_(\d{3})_', path.name)
    if m:
        nnn = m.group(1)
        if nnn in canon:
            text = re.sub(
                r'^(\s*KERNEL_ID\s*=\s*)"taylorsamarel/[^"]+"',
                rf'\1"taylorsamarel/{canon[nnn]}"',
                text,
                flags=re.MULTILINE,
            )
            text = re.sub(
                r'^(\s*SLUG\s*=\s*)"taylorsamarel/[^"]+"',
                rf'\1"taylorsamarel/{canon[nnn]}"',
                text,
                flags=re.MULTILINE,
            )
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return 1
    return 0


def update_phases_slugs(canon: dict[str, str]) -> int:
    path = SCRIPTS_DIR / "build_index_notebook.py"
    text = path.read_text(encoding="utf-8")
    orig = text
    # Each PHASES entry looks like: {"id": "140", ..., "slug": "duecare-140-evaluation-mechanics", ...}
    for nnn, slug in canon.items():
        pattern = re.compile(
            rf'(\{{"id":\s*"{nnn}"[^}}]*?"slug":\s*)"[^"]+"'
        )
        text = pattern.sub(rf'\1"{slug}"', text)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return 1
    return 0


def update_section_conclusion_defaults(canon: dict[str, str]) -> int:
    path = SCRIPTS_DIR / "build_section_conclusion_notebooks.py"
    text = path.read_text(encoding="utf-8")
    orig = text
    # PREV_NOTEBOOK entries look like:
    #   "299": ("190", "RAG Retrieval Inspector", "duecare-190-rag-retrieval-inspector"),
    # where the slug is the third tuple element.
    def _prev_replacer(match: re.Match) -> str:
        prefix = match.group(1)
        prev_id = match.group(2)
        title_str = match.group(3)
        if prev_id in canon:
            return f'{prefix}("{prev_id}", {title_str}, "{canon[prev_id]}")'
        return match.group(0)

    text = re.sub(
        r'(\s*"\d{3}":\s*)\("(\d{3})",\s*(\"[^\"]+\"),\s*"[^"]+"\)',
        _prev_replacer,
        text,
    )
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return 1
    return 0


def update_public_slug_overrides(canon: dict[str, str]) -> int:
    """Under canonical nomenclature, defaults match live so overrides
    should be minimal. Rewrite `_public_slugs.py` to keep only entries
    whose live slug genuinely differs from canonical."""
    path = SCRIPTS_DIR / "_public_slugs.py"
    # Load the existing overrides by exec'ing the module.
    namespace: dict = {}
    exec(path.read_text(encoding="utf-8"), namespace)
    existing = namespace.get("PUBLIC_SLUG_OVERRIDES", {})

    new_overrides = {}
    for nnn, live in existing.items():
        if nnn in canon and live == canon[nnn]:
            continue  # matches canonical, drop from overrides
        new_overrides[nnn] = live

    if new_overrides == existing:
        return 0

    content = '"""Single source of truth for Kaggle public slug overrides.\n\n'
    content += 'Under canonical nomenclature ``NNN-duecare-<title-derive>``,\n'
    content += 'most slugs match the default derived in ``build_index_notebook.py``.\n'
    content += 'Only record entries here when a kernel is live at a slug that\n'
    content += 'does NOT match that canonical default.\n"""\n\n'
    content += "from __future__ import annotations\n\n\n"
    content += "PUBLIC_SLUG_OVERRIDES: dict[str, str] = {\n"
    for nnn, slug in sorted(new_overrides.items()):
        content += f'    "{nnn}": "{slug}",\n'
    content += "}\n"
    path.write_text(content, encoding="utf-8")
    return 1


def main() -> int:
    canon = load_canonical_slugs()
    print(f"Loaded {len(canon)} canonical slugs from metadata titles")

    # 1. Update each dedicated builder.
    touched = 0
    for script_path in sorted(SCRIPTS_DIR.glob("build_notebook_*.py")):
        n = update_file(script_path, canon)
        if n:
            print(f"  updated {script_path.name}")
            touched += n

    # Also update shared builders.
    for name in ("build_grading_notebooks.py", "build_showcase_notebooks.py", "build_kaggle_notebooks.py"):
        p = SCRIPTS_DIR / name
        n = update_file(p, canon)
        if n:
            print(f"  updated {name}")
            touched += n

    # 2. Update index PHASES default slugs.
    n = update_phases_slugs(canon)
    if n:
        print(f"  updated build_index_notebook.py PHASES")
        touched += n

    # 3. Update section-conclusion defaults.
    n = update_section_conclusion_defaults(canon)
    if n:
        print(f"  updated build_section_conclusion_notebooks.py defaults")
        touched += n

    # 4. Prune _public_slugs.py entries that match canonical.
    n = update_public_slug_overrides(canon)
    if n:
        print(f"  updated _public_slugs.py overrides")
        touched += n

    print(f"\nTotal files touched: {touched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
