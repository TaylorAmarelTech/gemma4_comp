# ruff: noqa: E501
"""DueCare visualization toolkit -- the shared, importable chart helpers.

A REAL importable port of the prettify toolkit embedded in the DueCare Kaggle notebooks
(``scripts/_notebook_viz.py`` -- the ``PALETTE`` + ``HELPERS`` strings). Every chart shares one
polished theme (seaborn whitegrid + the DueCare warm-paper / ink / civic-teal palette + a Plotly
template) so figures across the notebooks, the HTML report, and downstream reuse read as one system:

  * ``pretty_table`` -- publication-grade pandas Styler tables (gradients, in-cell bars, captions),
  * ``stat_cards``   -- a row of big-number KPI tiles,
  * ``radar``        -- spider chart (great for the 5 rubric dimensions),
  * ``dumbbell``     -- baseline->harnessed lollipop with the delta labeled,
  * ``slope``        -- slope chart (per-judge / per-arm movement),
  * ``kde_hist``     -- filled density histograms (scipy KDE, step fallback),
  * ``heatmap``      -- seaborn annotated heatmap,
  * ``ibar``         -- interactive Plotly horizontal bar with a matplotlib fallback.

seaborn / plotly / scipy are optional -- every helper that uses them is wrapped so it still runs (and
stays pretty) without them. Each chart helper accepts a keyword-only ``show`` flag (default True, the
notebook behaviour) and RETURNS its matplotlib ``Figure`` so callers such as
:mod:`duecare.kit.report` can render it to an offline PNG. ASCII-only -> no Kaggle mojibake.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

# ---- DueCare palette: warm paper / ink / civic teal; ember reserved for headline + privacy ----
PAPER, PAPER2, PAPER3 = "#F7F6F1", "#EFEDE4", "#E4E1D7"
INK, INK2, INK3, INK4 = "#14181B", "#2A2D34", "#5B5F68", "#8A8E97"
TEAL, TEAL_SOFT, TEAL_DK = "#2f7d8c", "#cfe3e6", "#1f5a66"
EMBER, EMBER_SOFT = "#c15b2e", "#f0d8c8"
GOOD, WARN, LINE, LINE2 = "#4e8a5a", "#b8873a", "#DDD8C9", "#E8E4D7"
ARM_COLORS = {"baseline": INK3, "harness_core": TEAL, "harness_full": GOOD}
SEQ = [TEAL, EMBER, GOOD, WARN, "#6d5a7a", "#3d6b8a", INK3]  # categorical sequence

_HAS_SNS = False
_HAS_PLOTLY = False


def apply_theme() -> None:
    """Apply the DueCare matplotlib rcParams + seaborn theme + Plotly template (idempotent).

    Called once at import so charts are styled by default, exactly like the notebook setup cell.
    Safe to re-call; seaborn and plotly are optional and skipped when unavailable.
    """
    global _HAS_SNS, _HAS_PLOTLY
    try:
        import seaborn as sns
        sns.set_theme(style="whitegrid", context="notebook")
        _HAS_SNS = True
    except Exception:
        _HAS_SNS = False

    mpl.rcParams.update({
        "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER, "savefig.dpi": 130,
        "axes.edgecolor": LINE, "axes.linewidth": 1.1, "axes.labelcolor": INK2, "axes.labelweight": "medium",
        "text.color": INK, "xtick.color": INK3, "ytick.color": INK3, "font.size": 11.5,
        "axes.titlesize": 14, "axes.titleweight": "bold", "axes.titlepad": 12, "axes.titlecolor": INK,
        "axes.grid": True, "grid.color": LINE, "grid.alpha": 0.55, "grid.linewidth": 0.9,
        "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 120,
        "legend.frameon": True, "legend.framealpha": 0.92, "legend.edgecolor": LINE, "legend.fontsize": 10,
        "xtick.major.size": 0, "ytick.major.size": 0, "axes.axisbelow": True,
    })

    try:
        import plotly.io as pio
        import plotly.graph_objects as go
        pio.templates["duecare"] = go.layout.Template(layout=dict(
            paper_bgcolor=PAPER, plot_bgcolor=PAPER,
            font=dict(family="Inter, -apple-system, system-ui, sans-serif", color=INK, size=13),
            colorway=SEQ, title=dict(font=dict(size=18, color=INK)),
            xaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE),
            yaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE),
            legend=dict(bgcolor="rgba(247,246,241,0.85)", bordercolor=LINE, borderwidth=1),
            margin=dict(l=70, r=30, t=70, b=55), hoverlabel=dict(font_size=12)))
        pio.templates.default = "duecare"
        _HAS_PLOTLY = True
    except Exception:
        _HAS_PLOTLY = False


def _finish(fig: Figure, show: bool) -> Figure:
    """Shared tail: tighten layout, optionally show, always return the figure."""
    try:
        fig.tight_layout()
    except Exception:
        pass
    if show:
        plt.show()
    return fig


def _title(ax, title, subtitle=None) -> None:
    ax.set_title(title)
    if subtitle:
        ax.text(0, 1.015, subtitle, transform=ax.transAxes, fontsize=9.5, color=INK3, va="bottom")


def pretty_table(df, *, caption=None, fmt=None, gradient=None, cmap="BuGn", bars=None,
                 bar_color=None, highlight_row=None, max_rows=None):
    """Publication-grade pandas Styler. gradient/bars are column-name lists; highlight_row is an index label."""
    d = df.head(max_rows) if max_rows else df
    sty = d.style
    if fmt:
        sty = sty.format(fmt)
    if gradient:
        cols = [c for c in gradient if c in d.columns]
        if cols:
            sty = sty.background_gradient(cmap=cmap, subset=cols)
    for col in (bars or []):
        if col in d.columns:
            sty = sty.bar(subset=[col], color=(bar_color or TEAL_SOFT), align="left", width=88)
    if highlight_row is not None:
        def _hl(row):
            return [f"background-color: {EMBER_SOFT}" if row.name == highlight_row else "" for _ in row]
        sty = sty.apply(_hl, axis=1)
    try:
        sty = sty.hide(axis="index")
    except Exception:
        pass
    if caption:
        sty = sty.set_caption(caption)
    sty = sty.set_table_styles([
        {"selector": "caption", "props": [("caption-side", "top"), ("font-size", "13.5px"), ("font-weight", "700"),
                                          ("color", INK), ("padding", "4px 2px 10px"), ("text-align", "left")]},
        {"selector": "th.col_heading", "props": [("background-color", PAPER2), ("color", INK), ("font-weight", "700"),
                                                 ("border", "none"), ("border-bottom", f"2px solid {TEAL}"),
                                                 ("padding", "8px 13px"), ("text-align", "left"), ("font-size", "12px")]},
        {"selector": "td", "props": [("padding", "7px 13px"), ("border", "none"),
                                     ("border-bottom", f"1px solid {LINE2}"), ("color", INK2), ("font-size", "12.5px")]},
        {"selector": "tr:hover td", "props": [("background-color", PAPER2)]},
        {"selector": "", "props": [("border-collapse", "collapse"),
                                   ("font-family", "Inter, -apple-system, system-ui, sans-serif")]},
    ])
    return sty


def stat_cards(items, figsize=None, *, show: bool = True) -> Figure:
    """Row of big-number KPI tiles. items: list of (value, label, color). Returns the Figure."""
    n = len(items)
    fig, ax = plt.subplots(figsize=figsize or (2.75 * n, 1.95))
    ax.axis("off")
    for i, (val, lab, col) in enumerate(items):
        ax.add_patch(FancyBboxPatch((i + 0.05, 0.10), 0.90, 0.82, boxstyle="round,pad=0.012,rounding_size=0.05",
                                    facecolor=PAPER2, edgecolor=col, linewidth=2.4, mutation_aspect=0.5, zorder=1))
        ax.text(i + 0.50, 0.605, str(val), ha="center", va="center", fontsize=24, fontweight="bold", color=col)
        ax.text(i + 0.50, 0.245, lab, ha="center", va="center", fontsize=9, color=INK3)
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    return _finish(fig, show)


def radar(labels, series, title="", subtitle=None, rmax=None, *, show: bool = True) -> Figure:
    """Spider chart. series: list of (name, values, color). Returns the Figure."""
    N = len(labels)
    ang = list(np.linspace(0, 2 * np.pi, N, endpoint=False))
    ang += ang[:1]
    fig, ax = plt.subplots(figsize=(6.8, 6.8), subplot_kw=dict(polar=True))
    ax.set_facecolor(PAPER)
    for name, vals, col in series:
        v = list(vals) + [vals[0]]
        ax.plot(ang, v, color=col, lw=2.6, label=name, zorder=3)
        ax.fill(ang, v, color=col, alpha=0.14, zorder=2)
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels(labels, fontsize=10.5, color=INK2)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    if rmax:
        ax.set_ylim(0, rmax)
    ax.grid(color=LINE, alpha=0.75)
    ax.spines["polar"].set_color(LINE)
    ax.set_title(title, pad=22, fontsize=14, fontweight="bold")
    if subtitle:
        fig.text(0.5, 0.025, subtitle, ha="center", fontsize=9.5, color=INK3)
    ax.legend(loc="upper right", bbox_to_anchor=(1.30, 1.10))
    return _finish(fig, show)


def dumbbell(labels, lo, hi, lo_lab="baseline", hi_lab="harnessed", title="", subtitle=None,
             xlabel="", xlim=None, *, show: bool = True) -> Figure:
    """Lollipop/dumbbell with the delta labeled above each connector. Returns the Figure."""
    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9.8, 0.64 * len(labels) + 1.8))
    for yi, a, b in zip(y, lo, hi):
        ax.plot([a, b], [yi, yi], color=LINE, lw=4.5, zorder=1, solid_capstyle="round")
        ax.text((a + b) / 2, yi + 0.17, f"+{b - a:.1f}", ha="center", va="bottom", color=EMBER, fontweight="bold", fontsize=9.5)
    ax.scatter(lo, y, color=INK3, s=135, zorder=3, label=lo_lab, edgecolor=PAPER, linewidth=1.5)
    ax.scatter(hi, y, color=TEAL, s=135, zorder=3, label=hi_lab, edgecolor=PAPER, linewidth=1.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel(xlabel)
    if xlim:
        ax.set_xlim(*xlim)
    ax.grid(axis="y", alpha=0)
    ax.invert_yaxis()
    ax.legend(loc="lower right")
    _title(ax, title, subtitle)
    return _finish(fig, show)


def slope(labels, left, right, left_lab="baseline", right_lab="harnessed", title="", subtitle=None,
          ylabel="", invert=False, *, show: bool = True) -> Figure:
    """Slope chart: one line per label from a left value to a right value. Labels de-overlap when values tie.

    invert=True flips the y-axis (ranks: pass positive ranks, rank 1 on top, labels stay positive).
    Returns the Figure.
    """
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    allv = list(left) + list(right)
    span = (max(allv) - min(allv)) or 1.0

    def _spread(vals):
        gap = span * 0.055
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        ys = [float(v) for v in vals]
        for k in range(1, len(order)):
            i, j = order[k - 1], order[k]
            if ys[j] - ys[i] < gap:
                ys[j] = ys[i] + gap
        return ys

    lys, rys = _spread(left), _spread(right)
    for lab, a, b, la, rb in zip(labels, left, right, lys, rys):
        ax.plot([0, 1], [a, b], color=TEAL, lw=2.2, marker="o", markersize=8, markerfacecolor=PAPER,
                markeredgecolor=TEAL, markeredgewidth=2, zorder=3)
        ax.text(-0.04, la, f"{lab}  {a:.0f}", ha="right", va="center", fontsize=9.5, color=INK2)
        ax.text(1.04, rb, f"{b:.0f}", ha="left", va="center", fontsize=10, color=EMBER, fontweight="bold")
    ax.set_xlim(-0.5, 1.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([left_lab, right_lab], fontsize=11.5, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(axis="x", alpha=0)
    if invert:
        ax.invert_yaxis()
    _title(ax, title, subtitle)
    return _finish(fig, show)


def kde_hist(series_list, title="", subtitle=None, xlabel="", vlines=None, *, show: bool = True) -> Figure:
    """Filled histogram + smooth density per series. series_list: list of (name, values, color). Returns the Figure."""
    fig, ax = plt.subplots(figsize=(9.8, 4.7))
    for name, vals, col in series_list:
        vals = np.asarray(vals, dtype=float)
        vals = vals[np.isfinite(vals)]
        if not len(vals):
            continue
        ax.hist(vals, bins=42, density=True, color=col, alpha=0.16, edgecolor="none", zorder=1)
        try:
            from scipy.stats import gaussian_kde
            xs = np.linspace(vals.min(), vals.max(), 220)
            ax.plot(xs, gaussian_kde(vals)(xs), color=col, lw=2.7, label=f"{name} (mean {vals.mean():.0f})", zorder=3)
        except Exception:
            ax.hist(vals, bins=42, density=True, histtype="step", lw=2.7, color=col,
                    label=f"{name} (mean {vals.mean():.0f})", zorder=3)
    for xv, col, lab in (vlines or []):
        ax.axvline(xv, color=col, lw=2, ls="--", zorder=4)
        if lab:
            ax.text(xv, ax.get_ylim()[1] * 0.94, lab, color=col, fontweight="bold", ha="center", fontsize=9.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("density")
    ax.legend()
    _title(ax, title, subtitle)
    return _finish(fig, show)


def heatmap(mat, row_labels, col_labels, title="", subtitle=None, cmap="BuGn", fmt="+.1f",
            cbar_label="", *, show: bool = True) -> Figure:
    """Annotated heatmap (seaborn if present, matplotlib fallback). Returns the Figure."""
    fig, ax = plt.subplots(figsize=(1.15 * len(col_labels) + 3, 0.62 * len(row_labels) + 2.2))
    arr = np.asarray(mat, dtype=float)
    try:
        import seaborn as sns
        sns.heatmap(arr, annot=True, fmt=fmt, cmap=cmap, xticklabels=col_labels, yticklabels=row_labels,
                    linewidths=1.2, linecolor=PAPER, cbar_kws={"label": cbar_label}, ax=ax,
                    annot_kws={"fontsize": 9.5, "color": INK})
    except Exception:
        im = ax.imshow(arr, cmap=cmap, aspect="auto")
        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels)
        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels)
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                ax.text(j, i, format(arr[i, j], fmt), ha="center", va="center", fontsize=9, color=INK)
        fig.colorbar(im, ax=ax, label=cbar_label)
    ax.set_title(title, loc="left")
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9.5, color=INK3, va="bottom")
    return _finish(fig, show)


def ibar(labels, baseline, lift, ns=None, title="", subtitle=None,
         xlabel="mean rubric score (0-100)", *, show: bool = True):
    """Interactive Plotly stacked h-bar (baseline + lift) with a matplotlib fallback. Sorted by total.

    When ``show`` is False the matplotlib path is forced and the ``Figure`` is returned (so callers such
    as the HTML report can render an offline PNG); the Plotly path is only taken for interactive display.
    """
    order = np.argsort([b + l for b, l in zip(baseline, lift)])
    labels = [labels[i] for i in order]
    baseline = [baseline[i] for i in order]
    lift = [lift[i] for i in order]
    ns = [ns[i] for i in order] if ns is not None else None
    ticks = [f"{m}  (n={int(n):,})" for m, n in zip(labels, ns)] if ns is not None else list(labels)
    if _HAS_PLOTLY and show:
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_bar(y=ticks, x=baseline, orientation="h", name="baseline", marker_color=INK3,
                        hovertemplate="baseline %{x:.1f}<extra></extra>")
            fig.add_bar(y=ticks, x=lift, orientation="h", name="harness lift", marker_color=TEAL,
                        text=[f"+{l:.1f}" for l in lift], textposition="outside", textfont=dict(color=EMBER, size=12),
                        hovertemplate="lift +%{x:.1f}<extra></extra>")
            fig.update_layout(barmode="stack", title=title, xaxis_title=xlabel, height=90 * len(labels) + 170,
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), bargap=0.35)
            if subtitle:
                fig.add_annotation(text=subtitle, showarrow=False, xref="paper", yref="paper",
                                   x=0, y=1.10, font=dict(size=11, color=INK3))
            fig.update_xaxes(range=[0, 106])
            fig.show()
            return fig
        except Exception:
            pass
    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9.8, 0.66 * len(labels) + 1.7))
    ax.barh(y, baseline, color=INK3, label="baseline")
    ax.barh(y, lift, left=baseline, color=TEAL, label="harness lift")
    for yi, b, l in zip(y, baseline, lift):
        ax.text(b + l + 1.2, yi, f"+{l:.1f}", va="center", color=EMBER, fontweight="bold", fontsize=9.5)
    ax.set_yticks(y)
    ax.set_yticklabels(ticks)
    ax.set_xlim(0, 106)
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", alpha=0)
    ax.legend(loc="lower right")
    _title(ax, title, subtitle)
    return _finish(fig, show)


# Apply the theme once on import so charts are DueCare-styled by default (mirrors the notebook cell).
apply_theme()


__all__ = [
    "PAPER", "PAPER2", "PAPER3", "INK", "INK2", "INK3", "INK4",
    "TEAL", "TEAL_SOFT", "TEAL_DK", "EMBER", "EMBER_SOFT", "GOOD", "WARN", "LINE", "LINE2",
    "ARM_COLORS", "SEQ", "apply_theme",
    "pretty_table", "stat_cards", "radar", "dumbbell", "slope", "kde_hist", "heatmap", "ibar",
]
