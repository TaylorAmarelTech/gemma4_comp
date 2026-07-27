# ruff: noqa: E501
"""duecare-llm-kit -- the reusable, downloadable DueCare toolkit.

The indicator engine, chart helpers, HTML-report generator, and corpus exporter that ship embedded in
the DueCare Kaggle notebooks, now as importable source code with a planned
``pip install duecare-llm-kit`` registry interface. It can be downloaded,
reused, and used to generate HTML reports and package data corpuses without
touching a notebook.

    from duecare.kit.engine import scan, generate_chain, risk_level
    from duecare.kit.verify import verify, verify_score, verify_lift
    from duecare.kit.viz import radar, dumbbell, stat_cards
    from duecare.kit.report import generate_report
    from duecare.kit.corpus import export_corpus, describe

The same names are re-exported at the package root, e.g. ``from duecare.kit import scan, generate_report``.
"""
from __future__ import annotations

from .engine import (
    COUNTERFACTUALS,
    EVIDENCE_STATES,
    FEE_CAMOUFLAGE,
    HOTLINES,
    ILO_INDICATORS,
    ILO_REFS,
    INDICATOR_QUESTIONS,
    LIFECYCLE,
    PATTERNS,
    generate_chain,
    risk_level,
    scan,
)
from .corpus import describe, export_corpus
from .report import generate_report, report_from_jsonl
from .verify import verify, verify_lift, verify_score
from .viz import (
    apply_theme,
    dumbbell,
    heatmap,
    ibar,
    kde_hist,
    pretty_table,
    radar,
    slope,
    stat_cards,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # engine
    "scan", "risk_level", "generate_chain",
    "ILO_INDICATORS", "ILO_REFS", "PATTERNS", "FEE_CAMOUFLAGE", "HOTLINES",
    "INDICATOR_QUESTIONS", "LIFECYCLE", "EVIDENCE_STATES", "COUNTERFACTUALS",
    # verify (deterministic verifiable checker / verifiable reward)
    "verify", "verify_score", "verify_lift",
    # viz
    "apply_theme", "pretty_table", "stat_cards", "radar", "dumbbell", "slope",
    "kde_hist", "heatmap", "ibar",
    # report
    "generate_report", "report_from_jsonl",
    # corpus
    "export_corpus", "describe",
]
