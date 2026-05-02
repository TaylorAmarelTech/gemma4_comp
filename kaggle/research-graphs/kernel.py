"""
============================================================================
  DUECARE RESEARCH GRAPHS -- Kaggle notebook (paste into a single code cell)
============================================================================

  APPENDIX notebook (third). Visualization + research playground for
  judges, NGO partners, and researchers who want to inspect the
  harness data and any benchmark results.

  No model load required -- this kernel renders interactive Plotly
  charts from the bundled harness data (22 GREP rules, 18 RAG docs,
  4 corridor fee caps, 16 fee-camouflage labels, 11 ILO indicators,
  4 NGO intake hotlines, 204 example prompts) and from any
  benchmark / classifier outputs in the attached eval-results dataset.

  Charts produced:

    1. ENTITY GRAPH (Plotly network) -- recruiters, employers, money
       flows, victim cases extracted from the bundled sample corpus.
       Colored by entity type, sized by co-occurrence degree.

    2. CORRIDOR SANKEY -- worker-flow corridors (PH->HK, NP->Gulf,
       BD->Gulf, ID->HK) with controlling fee cap statutes overlaid
       as edge labels.

    3. PER-CATEGORY BENCHMARK BARS -- stock vs fine-tuned pass rates
       across the 11 prompt categories. Reads from the attached
       eval-results dataset; gracefully skips if no benchmark runs
       are present.

    4. FEE CAMOUFLAGE HEATMAP -- co-occurrence of the 16 known fee-
       camouflage labels across the 204 example prompts (which fees
       appear together in real scenarios).

    5. ILO INDICATOR HIT-RATE -- which of the 11 ILO indicators of
       forced labour fire most often, broken down by prompt category.

    6. RAG CORPUS STRUCTURE -- the 18-document BM25 corpus organized
       as a sunburst by source family (ILO conventions, POEA MCs,
       BP2MI Reg, HK statutes, NGO briefs).

  Requirements:
    - GPU: NOT required (pure visualization)
    - Internet: not required
    - Wheels dataset: duecare-research-graphs-wheels (3 wheels: core,
      chat, benchmark)
    - Optional: duecare-eval-results dataset (for chart 3)

  Expected runtime: ~30 sec end-to-end on CPU.

============================================================================
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


# ===========================================================================
# CONFIG
# ===========================================================================
DATASET_SLUG = "duecare-research-graphs-wheels"
EVAL_RESULTS_SLUG = "duecare-eval-results"   # optional
OUTPUT_DIR = Path("/kaggle/working/research_graphs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# PHASE 1 -- install only what we need (Plotly + NetworkX + duecare wheels)
# ===========================================================================
def install_deps() -> None:
    print("=" * 76)
    print("[phase 1] installing dependencies")
    print("=" * 76)
    deps = ["plotly>=5.20.0", "networkx>=3.2", "pandas>=2.0", "numpy>=1.26"]
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--no-input",
           "--disable-pip-version-check", *deps]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  WARN: dep install non-zero ({proc.returncode}): {proc.stderr[-300:]}")
    else:
        print(f"  installed: {' '.join(deps)}")

    # duecare wheels
    if not Path("/kaggle/input").exists():
        print("  /kaggle/input absent; assume local dev")
        return
    wheels = sorted(p for p in Path("/kaggle/input").rglob("*.whl")
                    if "duecare" in p.name.lower())
    print(f"  found {len(wheels)} duecare wheel(s)")
    if wheels:
        cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--no-input",
               "--disable-pip-version-check", *[str(w) for w in wheels]]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            print(f"  installed {len(wheels)} duecare wheels")
            for mod in list(sys.modules):
                if mod == "duecare" or mod.startswith("duecare."):
                    del sys.modules[mod]
        else:
            print(f"  duecare wheel install FAILED: {proc.stderr[-300:]}")


install_deps()


# ===========================================================================
# Lazy imports -- after dep install
# ===========================================================================
import plotly.graph_objects as go
import plotly.io as pio
import networkx as nx


# ===========================================================================
# Load harness data
# ===========================================================================
def load_harness_data() -> dict[str, Any]:
    print("=" * 76)
    print("[load] reading harness data")
    print("=" * 76)
    try:
        from duecare.chat.harness import (
            GREP_RULES, RAG_CORPUS, CORRIDOR_FEE_CAPS,
            FEE_CAMOUFLAGE_DICT, NGO_INTAKE, ILO_INDICATORS,
            EXAMPLE_PROMPTS, CLASSIFIER_EXAMPLES, _TOOL_DISPATCH,
        )
    except Exception as e:
        print(f"  duecare.chat.harness import FAILED: {e}")
        return {}
    out = {
        "grep_rules":          list(GREP_RULES),
        "rag_corpus":          list(RAG_CORPUS),
        "corridor_fee_caps":   dict(CORRIDOR_FEE_CAPS),
        "fee_camouflage":      dict(FEE_CAMOUFLAGE_DICT),
        "ngo_intake":          dict(NGO_INTAKE),
        "ilo_indicators":      list(ILO_INDICATORS),
        "example_prompts":     list(EXAMPLE_PROMPTS),
        "classifier_examples": list(CLASSIFIER_EXAMPLES),
        "tool_names":          list(_TOOL_DISPATCH.keys()),
    }
    print(f"  GREP rules: {len(out['grep_rules'])}")
    print(f"  RAG docs: {len(out['rag_corpus'])}")
    print(f"  Corridor fee caps: {len(out['corridor_fee_caps'])}")
    print(f"  Fee camouflage labels: {len(out['fee_camouflage'])}")
    print(f"  NGO intake hotlines: {len(out['ngo_intake'])}")
    print(f"  ILO indicators: {len(out['ilo_indicators'])}")
    print(f"  Example prompts: {len(out['example_prompts'])}")
    print(f"  Classifier examples: {len(out['classifier_examples'])}")
    print(f"  Tools: {len(out['tool_names'])}")
    return out


HARNESS = load_harness_data()


# ===========================================================================
# CHART 1 -- entity graph
# ===========================================================================
def chart_entity_graph(harness: dict) -> Path:
    """Render a force-directed network of entities extracted from the
    bundled sample corpus (recruiters / employers / money / victims)."""
    print("[chart 1] entity graph")
    # Hardcoded sample corpus entities (mirrors the live-demo's
    # pre-loaded evidence DB for reproducibility without ingest).
    nodes = [
        ("Pacific Coast Manpower",     "recruitment_agency", 5, "#ef4444"),
        ("Al-Rashid Household Services", "employer",         3, "#f59e0b"),
        ("Hong Kong City Credit Mgmt", "lender",             2, "#dc2626"),
        ("USD 1500 placement fee",     "money",              3, "#3b82f6"),
        ("HKD 25000 loan",             "money",              2, "#3b82f6"),
        ("AB1234567 (passport)",       "passport_id",        2, "#6b7280"),
        ("NP9876543 (passport)",       "passport_id",        2, "#6b7280"),
        ("Maria Santos (composite)",   "victim",             2, "#10b981"),
        ("Sita Tamang (composite)",    "victim",             2, "#10b981"),
        ("ILO C029 indicator: passport retention", "indicator", 4, "#a855f7"),
        ("HK Money Lenders Ord §24",   "statute",            2, "#a855f7"),
        ("PH RA 8042 §6(a)",           "statute",            1, "#a855f7"),
    ]
    edges = [
        (0, 3, "charged_fee"),
        (0, 1, "referred_to"),
        (1, 5, "withholds"),
        (1, 7, "employs"),
        (0, 7, "recruited"),
        (2, 4, "issued_loan"),
        (2, 8, "creditor_of"),
        (1, 6, "withholds"),
        (5, 9, "violates"),
        (4, 10, "violates"),
        (3, 11, "violates"),
    ]

    G = nx.Graph()
    for i, (label, kind, deg, color) in enumerate(nodes):
        G.add_node(i, label=label, kind=kind, deg=deg, color=color)
    for a, b, rel in edges:
        G.add_edge(a, b, rel=rel)

    pos = nx.spring_layout(G, seed=17, k=0.9)

    # Edge traces
    edge_x: list[Any] = []
    edge_y: list[Any] = []
    for a, b in G.edges():
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=1.2, color="#9ca3af"),
        hoverinfo="none", showlegend=False)

    # Node traces -- one per kind for color legend
    by_kind: dict[str, list[int]] = defaultdict(list)
    for i, n in G.nodes(data=True):
        by_kind[n["kind"]].append(i)

    node_traces = []
    for kind, ids in by_kind.items():
        x = [pos[i][0] for i in ids]
        y = [pos[i][1] for i in ids]
        text = [G.nodes[i]["label"] for i in ids]
        sizes = [10 + 6 * G.nodes[i]["deg"] for i in ids]
        color = G.nodes[ids[0]]["color"]
        node_traces.append(go.Scatter(
            x=x, y=y, mode="markers+text",
            text=text, textposition="top center",
            textfont=dict(size=10),
            marker=dict(size=sizes, color=color,
                        line=dict(color="white", width=2)),
            name=kind.replace("_", " ").title(),
            hovertemplate="<b>%{text}</b><br>type: " + kind + "<extra></extra>",
        ))

    fig = go.Figure(data=[edge_trace, *node_traces])
    fig.update_layout(
        title=("<b>Entity graph from sample corpus</b><br>"
               "<span style='font-size:11px;color:#6b7280'>"
               "Recruiters, employers, money flows, passport retention "
               "incidents, victim cases (composite), and the ILO/national "
               "statutes each violated</span>"),
        showlegend=True, hovermode="closest",
        margin=dict(t=80, l=20, r=20, b=20),
        plot_bgcolor="#f8fafc", paper_bgcolor="white",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=600,
    )
    out = OUTPUT_DIR / "01_entity_graph.html"
    pio.write_html(fig, str(out), include_plotlyjs="cdn")
    print(f"  -> {out}")
    return out


# ===========================================================================
# CHART 2 -- corridor Sankey
# ===========================================================================
def chart_corridor_sankey(harness: dict) -> Path:
    """Worker-flow corridors with controlling fee-cap statutes."""
    print("[chart 2] corridor flow Sankey")
    caps = harness.get("corridor_fee_caps", {})
    if not caps:
        # Fallback hardcoded
        caps = {
            "ph_hk":  {"fee_cap_amount": "HK$ 0",  "fee_cap_statute": "POEA MC 14-2017 (zero-fee)"},
            "ph_sa":  {"fee_cap_amount": "USD 0",  "fee_cap_statute": "PH RA 10022 §6"},
            "id_hk":  {"fee_cap_amount": "HK$ 0",  "fee_cap_statute": "BP2MI Reg 9/2020"},
            "np_qa":  {"fee_cap_amount": "NPR 10K","fee_cap_statute": "Nepal FEA 2007 §11(2)"},
            "np_sa":  {"fee_cap_amount": "NPR 10K","fee_cap_statute": "Nepal FEA 2007 §11(2)"},
            "bd_sa":  {"fee_cap_amount": "BDT 0",  "fee_cap_statute": "BD OEA 2013"},
            "lk_kw":  {"fee_cap_amount": "LKR 0",  "fee_cap_statute": "SLBFE Act"},
        }

    # Build flows: origin -> destination
    countries = {
        "ph": "Philippines", "id": "Indonesia", "np": "Nepal",
        "bd": "Bangladesh", "lk": "Sri Lanka",
        "hk": "Hong Kong", "sa": "Saudi Arabia", "qa": "Qatar",
        "ae": "UAE", "kw": "Kuwait",
    }
    sources, targets, values, labels_set = [], [], [], set()
    for corridor, info in caps.items():
        if "_" not in corridor:
            continue
        o, d = corridor.split("_", 1)
        o_full = countries.get(o, o.upper())
        d_full = countries.get(d, d.upper())
        labels_set.add(o_full)
        labels_set.add(d_full)
    label_idx = {lbl: i for i, lbl in enumerate(sorted(labels_set))}

    edge_labels = []
    for corridor, info in caps.items():
        if "_" not in corridor:
            continue
        o, d = corridor.split("_", 1)
        o_full = countries.get(o, o.upper())
        d_full = countries.get(d, d.upper())
        sources.append(label_idx[o_full])
        targets.append(label_idx[d_full])
        values.append(1)
        statute = info.get("fee_cap_statute", "?") if isinstance(info, dict) else "?"
        cap_amt = info.get("fee_cap_amount", "?") if isinstance(info, dict) else "?"
        edge_labels.append(f"{cap_amt}<br>{statute}")

    fig = go.Figure(go.Sankey(
        node=dict(
            label=sorted(labels_set),
            color=[("#3b82f6" if any(c.lower() in lbl.lower()
                                      for c in ("Hong Kong", "Saudi", "Qatar",
                                                 "UAE", "Kuwait"))
                    else "#10b981")
                   for lbl in sorted(labels_set)],
            pad=20, thickness=20,
        ),
        link=dict(
            source=sources, target=targets, value=values,
            label=edge_labels,
            color="rgba(76, 120, 168, 0.35)",
        ),
    ))
    fig.update_layout(
        title=("<b>Migration corridors with controlling fee-cap statutes</b><br>"
               "<span style='font-size:11px;color:#6b7280'>"
               "Hover an edge to see the corridor's controlling fee cap "
               "and the statute that imposes it. Origin countries (green) "
               "to destinations (blue).</span>"),
        height=550, margin=dict(t=80, l=20, r=20, b=20),
    )
    out = OUTPUT_DIR / "02_corridor_sankey.html"
    pio.write_html(fig, str(out), include_plotlyjs="cdn")
    print(f"  -> {out}")
    return out


# ===========================================================================
# CHART 3 -- benchmark per-category bars (stock vs fine-tuned)
# ===========================================================================
def chart_benchmark_bars() -> Path | None:
    """Read /kaggle/input/duecare-eval-results/* if present and render
    per-category pass-rate bars stock vs fine-tuned."""
    print("[chart 3] benchmark per-category bars")
    eval_dir = None
    for cand in (Path("/kaggle/input/duecare-eval-results"),
                 Path("/kaggle/working")):
        if cand.is_dir():
            eval_dir = cand
            break
    if eval_dir is None:
        print("  no eval-results dir found; skipping chart 3")
        return None

    stock = None
    ft = None
    for f in eval_dir.rglob("*.json"):
        name = f.name.lower()
        if "stock" in name and "aggregate" in name:
            try:
                stock = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
        elif ("fine_tuned" in name or "ft" in name) and "aggregate" in name:
            try:
                ft = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
    if stock is None and ft is None:
        print("  no stock/fine_tuned aggregate JSONs found; skipping chart 3")
        return None

    cats = sorted(set(
        list((stock or {}).get("by_category", {}).keys()) +
        list((ft or {}).get("by_category", {}).keys())
    ))
    if not cats:
        print("  no per-category data; skipping chart 3")
        return None

    stock_rates = [((stock or {}).get("by_category", {})
                     .get(c, {}).get("pass_rate", 0) or 0)
                    for c in cats]
    ft_rates = [((ft or {}).get("by_category", {})
                   .get(c, {}).get("pass_rate", 0) or 0)
                  for c in cats]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=cats, y=stock_rates, name="Stock Gemma 4",
        marker_color="#9ca3af",
        text=[f"{r:.0%}" for r in stock_rates],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=cats, y=ft_rates, name="Fine-tuned (Duecare SFT+DPO)",
        marker_color="#10b981",
        text=[f"{r:.0%}" for r in ft_rates],
        textposition="outside",
    ))
    fig.update_layout(
        title="<b>Per-category benchmark pass-rate: stock vs Duecare fine-tune</b>",
        barmode="group", height=520, margin=dict(t=80, l=60, r=20, b=120),
        xaxis=dict(tickangle=-30),
        yaxis=dict(title="pass rate", tickformat=".0%", range=[0, 1.1]),
        legend=dict(orientation="h", y=-0.3),
    )
    out = OUTPUT_DIR / "03_benchmark_bars.html"
    pio.write_html(fig, str(out), include_plotlyjs="cdn")
    print(f"  -> {out}")
    return out


# ===========================================================================
# CHART 4 -- fee-camouflage co-occurrence heatmap
# ===========================================================================
def chart_fee_camouflage_heatmap(harness: dict) -> Path:
    """Heatmap of which camouflage labels appear together across the
    204 example prompts."""
    print("[chart 4] fee-camouflage co-occurrence heatmap")
    labels = list(harness.get("fee_camouflage", {}).keys())
    if not labels:
        labels = ["training_fee", "medical_fee", "deposit", "bond",
                  "broker_fee", "service_charge", "processing_fee",
                  "transportation_fee"]
    examples = harness.get("example_prompts", [])

    # Build co-occurrence matrix
    n = len(labels)
    mat = [[0] * n for _ in range(n)]
    for ex in examples:
        text = (ex.get("text") or "").lower()
        present = [i for i, lbl in enumerate(labels)
                   if lbl.lower().replace("_", " ") in text
                   or lbl.lower() in text]
        for i in present:
            for j in present:
                mat[i][j] += 1

    fig = go.Figure(go.Heatmap(
        z=mat, x=labels, y=labels,
        colorscale=[[0, "#f8fafc"], [0.5, "#fbbf24"], [1, "#dc2626"]],
        hovertemplate="<b>%{y}</b> + <b>%{x}</b><br>"
                       "co-occurs in %{z} prompts<extra></extra>",
        showscale=True,
        colorbar=dict(title="prompts"),
    ))
    fig.update_layout(
        title=("<b>Fee-camouflage label co-occurrence</b><br>"
               "<span style='font-size:11px;color:#6b7280'>"
               "Which prohibited fee labels appear together in the 204 "
               "example prompts. Diagonal shows self-occurrence.</span>"),
        height=600, margin=dict(t=80, l=140, r=80, b=140),
        xaxis=dict(tickangle=-45),
    )
    out = OUTPUT_DIR / "04_fee_camouflage_heatmap.html"
    pio.write_html(fig, str(out), include_plotlyjs="cdn")
    print(f"  -> {out}")
    return out


# ===========================================================================
# CHART 5 -- ILO indicator hit-rate per category
# ===========================================================================
def chart_ilo_indicator_hits(harness: dict) -> Path:
    """Stacked bars: which ILO indicators fire in which prompt categories."""
    print("[chart 5] ILO indicator hit-rate per prompt category")
    indicators = harness.get("ilo_indicators", [])
    examples = harness.get("example_prompts", [])
    if not indicators or not examples:
        print("  no indicators/examples; skipping chart 5")
        return OUTPUT_DIR / "05_ilo_hits.html"

    # Build (category, indicator) -> count
    by_cat_ind: dict[str, Counter] = defaultdict(Counter)
    for ex in examples:
        cat = ex.get("category") or "uncategorized"
        text = (ex.get("text") or "").lower()
        for ind in indicators:
            if isinstance(ind, dict):
                key = ind.get("name") or ind.get("indicator") or ""
            else:
                key = str(ind)
            if not key:
                continue
            # Crude match: any keyword from the indicator name appears
            tokens = key.lower().split()
            if any(tok in text for tok in tokens if len(tok) > 4):
                by_cat_ind[cat][key] += 1

    cats = sorted(by_cat_ind.keys())
    inds = sorted({k for c in by_cat_ind.values() for k in c.keys()})
    if not cats or not inds:
        print("  no matches; skipping chart 5")
        return OUTPUT_DIR / "05_ilo_hits.html"

    fig = go.Figure()
    palette = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#a855f7",
               "#ec4899", "#14b8a6", "#f97316", "#84cc16", "#6366f1",
               "#06b6d4", "#d946ef"]
    for i, ind in enumerate(inds):
        ys = [by_cat_ind[c].get(ind, 0) for c in cats]
        fig.add_trace(go.Bar(name=ind, x=cats, y=ys,
                              marker_color=palette[i % len(palette)]))
    fig.update_layout(
        barmode="stack",
        title=("<b>ILO indicator hit counts per prompt category</b><br>"
               "<span style='font-size:11px;color:#6b7280'>"
               "Which of the 11 ILO indicators of forced labour are "
               "matched in the 204 example prompts, broken down by "
               "category.</span>"),
        height=560, margin=dict(t=80, l=60, r=20, b=140),
        xaxis=dict(tickangle=-30),
        yaxis=dict(title="prompt count"),
        legend=dict(orientation="v", x=1.02, y=1, font=dict(size=10)),
    )
    out = OUTPUT_DIR / "05_ilo_hits.html"
    pio.write_html(fig, str(out), include_plotlyjs="cdn")
    print(f"  -> {out}")
    return out


# ===========================================================================
# CHART 6 -- RAG corpus sunburst
# ===========================================================================
def chart_rag_corpus_sunburst(harness: dict) -> Path:
    """Sunburst of the 18-doc RAG corpus organized by source family."""
    print("[chart 6] RAG corpus sunburst")
    docs = harness.get("rag_corpus", [])
    if not docs:
        print("  empty rag_corpus; skipping chart 6")
        return OUTPUT_DIR / "06_rag_sunburst.html"

    # Categorize each doc by source
    def family(doc):
        src = (doc.get("source") or "").lower()
        title = (doc.get("title") or "").lower()
        if "ilo" in src or "ilo" in title or "c029" in title:
            return "ILO conventions"
        if "poea" in src or "poea" in title:
            return "Philippines (POEA)"
        if "bp2mi" in src or "bp2mi" in title or "indonesia" in src:
            return "Indonesia (BP2MI)"
        if ("hk " in src.lower() or "hong kong" in src or "hong kong" in title
                or "money lenders" in title):
            return "Hong Kong statutes"
        if "nepal" in src or "nepal" in title:
            return "Nepal"
        if any(k in src or k in title for k in ("polaris", "ijm", "ecpat",
                                                  "verite", "mfmw")):
            return "NGO briefs"
        return "Other"

    labels = ["RAG corpus"]
    parents = [""]
    values = [len(docs)]
    family_groups: dict[str, list] = defaultdict(list)
    for d in docs:
        family_groups[family(d)].append(d)
    for fam, group in family_groups.items():
        labels.append(fam)
        parents.append("RAG corpus")
        values.append(len(group))
        for d in group:
            tid = d.get("id") or d.get("title", "")[:20]
            labels.append(tid)
            parents.append(fam)
            values.append(1)

    fig = go.Figure(go.Sunburst(
        labels=labels, parents=parents, values=values,
        branchvalues="total",
        marker=dict(colors=[f"hsl({i*40 % 360}, 60%, 65%)"
                              for i in range(len(labels))]),
        hovertemplate="<b>%{label}</b><br>%{value} doc(s)<extra></extra>",
    ))
    fig.update_layout(
        title=("<b>RAG corpus structure (18 documents)</b><br>"
               "<span style='font-size:11px;color:#6b7280'>"
               "Click a slice to drill in. Outer ring: individual "
               "documents. Inner ring: source family.</span>"),
        height=600, margin=dict(t=80, l=20, r=20, b=20),
    )
    out = OUTPUT_DIR / "06_rag_sunburst.html"
    pio.write_html(fig, str(out), include_plotlyjs="cdn")
    print(f"  -> {out}")
    return out


# ===========================================================================
# Index + main
# ===========================================================================
def write_index(charts: list[Path]) -> Path:
    """Write a single index.html that links to all six charts so a judge
    can navigate them from one page."""
    rows = []
    for c in charts:
        if c is None or not c.exists():
            continue
        title = c.stem.split("_", 1)[1].replace("_", " ").title()
        rows.append(
            f'<li><a href="{c.name}" style="color:#1e40af;font-weight:600;'
            f'text-decoration:none">{title}</a> '
            f'<span style="color:#6b7280;font-size:12px">'
            f'({c.stat().st_size // 1024} KB)</span></li>')
    html = f"""<!doctype html><html><head>
<meta charset="utf-8"><title>Duecare Research Graphs</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif;
         max-width: 760px; margin: 40px auto; padding: 0 20px;
         color: #1f2937; background: #f8fafc; }}
  h1 {{ color: #1e40af; letter-spacing: -0.02em; }}
  ul {{ background: white; padding: 24px 40px; border-radius: 12px;
        border: 1px solid #e5e7eb; line-height: 2; }}
  .badge {{ display: inline-block; background: #ddd6fe; color: #5b21b6;
            padding: 2px 8px; border-radius: 999px; font-size: 11px;
            font-weight: 600; margin-left: 8px; }}
</style></head><body>
<h1>Duecare Research Graphs <span class="badge">Appendix · Visualization</span></h1>
<p style="color:#6b7280;line-height:1.6">
  Six interactive Plotly charts rendered from the bundled Duecare
  harness data. Click any link to open the chart in a new view.
</p>
<ul>{''.join(rows)}</ul>
<p style="color:#6b7280;font-size:12px;margin-top:30px">
  Built with Google's Gemma 4 ecosystem. Charts use Plotly + NetworkX
  on CPU only — no GPU or model load required.
</p>
</body></html>"""
    out = OUTPUT_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


def main() -> None:
    if not HARNESS:
        print("[main] no harness data loaded; cannot render charts")
        sys.exit(1)
    charts = [
        chart_entity_graph(HARNESS),
        chart_corridor_sankey(HARNESS),
        chart_benchmark_bars(),
        chart_fee_camouflage_heatmap(HARNESS),
        chart_ilo_indicator_hits(HARNESS),
        chart_rag_corpus_sunburst(HARNESS),
    ]
    idx = write_index(charts)
    print("=" * 76)
    print(f"[done] {len([c for c in charts if c])} chart(s) written to {OUTPUT_DIR}")
    print(f"  open: {idx}")
    print("=" * 76)
    # Show inline in the Kaggle notebook if IPython available
    try:
        from IPython.display import IFrame, display
        for c in charts:
            if c and c.exists():
                display(IFrame(src=str(c), width="100%", height="600"))
    except Exception:
        pass


if __name__ == "__main__":
    main()
