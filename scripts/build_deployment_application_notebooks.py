#!/usr/bin/env python3
"""Build the DueCare deployment-application notebooks (660-695).

These notebooks are deliberately plain-English, CPU-only deployment
playbooks. They sit beside the heavier late-suite implementation
surfaces (610, 620, 650) so judges and adopters can open one notebook
per application instead of inferring the product story from the API and
domain-pack walkthroughs.
"""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import canonical_header_table, patch_final_print_cell
from notebook_hardening_utils import INSTALL_PACKAGES, harden_notebook


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
KEYWORDS = ["deployment", "evaluation"]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_180 = "https://www.kaggle.com/code/taylorsamarel/duecare-180-multimodal-document-inspector"
URL_200 = "https://www.kaggle.com/code/taylorsamarel/duecare-200-cross-domain-proof"
URL_300 = "https://www.kaggle.com/code/taylorsamarel/300-gemma-4-against-15-adversarial-attack-vectors"
URL_400 = "https://www.kaggle.com/code/taylorsamarel/duecare-400-function-calling-multimodal"
URL_410 = "https://www.kaggle.com/code/taylorsamarel/duecare-410-llm-judge-grading"
URL_430 = "https://www.kaggle.com/code/taylorsamarel/duecare-430-rubric-evaluation"
URL_460 = "https://www.kaggle.com/code/taylorsamarel/460-duecare-citation-verifier"
URL_530 = "https://www.kaggle.com/code/taylorsamarel/duecare-530-phase3-unsloth-finetune"
URL_600 = "https://www.kaggle.com/code/taylorsamarel/600-duecare-results-dashboard"
URL_610 = "https://www.kaggle.com/code/taylorsamarel/610-duecare-submission-walkthrough"
URL_620 = "https://www.kaggle.com/code/taylorsamarel/620-duecare-demo-api-endpoint-tour"
URL_650 = "https://www.kaggle.com/code/taylorsamarel/650-duecare-custom-domain-walkthrough"
URL_660 = "https://www.kaggle.com/code/taylorsamarel/duecare-660-enterprise-moderation"
URL_670 = "https://www.kaggle.com/code/taylorsamarel/duecare-670-private-client-side-checker"
URL_680 = "https://www.kaggle.com/code/taylorsamarel/duecare-680-ngo-api-triage"
URL_690 = "https://www.kaggle.com/code/taylorsamarel/duecare-690-migration-case-workflow"
URL_695 = "https://www.kaggle.com/code/taylorsamarel/duecare-695-custom-domain-adoption"
URL_899 = "https://www.kaggle.com/code/taylorsamarel/duecare-solution-surfaces-conclusion"


def md(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": text.splitlines(keepends=True),
    }


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
    "kaggle": {"accelerator": "none", "isInternetEnabled": True},
}


APPLICATIONS = [
    {
        "id": "660",
        "title": "Enterprise Moderation",
        "snake": "enterprise_moderation",
        "slug": "duecare-660-enterprise-moderation",
        "kaggle_title": "660: DueCare Enterprise Moderation",
        "url": URL_660,
        "previous": ("650", "650 Custom Domain Walkthrough", URL_650),
        "next": ("670", "670 Private Client-Side Checker", URL_670),
        "tagline": "Screen risky recruitment and trafficking-adjacent content before it reaches workers.",
        "audience": "Platform trust-and-safety teams, job-board operators, regulators, and large labor intermediaries.",
        "decision": "Choose this when the problem is queue triage at volume, not one-off casework.",
        "inputs_html": (
            "Batches of job posts, chat snippets, ad copy, recruiter outreach, or complaint text. The notebook uses a synthetic moderation queue and a staged action policy so the flow is visible without a running server."
        ),
        "outputs_html": (
            "Risk bands, action buckets (<code>pass</code>, <code>warn</code>, <code>review</code>, <code>block</code>), escalation reasons, and the operator queue shape a moderation team would actually work from."
        ),
        "prerequisites_html": (
            f"CPU-only. No API keys, no model loading, no external server. Read <a href=\"{URL_600}\">600 Results Dashboard</a> first if you want the measured proof before the product story."
        ),
        "runtime_html": "Under 10 seconds. Static scenario rendering only.",
        "pipeline_html": (
            f"Deployment Applications section. Previous: <a href=\"{URL_650}\">650 Custom Domain Walkthrough</a>. Next: <a href=\"{URL_670}\">670 Private Client-Side Checker</a>. Implementation companions: <a href=\"{URL_600}\">600 Results Dashboard</a>, <a href=\"{URL_620}\">620 Demo API Endpoint Tour</a>, <a href=\"{URL_300}\">300 Adversarial Resistance</a>."
        ),
        "why": (
            "This is the large-scale operator story. A platform or regulator does not need the full 620 endpoint catalog to understand the product shape; they need to know what gets screened, what lands in a review queue, and why DueCare is safer than a generic moderation labeler."
        ),
        "reading_order": [
            ("Measured proof", "600 Results Dashboard", URL_600),
            ("Implementation detail", "620 Demo API Endpoint Tour", URL_620),
            ("Adversarial evidence", "300 Adversarial Resistance", URL_300),
            ("Section close", "899 Solution Surfaces Conclusion", URL_899),
        ],
        "what_it_does": [
            "Defines the operator, the queue, and the action policy in plain English.",
            "Shows one moderation batch with the exact fields a platform team would see.",
            "Maps the product claim back to the measured and implementation notebooks that make it credible.",
        ],
        "flow_steps": [
            "Ingest posts, recruiter chats, or ad copy.",
            "Run quick triage and full analysis where needed.",
            "Assign pass, warn, review, or block.",
            "Escalate flagged items to operators with evidence.",
        ],
        "sample_input": {
            "queue_id": "enterprise-batch-01",
            "items": [
                {"channel": "job_post", "text": "Employer covers flights and fees. Weekly day off guaranteed."},
                {"channel": "dm", "text": "Send passport photo now. Six months salary deposit required before departure."},
                {"channel": "ad", "text": "Fast overseas placement. Training charges deducted after arrival."},
            ],
        },
        "sample_output": {
            "summary": {"pass": 1, "warn": 0, "review": 1, "block": 1},
            "flagged_items": [
                {"channel": "dm", "action": "block", "reason": "passport capture + upfront debt demand"},
                {"channel": "ad", "action": "review", "reason": "post-arrival fee deduction language"},
            ],
        },
        "evidence": [
            {"notebook": "600 Results Dashboard", "url": URL_600, "proof": "Shows the measured lift and failure panels behind the moderation policy."},
            {"notebook": "620 Demo API Endpoint Tour", "url": URL_620, "proof": "Shows the route-level contract for analyze, batch, and quick-check style flows."},
            {"notebook": "300 Adversarial Resistance", "url": URL_300, "proof": "Stress-tests the exact kinds of wording a bad actor uses to evade simple filters."},
            {"notebook": "410 LLM Judge Grading", "url": URL_410, "proof": "Explains how the safety dimensions behind the queue labels are scored."},
        ],
        "boundaries": [
            "This notebook explains the product surface, not the raw endpoint catalog. Use 620 for the request and response contract.",
            "It is a screening layer, not a full case-management workflow. Use 690 for the document-bundle case path.",
        ],
    },
    {
        "id": "670",
        "title": "Private Client-Side Checker",
        "snake": "private_client_side_checker",
        "slug": "duecare-670-private-client-side-checker",
        "kaggle_title": "670: DueCare Private Client-Side Checker",
        "url": URL_670,
        "previous": ("660", "660 Enterprise Moderation", URL_660),
        "next": ("680", "680 NGO API Triage", URL_680),
        "tagline": "Let a worker or advocate verify one suspicious message or document locally before sending anything upstream.",
        "audience": "Workers, hotline staff, community advocates, and field investigators handling one case at a time.",
        "decision": "Choose this when privacy and immediate guidance matter more than platform-scale queueing.",
        "inputs_html": (
            "One suspicious message, ad, contract excerpt, or document photo. The notebook uses a composite worker-side example and a plain-language response shape."
        ),
        "outputs_html": (
            "A plain-language warning, the main risk signals, a safer next step, and resource or hotline guidance suitable for a person reading on a phone."
        ),
        "prerequisites_html": (
            f"CPU-only narrative notebook. Companion proof lives in <a href=\"{URL_400}\">400 Function Calling and Multimodal</a>, <a href=\"{URL_180}\">180 Multimodal Document Inspector</a>, and <a href=\"{URL_600}\">600 Results Dashboard</a>."
        ),
        "runtime_html": "Under 10 seconds. Static scenario rendering only.",
        "pipeline_html": (
            f"Deployment Applications section. Previous: <a href=\"{URL_660}\">660 Enterprise Moderation</a>. Next: <a href=\"{URL_680}\">680 NGO API Triage</a>. Implementation companions: <a href=\"{URL_180}\">180 Multimodal Document Inspector</a>, <a href=\"{URL_400}\">400 Function Calling and Multimodal</a>, <a href=\"{URL_600}\">600 Results Dashboard</a>."
        ),
        "why": (
            "This is the worker-side story. The user does not care about queue architecture or API endpoints first; they care whether DueCare can look at one scary message or contract photo and answer safely, clearly, and locally."
        ),
        "reading_order": [
            ("Measured proof", "600 Results Dashboard", URL_600),
            ("Multimodal proof", "180 Multimodal Document Inspector", URL_180),
            ("Tool and image proof", "400 Function Calling and Multimodal", URL_400),
            ("Section close", "899 Solution Surfaces Conclusion", URL_899),
        ],
        "what_it_does": [
            "Defines the private checker in user-facing terms instead of endpoint terms.",
            "Shows a single-message plus single-document example that a worker or advocate would actually paste in.",
            "Separates the local guidance experience from the heavier NGO case-management path."
        ],
        "flow_steps": [
            "Paste or photograph one suspicious item.",
            "Extract the signal that matters most.",
            "Return a short warning in plain language.",
            "Offer a safer next action and support resource.",
        ],
        "sample_input": {
            "message": "Recruiter says I must send passport photo and borrow the fee from their partner lender before flight booking.",
            "document_photo": "recruitment_contract_photo.jpg",
            "mode": "local_private_check",
        },
        "sample_output": {
            "risk_level": "high",
            "warning": "This combines document capture with debt pressure before travel.",
            "signals": ["passport request", "recruitment fee", "partner lender dependency"],
            "next_step": "Do not send identity documents yet. Ask for the fee policy in writing and contact a trusted support organization.",
        },
        "evidence": [
            {"notebook": "180 Multimodal Document Inspector", "url": URL_180, "proof": "Shows a document-photo path instead of text only."},
            {"notebook": "400 Function Calling and Multimodal", "url": URL_400, "proof": "Shows document-aware analysis and tool-grounded responses as load-bearing features."},
            {"notebook": "600 Results Dashboard", "url": URL_600, "proof": "Shows the measured gap the checker is trying to close."},
            {"notebook": "530 Phase 3 Unsloth Fine-tune", "url": URL_530, "proof": "Supplies the tuned model artifact the local checker would ship with."},
        ],
        "boundaries": [
            "This is the private single-item experience. It is not the batch moderation queue in 660.",
            "It is also not the document-bundle NGO workflow. Use 690 for multi-document case intake and draft complaints.",
        ],
    },
    {
        "id": "680",
        "title": "NGO API Triage",
        "snake": "ngo_api_triage",
        "slug": "duecare-680-ngo-api-triage",
        "kaggle_title": "680: DueCare NGO API Triage",
        "url": URL_680,
        "previous": ("670", "670 Private Client-Side Checker", URL_670),
        "next": ("690", "690 Migration Case Workflow", URL_690),
        "tagline": "Expose DueCare as a structured analysis and triage service that other NGO software can call.",
        "audience": "NGO engineers, civic-tech teams, and partner product teams integrating DueCare into an existing stack.",
        "decision": "Choose this when the deployment target is software-to-software integration, not a human-only notebook or phone experience.",
        "inputs_html": (
            "A JSON request from another application, typically one message, one job post, or one extracted document payload plus optional jurisdiction or context labels."
        ),
        "outputs_html": (
            "Structured grades, actions, indicators, legal references, resources, and rubric results that a partner system can store, route, or display downstream."
        ),
        "prerequisites_html": (
            f"CPU-only narrative notebook. Technical contract lives in <a href=\"{URL_620}\">620 Demo API Endpoint Tour</a>; measured proof lives in <a href=\"{URL_600}\">600 Results Dashboard</a>."
        ),
        "runtime_html": "Under 10 seconds. Static request and response rendering only.",
        "pipeline_html": (
            f"Deployment Applications section. Previous: <a href=\"{URL_670}\">670 Private Client-Side Checker</a>. Next: <a href=\"{URL_690}\">690 Migration Case Workflow</a>. Implementation companion: <a href=\"{URL_620}\">620 Demo API Endpoint Tour</a>."
        ),
        "why": (
            "This is the integrator story. A partner deciding whether to wire DueCare into intake tooling, a hotline dashboard, or a monitoring system needs a plain-English API playbook before they need all 17 routes."
        ),
        "reading_order": [
            ("Measured proof", "600 Results Dashboard", URL_600),
            ("Implementation detail", "620 Demo API Endpoint Tour", URL_620),
            ("Scoring detail", "410 LLM Judge Grading", URL_410),
            ("Section close", "899 Solution Surfaces Conclusion", URL_899),
        ],
        "what_it_does": [
            "Defines the NGO API in deployment terms: caller, payload, response, and handoff.",
            "Shows one structured request and one structured response with the fields a partner system would consume.",
            "Separates the generalized API story from the heavier migration-case orchestration path in 690."
        ],
        "flow_steps": [
            "Receive structured input from a partner system.",
            "Run DueCare analysis and scoring.",
            "Return action, evidence, and resource guidance.",
            "Hand the result back to the caller for triage or case routing.",
        ],
        "sample_input": {
            "text": "Agency says the worker must reimburse visa, medical, and training fees after arrival.",
            "context": "job_posting",
            "jurisdiction": "PH_HK",
            "caller": "ngo-intake-dashboard",
        },
        "sample_output": {
            "grade": "bad",
            "action": "review",
            "indicators": ["illegal recruitment fees", "cost shifting"],
            "legal_refs": ["ILO C181 Article 7"],
            "resources": ["trusted hotline referral"],
            "triage_note": "Send to labor-rights reviewer for manual follow-up.",
        },
        "evidence": [
            {"notebook": "620 Demo API Endpoint Tour", "url": URL_620, "proof": "Shows the actual request and response shapes that make this application real."},
            {"notebook": "600 Results Dashboard", "url": URL_600, "proof": "Shows the measured quality behind the JSON a partner would trust."},
            {"notebook": "410 LLM Judge Grading", "url": URL_410, "proof": "Explains the graded fields and dimensions the response exposes."},
            {"notebook": "430 Rubric Evaluation", "url": URL_430, "proof": "Shows the explicit pass-fail criteria behind the triage response."},
        ],
        "boundaries": [
            "This is the generalized software integration path. It does not assume a multi-document bundle or case timeline.",
            "Use 690 when the input is a case file with several documents and the output needs to include a chronology and complaint draft.",
        ],
    },
    {
        "id": "690",
        "title": "Migration Case Workflow",
        "snake": "migration_case_workflow",
        "slug": "duecare-690-migration-case-workflow",
        "kaggle_title": "690: DueCare Migration Case Workflow",
        "url": URL_690,
        "previous": ("680", "680 NGO API Triage", URL_680),
        "next": ("695", "695 Custom Domain Adoption", URL_695),
        "tagline": "Turn a bundle of uploaded case documents into a timeline, grounded findings, and draft complaint materials.",
        "audience": "NGO case workers, legal intake teams, migration support organizations, and investigators handling document bundles.",
        "decision": "Choose this when the problem is case assembly and grounded drafting, not single-message triage.",
        "inputs_html": (
            "A case bundle: messages, contracts, identity pages, receipts, and notes uploaded together with corridor or jurisdiction context. The notebook uses a composite bundle description only."
        ),
        "outputs_html": (
            "A normalized case timeline, grounded findings with citations, a short risk summary, and draft complaint or intake text that a case worker can edit before submission."
        ),
        "prerequisites_html": (
            f"CPU-only narrative notebook. The concrete implementation lives in <a href=\"{URL_620}\">620 Demo API Endpoint Tour</a>; the document and citation substrate lives in <a href=\"{URL_400}\">400 Function Calling and Multimodal</a> and <a href=\"{URL_460}\">460 Citation Verifier</a>."
        ),
        "runtime_html": "Under 10 seconds. Static bundle, timeline, and finding rendering only.",
        "pipeline_html": (
            f"Deployment Applications section. Previous: <a href=\"{URL_680}\">680 NGO API Triage</a>. Next: <a href=\"{URL_695}\">695 Custom Domain Adoption</a>. Implementation companions: <a href=\"{URL_620}\">620 Demo API Endpoint Tour</a>, <a href=\"{URL_400}\">400 Function Calling and Multimodal</a>, <a href=\"{URL_460}\">460 Citation Verifier</a>."
        ),
        "why": (
            "This is the case-worker story. It is where DueCare stops being just a classifier or API and becomes a document workflow that helps an NGO turn scattered files into a usable case chronology."
        ),
        "reading_order": [
            ("Implementation detail", "620 Demo API Endpoint Tour", URL_620),
            ("Document analysis proof", "400 Function Calling and Multimodal", URL_400),
            ("Citation audit", "460 Citation Verifier", URL_460),
            ("Section close", "899 Solution Surfaces Conclusion", URL_899),
        ],
        "what_it_does": [
            "Defines the case-bundle workflow in operational terms a case worker can understand.",
            "Shows the difference between a raw bundle, a normalized timeline, and an editable complaint draft.",
            "Ties the product claim back to the implementation routes and citation checks that support it."
        ],
        "flow_steps": [
            "Upload a document bundle with corridor context.",
            "Normalize files into a shared case record.",
            "Assemble chronology and grounded findings.",
            "Draft complaint or intake text for human review.",
        ],
        "sample_input": {
            "bundle": ["chat_export.txt", "contract_scan.jpg", "receipt_photo.jpg", "intake_notes.md"],
            "corridor": "NP_QA",
            "requested_output": ["timeline", "grounded_findings", "draft_complaint"],
        },
        "sample_output": {
            "timeline": [
                "Recruiter requested passport image before written contract.",
                "Training and medical fees shifted to the worker.",
                "Receipt shows repayment terms tied to departure timeline.",
            ],
            "grounded_findings": [
                "document capture before travel",
                "illegal fee shifting",
                "debt-linked travel pressure",
            ],
            "draft_complaint": "Editable intake summary with facts, chronology, and cited risk indicators.",
        },
        "evidence": [
            {"notebook": "620 Demo API Endpoint Tour", "url": URL_620, "proof": "Shows the migration-case and migration-case-upload routes that implement this workflow."},
            {"notebook": "400 Function Calling and Multimodal", "url": URL_400, "proof": "Shows the document-aware substrate required to analyze mixed file types."},
            {"notebook": "460 Citation Verifier", "url": URL_460, "proof": "Shows why the grounded-findings and legal-reference outputs are not decorative."},
            {"notebook": "600 Results Dashboard", "url": URL_600, "proof": "Provides the measured context for why this workflow exists after Phase 3 improvements."},
        ],
        "boundaries": [
            "This is a multi-document case workflow, not the simplest API call or worker-side single-item check.",
            "The complaint draft remains human-reviewed. The notebook describes an assistive workflow, not automated filing.",
        ],
    },
    {
        "id": "695",
        "title": "Custom Domain Adoption",
        "snake": "custom_domain_adoption",
        "slug": "duecare-695-custom-domain-adoption",
        "kaggle_title": "695: DueCare Custom Domain Adoption",
        "url": URL_695,
        "previous": ("690", "690 Migration Case Workflow", URL_690),
        "next": ("899", "899 Solution Surfaces Conclusion", URL_899),
        "tagline": "Show a partner how the same stack becomes reusable in a new safety domain without changing Python code.",
        "audience": "Partner researchers, NGOs, and labs evaluating DueCare as a reusable framework rather than a trafficking-only demo.",
        "decision": "Choose this when the question is reusability: can this stack move into a new safety domain cleanly?",
        "inputs_html": (
            "A new domain definition expressed as YAML and JSONL files. The notebook uses the medical-misinformation example as a deployment playbook rather than a code tutorial."
        ),
        "outputs_html": (
            "A partner-adoption map: what files change, what stays stable, what proof notebooks matter, and how a new domain reaches the same evaluation and deployment surfaces."
        ),
        "prerequisites_html": (
            f"CPU-only narrative notebook. Technical how-to lives in <a href=\"{URL_650}\">650 Custom Domain Walkthrough</a>; generalization proof lives in <a href=\"{URL_200}\">200 Cross-Domain Proof</a>."
        ),
        "runtime_html": "Under 10 seconds. Static adoption playbook only.",
        "pipeline_html": (
            f"Deployment Applications section. Previous: <a href=\"{URL_690}\">690 Migration Case Workflow</a>. Next: <a href=\"{URL_899}\">899 Solution Surfaces Conclusion</a>. Implementation companions: <a href=\"{URL_650}\">650 Custom Domain Walkthrough</a>, <a href=\"{URL_200}\">200 Cross-Domain Proof</a>, <a href=\"{URL_530}\">530 Phase 3 Unsloth Fine-tune</a>."
        ),
        "why": (
            "This is the partner-adoption story in plain English. 650 is the technical walkthrough; this notebook makes the business and deployment meaning of that walkthrough explicit so judges do not have to infer it from YAML alone."
        ),
        "reading_order": [
            ("Technical how-to", "650 Custom Domain Walkthrough", URL_650),
            ("Generalization proof", "200 Cross-Domain Proof", URL_200),
            ("Model substrate", "530 Phase 3 Unsloth Fine-tune", URL_530),
            ("Section close", "899 Solution Surfaces Conclusion", URL_899),
        ],
        "what_it_does": [
            "Explains what a partner changes and what stays stable when adopting DueCare.",
            "Shows one concrete adoption example without dropping the reader into implementation details too early.",
            "Connects framework reuse to the same deployment surfaces the other application notebooks rely on."
        ],
        "flow_steps": [
            "Choose a new safety domain.",
            "Write the pack files that encode taxonomy, rubric, PII, and seed prompts.",
            "Register the pack and verify it through the shared harness.",
            "Reuse the same evaluation, dashboard, and deployment surfaces.",
        ],
        "sample_input": {
            "domain_id": "medical_misinformation",
            "files": ["taxonomy.yaml", "rubric.yaml", "pii_spec.yaml", "seed_prompts.jsonl"],
            "goal": "Reuse DueCare without modifying Python packages.",
        },
        "sample_output": {
            "adoption_outcome": "New domain pack discovered by the registry",
            "reuse_surfaces": ["evaluation harness", "results dashboard", "API routes", "deployment playbooks"],
            "partner_message": "Config changes, not framework surgery.",
        },
        "evidence": [
            {"notebook": "650 Custom Domain Walkthrough", "url": URL_650, "proof": "Shows the exact file-level steps needed to add a new domain pack."},
            {"notebook": "200 Cross-Domain Proof", "url": URL_200, "proof": "Shows the shared harness already running across multiple shipped domains."},
            {"notebook": "530 Phase 3 Unsloth Fine-tune", "url": URL_530, "proof": "Shows where domain-specific improvement work plugs into the broader model pipeline."},
            {"notebook": "620 Demo API Endpoint Tour", "url": URL_620, "proof": "Shows that the same deployment surface can sit above multiple domain packs."},
        ],
        "boundaries": [
            "This notebook is the adoption story, not the file-by-file implementation guide. Use 650 for the exact pack build.",
            "It explains reuse of the framework, not a guarantee that every domain performs equally without evaluation work.",
        ],
    },
]


def _reading_order_md(app: dict) -> str:
    lines = []
    for label, title, url in app["reading_order"]:
        lines.append(f"- **{label}:** [{title}]({url})")
    return "\n".join(lines)


def _what_it_does_md(app: dict) -> str:
    return "\n".join(f"{index}. {line}" for index, line in enumerate(app["what_it_does"], start=1))


def _header_markdown(app: dict) -> str:
    previous_id, previous_title, previous_url = app["previous"]
    next_id, next_title, next_url = app["next"]
    header_table = canonical_header_table(
        inputs_html=app["inputs_html"],
        outputs_html=app["outputs_html"],
        prerequisites_html=app["prerequisites_html"],
        runtime_html=app["runtime_html"],
        pipeline_html=app["pipeline_html"],
    )
    return f"""# {app['id']}: DueCare {app['title']}

**{app['tagline']}**

DueCare is an on-device Gemma 4 safety system. This notebook is not the full implementation deep dive. It is the plain-English deployment playbook for one specific application so a judge or adopter can answer a simple question fast: what does this product do, who uses it, and which existing notebooks prove it is real?

{header_table}

### Why this notebook matters

{app['why']}

### Reading order

- **Previous notebook:** [{previous_id} {previous_title}]({previous_url})
- **Next notebook:** [{next_id} {next_title}]({next_url})
{_reading_order_md(app)}
- **Back to navigation:** [000 Index]({URL_000})

### What this notebook does

{_what_it_does_md(app)}
"""


def _overview_code(app: dict) -> str:
    payload = {
        "title": app["title"],
        "audience": app["audience"],
        "decision": app["decision"],
        "flow_steps": app["flow_steps"],
        "proof_anchor": app["evidence"][0]["notebook"],
    }
    return f"""import json
from IPython.display import HTML, display

APP = json.loads({json.dumps(json.dumps(payload))!r})

palette = {{
    'primary': '#4c78a8',
    'success': '#10b981',
    'warning': '#f59e0b',
    'info': '#3b82f6',
    'muted': '#6b7280',
    'bg_primary': '#eff6ff',
    'bg_success': '#ecfdf5',
    'bg_warning': '#fffbeb',
    'bg_info': '#eff6ff',
}}

def card(label, value, kind='primary'):
    color = palette[kind]
    bg = palette[f'bg_{{kind}}']
    return (
        f'<div style="display:inline-block;vertical-align:top;width:23%;margin:4px 1%;padding:14px 16px;'
        f'background:{{bg}};border-left:5px solid {{color}};border-radius:4px;'
        f'font-family:system-ui,-apple-system,sans-serif">'
        f'<div style="font-size:11px;font-weight:600;color:{{color}};text-transform:uppercase;letter-spacing:0.04em">{{label}}</div>'
        f'<div style="font-size:15px;font-weight:600;color:#1f2937;margin-top:6px;line-height:1.35">{{value}}</div>'
        '</div>'
    )

cards = [
    card('Application', APP['title'], 'primary'),
    card('Primary user', APP['audience'], 'info'),
    card('Use this when', APP['decision'], 'warning'),
    card('Proof anchor', APP['proof_anchor'], 'success'),
]
display(HTML('<div style="margin:10px 0">' + ''.join(cards) + '</div>'))

steps = []
for index, step in enumerate(APP['flow_steps'], start=1):
    steps.append(
        '<div style="display:inline-block;vertical-align:middle;min-width:150px;margin:4px 6px 4px 0;'
        'padding:10px 12px;background:#f8fafc;border:1px solid #d1d5db;border-radius:6px;'
        'font-family:system-ui,-apple-system,sans-serif">'
        f'<div style="font-size:11px;color:#4c78a8;font-weight:600;text-transform:uppercase">Step {{index}}</div>'
        f'<div style="font-size:13px;color:#1f2937;margin-top:4px">{{step}}</div>'
        '</div>'
    )

display(HTML(
    '<div style="margin:12px 0 6px 0;font-family:system-ui,-apple-system,sans-serif;font-weight:600;color:#1f2937">'
    'At a glance flow</div>' + ''.join(steps)
))
"""


def _sample_code(app: dict) -> str:
    payload = {
        "sample_input": app["sample_input"],
        "sample_output": app["sample_output"],
    }
    return f"""import json
from IPython.display import HTML, display

PAYLOAD = json.loads({json.dumps(json.dumps(payload))!r})

input_json = json.dumps(PAYLOAD['sample_input'], indent=2)
output_json = json.dumps(PAYLOAD['sample_output'], indent=2)

display(HTML(
    '<table style="width:100%;border-collapse:collapse;margin:4px 0 8px 0;font-family:system-ui,-apple-system,sans-serif">'
    '<thead><tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da">'
    '<th style="padding:8px 10px;text-align:left;width:50%">Composite input</th>'
    '<th style="padding:8px 10px;text-align:left;width:50%">Expected output shape</th>'
    '</tr></thead><tbody><tr>'
    '<td style="padding:8px 10px;vertical-align:top;border-top:1px solid #e5e7eb"><pre style="white-space:pre-wrap;margin:0">' + input_json + '</pre></td>'
    '<td style="padding:8px 10px;vertical-align:top;border-top:1px solid #e5e7eb"><pre style="white-space:pre-wrap;margin:0">' + output_json + '</pre></td>'
    '</tr></tbody></table>'
))
"""


def _evidence_code(app: dict) -> str:
    payload = {"evidence": app["evidence"]}
    return f"""import json
from IPython.display import HTML, display

EVIDENCE = json.loads({json.dumps(json.dumps(payload))!r})['evidence']

rows = []
for item in EVIDENCE:
    rows.append(
        '<tr>'
        f'<td style="padding:8px 10px;vertical-align:top;border-top:1px solid #e5e7eb"><a href="{{item["url"]}}">{{item["notebook"]}}</a></td>'
        f'<td style="padding:8px 10px;vertical-align:top;border-top:1px solid #e5e7eb">{{item["proof"]}}</td>'
        '</tr>'
    )

display(HTML(
    '<table style="width:100%;border-collapse:collapse;margin:4px 0 8px 0;font-family:system-ui,-apple-system,sans-serif">'
    '<thead><tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da">'
    '<th style="padding:8px 10px;text-align:left;width:30%">Supporting notebook</th>'
    '<th style="padding:8px 10px;text-align:left;width:70%">What it proves</th>'
    '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
))
"""


def _boundaries_markdown(app: dict) -> str:
    bullets = "\n".join(f"- {line}" for line in app["boundaries"])
    return f"""## Boundaries and handoff

{bullets}

This notebook is intentionally short. Its job is to make the deployment application legible in minutes, then hand you to the heavier implementation notebook if you want the mechanics.
"""


def _final_print_src(app: dict) -> str:
    next_id, next_title, next_url = app["next"]
    text = (
        f"{app['title']} handoff >>> {next_id} {next_title} {next_url} | "
        f"600 Results Dashboard {URL_600} | 620 Demo API Endpoint Tour {URL_620} | "
        f"650 Custom Domain Walkthrough {URL_650}"
    )
    return f"print({text!r})\n"


def _build_one(app: dict) -> None:
    filename = f"{app['id']}_{app['snake']}.ipynb"
    kernel_dir_name = f"duecare_{app['id']}_{app['snake']}"
    kernel_id = f"taylorsamarel/{app['slug']}"
    INSTALL_PACKAGES[filename] = ["duecare-llm-core==0.1.0"]

    cells = [
        md(_header_markdown(app)),
        md("## At a glance\n\nThe cards below define the application, the primary user, the decision rule for when to deploy it, and the basic operational flow."),
        code(_overview_code(app)),
        md("## Composite example\n\nThis is the simplest believable input and output shape for the application. It is not meant to replace the implementation notebook; it exists so the product story is visible at a glance."),
        code(_sample_code(app)),
        md("## Repo evidence\n\nThe application notebook is only useful if it points back to the notebooks that make the claim defensible."),
        code(_evidence_code(app)),
        md(_boundaries_markdown(app)),
    ]

    nb = {"cells": cells, "metadata": NB_METADATA, "nbformat": 4, "nbformat_minor": 5}
    nb = harden_notebook(nb, filename=filename)
    patch_final_print_cell(
        nb,
        final_print_src=_final_print_src(app),
        marker=f"{app['title']} handoff >>>",
    )

    NB_DIR.mkdir(parents=True, exist_ok=True)
    kernel_dir = KAGGLE_KERNELS / kernel_dir_name
    kernel_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(nb, indent=1, ensure_ascii=False) + "\n"
    (NB_DIR / filename).write_text(payload, encoding="utf-8")
    (kernel_dir / filename).write_text(payload, encoding="utf-8")

    metadata = {
        "id": kernel_id,
        "title": app["kaggle_title"],
        "code_file": filename,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [WHEELS_DATASET],
        "keywords": KEYWORDS,
    }
    (kernel_dir / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {NB_DIR / filename}")
    print(f"Wrote {kernel_dir / filename}")
    print(f"Wrote {kernel_dir / 'kernel-metadata.json'}")


def main() -> int:
    for app in APPLICATIONS:
        _build_one(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())