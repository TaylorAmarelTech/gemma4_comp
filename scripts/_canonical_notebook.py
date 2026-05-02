"""Shared helpers for building canonical DueCare comparison notebooks.

These helpers encode the structural invariants that the 31c/31d
canonicalization pass enforces across every comparison notebook:

- HTML header with 22%/78% column widths carrying Inputs, Outputs,
  Prerequisites, Runtime, and Pipeline position.
- HTML troubleshooting table with Symptom / Resolution columns.
- Inline ``_hex_to_rgba`` helper used by every radar fill.
- URL-bearing final-print patch that overrides the hardener default.

Keep this module narrow. Things that belong in ``notebook_hardening_utils``
(install cell pinning, PyPI version bumps) stay there. Things that only
matter to the narrative shell of a comparison notebook live here.
"""

from __future__ import annotations

from html import escape
from typing import Iterable


def canonical_hero_code(*, title: str, kicker: str, tagline: str) -> str:
    """Return the code-cell source for the canonical DueCare hero banner.

    Every DueCare notebook opens with the same gradient banner so judges
    landing on any single notebook see a consistent frame. The banner has
    three lines:

    - ``kicker`` — small uppercase label identifying the notebook role
      (``DueCare - Section Conclusion``, ``DueCare - Gemma 4 Exploration``,
      ``DueCare - Orientation Navigation Surface``).
    - ``title`` — the canonical ``NNN: DueCare <Name>`` heading.
    - ``tagline`` — a single sentence that describes what a reader gets
      from the notebook.

    Emit as a ``code`` cell at position 0 of the notebook's cell list.
    """

    def _sq_escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    return (
        f"NOTEBOOK_TITLE = '{_sq_escape(title)}'\n"
        "from IPython.display import HTML, display\n"
        "display(HTML(\n"
        "    '<div style=\"background:linear-gradient(135deg,#1e3a8a 0%,#4c78a8 100%);'\n"
        "    'color:white;padding:20px 24px;border-radius:8px;margin:8px 0;'\n"
        "    'font-family:system-ui,-apple-system,sans-serif\">'\n"
        "    '<div style=\"font-size:10px;font-weight:600;letter-spacing:0.14em;'\n"
        "    'opacity:0.8;text-transform:uppercase\">"
        f"{_sq_escape(kicker)}</div>'\n"
        "    f'<div style=\"font-size:22px;font-weight:700;margin:6px 0 4px 0\">'\n"
        "    f'{NOTEBOOK_TITLE}</div>'\n"
        "    '<div style=\"font-size:13px;opacity:0.92;line-height:1.5\">"
        f"{_sq_escape(tagline)}</div>'\n"
        "    '</div>'\n"
        "))\n"
    )


HEX_TO_RGBA_SRC = """def _hex_to_rgba(hex_color: str, alpha: float = 0.08) -> str:
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'
"""
"""Inline definition of ``_hex_to_rgba``.

Plotly's ``fillcolor`` no longer accepts a 6-digit hex with a two-char
alpha suffix (``#AABBCC15``); it needs ``rgba(170, 187, 204, 0.08)``. Use
this snippet at the top of any cell that passes a translucent fill.
"""


def canonical_header_table(
    *,
    inputs_html: str,
    outputs_html: str,
    prerequisites_html: str,
    runtime_html: str,
    pipeline_html: str,
) -> str:
    """Return the 22%/78% HTML header table used by every canonical notebook.

    All five values are taken verbatim, so callers may include ``<code>``,
    ``<a>``, and other inline HTML. No values are escaped; sanitize
    upstream if you do not control them.
    """

    return (
        '<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">\n'
        "  <thead>\n"
        '    <tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">\n'
        '      <th style="padding: 6px 10px; text-align: left; width: 22%;">Field</th>\n'
        '      <th style="padding: 6px 10px; text-align: left; width: 78%;">Value</th>\n'
        "    </tr>\n"
        "  </thead>\n"
        "  <tbody>\n"
        f'    <tr><td style="padding: 6px 10px;"><b>Inputs</b></td><td style="padding: 6px 10px;">{inputs_html}</td></tr>\n'
        f'    <tr><td style="padding: 6px 10px;"><b>Outputs</b></td><td style="padding: 6px 10px;">{outputs_html}</td></tr>\n'
        f'    <tr><td style="padding: 6px 10px;"><b>Prerequisites</b></td><td style="padding: 6px 10px;">{prerequisites_html}</td></tr>\n'
        f'    <tr><td style="padding: 6px 10px;"><b>Runtime</b></td><td style="padding: 6px 10px;">{runtime_html}</td></tr>\n'
        f'    <tr><td style="padding: 6px 10px;"><b>Pipeline position</b></td><td style="padding: 6px 10px;">{pipeline_html}</td></tr>\n'
        "  </tbody>\n"
        "</table>\n"
    )


def troubleshooting_table_html(rows: Iterable[tuple[str, str]]) -> str:
    """Return a canonical HTML Symptom / Resolution troubleshooting table.

    ``rows`` yields ``(symptom_html, resolution_html)`` tuples. No values
    are escaped; ``rows`` may include inline HTML such as ``<code>``.
    """

    row_html = []
    for symptom, resolution in rows:
        row_html.append(
            f'    <tr><td style="padding: 6px 10px;">{symptom}</td>'
            f'<td style="padding: 6px 10px;">{resolution}</td></tr>'
        )
    return (
        '<table style="width: 100%; border-collapse: collapse; margin: 4px 0 8px 0;">\n'
        "  <thead>\n"
        '    <tr style="background: #f6f8fa; border-bottom: 2px solid #d1d5da;">\n'
        '      <th style="padding: 6px 10px; text-align: left; width: 38%;">Symptom</th>\n'
        '      <th style="padding: 6px 10px; text-align: left; width: 62%;">Resolution</th>\n'
        "    </tr>\n"
        "  </thead>\n"
        "  <tbody>\n"
        + "\n".join(row_html)
        + "\n  </tbody>\n"
        "</table>\n"
    )


def patch_final_print_cell(
    nb: dict,
    *,
    final_print_src: str,
    marker: str | None = None,
    max_len: int = 400,
) -> bool:
    """Replace the hardener's default final-print cell with a URL-bearing one.

    The hardener emits a short closing ``print(...)`` cell at the end of
    each notebook. The canonical variant prints the next-notebook URL and
    the section-conclusion URL verbatim so the handoff is clickable in
    the Kaggle viewer.

    Arguments:
        nb: the harden-notebook output dict (mutated in place).
        final_print_src: the source of the replacement cell.
        marker: a short substring unique to the new source. If a cell
            already contains it, the patch is skipped (idempotent).
        max_len: a safety limit on the length of the cell being replaced.
            The hardener's default is very short; guard against mistaking
            a large analysis cell for the closing print.

    Returns ``True`` if a replacement or append happened.
    """

    if marker is None:
        marker = final_print_src[:40]
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if "pip install" in src or "PACKAGES = [" in src:
            continue
        if marker in src:
            return False
        if "print(" in src and (
            "complete" in src.lower() or "continue to" in src.lower()
        ):
            if len(src) < max_len:
                cell["source"] = final_print_src.splitlines(keepends=True)
                # Hide both the source and any plain-text print output from
                # the rendered Kaggle view — handoff is navigation, not data.
                md = cell.setdefault("metadata", {})
                md["_kg_hide-input"] = True
                md["_kg_hide-output"] = True
                md.setdefault("jupyter", {})["source_hidden"] = True
                md["jupyter"]["outputs_hidden"] = True
                return True

    nb.setdefault("cells", []).append(
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {
                "language": "python",
                "_kg_hide-input": True,
                "_kg_hide-output": True,
                "jupyter": {"source_hidden": True, "outputs_hidden": True},
            },
            "outputs": [],
            "source": final_print_src.splitlines(keepends=True),
        }
    )
    return True


def escape_cell(text: str) -> str:
    """Convenience re-export of html.escape for builder-side formatting."""

    return escape(text)
