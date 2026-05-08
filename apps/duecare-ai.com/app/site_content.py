"""Static public website pages for duecare-ai.com."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class Component:
    """Visible component in the Duecare architecture."""

    name: str
    status: str
    summary: str
    detail: str


@dataclass(frozen=True)
class CatalogItem:
    """Small public catalog entry used by the marketing pages."""

    name: str
    label: str
    summary: str


COMPONENTS: tuple[Component, ...] = (
    Component(
        "Gemma 4 Model Layer",
        "Live",
        "Loads and calls Gemma 4 models for classification, explanation, summarization, multimodal reading, and draft generation.",
        "The public server does not need to run GPU inference; local, Kaggle, mobile, or tenant deployments can call the model.",
    ),
    Component(
        "Safety Guidance Layer",
        "Live",
        "Wraps Gemma 4 with persona, GREP rules, RAG, tools, online search, and imports so answers are grounded and traceable.",
        "Displays fired rules, retrieved sources, tool outputs, imported evidence, and the final draft.",
    ),
    Component(
        "Knowledge Packs",
        "Live",
        "Versioned bundles of GREP data, RAG documents, defined tools, contacts, corridor fees, regulations, examples, and policies.",
        "Displays pack name, version, jurisdiction, source list, change log, and pull instructions.",
    ),
    Component(
        "Quality Testing Framework",
        "Live",
        "Tests model and guidance behavior with text prompts, image prompts, rule-based scoring, LLM-based judging, and regression checks.",
        "Displays scorecards, pass/fail gates, worst-to-best examples, model comparisons, and provenance.",
    ),
    Component(
        "Local Anonymization Module",
        "Prototype",
        "Runs locally or inside a trusted tenant to convert sensitive content into anonymized information objects before anything is shared.",
        "Displays redaction summaries, blocked PII categories, sanitized previews, and local hash receipts.",
    ),
    Component(
        "Information Submission Module",
        "Prototype",
        "Sends only anonymized objects, public-source updates, aggregate counts, or signed pack proposals to the central server.",
        "Displays consent status, payload previews, receipt IDs, and review state.",
    ),
    Component(
        "Central Knowledge Server",
        "Prototype",
        "Receives anonymized submissions, stores review queues, publishes pack metadata, and powers the duecare-ai.com website/API.",
        "Displays public pages, API docs, pack registry, anonymized trends, and curator queues.",
    ),
    Component(
        "Public Information Research Monitor",
        "Roadmap",
        "Uses public-source research tools such as OpenClaw to find updated laws, advisories, trends, negative news, and policies.",
        "Displays discovered sources, crawler status, extracted public facts, and freshness warnings.",
    ),
    Component(
        "Knowledge Formatter",
        "Prototype",
        "Converts scraped public content or submitted observations into standard knowledge objects and pack updates.",
        "Displays extracted fields, confidence, validation issues, and proposed pack diffs.",
    ),
    Component(
        "Stakeholder Engagement Module",
        "Roadmap",
        "Regularly asks subscribers to rank responses, share observations, suggest tools, and submit new public information.",
        "Displays survey prompts, ranking forms, observation forms, and participation status.",
    ),
    Component(
        "Newsletter and Alert Module",
        "Roadmap",
        "Shares reviewed summaries of anonymized patterns and public facts with subscribed NGOs, regulators, and authorized partners.",
        "Displays digest previews, topic filters, subscriber settings, and send logs.",
    ),
    Component(
        "Fine-Tuning Module",
        "Prototype",
        "Fine-tunes or adapts Gemma 4 using approved, anonymized, provenance-tracked examples and stakeholder rankings.",
        "Displays dataset manifests, training status, evaluation gates, model cards, and release artifacts.",
    ),
    Component(
        "Channel and Deployment Package",
        "Prototype",
        "Packages models, guidance layer, knowledge packs, configuration UI, API endpoint, and webhook service for real deployments.",
        "Displays setup steps, endpoint URL, webhook instructions, health checks, and audit traces.",
    ),
)

GREP_CATEGORIES: tuple[CatalogItem, ...] = (
    CatalogItem("Recruitment fees", "economic coercion", "Detects placement fees, salary deductions, hidden debt, and fee camouflage."),
    CatalogItem("Document retention", "control indicator", "Flags passport, visa, contract, and ID confiscation patterns."),
    CatalogItem("Threats and retaliation", "coercion", "Finds deportation threats, blacklisting, isolation, and family-pressure language."),
    CatalogItem("Jailbreak resistance", "model safety", "Catches attempts to force illegal evasion, fake documents, or unsafe procedural guidance."),
    CatalogItem("Complaint routing", "help-seeking", "Surfaces when a user needs contacts, hotlines, consulates, or regulator forms."),
    CatalogItem("Grounding gaps", "evaluation", "Marks claims that should be backed by ILO, corridor, or jurisdiction context."),
)

TOOLS: tuple[CatalogItem, ...] = (
    CatalogItem("Fee-cap checker", "worker-facing", "Compares described fees and deductions against corridor-specific rules."),
    CatalogItem("Complaint draft builder", "draft-only", "Creates a structured complaint draft for a user or caseworker to review and send."),
    CatalogItem("Contact router", "NGO/regulator", "Chooses relevant public hotlines, consulates, NGOs, and government channels."),
    CatalogItem("Citation verifier", "evaluation", "Checks that answers cite the right statute, convention, or knowledge-pack document."),
    CatalogItem("Anonymization gate", "privacy", "Rejects obvious phone, email, address, passport, or ID content before hub storage."),
    CatalogItem("Pack diff reviewer", "curator", "Shows public-source changes proposed by Sentinel before any signed pack update."),
)

CONTEXT_GROUPS: tuple[CatalogItem, ...] = (
    CatalogItem("Philippines → Hong Kong", "domestic work", "Recruitment fees, passport handling, consular escalation, and agency accountability."),
    CatalogItem("Indonesia → Gulf", "domestic work", "Contract substitution, wage withholding, sponsorship risk, and hotline routing."),
    CatalogItem("Nepal → Malaysia", "construction/manufacturing", "Debt pressure, recruitment subagents, medical checks, and complaint mechanisms."),
    CatalogItem("Bangladesh → Singapore", "construction/marine", "Permit dependency, deductions, dormitory conditions, and ministry escalation."),
    CatalogItem("Global maritime", "fishing", "Document retention, isolation at sea, wage theft, and port-state reporting paths."),
    CatalogItem("Cross-border online ads", "platform moderation", "Suspicious job posts, fee language, forged promises, and takedown evidence capture."),
)

USE_CASES: tuple[CatalogItem, ...] = (
    CatalogItem("Platform Safety", "trust & safety", "Social media companies, job platforms, and marketplaces screen risky recruitment posts, warn users, route reviewer queues, and share only anonymized pattern signals."),
    CatalogItem("NGO / Regulators", "trusted review", "NGOs, government regulators, consulates, and labor agencies use grounded drafts, contact routing, complaint-channel context, and signed knowledge packs."),
    CatalogItem("Migrant Worker Chat", "private guidance", "A worker uses a local, mobile, or trusted chat client to understand suspicious messages and documents without sending raw content to the public hub."),
    CatalogItem("Academic Research", "reproducibility", "Researchers, evaluators, auditors, and Kaggle judges rerun notebooks to verify prompts, evaluations, model behavior, and domain-pack provenance."),
)


def _layout(title: str, eyebrow: str, body: str) -> str:
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(title)} — Duecare AI</title>
  <style>
    :root {{ --bg:#07111f; --panel:#0f172a; --panel2:#111c31; --line:rgba(148,163,184,.24); --text:#f8fafc; --muted:#b6c2d2; --blue:#3b82f6; --green:#10b981; --amber:#f59e0b; --red:#ef4444; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; color:var(--text); background:radial-gradient(circle at 15% 0%, rgba(59,130,246,.30), transparent 28%), radial-gradient(circle at 85% 12%, rgba(16,185,129,.20), transparent 32%), var(--bg); }}
    a {{ color:#93c5fd; text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
    header {{ position:sticky; top:0; z-index:2; backdrop-filter:blur(16px); background:rgba(7,17,31,.78); border-bottom:1px solid var(--line); }}
    nav {{ max-width:1180px; margin:0 auto; padding:14px 20px; display:flex; justify-content:space-between; gap:14px; align-items:center; flex-wrap:wrap; }}
    .brand {{ font-weight:950; letter-spacing:-.04em; }}
    .navlinks {{ display:flex; gap:14px; flex-wrap:wrap; font-size:.94rem; }}
    main {{ max-width:1180px; margin:0 auto; padding:42px 20px 80px; }}
    .hero {{ padding:42px; border:1px solid var(--line); border-radius:32px; background:linear-gradient(135deg, rgba(59,130,246,.24), rgba(16,185,129,.12)); box-shadow:0 30px 90px rgba(0,0,0,.28); }}
    .eyebrow, .pill {{ display:inline-flex; align-items:center; gap:8px; border:1px solid var(--line); border-radius:999px; padding:6px 10px; color:#bfdbfe; background:rgba(59,130,246,.14); font-size:12px; font-weight:850; text-transform:uppercase; letter-spacing:.08em; }}
    h1 {{ font-size:clamp(2.5rem, 6vw, 5.7rem); line-height:.90; letter-spacing:-.075em; margin:18px 0; max-width:920px; }}
    h2 {{ margin:46px 0 16px; font-size:clamp(1.55rem, 3vw, 2.3rem); letter-spacing:-.04em; }}
    h3 {{ margin:0 0 10px; font-size:1.1rem; }}
    p {{ color:#d7e0eb; line-height:1.68; }}
    .lead {{ font-size:1.18rem; max-width:880px; color:#e2e8f0; }}
    .muted {{ color:var(--muted); }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(240px,1fr)); gap:16px; }}
    .two {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(330px,1fr)); gap:18px; }}
    .card {{ border:1px solid var(--line); background:rgba(15,23,42,.78); border-radius:22px; padding:20px; }}
    .card strong {{ color:#fff; }}
    .cta {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:22px; }}
    .button {{ display:inline-block; padding:12px 16px; border-radius:999px; font-weight:850; background:linear-gradient(135deg, var(--blue), var(--green)); color:white; }}
    .button.secondary {{ background:rgba(148,163,184,.13); border:1px solid var(--line); }}
    .diagram {{ margin-top:20px; display:grid; gap:12px; }}
    .flow {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:10px; align-items:stretch; }}
    .flow .node {{ border:1px solid var(--line); border-radius:18px; padding:16px; background:rgba(17,28,49,.88); min-height:130px; }}
    .status {{ font-size:12px; color:#dbeafe; border:1px solid var(--line); border-radius:999px; padding:4px 8px; display:inline-block; margin-bottom:10px; }}
    .arrow {{ text-align:center; color:#93c5fd; font-weight:900; align-self:center; }}
    .table {{ width:100%; border-collapse:separate; border-spacing:0 10px; }}
    .table td {{ padding:14px; background:rgba(15,23,42,.86); border-top:1px solid var(--line); border-bottom:1px solid var(--line); vertical-align:top; }}
    .table td:first-child {{ border-left:1px solid var(--line); border-radius:14px 0 0 14px; font-weight:850; color:#fff; }}
    .table td:last-child {{ border-right:1px solid var(--line); border-radius:0 14px 14px 0; color:#d7e0eb; }}
    code {{ color:#bfdbfe; }}
    footer {{ border-top:1px solid var(--line); color:var(--muted); padding:24px 20px; text-align:center; }}
  </style>
</head>
<body>
<header>
  <nav>
    <a class=\"brand\" href=\"/\">Duecare AI</a>
    <div class=\"navlinks\">
      <a href=\"/components\">Components</a>
      <a href=\"/use-cases\">Use cases</a>
      <a href=\"/grep-rules\">GREP rules</a>
      <a href=\"/tools\">Tools</a>
      <a href=\"/context\">Context</a>
      <a href=\"/dashboard\">Live dashboard</a>
      <a href=\"/docs\">API</a>
    </div>
  </nav>
</header>
<main>
  <section class=\"hero\">
    <span class=\"eyebrow\">{escape(eyebrow)}</span>
    {body}
  </section>
</main>
<footer>Duecare drafts; the user or trusted caseworker decides. Privacy is non-negotiable.</footer>
</body>
</html>"""


def _cards(items: tuple[CatalogItem, ...]) -> str:
    return "\n".join(
        f"""<article class=\"card\"><span class=\"pill\">{escape(item.label)}</span><h3>{escape(item.name)}</h3><p>{escape(item.summary)}</p></article>"""
        for item in items
    )


def _component_cards() -> str:
    return "\n".join(
        f"""<article class=\"node\"><span class=\"status\">{escape(component.status)}</span><h3>{escape(component.name)}</h3><p>{escape(component.summary)}</p><p class=\"muted\">{escape(component.detail)}</p></article>"""
        for component in COMPONENTS
    )


def _component_table() -> str:
    rows = "\n".join(
        f"""<tr><td>{escape(component.name)}<br><span class=\"muted\">{escape(component.status)}</span></td><td>{escape(component.summary)} {escape(component.detail)}</td></tr>"""
        for component in COMPONENTS
    )
    return f"<table class=\"table\"><tbody>{rows}</tbody></table>"


def home_html() -> str:
    body = f"""
    <h1>Centralized knowledge. Decentralized privacy.</h1>
    <p class=\"lead\">Duecare AI turns Gemma 4 into a privacy-preserving migrant-worker safety system: a grounded Kaggle harness, a public coordination hub, and future NGO/government channels that never require raw cases to leave trusted hands.</p>
    <div class=\"cta\">
      <a class=\"button\" href=\"/components\">Explore the architecture</a>
      <a class=\"button secondary\" href=\"/dashboard\">Open live dashboard</a>
      <a class=\"button secondary\" href=\"/docs\">View API docs</a>
    </div>
    <h2>How the system fits together</h2>
    <div class=\"flow\">
    <div class=\"node\"><span class=\"status\">Kaggle</span><h3>Gemma 4 + Safety Guidance</h3><p>Runs the visible chat demo, GREP rules, RAG context, contacts, tools, and evaluation rubrics.</p></div>
    <div class=\"node\"><span class=\"status\">Website</span><h3>Central Knowledge Server</h3><p>Accepts anonymized patterns and public-source update proposals for curator review.</p></div>
    <div class=\"node\"><span class=\"status\">Partners</span><h3>NGO / Regulators</h3><p>Use signed knowledge packs, complaint-channel context, and draft-only handoff flows.</p></div>
    <div class=\"node\"><span class=\"status\">Private edge</span><h3>Migrant Worker Chat</h3><p>Keeps sensitive worker messages on-device or inside trusted NGO systems.</p></div>
    </div>
    <h2>Public hub pages</h2>
    <div class=\"grid\">
      <article class=\"card\"><h3>GREP rules</h3><p>What deterministic indicators catch before Gemma answers.</p><a href=\"/grep-rules\">Open rule catalog →</a></article>
      <article class=\"card\"><h3>Tools</h3><p>Complaint drafts, contact routing, fee checks, citation verification, and pack diff review.</p><a href=\"/tools\">Open tools page →</a></article>
      <article class=\"card\"><h3>Context by corridor</h3><p>How RAG context is organized by jurisdiction, route, sector, and risk pattern.</p><a href=\"/context\">Open context page →</a></article>
    <article class=\"card\"><h3>Use cases</h3><p>Platform Safety, NGO / Regulators, Migrant Worker Chat, and Academic Research — always in that order.</p><a href=\"/use-cases\">Open use cases →</a></article>
    </div>
    """
    return _layout("Home", "Gemma 4 Good public hub", body)


def components_html() -> str:
    body = f"""
    <h1>Plain-language components, one privacy boundary.</h1>
    <p class=\"lead\">The public website should make the platform legible in seconds: what each component does, what it displays, and where sensitive data is allowed to go.</p>
    <div class=\"diagram flow\">{_component_cards()}</div>
    <h2>Status table</h2>
    {_component_table()}
    """
    return _layout("Components", "Architecture map", body)


def grep_rules_html() -> str:
    body = f"""
    <h1>Deterministic rules before generation.</h1>
    <p class=\"lead\">GREP rules are the fast safety layer: they fire in milliseconds, explain what they caught, and feed grounded context into Gemma 4 before any answer is drafted.</p>
    <div class=\"grid\">{_cards(GREP_CATEGORIES)}</div>
    <h2>Why this matters</h2>
    <div class=\"two\"><article class=\"card\"><h3>Video-visible</h3><p>A judge can paste a suspicious job pitch and immediately see which indicators fired, before model latency dominates the demo.</p></article><article class=\"card\"><h3>Auditable</h3><p>Rules are explainable and testable. They reduce hallucinated safety claims and create regression targets for future pack updates.</p></article></div>
    """
    return _layout("GREP rules", "Safety layer", body)


def tools_html() -> str:
    body = f"""
    <h1>Tools draft; humans decide.</h1>
    <p class=\"lead\">Duecare tools transform model output into safe, reviewable actions. They do not auto-send reports or replace trusted caseworkers.</p>
    <div class=\"grid\">{_cards(TOOLS)}</div>
    <h2>Safety boundary</h2>
    <div class=\"card\"><p><strong>No auto-submission.</strong> Complaint flows produce drafts, contact suggestions, citations, and evidence checklists. The worker, NGO, regulator, or trusted caseworker reviews and sends.</p></div>
    """
    return _layout("Tools", "Draft-only action layer", body)


def context_html() -> str:
    body = f"""
    <h1>Context organized by corridor and jurisdiction.</h1>
    <p class=\"lead\">The RAG layer is designed around real migration routes, sectors, ILO indicators, complaint mechanisms, and public legal references.</p>
    <div class=\"grid\">{_cards(CONTEXT_GROUPS)}</div>
    <h2>How context updates flow</h2>
    <div class=\"flow\"><div class=\"node\"><h3>Public source</h3><p>Regulator page, NGO advisory, court/public policy document, or platform safety policy.</p></div><div class=\"node\"><h3>Sentinel proposal</h3><p>OpenCrawl submits hashes and extracted public facts to the hub.</p></div><div class=\"node\"><h3>Curator review</h3><p>A human approves, rejects, or requests changes before publication.</p></div><div class=\"node\"><h3>Signed pack</h3><p>Approved context ships to Kaggle, local, mobile, and NGO deployments.</p></div></div>
    """
    return _layout("Context", "RAG by corridor", body)


def use_cases_html() -> str:
    body = f"""
    <h1>Four use cases, one privacy rule.</h1>
    <p class=\"lead\">Duecare uses one canonical order everywhere: Platform Safety, NGO / Regulators, Migrant Worker Chat, and Academic Research. It is not a public raw-case intake portal; it is infrastructure for safer advice, evaluation, and coordination around Gemma 4.</p>
    <div class=\"grid\">{_cards(USE_CASES)}</div>
    <h2>Deployment principle</h2>
    <div class=\"card\"><p><strong>Centralized knowledge, decentralized privacy.</strong> The public hub coordinates anonymized signals and public updates. Sensitive messages stay on trusted devices, NGO systems, or regulator infrastructure.</p></div>
    """
    return _layout("Use cases", "Deployment stories", body)
