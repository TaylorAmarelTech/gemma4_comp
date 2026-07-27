"""Tests for the DueCare visualization helpers (run headless under MPLBACKEND=Agg)."""
from __future__ import annotations

import tomllib
import warnings
from pathlib import Path

import matplotlib
import pandas as pd
from duecare.kit import viz
from matplotlib.figure import Figure

LABELS = ["gemma4:31b", "gpt-oss:120b", "glm-5.2"]
BASE = [48.4, 55.0, 60.0]
CORE = [89.1, 82.0, 78.0]


def test_styler_runtime_dependency_is_declared():
    package_root = Path(__file__).resolve().parents[1]
    metadata = tomllib.loads((package_root / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = [item.lower() for item in metadata["project"]["dependencies"]]

    assert any(item.startswith("jinja2") for item in dependencies)


def test_backend_is_headless():
    assert matplotlib.get_backend().lower() == "agg"


def test_stat_cards_returns_figure():
    fig = viz.stat_cards(
        [("+40.7", "lift", viz.EMBER), ("99.8%", "win rate", viz.TEAL)],
        show=False,
    )
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
    deltas = [c - b for b, c in zip(BASE, CORE, strict=True)]
    fig = viz.ibar(LABELS, BASE, deltas, ns=[100, 50, 25], show=False)
    assert isinstance(fig, Figure)


def test_pretty_table_renders_html_table():
    df = pd.DataFrame({"model": LABELS, "lift": [40.7, 27.0, 18.0]})
    html = viz.pretty_table(df, caption="board", gradient=["lift"], bars=["lift"]).to_html()
    assert "<table" in html and "lift" in html


def test_pretty_table_skips_undefined_constant_gradient_and_bar_without_warning():
    df = pd.DataFrame({"model": ["a", "b"], "lift": [10.0, 10.0]})

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        html = viz.pretty_table(df, gradient=["lift"], bars=["lift"]).to_html()

    assert "<table" in html and "lift" in html
