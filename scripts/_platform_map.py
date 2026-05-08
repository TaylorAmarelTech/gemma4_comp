"""Single canonical Duecare platform-map data.

Used by `scripts/build_notebook_*.py` to render the 8-component
platform overview as a notebook cell using the shared helpers in
`_notebook_display.py`. Keeping this list in ONE place avoids the
stale-number problem we hit with 21-dim / 33-doc / etc.: when a
component flips status (Roadmap → Prototype → Live), it's a one-file
edit and every notebook + page that uses it picks up the change.

Component shape:

    name              short_name (used in compact tables)
    status            "Live" | "Prototype" | "Roadmap"
    primary_users     list of: "platforms", "ngo_gov", "researchers", "workers"
    inputs            short list — what feeds the component
    outputs           short list — what it produces
    demo_visible      bool — does a judge see this in the live demo?
    risk_boundary     one-line safety note ("never X / always Y")

Status colors:

    Live      green   in production at submission time
    Prototype amber   shipped as appendix / prototype, not multi-tenant
    Roadmap   muted   documented design target, no code in critical path
"""

from __future__ import annotations

from typing import TypedDict


class Component(TypedDict):
    n:             int
    name:          str
    short_name:    str
    status:        str  # "Live" | "Prototype" | "Roadmap"
    primary_users: list[str]
    inputs:        list[str]
    outputs:       list[str]
    demo_visible:  bool
    risk_boundary: str
    viewer_path:   str  # /static/<page>.html or "" if no static viewer
    docs_path:     str  # docs/architecture/<file>.md


COMPONENTS: list[Component] = [
    {
        "n":             1,
        "name":          "Duecare Runtime",
        "short_name":    "Runtime",
        "status":        "Live",
        "primary_users": ["workers", "ngo_gov", "platforms", "researchers"],
        "inputs":        ["chat messages", "image attachments"],
        "outputs":       ["sanitized model output", "tool calls"],
        "demo_visible":  True,
        "risk_boundary": "model does NOT own truth — laws / contacts / policy come from upstream",
        "viewer_path":   "",
        "docs_path":     "docs/architecture/duecare_runtime.md",
    },
    {
        "n":             2,
        "name":          "Duecare Harness",
        "short_name":    "Harness",
        "status":        "Live",
        "primary_users": ["workers", "ngo_gov", "platforms", "researchers"],
        "inputs":        ["user prompt", "GREP rules", "RAG corpus", "tool tables", "contacts"],
        "outputs":       ["grounded response", "audit trace", "fired-rule list"],
        "demo_visible":  True,
        "risk_boundary": "auditable, deterministic; trace shows why every flag fired",
        "viewer_path":   "/static/harness.html",
        "docs_path":     "docs/architecture/duecare_harness.md",
    },
    {
        "n":             3,
        "name":          "Duecare Exchange",
        "short_name":    "Exchange",
        "status":        "Roadmap",
        "primary_users": ["ngo_gov", "platforms", "researchers"],
        "inputs":        ["partner-submitted proposals (anonymized)"],
        "outputs":       ["signed knowledge packs"],
        "demo_visible":  False,
        "risk_boundary": "raw cases stay local; only anonymized signals shared",
        "viewer_path":   "",
        "docs_path":     "docs/architecture/duecare_exchange.md",
    },
    {
        "n":             4,
        "name":          "Duecare Eval",
        "short_name":    "Eval",
        "status":        "Partial",
        "primary_users": ["researchers", "platforms", "ngo_gov"],
        "inputs":        ["model responses", "ground-truth refs", "adversarial prompts"],
        "outputs":       ["46-dim scores", "regression reports", "lift numbers"],
        "demo_visible":  True,
        "risk_boundary": "gates every new rule / RAG doc / rubric dim before release",
        "viewer_path":   "",
        "docs_path":     "docs/architecture/duecare_eval.md",
    },
    {
        "n":             5,
        "name":          "Duecare Trainer",
        "short_name":    "Trainer",
        "status":        "Prototype",
        "primary_users": ["researchers", "ngo_gov", "platforms"],
        "inputs":        ["anonymized case data", "synthetic evidence", "graded responses"],
        "outputs":       ["LoRA adapters", "GGUF / LiteRT exports", "HF Hub model cards"],
        "demo_visible":  False,
        "risk_boundary": "PII gate before training; evaluation gate before release",
        "viewer_path":   "",
        "docs_path":     "docs/architecture/duecare_trainer.md",
    },
    {
        "n":             6,
        "name":          "Duecare Sentinel",
        "short_name":    "Sentinel",
        "status":        "Roadmap",
        "primary_users": ["ngo_gov", "researchers"],
        "inputs":        ["public sources (laws / NGO reports / advisories)"],
        "outputs":       ["update proposals (never auto-applied)"],
        "demo_visible":  False,
        "risk_boundary": "agent proposes; humans approve; no silent mutations",
        "viewer_path":   "",
        "docs_path":     "docs/architecture/duecare_sentinel.md",
    },
    {
        "n":             7,
        "name":          "Duecare Channels",
        "short_name":    "Channels",
        "status":        "Roadmap",
        "primary_users": ["ngo_gov", "workers"],
        "inputs":        ["worker messages on Messenger / WhatsApp / SMS / web"],
        "outputs":       ["grounded replies", "draft complaints", "human handoff"],
        "demo_visible":  False,
        "risk_boundary": "Duecare drafts; the user or trusted caseworker decides — never auto-send",
        "viewer_path":   "",
        "docs_path":     "docs/architecture/duecare_channels.md",
    },
    {
        "n":             8,
        "name":          "Duecare Mobile",
        "short_name":    "Mobile",
        "status":        "Live",  # sibling repo
        "primary_users": ["workers"],
        "inputs":        ["recruiter messages", "screenshots", "contracts"],
        "outputs":       ["risk explanations", "draft reports", "trusted contacts"],
        "demo_visible":  False,  # sibling repo APK, not in this notebook
        "risk_boundary": "private risk check + resource guide — no auto-report, no confront-employer advice",
        "viewer_path":   "",
        "docs_path":     "docs/architecture/duecare_mobile.md",
    },
]


# Status badge colors (match _notebook_display palette + brand
# severity palette).
STATUS_COLOR: dict[str, str] = {
    "Live":      "#10b981",  # green
    "Prototype": "#f59e0b",  # amber
    "Partial":   "#3b82f6",  # blue
    "Roadmap":   "#94a3b8",  # muted
}


USER_GROUP_LABEL: dict[str, str] = {
    "platforms":   "Platform Safety",
    "ngo_gov":     "NGO / Regulators",
    "workers":     "Migrant Worker Chat",
    "researchers": "Academic Research",
}


# ---------------------------------------------------------------------------
# Utilities for notebook-builder scripts to consume
# ---------------------------------------------------------------------------

def status_counts() -> dict[str, int]:
    """How many components in each status. For a stat-cards row."""
    out: dict[str, int] = {"Live": 0, "Prototype": 0, "Partial": 0, "Roadmap": 0}
    for c in COMPONENTS:
        out[c["status"]] = out.get(c["status"], 0) + 1
    return out


def render_pipeline_steps() -> list[dict]:
    """List of {label, color} for show_pipeline_diagram()."""
    return [
        {"label": c["short_name"], "color": STATUS_COLOR[c["status"]]}
        for c in COMPONENTS
    ]


def render_component_table_rows() -> list[dict]:
    """Records suitable for show_table()."""
    rows = []
    for c in COMPONENTS:
        rows.append({
            "#":            c["n"],
            "Component":    c["name"],
            "Status":       c["status"],
            "Demo visible": "✓" if c["demo_visible"] else "—",
            "Primary users": ", ".join(USER_GROUP_LABEL[u] for u in c["primary_users"]),
            "Risk boundary": c["risk_boundary"],
        })
    return rows


__all__ = [
    "Component", "COMPONENTS", "STATUS_COLOR", "USER_GROUP_LABEL",
    "status_counts", "render_pipeline_steps", "render_component_table_rows",
]
