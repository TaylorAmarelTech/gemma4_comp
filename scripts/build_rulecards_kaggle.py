#!/usr/bin/env python3
# ruff: noqa: E501  (embedded Kaggle notebook cell source has long matplotlib lines)
"""Package the RuleCard deck as a public Kaggle dataset + a visual notebook.

Builds a self-contained Kaggle dataset directory (typed deck, independence
report, summary, flat CSV, data card, license, metadata, release manifest) and
a CPU notebook that renders the correlated-witness result: 451 real GREP rules
collapsing to ~80 witness families and an effective-independent-witness range
under the design-effect formula. Everything is derived deterministically from
the real rules; no model is called and nothing is invented.

The dataset carries only rule metadata (ids, severities, legal citations,
inferred roles, witness families) -- no worker data, no PII, no case content.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GREP_RULES_PATH = (
    ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat"
    / "harness" / "_grep_rules.py"
)
DEFAULT_OUTPUT = ROOT / "reports" / "kaggle_publish" / "rulecard_supervision_fabric_v1"
DATASET_ID = "taylorsamarel/duecare-rulecard-supervision-fabric"
NOTEBOOK_ID = "taylorsamarel/duecare-rulecard-witness-atlas"
TITLE = "DueCare RuleCard Supervision Fabric"
NOTEBOOK_TITLE = "DueCare RuleCard Witness Atlas"
MARKER = ".duecare-rulecard-kaggle"

_RC_SPEC = importlib.util.spec_from_file_location(
    "duecare_rulecards",
    ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "rulecards.py",
)
assert _RC_SPEC and _RC_SPEC.loader
rulecards = importlib.util.module_from_spec(_RC_SPEC)
sys.modules["duecare_rulecards"] = rulecards
_RC_SPEC.loader.exec_module(rulecards)

_BUILD_SPEC = importlib.util.spec_from_file_location(
    "duecare_build_rulecards", ROOT / "scripts" / "build_rulecards.py"
)
assert _BUILD_SPEC and _BUILD_SPEC.loader
build_rulecards = importlib.util.module_from_spec(_BUILD_SPEC)
sys.modules["duecare_build_rulecards"] = build_rulecards
_BUILD_SPEC.loader.exec_module(build_rulecards)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_json(path: Path, value: Any) -> None:
    _write(path, json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n")


def _deck_csv(cards: list[Any]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["rule_id", "category", "severity", "authoritative_sources", "jurisdictions",
         "roles", "witness_family", "candidate_invariant_review"]
    )
    for card in cards:
        writer.writerow([
            card.rule_id, card.category, card.severity,
            "; ".join(card.authoritative_sources), "; ".join(card.jurisdictions),
            "; ".join(card.roles), card.witness_family,
            str(card.candidate_invariant_review).lower(),
        ])
    return buffer.getvalue()


def _prepare_output(path: Path, *, force: bool) -> Path:
    path = path.resolve()
    if path.exists():
        if not force:
            raise RuntimeError(f"output exists; pass --force to replace: {path.name}")
        if not (path / MARKER).is_file():
            raise RuntimeError("refusing to replace a directory this builder did not create")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / MARKER).write_text("duecare.rulecard_kaggle.v1\n", encoding="utf-8")
    return path


def build(output_dir: Path, *, force: bool, grep_path: Path = GREP_RULES_PATH) -> dict[str, Any]:
    rules = build_rulecards.load_grep_rules(grep_path)
    categories = build_rulecards.categories_by_rule_order(grep_path)
    if len(categories) != len(rules):
        categories = ["uncategorized"] * len(rules)
    cards = rulecards.compile_deck(rules, categories)
    deck = [card.to_dict() for card in cards]
    summary = rulecards.deck_summary(cards)
    independence = rulecards.independence_report(cards)

    output_dir = _prepare_output(output_dir, force=force)
    dataset = output_dir / "dataset"
    dataset.mkdir()

    _write_json(dataset / "rulecard-deck.json", {
        "schema_version": rulecards.SCHEMA_VERSION,
        "source": "packages/duecare-llm-chat/src/duecare/chat/harness/_grep_rules.py",
        "cards": deck,
    })
    _write_json(dataset / "rulecard-independence.json", independence)
    _write_json(dataset / "rulecard-summary.json", summary)
    _write(dataset / "rulecards.csv", _deck_csv(cards))
    _write(dataset / "README.md", _dataset_readme(summary, independence))
    _write(dataset / "DATA_CARD.md", _data_card(summary, independence))
    _write(dataset / "LICENSE", _LICENSE)

    # Deterministic release manifest binds every file by SHA-256.
    artifacts = {}
    for path in sorted(dataset.iterdir()):
        if path.is_file():
            artifacts[path.name] = {
                "bytes": path.stat().st_size,
                "sha256": _sha256_bytes(path.read_bytes()),
            }
    release = {
        "schema_version": rulecards.SCHEMA_VERSION,
        "dataset_id": DATASET_ID,
        "total_rules": independence["total_rules"],
        "witness_families": independence["effective_independent_families"],
        "effective_witnesses_by_rho": independence["effective_witnesses_by_rho"],
        "safe_to_publish": True,
        "contains_worker_data_or_pii": False,
        "artifacts": artifacts,
    }
    release_bytes = json.dumps(release, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    _write(dataset / "release-manifest.json", release_bytes)
    _write_json(dataset / "dataset-metadata.json", _dataset_metadata(summary, independence))

    notebook_dir = output_dir / "notebook"
    notebook_dir.mkdir()
    _write_json(notebook_dir / "notebook.ipynb", _notebook())
    _write_json(notebook_dir / "kernel-metadata.json", {
        "id": NOTEBOOK_ID,
        "title": NOTEBOOK_TITLE,
        "code_file": "notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_internet": False,
        "dataset_sources": [DATASET_ID],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    })

    return {
        "output_dir": str(output_dir),
        "dataset_id": DATASET_ID,
        "notebook_id": NOTEBOOK_ID,
        "total_rules": independence["total_rules"],
        "witness_families": independence["effective_independent_families"],
        "effective_witnesses_by_rho": independence["effective_witnesses_by_rho"],
    }


_LICENSE = """Creative Commons Attribution 4.0 International (CC BY 4.0)

This dataset contains only rule metadata (identifiers, severities, legal
citations, inferred supervision roles, and correlated-witness family
assignments) derived from DueCare's open GREP indicator rules. It contains no
worker data, no personal data, and no case content.
"""

SUBTITLE = "451 trafficking-indicator rules as auditable, correlation-aware RuleCards"


def _dataset_metadata(summary: dict[str, Any], independence: dict[str, Any]) -> dict[str, Any]:
    eff = independence["effective_witnesses_by_rho"]
    description = (
        "DueCare's hard-coded trafficking-indicator rules, compiled into auditable "
        "RuleCards, and the weak-supervision result that follows. Each RuleCard is "
        "a fallible labeling function carrying its authoritative legal sources, "
        "antecedent (regex patterns), consequence (severity + indicator reasoning), "
        "inferred jurisdiction, and -- crucially -- the correlated-witness family it "
        "belongs to.\n\n"
        f"The load-bearing result: {independence['total_rules']} rules resolve to "
        f"{independence['effective_independent_families']} correlated-witness "
        f"families (the largest holds {independence['largest_family_rule_count']} "
        "rules). Under the design-effect formula m/(1+(m-1)*rho), the effective "
        f"independent-witness count is about {eff.get('rho_0.9')} (rho=0.9), "
        f"{eff.get('rho_0.7')} (rho=0.7), and {eff.get('rho_0.5')} (rho=0.5) -- far "
        "below the raw rule count. Rules that cite the same legal instrument (e.g. "
        "153 on the Palermo Protocol) are correlated votes, not independent "
        "confirmations, so any weak-supervision label model built on them must "
        "down-weight within-family agreement.\n\n"
        "The dataset carries rule metadata and public legal citations only -- no "
        "worker data, no PII, no case content. Each rule is grounds for inquiry, "
        "not proof, and none are auto-promoted to a runtime invariant. It is "
        "supervision and measurement evidence, never ground truth about any person."
    )
    return {
        "title": TITLE,
        "subtitle": SUBTITLE,
        "id": DATASET_ID,
        "isPrivate": False,
        "licenses": [{"name": "CC-BY-4.0"}],
        "keywords": ["nlp", "text", "classification", "artificial intelligence"],
        "description": description,
        "resources": [
            {"path": "rulecards.csv",
             "description": f"One row per RuleCard ({summary['total_cards']} trafficking-indicator rules) with its metadata.",
             "schema": {"fields": [
                 {"name": "rule_id", "type": "string", "description": "Unique rule identifier (e.g. ilo_indicator_passport_retention)."},
                 {"name": "category", "type": "string", "description": "Exploitation category the rule belongs to (from the rules-file section headers)."},
                 {"name": "severity", "type": "string", "description": "critical / high / medium / low / info."},
                 {"name": "authoritative_sources", "type": "string", "description": "Semicolon-separated legal instruments the citation anchors on (e.g. ILO C189; HK Cap. 57)."},
                 {"name": "jurisdictions", "type": "string", "description": "Inferred jurisdiction codes (e.g. HK; PH)."},
                 {"name": "roles", "type": "string", "description": "Inferred supervision roles: labeling_function; feature_extractor."},
                 {"name": "witness_family", "type": "string", "description": "Correlated-witness family key (shared legal anchor or category)."},
                 {"name": "candidate_invariant_review", "type": "string", "description": "true if the rule is flagged for human hard-invariant review (critical severity)."},
             ]}},
            {"path": "rulecard-deck.json",
             "description": "The full typed RuleCard deck: one object per rule with antecedent, consequence, sources, roles, calibration gaps, and source-rule SHA-256."},
            {"path": "rulecard-independence.json",
             "description": "Correlated-witness families, per-instrument concentration, and effective-independent-witness estimates across rho."},
            {"path": "rulecard-summary.json",
             "description": "Aggregate roll-up: severity counts, source coverage, and human-review candidates."},
        ],
    }


def _dataset_readme(summary: dict[str, Any], independence: dict[str, Any]) -> str:
    eff = independence["effective_witnesses_by_rho"]
    return f"""# {TITLE}

DueCare's hard-coded trafficking-indicator rules, compiled into an auditable
**RuleCard** deck. This turns opaque regex rules into typed supervision objects
and measures the load-bearing weak-supervision insight: **rules that cite the
same legal instrument are correlated witnesses, not independent confirmations.**

## The headline result (measured from the real deck)

- **{summary['total_cards']} RuleCards** compiled from the live GREP rules.
- They resolve to **{independence['effective_independent_families']} correlated-witness families**.
- The largest single family holds **{independence['largest_family_rule_count']} rules**;
  the top five hold **{int(independence['top5_family_concentration'] * 100)}%** of the deck.
- Under the design-effect formula `m/(1+(m-1)*rho)`, the **effective independent
  witness count** is about {eff.get('rho_0.9')} (rho=0.9), {eff.get('rho_0.7')}
  (rho=0.7), and {eff.get('rho_0.5')} (rho=0.5) -- far below the raw rule count.

## Files

| File | Contents |
|---|---|
| `rulecard-deck.json` | The full typed RuleCard deck (one object per rule). |
| `rulecard-independence.json` | Correlated-witness families + effective-witness estimates. |
| `rulecard-summary.json` | Aggregate roll-up (severity, sources, review candidates). |
| `rulecards.csv` | Flat one-row-per-rule view for quick exploration. |
| `release-manifest.json` | SHA-256 of every file. |

## What this is and is not

Each RuleCard is a fallible **labeling function** and **feature extractor** -- a
vote that a trafficking indicator is present, and a grounds for inquiry, **not
proof**. No rule is auto-promoted to a runtime invariant; critical-severity
rules are flagged for human review only. This deck is supervision and
measurement evidence for building correlation-aware weak supervision. It is not
a trafficking-detection model and must never be treated as ground truth about
any person.

Companion code: `duecare.chat.rulecards`, `scripts/build_rulecards.py`.
Reconciliation with the full best-practice blueprint:
`docs/research/rulecard_supervision_fabric.md`.
"""


def _data_card(summary: dict[str, Any], independence: dict[str, Any]) -> str:
    return f"""# Data card

- **Rows:** {summary['total_cards']} RuleCards (one per GREP indicator rule).
- **Source:** DueCare open GREP indicator rules
  (`packages/duecare-llm-chat/src/duecare/chat/harness/_grep_rules.py`).
- **Fields per card:** rule_id, category, severity, authoritative_sources,
  jurisdictions, antecedent (regex patterns), consequence (severity + indicator
  reasoning + legal citation), roles, witness_family, calibration_gaps,
  candidate_invariant_review, source_rule_sha256.
- **Contains no** worker data, personal data, case content, or free-text
  narratives -- only rule metadata and public legal citations.
- **Severity distribution:** {summary['severity_counts']}.
- **Correlated-witness families:** {independence['effective_independent_families']}.
- **License:** CC BY 4.0.
- **Intended use:** research on correlation-aware weak supervision and auditable
  rule governance. **Not** for automated trafficking determinations.
"""


# --- Notebook -----------------------------------------------------------------

def _md(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "id": identifier, "metadata": {},
            "source": source.splitlines(True)}


def _code(identifier: str, source: str) -> dict[str, Any]:
    return {"cell_type": "code", "execution_count": None, "id": identifier,
            "metadata": {}, "outputs": [], "source": source.splitlines(True)}


def _notebook() -> dict[str, Any]:
    cells = [
        _md("banner", """<div style="padding:28px 32px;border-radius:18px;background:linear-gradient(120deg,#102a43,#136f63,#f2b134);color:white">
<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.85">DueCare | supervision fabric</div>
<h1 style="margin:.3em 0 .2em;font-size:32px">RuleCards: correlated witnesses, not independent confirmations</h1>
<p style="font-size:16px;line-height:1.5;margin:0;max-width:900px">DueCare's hard-coded trafficking-indicator rules, compiled into auditable RuleCards, and the weak-supervision result that follows: many rules, far fewer independent witnesses.</p>
</div>"""),
        _md("intro", """## The question this notebook answers

DueCare's harness has hundreds of hard-coded trafficking-indicator rules. A
natural mistake is to treat every rule that fires as an independent
confirmation. But rules that cite the same legal instrument -- for example the
Palermo Protocol -- are **correlated witnesses**. If a weak-supervision label
model counts them as independent, one legal principle expressed as many patterns
masquerades as many confirmations and badly inflates confidence.

This notebook compiles the real rule deck into RuleCards and measures how many
**independent witness families** it really contains."""),
        _code("setup", """import json, os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import Markdown, display

COLORS = ["#136f63", "#f2b134", "#d1495b", "#247ba0", "#6d597a", "#4f772d"]
plt.rcParams.update({"figure.figsize": (11, 5.6), "figure.dpi": 115,
                     "axes.facecolor": "#f7faf9", "axes.edgecolor": "#bed2cc",
                     "axes.grid": True, "grid.alpha": 0.2, "font.size": 11})

def find_dataset():
    candidates = []
    override = os.environ.get("DUECARE_RULECARD_ROOT")
    if override:
        candidates.append(Path(override))
    if Path("/kaggle/input").exists():
        candidates.extend(p.parent for p in Path("/kaggle/input").rglob("rulecard-independence.json"))
    candidates.extend(p.parent for p in Path.cwd().rglob("rulecard-independence.json"))
    for root in candidates:
        if (root / "rulecard-independence.json").is_file():
            return root
    raise FileNotFoundError("Attach the duecare-rulecard-supervision-fabric dataset")

root = find_dataset()
independence = json.loads((root / "rulecard-independence.json").read_text(encoding="utf-8"))
summary = json.loads((root / "rulecard-summary.json").read_text(encoding="utf-8"))
deck = json.loads((root / "rulecard-deck.json").read_text(encoding="utf-8"))["cards"]
in_kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) or Path("/kaggle/input").exists()
out_dir = Path(os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR", "/kaggle/working" if in_kaggle else Path.cwd()))
out_dir.mkdir(parents=True, exist_ok=True)
display(Markdown(f"**Loaded {summary['total_cards']} RuleCards** resolving to **{independence['effective_independent_families']} witness families**."))"""),
        _md("reduction-note", """## 1. Many rules, far fewer independent witnesses

The structural family count treats every rule that shares a primary legal anchor
as one witness family. The design-effect formula `m/(1+(m-1)*rho)` then estimates
the *effective* independent-witness count for a within-family vote correlation
`rho`. `rho=1` collapses each family to a single witness (the structural count);
`rho=0` treats every rule as independent (the raw count). Reporting a range is
honest, because `rho` is an assumption, not a measured constant."""),
        _code("reduction", """total = independence["total_rules"]
families = independence["effective_independent_families"]
eff = independence["effective_witnesses_by_rho"]
rhos = sorted(float(k.split("_")[1]) for k in eff)
values = [eff[f"rho_{r}"] for r in rhos]

fig, axes = plt.subplots(1, 2, figsize=(16, 5.6))
bars = axes[0].bar(["All rules\\n(rho=0)", "Effective\\nrho=0.5", "Effective\\nrho=0.7",
                    "Effective\\nrho=0.9", "Witness families\\n(rho=1)"],
                   [total, eff["rho_0.5"], eff["rho_0.7"], eff["rho_0.9"], families],
                   color=[COLORS[2], COLORS[1], COLORS[1], COLORS[1], COLORS[0]])
axes[0].bar_label(bars, fmt="%.0f", padding=3)
axes[0].set(title="From raw rules to independent witnesses", ylabel="Effective witness count")
axes[0].tick_params(axis="x", rotation=0)

axes[1].plot([0.0] + rhos + [1.0], [total] + values + [families], "o-", color=COLORS[0], lw=2.4, ms=9)
axes[1].set(title="Effective witnesses vs assumed within-family correlation",
            xlabel="within-family vote correlation rho", ylabel="effective witnesses", xlim=(-0.05, 1.05))
for r, v in zip(rhos, values):
    axes[1].annotate(f"{v:.0f}", xy=(r, v), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=9)
fig.tight_layout()
fig.savefig(out_dir / "effective_witnesses.png", bbox_inches="tight")
plt.show()
display(Markdown(independence["effective_witnesses_note"]))"""),
        _md("families-note", """## 2. Which legal instruments anchor the deck

Every RuleCard records the authoritative instruments its citation anchors on.
The counts below show how concentrated the deck is: a small number of
instruments carry most of the rules, so those rules move together as evidence."""),
        _code("sources", """sources = independence["rules_per_authoritative_source"]
top = list(sources.items())[:15]
labels = [s for s, _ in top][::-1]
counts = [c for _, c in top][::-1]
fig, ax = plt.subplots(figsize=(11, 6.2))
bars = ax.barh(labels, counts, color=COLORS[0])
ax.bar_label(bars, padding=3)
ax.set(title="Rules anchored on each authoritative instrument (top 15)", xlabel="rule count")
fig.tight_layout()
fig.savefig(out_dir / "rules_per_source.png", bbox_inches="tight")
plt.show()
display(pd.DataFrame(top, columns=["authoritative instrument", "rules anchored on it"]))"""),
        _md("severity-note", """## 3. Severity and the human-review boundary

Severity is a rule property, not a case conclusion. Critical-severity rules are
flagged as **candidates for human hard-invariant review** -- never
auto-promoted. A pattern match is grounds for inquiry, not proof or action."""),
        _code("severity", """sev = summary["severity_counts"]
fig, axes = plt.subplots(1, 2, figsize=(15, 5.2))
order = [k for k in ["critical", "high", "medium", "low", "info"] if k in sev]
bars = axes[0].bar(order, [sev[k] for k in order],
                   color=[COLORS[2], COLORS[1], COLORS[3], COLORS[5], "#b8c4c0"])
axes[0].bar_label(bars, padding=3)
axes[0].set(title="RuleCards by severity", ylabel="rule count")
review = summary["candidate_invariant_review_count"]
axes[1].bar(["flagged for\\nhuman review", "labeling functions\\n(all cards)"],
            [review, summary["total_cards"]], color=[COLORS[2], COLORS[0]])
axes[1].set(title="No rule is an auto-invariant", ylabel="rule count")
fig.tight_layout()
fig.savefig(out_dir / "severity_and_review.png", bbox_inches="tight")
plt.show()
display(Markdown(f"Every card is a fallible labeling function + feature extractor. "
                 f"**{review} critical cards** are flagged for human hard-invariant review; "
                 f"**none** are auto-promoted."))"""),
        _md("category-note", """## 4. Coverage by rule category

The deck spans many exploitation categories. Category breadth is genuine
coverage, but within a category the rules still share legal anchors, so category
count is not the same as independent-witness count."""),
        _code("categories", """cats = independence["rules_per_category"]
top = [(c, n) for c, n in list(cats.items())[:16] if c != "uncategorized"][::-1]
fig, ax = plt.subplots(figsize=(11, 7))
bars = ax.barh([c for c, _ in top], [n for _, n in top], color=COLORS[3])
ax.bar_label(bars, padding=3)
ax.set(title="Rules per category (top 16)", xlabel="rule count")
fig.tight_layout()
fig.savefig(out_dir / "rules_per_category.png", bbox_inches="tight")
plt.show()"""),
        _code("summary-out", """notebook_summary = {
    "total_rules": independence["total_rules"],
    "witness_families": independence["effective_independent_families"],
    "largest_family_rule_count": independence["largest_family_rule_count"],
    "top5_family_concentration": independence["top5_family_concentration"],
    "effective_witnesses_by_rho": independence["effective_witnesses_by_rho"],
    "severity_counts": summary["severity_counts"],
    "candidate_invariant_review_count": summary["candidate_invariant_review_count"],
    "boundary": "Supervision + measurement evidence. Not a trafficking-detection model; never ground truth about a person.",
}
(out_dir / "rulecard-notebook-summary.json").write_text(json.dumps(notebook_summary, indent=2), encoding="utf-8")
display(Markdown("Saved four charts and a machine-readable summary."))"""),
        _md("close", """## What to do with this

The witness families are the input a **correlation-aware weak-supervision label
model** needs: down-weight within-family agreement so a single legal principle
expressed as many patterns cannot inflate confidence. This is step one of turning
DueCare's hard-coded intelligence into a governed supervision fabric that can
teach, challenge, validate, and constrain learned models -- without ever being
mistaken for ground truth.

Full reconciliation with the best-practice blueprint:
`docs/research/rulecard_supervision_fabric.md`."""),
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _execute_notebook(output_dir: Path) -> None:
    import nbformat
    from nbclient import NotebookClient

    notebook_path = output_dir / "notebook" / "notebook.ipynb"
    out_root = output_dir / "notebook" / "local-output"
    out_root.mkdir(exist_ok=True)
    old_root = os.environ.get("DUECARE_RULECARD_ROOT")
    old_out = os.environ.get("DUECARE_NOTEBOOK_OUTPUT_DIR")
    os.environ["DUECARE_RULECARD_ROOT"] = str(output_dir / "dataset")
    os.environ["DUECARE_NOTEBOOK_OUTPUT_DIR"] = str(out_root)
    try:
        notebook = nbformat.read(notebook_path, as_version=4)
        NotebookClient(notebook, timeout=180, kernel_name="python3",
                       resources={"metadata": {"path": str(notebook_path.parent)}}).execute()
        nbformat.write(notebook, notebook_path.parent / "notebook.executed.ipynb")
    finally:
        for key, old in (("DUECARE_RULECARD_ROOT", old_root),
                         ("DUECARE_NOTEBOOK_OUTPUT_DIR", old_out)):
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    value.add_argument("--grep-rules", type=Path, default=GREP_RULES_PATH)
    value.add_argument("--force", action="store_true")
    value.add_argument("--execute-local", action="store_true")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = build(args.output, force=args.force, grep_path=args.grep_rules)
    if args.execute_local:
        _execute_notebook(Path(result["output_dir"]))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
