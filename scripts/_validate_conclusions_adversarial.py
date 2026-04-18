"""Adversarial validation for all 8 DueCare section-conclusion notebooks.

099, 199, 299, 399, 499, 599, 699, 799 are emitted by
`scripts/build_section_conclusion_notebooks.py` from a single shared
`_build_one` function. They share an identical canonical shape, so one
validator with a loop is both cheaper and more accurate than eight
near-identical files.

Per notebook, the checks enforce:
- Kernel metadata id (prefers `PUBLIC_SLUG_OVERRIDES[NNN]` if present,
  otherwise the title-derived slug).
- Canonical title `NNN: DueCare <Section Title> Conclusion`.
- `is_private: False`.
- Cell 0 opens with `# NNN: DueCare <Section Title> Conclusion` (no em
  dash on the H1 line).
- Cell 0 includes the canonical 22%/78% HTML header table with all
  five rows (Inputs, Outputs, Prerequisites, Runtime, Pipeline
  position).
- Required cross-links: to the previous notebook and the next section
  opener (both pulled from `PREV_NOTEBOOK` and the SECTIONS list in
  the shared builder).
- `Recap` and `Key takeaways` headings.
- No `Privacy is non-negotiable` phrase (reserved for 610/899 prose).
- No `| | |` markdown pseudo-table.
- Exactly one install cell.
- A terminal `print(...)` cell that names the next-section starting
  notebook slug or, for 899, the 000 Index slug.

Prints `CONCLUSION CHECKS PASSED (8 of 8)` on success. On any failure
prints `FAIL  <NNN> <detail>` and exits 1 at the first failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KERNELS_DIR = REPO_ROOT / "kaggle" / "kernels"
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Pull the authoritative section metadata from the shared builder.
sys.path.insert(0, str(SCRIPTS_DIR))
from build_section_conclusion_notebooks import (  # noqa: E402
    PREV_NOTEBOOK,
    PUBLIC_SLUG_OVERRIDES,
    SECTIONS,
    _title_derived_slug,
)


def _fail(nnn: str, msg: str) -> None:
    print(f"FAIL  {nnn} {msg}")
    sys.exit(1)


def _ok(nnn: str, msg: str) -> None:
    print(f"OK    {nnn} {msg}")


def _kernel_dir(section: dict) -> Path:
    return KERNELS_DIR / f"duecare_{section['num']}_{section['snake']}"


def _derived_id(section: dict) -> str:
    override = PUBLIC_SLUG_OVERRIDES.get(section["num"])
    slug = override or _title_derived_slug(section["kaggle_title"])
    return f"taylorsamarel/{slug}"


def _run_for(section: dict) -> None:
    nnn = section["num"]
    kd = _kernel_dir(section)
    meta_path = kd / "kernel-metadata.json"
    nb_path = kd / f"{section['num']}_{section['snake']}.ipynb"

    if not nb_path.exists():
        _fail(nnn, f"notebook file missing: {nb_path}")
    if not meta_path.exists():
        _fail(nnn, f"metadata file missing: {meta_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    nb = json.loads(nb_path.read_text(encoding="utf-8"))

    expected_id = _derived_id(section)
    if meta.get("id") != expected_id:
        _fail(nnn, f"metadata id wrong: {meta.get('id')!r} (expected {expected_id!r})")

    expected_title = section["kaggle_title"]
    if meta.get("title") != expected_title:
        _fail(nnn, f"metadata title wrong: {meta.get('title')!r} (expected {expected_title!r})")

    if meta.get("is_private") is not False:
        _fail(nnn, f"is_private is not False: {meta.get('is_private')!r}")

    cells = nb["cells"]
    md_cells = [c for c in cells if c["cell_type"] == "markdown"]
    code_cells = [c for c in cells if c["cell_type"] == "code"]

    def src(cell: dict) -> str:
        s = cell.get("source", [])
        return "".join(s) if isinstance(s, list) else str(s)

    all_md = "\n\n".join(src(c) for c in md_cells)
    all_code = "\n\n".join(src(c) for c in code_cells)
    all_text = all_md + "\n\n" + all_code

    cell0 = src(md_cells[0])
    expected_h1 = f"# {section['num']}: DueCare {section['section_title']} Conclusion"
    if not cell0.startswith(expected_h1):
        _fail(nnn, f"cell 0 does not open with {expected_h1!r} (got {cell0.splitlines()[0][:120]!r})")

    h1_line = cell0.split("\n", 1)[0]
    if "\u2014" in h1_line:
        _fail(nnn, "H1 line contains an em dash")

    # Canonical HTML header table with five rows.
    if "<table" not in cell0:
        _fail(nnn, "cell 0 missing HTML header table")
    for tag in ("<b>Inputs</b>", "<b>Outputs</b>", "<b>Prerequisites</b>", "<b>Runtime</b>", "<b>Pipeline position</b>"):
        if tag not in cell0:
            _fail(nnn, f"HTML header missing {tag}")

    # Required cross-links: previous notebook (from PREV_NOTEBOOK) and next section opener.
    # Both use PUBLIC_SLUG_OVERRIDES when the default slug is overridden, to match
    # what the builder actually emits in the cross-link URLs.
    required_slugs: list[str] = []
    prev_entry = PREV_NOTEBOOK.get(nnn)
    if prev_entry is not None:
        prev_id, _, prev_default_slug = prev_entry
        required_slugs.append(PUBLIC_SLUG_OVERRIDES.get(prev_id, prev_default_slug))

    next_id = section.get("next_notebook_id")
    next_slug_default = section.get("next_notebook_slug")
    if next_slug_default:
        required_slugs.append(
            PUBLIC_SLUG_OVERRIDES.get(next_id, next_slug_default)
            if next_id
            else next_slug_default
        )

    for slug in required_slugs:
        if slug not in all_text:
            _fail(nnn, f"missing cross-link slug {slug!r}")

    # Structural prose requirements.
    if "## Recap" not in all_md:
        _fail(nnn, "missing 'Recap' section")
    if "## Key takeaways" not in all_md and "Key points" not in all_md and "Key takeaways" not in all_md:
        _fail(nnn, "missing 'Key takeaways' / 'Key points' block")

    # 899 is the only conclusion where "Privacy is non-negotiable" is allowed
    # as the suite-closing framing phrase. Every other conclusion must omit it.
    if nnn != "899" and "Privacy is non-negotiable" in all_text:
        _fail(nnn, "'Privacy is non-negotiable' should only appear in 610/899")

    if "| | |" in all_md:
        _fail(nnn, "pre-canonical '| | |' markdown pseudo-table present")

    # Exactly one install cell.
    install_cells = [
        c for c in code_cells
        if ("pip install" in src(c).lower()) or ("PACKAGES = [" in src(c))
    ]
    if len(install_cells) != 1:
        _fail(nnn, f"expected exactly 1 install cell, found {len(install_cells)}")

    # Terminal print cell with a URL substring.
    print_cells = [c for c in code_cells if "print(" in src(c)]
    if not print_cells:
        _fail(nnn, "missing a print cell with a URL handoff")
    final_print = src(print_cells[-1])
    # For end-of-suite conclusions (section["next_section"] == "(end of suite)"),
    # the final print points at the 000 index instead of a next-section slug.
    if section.get("next_section") == "(end of suite)":
        target_slug = "duecare-000-index"
    else:
        target_slug = (
            PUBLIC_SLUG_OVERRIDES.get(next_id, next_slug_default)
            if next_id and next_slug_default
            else "duecare-000-index"
        )
    if target_slug not in final_print:
        _fail(nnn, f"final print does not contain target slug {target_slug!r}")

    _ok(nnn, f"conclusion shape is canonical ({section['section_title']})")


def main() -> int:
    for section in SECTIONS:
        _run_for(section)
    print(f"\nCONCLUSION CHECKS PASSED ({len(SECTIONS)} of {len(SECTIONS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
