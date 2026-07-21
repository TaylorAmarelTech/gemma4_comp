"""Tests for the DueCare visualization helpers (run headless under MPLBACKEND=Agg)."""
from __future__ import annotations

import matplotlib
import pandas as pd
from matplotlib.figure import Figure

from duecare.kit import viz

LABELS = ["gemma4:31b", "gpt-oss:120b", "glm-5.2"]
BASE = [48.4, 55.0, 60.0]
CORE = [89.1, 82.0, 78.0]


def test_backend_is_headless():
    assert matplotlib.get_backend().lower() == "agg"


def test_stat_cards_returns_figure():
    fig = viz.stat_cards([("+40.7", "lift", viz.EMBER), ("99.8%", "win rate", viz.TEAL)], show=False)
    assert isinstance(fig, Figure)


def test_radar_returns_figure():
    fig = viz.radar(["A", "B", "C", "D", "E"],
                    [("baseline", [5, 4, 3, 2, 1], viz.INK3), ("core", [9, 8, 7, 6, 5], viz.TEAL)],
                    show=False)
    assert isinstance(fig, Figure)


def test_dumbbell_returns_figure():
    fig = viz.dumbbell(LABELS, BASE, CORE, show=False)
    assert isinstance(fig, Figure)


def test_slope_returns_figure():
    fig = viz.slope(LABELS, BASE, CORE, show=False)
    assert isinstance(fig, Figure)


def test_kde_hist_returns_figure():
    fig = viz.kde_hist([("baseline", BASE, viz.INK3), ("core", CORE, viz.TEAL)], show=False)
    assert isinstance(fig, Figure)


def test_heatmap_returns_figure():
    fig = viz.heatmap([[1.0, 2.0], [3.0, 4.0]], ["r1", "r2"], ["c1", "c2"], show=False)
    assert isinstance(fig, Figure)


def test_ibar_matplotlib_path_returns_figure():
    # show=False forces the matplotlib fallback (never the Plotly branch), which is embeddable.
    fig = viz.ibar(LABELS, BASE, [c - b for b, c in zip(BASE, CORE)], ns=[100, 50, 25], show=False)
    assert isinstance(fig, Figure)


def test_pretty_table_renders_html_table():
    df = pd.DataFrame({"model": LABELS, "lift": [40.7, 27.0, 18.0]})
    html = viz.pretty_table(df, caption="board", gradient=["lift"], bars=["lift"]).to_html()
    assert "<table" in html and "lift" in html
