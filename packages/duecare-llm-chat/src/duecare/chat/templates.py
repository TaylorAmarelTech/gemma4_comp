"""NGO complaint / referral template orchestrator.

Lets an NGO caseworker who has just processed a bundle on Bulk File Review
turn the structured intelligence (people, employers, journey points,
payments, evidence edges) into a filled complaint or referral document
via Gemma 4.

Each registered template carries:

* a stable id + audience metadata (HK Labour Department, POEA/DMW, IOM,
  generic NGO intake)
* an ordered field list with id/label/required/source_hint
* a body template with ``{{field_id}}`` placeholders (no HTML)
* a render contract: every placeholder either gets a value or renders
  as ``(not provided)`` so drafts are honest about what's still blank

This module was extracted out of ``kaggle/01-duecare-exploration-workbench/
kernel.py`` so the kernel stays focused on runtime orchestration and the
template definitions can grow without bloating the kernel script.

Wiring:

    from duecare.chat.templates import register_template_routes
    register_template_routes(app)

The function reads ``app.state.gemma_call`` lazily at request time so
template fills automatically pick up the resident chat model (or the
mirror, when "Use chat model as judge" is on).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from fastapi import Body
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Template body literals (Jinja-style placeholders, no HTML)
# ---------------------------------------------------------------------------

_TEMPLATE_HK_LD_BODY = """COMPLAINT TO HONG KONG LABOUR DEPARTMENT
Foreign Domestic Helper Section
Date: {{filed_date}}

COMPLAINANT
  Name (caseworker): {{complainant_name}}
  Organisation:      {{complainant_org}}
  Contact:           {{complainant_contact}}

WORKER (subject of the complaint)
  Name (anonymized):    {{worker_name}}
  Nationality:          {{worker_nationality}}
  Hong Kong ID prefix:  {{worker_hkid_prefix}}

EMPLOYER / AGENCY
  Employer name:        {{employer_name}}
  Employer address:     {{employer_address}}
  Agency name:          {{agency_name}}
  Agency licence no.:   {{agency_license}}

INCIDENT
  Date(s):              {{incident_dates}}
  Placement fee paid:   {{placement_fee_amount_hkd}}
  Wages owed:           {{wage_owed_hkd}}

SUMMARY
{{incident_summary}}

ILO FORCED-LABOUR INDICATORS OBSERVED
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

I confirm the above is provided in good faith based on case material
held by {{complainant_org}}. Worker identity has been redacted in
this submission; the case file can be released to the Labour
Department under the agency's standard data-protection terms.

Signature: ________________________    Date: __________
"""

_TEMPLATE_PH_DMW_BODY = """KOMPLEYNT SA DEPARTMENT OF MIGRANT WORKERS / DMW
Anti-Illegal Recruitment and Placement Fee Violation
Petsa: {{filed_date}}

NAGREREKLAMO (NGO caseworker)
  Pangalan:        {{complainant_name}}
  Organisasyon:    {{complainant_org}}
  Contact:         {{complainant_contact}}

MIGRANT WORKER (subject)
  Pangalan (anonymized):  {{worker_name}}
  Bansang pinagtatrabauhan: {{destination_country}}
  Passport prefix:         {{worker_passport_prefix}}

RECRUITMENT AGENCY
  Pangalan ng ahensiya:    {{agency_name}}
  POEA / DMW licence no.:  {{agency_license}}
  Lugar ng tanggapan:      {{agency_address}}

PARTIKULAR NG PAGLABAG
  Petsa ng deployment:     {{deployment_date}}
  Placement fee na binayaran (PHP):  {{placement_fee_amount_php}}
  Allowable cap (POEA MC):           {{placement_fee_cap_php}}

BUOD NG INSIDENTE
{{incident_summary}}

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE
{{evidence_list}}

HINIHILING NA AKSYON
{{relief_requested}}

Pinatutunayan kong tama ang impormasyon batay sa case file ng
{{complainant_org}}. Ang pagkakakilanlan ng manggagawa ay
ginawang anonymized.

Lagda: ________________________    Petsa: __________
"""

_TEMPLATE_IOM_REFERRAL_BODY = """IOM REFERRAL FORM
International Organization for Migration
Protection / Repatriation Assistance Request

REFERRING ORGANISATION
  Name:           {{complainant_org}}
  Caseworker:     {{complainant_name}}
  Contact:        {{complainant_contact}}
  Country office: {{referring_country}}

REFERRAL DATE: {{filed_date}}

SUBJECT (anonymized for transmission)
  Reference code:     {{case_reference}}
  Nationality:        {{worker_nationality}}
  Age range:          {{worker_age_range}}
  Gender:             {{worker_gender}}
  Current location:   {{current_location}}
  Country of origin:  {{country_of_origin}}

PROTECTION CONCERN
  Identified risks:   {{risk_factors}}
  Trafficking indicators present: {{trafficking_indicators}}
  Immediate safety concern (Y/N): {{immediate_safety}}

ASSISTANCE REQUESTED
  Repatriation:       {{repat_required}}
  Medical:            {{medical_required}}
  Legal aid:          {{legal_aid_required}}
  Shelter:            {{shelter_required}}

CASE NARRATIVE
{{incident_summary}}

EVIDENCE / DOCUMENTATION HELD
{{evidence_list}}

CONSENT
The subject has provided informed consent to be referred to IOM
({{consent_status}}). The referring organisation confirms the case
file can be shared under IOM's protection-information protocols.

Caseworker signature: ________________________    Date: __________
"""

_TEMPLATE_NGO_INTAKE_BODY = """CIVIL-SOCIETY CASE INTAKE
Migrant-Worker Protection Network

CASE REFERENCE: {{case_reference}}
INTAKE DATE:    {{filed_date}}

RECEIVING ORGANISATION
  Name:        {{complainant_org}}
  Caseworker:  {{complainant_name}}
  Contact:     {{complainant_contact}}

WORKER (intake details)
  Anonymized identifier:  {{worker_name}}
  Nationality:            {{worker_nationality}}
  Sector:                 {{sector}}
  Corridor:               {{corridor}}
  Current status:         {{current_status}}

INCIDENT TIMELINE
{{incident_timeline}}

KEY FACTS
  Recruitment fee disputed: {{placement_fee_amount}}
  Wages disputed:           {{wage_owed}}
  Contract substitution:    {{contract_substitution}}
  Document retention:       {{document_retention}}

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE INVENTORY
{{evidence_list}}

NEXT STEPS / REFERRAL TARGET
{{next_steps}}

CONSENT + DATA-SHARING
The worker has consented to internal case-tracking by
{{complainant_org}} ({{consent_status}}). External sharing requires
a separate authorisation.

Caseworker signature: ________________________    Date: __________
"""


# ---------------------------------------------------------------------------
# Field + Template schema
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemplateField:
    """One placeholder slot inside a template body."""

    id: str
    label: str
    required: bool = False
    source_hint: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "required": self.required,
            "source_hint": self.source_hint,
        }


def _f(field_id: str, label: str, required: bool = False,
       source_hint: str = "") -> TemplateField:
    """Compact factory used inside the registry definitions below."""
    return TemplateField(id=field_id, label=label, required=required,
                         source_hint=source_hint)


@dataclass(frozen=True)
class TemplateSpec:
    """One NGO complaint / referral template.

    The frozen dataclass makes the registry an immutable source of
    truth -- routes and tests both read from the same object without
    fear of in-place mutation drifting the schema.
    """

    id: str
    title: str
    jurisdiction: str
    audience: str
    summary: str
    body: str
    fields: tuple[TemplateField, ...]

    def summary_payload(self) -> dict:
        """Lightweight metadata for /api/templates/list. Excludes the
        body literal so the listing payload stays small."""
        return {
            "id": self.id,
            "title": self.title,
            "jurisdiction": self.jurisdiction,
            "audience": self.audience,
            "summary": self.summary,
            "fields": [f.to_dict() for f in self.fields],
            "n_fields": len(self.fields),
            "n_required": sum(1 for f in self.fields if f.required),
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TEMPLATES_REGISTRY: dict[str, TemplateSpec] = {
    "hk_ld_fdh_complaint": TemplateSpec(
        id="hk_ld_fdh_complaint",
        title="Hong Kong Labour Department Complaint (FDH)",
        jurisdiction="Hong Kong",
        audience="HK Labour Department · FDH Section",
        summary=(
            "Complaint for fee charging, contract substitution, or wage theft "
            "against a Hong Kong employer or employment agency of a foreign "
            "domestic helper. Aligns with EAO and Employment Ordinance."
        ),
        body=_TEMPLATE_HK_LD_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("worker_nationality", "Worker nationality", False, "entities.nationality[0]"),
            _f("worker_hkid_prefix", "Worker HKID prefix (e.g., Z123****)", False),
            _f("employer_name", "Employer name", True, "entities.employer[0]"),
            _f("employer_address", "Employer address", False, "entities.address[0]"),
            _f("agency_name", "Recruitment agency", False, "entities.agency[0]"),
            _f("agency_license", "Agency licence number", False),
            _f("incident_dates", "Incident date(s)", True),
            _f("placement_fee_amount_hkd", "Placement fee paid (HKD)", False, "payments[*].amount"),
            _f("wage_owed_hkd", "Wages owed (HKD)", False),
            _f("incident_summary", "Incident summary (<=300 words)", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),
    "ph_dmw_complaint": TemplateSpec(
        id="ph_dmw_complaint",
        title="Philippines DMW Complaint (Illegal Recruitment / Fee Cap)",
        jurisdiction="Philippines",
        audience="Department of Migrant Workers · Anti-Illegal Recruitment",
        summary=(
            "Complaint for placement-fee violations or illegal recruitment "
            "against a Philippine recruitment agency deploying workers "
            "abroad. References POEA Memorandum Circular fee caps."
        ),
        body=_TEMPLATE_PH_DMW_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("destination_country", "Destination country", True),
            _f("worker_passport_prefix", "Worker passport prefix", False),
            _f("agency_name", "Recruitment agency", True),
            _f("agency_license", "DMW / POEA licence no.", False),
            _f("agency_address", "Agency office address", False),
            _f("deployment_date", "Deployment date", True),
            _f("placement_fee_amount_php", "Placement fee paid (PHP)", False, "payments[*].amount"),
            _f("placement_fee_cap_php", "Allowable POEA cap (PHP)", False),
            _f("incident_summary", "Incident summary", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO indicators", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),
    "iom_referral": TemplateSpec(
        id="iom_referral",
        title="IOM Referral (Protection / Repatriation)",
        jurisdiction="International (IOM)",
        audience="IOM Country Office · Protection Unit",
        summary=(
            "Referral form for protection assistance, repatriation, medical "
            "care, legal aid, or shelter. Intended for IOM country offices; "
            "all PII anonymized at transmission."
        ),
        body=_TEMPLATE_IOM_REFERRAL_BODY,
        fields=(
            _f("filed_date", "Referral date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "Referring organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("referring_country", "Country office (referring)", True),
            _f("case_reference", "Case reference code", True),
            _f("worker_nationality", "Subject nationality", True, "entities.nationality[0]"),
            _f("worker_age_range", "Age range (e.g., 25-30)", False),
            _f("worker_gender", "Gender", False),
            _f("current_location", "Current location", True),
            _f("country_of_origin", "Country of origin", True),
            _f("risk_factors", "Identified risks", True, "intelligence.risk_signals"),
            _f("trafficking_indicators", "Trafficking indicators", False, "intelligence.ilo_indicators"),
            _f("immediate_safety", "Immediate safety concern (Y/N)", True),
            _f("repat_required", "Repatriation assistance needed", False),
            _f("medical_required", "Medical assistance needed", False),
            _f("legal_aid_required", "Legal aid needed", False),
            _f("shelter_required", "Shelter needed", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("evidence_list", "Documentation held", False, "intelligence.evidence_edges"),
            _f("consent_status", "Subject consent status", True),
        ),
    ),
    "ngo_intake": TemplateSpec(
        id="ngo_intake",
        title="Generic NGO Case Intake (handover form)",
        jurisdiction="Generic / civil society",
        audience="Civil-society casework network",
        summary=(
            "Internal case-handover form for migrant-worker protection NGOs. "
            "Captures incident, timeline, evidence, and next-steps without "
            "binding the case to a specific regulator yet."
        ),
        body=_TEMPLATE_NGO_INTAKE_BODY,
        fields=(
            _f("filed_date", "Intake date", True),
            _f("case_reference", "Case reference", True),
            _f("complainant_name", "Receiving caseworker", True),
            _f("complainant_org", "Organisation", True),
            _f("complainant_contact", "Contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("worker_nationality", "Nationality", False),
            _f("sector", "Sector", False, "intelligence.sector"),
            _f("corridor", "Corridor", False, "intelligence.corridor"),
            _f("current_status", "Current worker status", True),
            _f("incident_timeline", "Incident timeline", True, "intelligence.journey_points"),
            _f("placement_fee_amount", "Recruitment fee disputed", False),
            _f("wage_owed", "Wages disputed", False),
            _f("contract_substitution", "Contract substitution (Y/N + detail)", False),
            _f("document_retention", "Document retention (Y/N + detail)", False),
            _f("ilo_indicators", "ILO indicators", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence inventory", False, "intelligence.evidence_edges"),
            _f("next_steps", "Next steps / referral target", True),
            _f("consent_status", "Worker consent status", True),
        ),
    ),
}


# ---------------------------------------------------------------------------
# Render + fill primitives
# ---------------------------------------------------------------------------


def render_template(body: str, field_values: dict) -> str:
    """Replace ``{{field_id}}`` placeholders with the provided values.

    Missing fields render as ``(not provided)`` so the draft is honest
    about what the caseworker still needs to fill in. No HTML.
    """
    out = body
    placeholders = re.findall(r"\{\{(\w+)\}\}", body)
    for fid in set(placeholders):
        value = field_values.get(fid)
        if value is None or str(value).strip() == "":
            replacement = "(not provided)"
        else:
            replacement = str(value).strip()
        out = out.replace("{{" + fid + "}}", replacement)
    return out


_HINT_PART_RE = re.compile(r"[a-zA-Z_]+|\[\d+\]|\[\*\]")


def bundle_field_hint(bundle: dict, source_hint: str) -> Optional[str]:
    """Best-effort lookup of a ``source_hint`` inside a process bundle.

    Supports a tiny path syntax:

      * ``people[0].label``
      * ``entities.employer[0]``
      * ``intelligence.case_brief``
      * ``payments[*].amount`` (collects all amounts as a comma-list)

    Returns ``None`` when the path cannot be resolved. Always honest:
    never fabricates a value; downstream callers treat ``None`` as
    "Gemma or manual entry should fill this".
    """
    if not bundle or not source_hint:
        return None
    try:
        parts = _HINT_PART_RE.findall(source_hint)
        node: Any = bundle
        collected: list = []
        for part in parts:
            if part == "[*]":
                if isinstance(node, list):
                    collected = node
                    node = collected
                else:
                    return None
            elif part.startswith("[") and part.endswith("]"):
                idx = int(part[1:-1])
                if isinstance(node, list) and 0 <= idx < len(node):
                    node = node[idx]
                else:
                    return None
            else:
                if collected:
                    node = [
                        (x.get(part) if isinstance(x, dict) else None)
                        for x in collected
                    ]
                    node = [x for x in node if x is not None]
                    collected = node
                elif isinstance(node, dict):
                    node = node.get(part)
                else:
                    return None
            if node is None:
                return None
        if isinstance(node, list):
            return ", ".join(str(x) for x in node[:10])
        if isinstance(node, (dict, set)):
            return None
        return str(node)
    except Exception:
        return None


def bundle_excerpt_for_template(bundle: dict, *, max_chars: int = 3000) -> str:
    """Compress a case bundle into a Gemma-friendly text excerpt.

    Trims to ``max_chars`` characters so prompts stay inside reasonable
    token budgets. Structured so Gemma can spot ``CASE BRIEF``,
    ``PEOPLE``, ``ENTITIES`` etc. headers without needing the full
    bundle JSON.
    """
    if not bundle:
        return "(no bundle provided)"
    parts: list[str] = []
    intel = bundle.get("intelligence") or {}
    summary = intel.get("summary") or bundle.get("summary") or {}
    if summary:
        parts.append("SUMMARY: " + json.dumps(summary, default=str)[:600])
    case_brief = intel.get("case_brief")
    if case_brief:
        parts.append("CASE BRIEF: " + str(case_brief)[:800])
    people = (intel.get("people") or [])[:5]
    if people:
        parts.append("PEOPLE: " + json.dumps(people, default=str)[:400])
    entities = intel.get("entities") or {}
    if entities:
        parts.append("ENTITIES: " + json.dumps(entities, default=str)[:400])
    payments = (intel.get("payments") or [])[:8]
    if payments:
        parts.append("PAYMENTS: " + json.dumps(payments, default=str)[:300])
    journey = (intel.get("journey_points") or [])[:8]
    if journey:
        parts.append("JOURNEY: " + json.dumps(journey, default=str)[:600])
    ilo = intel.get("ilo_indicators") or []
    if ilo:
        parts.append("ILO INDICATORS: " + json.dumps(ilo, default=str)[:300])
    evidence = (intel.get("evidence_edges") or [])[:8]
    if evidence:
        parts.append("EVIDENCE: " + json.dumps(evidence, default=str)[:400])
    text = "\n".join(parts)
    return text[:max_chars] if len(text) > max_chars else text


def safe_json_extract(text: str) -> Any:
    """Pull the first ``{...}`` block out of a model response and
    parse it. Returns ``{}`` on failure so callers never see a raw
    exception from a slightly malformed Gemma output.
    """
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except Exception:
                    start = -1
    return {}


def gemma_fill_template(
    template: TemplateSpec,
    bundle: dict,
    manual_fields: dict,
    gemma_call: Optional[Callable[..., Any]] = None,
) -> tuple[dict, dict]:
    """Three-pass fill: deterministic source hints, manual overrides,
    Gemma orchestration for remaining gaps.

    Manual fields ALWAYS override Gemma's suggestion -- this is the
    caseworker's authority.

    Returns ``(filled_values, meta)`` where ``meta`` carries:
      * ``per_field``  -- {field_id: "manual" | "bundle_hint" |
                            "gemma" | "missing"}
      * ``used_gemma`` -- True if a real Gemma call completed
      * ``__gemma_error`` -- present only on Gemma failure
    """
    filled: dict = {}
    provenance: dict = {}

    # Pass 1: deterministic source hints from the bundle.
    for field in template.fields:
        if field.source_hint:
            value = bundle_field_hint(bundle, field.source_hint)
            if value:
                filled[field.id] = value
                provenance[field.id] = "bundle_hint"

    # Pass 2: manual fields override (caseworker has final say).
    for fid, value in (manual_fields or {}).items():
        if value is None:
            continue
        sval = str(value).strip()
        if not sval:
            continue
        filled[fid] = sval
        provenance[fid] = "manual"

    # Pass 3: Gemma fills gaps when available + requested.
    used_gemma = False
    gemma_error: Optional[str] = None
    if gemma_call is not None:
        gaps = [f for f in template.fields if f.id not in filled]
        if gaps:
            bundle_excerpt = bundle_excerpt_for_template(bundle)
            field_summary = "\n".join(
                f"  - {f.id} ({'required' if f.required else 'optional'}): {f.label}"
                for f in gaps
            )
            prompt = (
                "You are an NGO caseworker assistant. Based on the case bundle "
                "below, propose values for the listed fields of an official "
                "complaint or referral document. Return strict JSON: "
                "{\"fields\": {\"field_id\": \"value\", ...}}. Do NOT invent "
                "facts not present in the bundle. Anonymize names to their "
                "first initial or to '(anonymized)'. Currency values keep "
                "their numeric amount + currency. If you do not have enough "
                "evidence for a field, omit it from the JSON.\n\n"
                f"TEMPLATE: {template.title}\n"
                f"FIELDS TO PROPOSE:\n{field_summary}\n\n"
                f"CASE BUNDLE EXCERPT:\n{bundle_excerpt}\n\n"
                "Respond with the JSON only."
            )
            try:
                raw = gemma_call(prompt, max_new_tokens=1024, temperature=0.6)
                used_gemma = True
                parsed = safe_json_extract(raw)
                proposed = (parsed.get("fields") if isinstance(parsed, dict) else None) or {}
                # Guard against fabricated field IDs: only accept
                # field_ids that exist in this template's schema.
                valid_ids = {f.id for f in template.fields}
                for fid, value in proposed.items():
                    if fid not in valid_ids:
                        continue
                    if fid in filled:
                        continue
                    sval = str(value).strip()
                    if sval:
                        filled[fid] = sval
                        provenance[fid] = "gemma"
            except Exception as e:  # noqa: BLE001
                gemma_error = f"{type(e).__name__}: {str(e)[:120]}"

    # Mark remaining gaps as missing so the UI can highlight them.
    for field in template.fields:
        if field.id not in filled:
            provenance[field.id] = "missing"

    meta: dict = {"per_field": provenance, "used_gemma": used_gemma}
    if gemma_error:
        meta["__gemma_error"] = gemma_error
    return filled, meta


# ---------------------------------------------------------------------------
# Robust boolean parsing for body fields
# ---------------------------------------------------------------------------


def parse_bool(value: Any, default: bool = False) -> bool:
    """Parse a request-body field that should be boolean.

    ``bool("false")`` returns ``True`` in plain Python; browsers and
    curl users routinely send JSON booleans as strings, so we need an
    explicit parser. Accepts:

      * native True / False  -> as-is
      * 1 / 0                -> True / False
      * "true" / "false" / "yes" / "no" / "on" / "off" (case-insensitive)
      * None / missing       -> default

    Anything else returns ``default`` so an obviously bogus value
    cannot quietly enable a destructive flag.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("true", "1", "yes", "y", "on"):
            return True
        if s in ("false", "0", "no", "n", "off", ""):
            return False
    return default


# ---------------------------------------------------------------------------
# FastAPI integration
# ---------------------------------------------------------------------------


def register_template_routes(app: Any) -> None:
    """Attach ``GET /api/templates/list`` and ``POST /api/templates/fill``
    to the supplied FastAPI app.

    Idempotent: the second call no-ops so a hot-reload during
    development does not raise "duplicate operation_id" on uvicorn
    restart. The kernel script calls this exactly once after
    ``create_app``.
    """

    if getattr(app.state, "_dc_templates_registered", False):
        return
    app.state._dc_templates_registered = True

    @app.get("/api/templates/list")
    def api_templates_list():
        """List all registered NGO complaint / referral templates."""
        return {
            "templates": [t.summary_payload() for t in TEMPLATES_REGISTRY.values()],
        }

    @app.post("/api/templates/fill")
    def api_templates_fill(body: dict = Body(...)):
        """Fill a template with values from a case bundle + manual
        overrides + an optional Gemma 4 orchestration pass."""
        body = body or {}
        template_id = (body.get("template_id") or "").strip()
        template = TEMPLATES_REGISTRY.get(template_id)
        if template is None:
            return JSONResponse(
                {
                    "status": "unknown_template",
                    "message": (
                        f"No template registered for id={template_id!r}. "
                        f"Call /api/templates/list for the available set."
                    ),
                    "available": list(TEMPLATES_REGISTRY.keys()),
                },
                status_code=404,
            )
        bundle = body.get("bundle") or {}
        manual_fields = body.get("manual_fields") or {}
        use_gemma = parse_bool(body.get("use_gemma"), default=True)
        gemma_call = (
            getattr(app.state, "gemma_call", None) if use_gemma else None
        )
        filled, meta = gemma_fill_template(
            template, bundle, manual_fields, gemma_call=gemma_call,
        )
        rendered = render_template(template.body, filled)
        return {
            "template": template.summary_payload(),
            "rendered": rendered,
            "field_values": filled,
            "provenance": meta.get("per_field", {}),
            "used_gemma": meta.get("used_gemma", False),
            "gemma_error": meta.get("__gemma_error"),
        }


__all__ = [
    "TEMPLATES_REGISTRY",
    "TemplateField",
    "TemplateSpec",
    "bundle_excerpt_for_template",
    "bundle_field_hint",
    "gemma_fill_template",
    "parse_bool",
    "register_template_routes",
    "render_template",
    "safe_json_extract",
]
