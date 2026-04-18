"""Shared notebook display helpers for the DueCare suite.

Every notebook build script pulls from this module so presentation stays
consistent across the ~60 kernels. The helpers are designed to render
cleanly in the Kaggle saved-output viewer (which strips <script>, flex
layouts, max-height overflow, and some CSS). The two workhorses are
``pandas.Styler`` and ``IPython.display.Markdown`` with fenced code
blocks — both are safe and preserve full content (no truncation).

Usage inside a build script cell source:

    from _notebook_display import DISPLAY_BOOTSTRAP
    CELL = DISPLAY_BOOTSTRAP + '''
        # your cell code here, referencing show_headline, show_preview, ...
    '''

DISPLAY_BOOTSTRAP is a string containing all the runtime helper defs;
embed it at the top of any cell that uses them so the cell is
self-contained and does not depend on execution order.
"""

from __future__ import annotations


PALETTE = {
    "primary":   "#4c78a8",
    "success":   "#10b981",
    "warning":   "#f59e0b",
    "danger":    "#ef4444",
    "info":      "#3b82f6",
    "muted":     "#6b7280",
    "surface":   "#fafbfc",
    "surface_2": "#f6f8fa",
    "bg_success":"#ecfdf5",
    "bg_warning":"#fffbeb",
    "bg_danger": "#fef2f2",
    "bg_info":   "#eff6ff",
}


# ---- Runtime helpers embedded at the top of every consuming cell -----------

DISPLAY_BOOTSTRAP = '''import subprocess as _sp, sys as _sys
try:
    import pandas as _pd  # noqa: F401
except Exception:
    _sp.check_call([_sys.executable, "-m", "pip", "install", "-q", "pandas"])
try:
    import tabulate as _tab  # noqa: F401
except Exception:
    _sp.check_call([_sys.executable, "-m", "pip", "install", "-q", "tabulate"])
import html as _dc_html
import pandas as pd
from IPython.display import HTML, Markdown, display

# Palette mirrors the HEADER_TABLE colors across the suite.
_DC_PALETTE = {
    "primary": "#4c78a8", "success": "#10b981", "warning": "#f59e0b",
    "danger":  "#ef4444", "info":    "#3b82f6", "muted":   "#6b7280",
    "surface": "#fafbfc", "surface_2": "#f6f8fa",
    "bg_success": "#ecfdf5", "bg_warning": "#fffbeb", "bg_danger": "#fef2f2",
    "bg_info":    "#eff6ff",
}

def show_callout(text, kind="info", title=None):
    """Banner box. One-line or multi-line text. Safe inline HTML."""
    accent = _DC_PALETTE.get(kind, _DC_PALETTE["info"])
    bg = _DC_PALETTE.get(f"bg_{kind}", _DC_PALETTE["bg_info"])
    header = f\'<div style="font-weight:600;color:{accent};margin-bottom:4px">{_dc_html.escape(title)}</div>\' if title else ""
    body = _dc_html.escape(text).replace("\\n", "<br>")
    display(HTML(
        f\'<div style="border-left:4px solid {accent};background:{bg};\'
        f\'padding:10px 14px;margin:8px 0;border-radius:3px;color:#222;\'
        f\'font-family:system-ui,-apple-system,sans-serif">\'
        f\'{header}{body}</div>\'
    ))

def show_headline(rows, title=None):
    """rows = list of (label, value) or list of dicts with 'metric','value'."""
    if rows and isinstance(rows[0], (list, tuple)):
        df = pd.DataFrame(rows, columns=["metric", "value"]).set_index("metric")
    else:
        df = pd.DataFrame(rows).set_index("metric")
    if title:
        display(Markdown(f"### {title}"))
    display(
        df.style
          .set_properties(**{"text-align": "left"})
          .set_table_styles([{"selector": "th", "props": [("text-align", "left")]}])
          .hide(axis="columns")
    )

def show_distribution(counter_like, *, count_col="count", bar_color=None, title=None, pct=False):
    """Render a Counter / dict of counts as a Styler bar table. No truncation."""
    items = counter_like.most_common() if hasattr(counter_like, "most_common") else list(counter_like.items())
    df = pd.DataFrame(items, columns=["category", count_col]).set_index("category")
    if pct:
        total = df[count_col].sum() or 1
        df["pct"] = df[count_col] / total
    sty = (df.style
             .format({count_col: "{:,}", **({"pct": "{:.1%}"} if pct else {})})
             .bar(subset=[count_col], color=bar_color or _DC_PALETTE["primary"])
             .set_properties(**{"text-align": "right"}))
    if title:
        display(Markdown(f"### {title}"))
    display(sty)

def show_table(df_or_records, *, wrap_cols=None, center_cols=None,
               row_bg=None, title=None, max_col_px=820, show_index=False):
    """Full-text pandas table, no truncation. Word-wrap on `wrap_cols`.

    row_bg is a callable taking a row -> list of CSS strings per column
    (e.g. for coloring rows by status).
    """
    df = pd.DataFrame(df_or_records) if not isinstance(df_or_records, pd.DataFrame) else df_or_records
    sty = df.style
    if wrap_cols:
        for col in wrap_cols:
            if col in df.columns:
                sty = sty.set_properties(subset=[col], **{
                    "white-space": "pre-wrap",
                    "text-align": "left",
                    "max-width": f"{max_col_px}px",
                })
    if center_cols:
        sty = sty.set_properties(subset=[c for c in center_cols if c in df.columns], **{"text-align": "center"})
    if row_bg is not None:
        sty = sty.apply(row_bg, axis=1)
    sty = sty.set_table_styles([{"selector": "th", "props": [("text-align", "left")]}])
    if not show_index:
        sty = sty.hide(axis="index")
    if title:
        display(Markdown(f"### {title}"))
    display(sty)

def show_prompt_response(*, prompt, response, title=None, badges=None, prompt_label="Prompt", response_label="Response"):
    """One prompt-response pair as fenced code blocks in Markdown.

    Fenced blocks render identically across every Jupyter surface and
    preserve the full text verbatim. Use `badges=['grade: bad', 'ENABLES_HARM']`
    to add a metadata line above the blocks.
    """
    chunks = []
    if title:
        chunks.append(f"#### {title}")
    if badges:
        chunks.append(" ".join(f"`{b}`" for b in badges))
    chunks.append(f"**{prompt_label}**")
    chunks.append(f"```text\\n{prompt}\\n```")
    chunks.append(f"**{response_label}**")
    chunks.append(f"```text\\n{response}\\n```")
    display(Markdown("\\n\\n".join(chunks)))

def show_compare_table(rows, *, title=None):
    """rows = list of {'label':..., 'prompt':..., 'response':...}. Full text.
    Renders as a pandas Styler table with word-wrap on prompt+response columns.
    """
    df = pd.DataFrame(rows)
    show_table(
        df,
        wrap_cols=[c for c in ("prompt", "response", "note", "why") if c in df.columns],
        title=title,
    )

def show_stat_cards(cards, *, cols=4):
    """Render a row of colored stat tiles.

    Each card is a dict with keys: value, label, kind (optional, maps to palette).
    Cards wrap to new rows after `cols` items. Uses inline-block + inline-styled
    divs so the Kaggle viewer renders it identically in saved output.
    """
    pieces = []
    for card in cards:
        kind = card.get("kind", "primary")
        accent = _DC_PALETTE.get(kind, _DC_PALETTE["primary"])
        bg = _DC_PALETTE.get(f"bg_{kind}", _DC_PALETTE["bg_info"])
        value = card.get("value", "")
        label = card.get("label", "")
        sub = card.get("sub", "")
        width_pct = int(100 / max(cols, 1)) - 2
        pieces.append(
            f'<div style="display:inline-block;vertical-align:top;width:{width_pct}%;'
            f'margin:4px 1%;padding:14px 16px;background:{bg};'
            f'border-left:5px solid {accent};border-radius:4px;'
            f'font-family:system-ui,-apple-system,sans-serif">'
            f'<div style="font-size:11px;font-weight:600;color:{accent};'
            f'text-transform:uppercase;letter-spacing:0.04em">{_dc_html.escape(str(label))}</div>'
            f'<div style="font-size:26px;font-weight:700;color:#1f2937;margin:4px 0 0 0">'
            f'{_dc_html.escape(str(value))}</div>'
            + (f'<div style="font-size:12px;color:{_DC_PALETTE["muted"]};margin-top:2px">'
               f'{_dc_html.escape(str(sub))}</div>' if sub else '')
            + '</div>'
        )
    display(HTML('<div style="margin:8px 0">' + ''.join(pieces) + '</div>'))


def show_pipeline_diagram(steps, *, title=None):
    """Render a horizontal left-to-right flow diagram with optional titles.

    steps = list of dicts {label, sub (optional), kind (optional: primary/success/warning/danger/info/muted)}
    Uses inline-block with arrow separators. Kaggle-safe (no flex, no script).
    """
    if title:
        display(Markdown(f"### {title}"))
    parts = ['<div style="margin:10px 0;font-family:system-ui,-apple-system,sans-serif;line-height:1.4">']
    for i, step in enumerate(steps):
        kind = step.get("kind", "primary")
        accent = _DC_PALETTE.get(kind, _DC_PALETTE["primary"])
        bg = _DC_PALETTE.get(f"bg_{kind}", _DC_PALETTE["bg_info"])
        label = _dc_html.escape(str(step.get("label", "")))
        sub = _dc_html.escape(str(step.get("sub", "")))
        parts.append(
            f'<div style="display:inline-block;vertical-align:middle;min-width:160px;'
            f'padding:10px 14px;margin:4px 0;background:{bg};border:2px solid {accent};'
            f'border-radius:6px;text-align:center">'
            f'<div style="font-weight:600;color:#1f2937;font-size:13px">{label}</div>'
            + (f'<div style="color:{_DC_PALETTE["muted"]};font-size:11px;margin-top:2px">{sub}</div>' if sub else '')
            + '</div>'
        )
        if i < len(steps) - 1:
            parts.append(
                f'<span style="display:inline-block;vertical-align:middle;'
                f'margin:0 6px;color:{_DC_PALETTE["muted"]};font-size:20px">&rarr;</span>'
            )
    parts.append('</div>')
    display(HTML(''.join(parts)))


def register_pd_display_defaults():
    """Set pandas to never truncate strings when a notebook prints a DataFrame."""
    pd.set_option("display.max_colwidth", None)
    pd.set_option("display.width", None)
    pd.set_option("display.max_rows", 200)

register_pd_display_defaults()
'''


def inject_display_bootstrap(cell_source: str) -> str:
    """Prepend the display bootstrap to a raw cell source string.

    Use when building new cells that call show_* helpers; keeps the cell
    self-contained so execution order does not matter.
    """
    return DISPLAY_BOOTSTRAP + "\n\n" + cell_source
