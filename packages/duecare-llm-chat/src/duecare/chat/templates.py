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

# Shared scrub used to keep operational kernel metadata out of the
# bundle excerpt Gemma sees and out of the filled field values that
# end up in the rendered complaint document. Without this, paths like
# /kaggle/working/process-staging/case_files_*.zip can land verbatim
# in an HK Labour Department complaint draft.
from .harnesses._safe_text import (
    clean_for_knowledge_fact as _clean_for_knowledge_fact,
    fact_excerpt as _fact_excerpt,
)


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
# Corridor complaint templates (added 2026-05-21).
#
# Each body cites the corridor's specific statute set so the rendered
# complaint reads correctly to the destination authority. Field
# placeholders use the same naming convention as the original four
# templates so source_hint paths into the bundle stay consistent.
# ---------------------------------------------------------------------------

_TEMPLATE_NP_DOFE_BODY = """COMPLAINT TO DEPARTMENT OF FOREIGN EMPLOYMENT (DoFE)
Foreign Employment Act 2007 / Foreign Employment Rules 2008
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

NEPALI MIGRANT WORKER (subject of complaint)
  Anonymized identifier:  {{worker_name}}
  Destination country:    {{destination_country}}
  Passport prefix:        {{worker_passport_prefix}}

LICENSED MANPOWER AGENCY
  Agency name:            {{agency_name}}
  DoFE licence no.:       {{agency_license}}
  Agency address:         {{agency_address}}

PARTICULARS OF THE VIOLATION
  Deployment date:                     {{deployment_date}}
  Service charge collected (NPR):      {{recruitment_fee_amount_npr}}
  Statutory ceiling (Foreign Employment Rules 2008): {{recruitment_fee_cap_npr}}
  Document fees collected (NPR):       {{document_fees_npr}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - Foreign Employment Act 2007 sections 21-25 (recruitment service
    charge ceiling, prohibition on collection of fees beyond schedule)
  - Foreign Employment Rules 2008 (destination-specific ceilings)
  - ILO C181 Art. 7 (no worker-paid recruitment fees, direct or
    indirect)

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

This complaint is submitted in good faith based on case material held
by {{complainant_org}}. The complainant requests referral to the
Foreign Employment Tribunal (FETB) where warranted, refund of all
excess charges, and cross-notification to the destination-country
labour authority.

Signature: ________________________    Date: __________
"""

_TEMPLATE_ID_BP2MI_BODY = """COMPLAINT TO BP2MI
Badan Pelindungan Pekerja Migran Indonesia
UU 18/2017 / BP2MI Regulation 09/2020
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

INDONESIAN MIGRANT WORKER (Pekerja Migran Indonesia)
  Anonymized identifier:  {{worker_name}}
  Destination country:    {{destination_country}}
  Sector:                 {{sector}}
  Passport prefix:        {{worker_passport_prefix}}

LICENSED P3MI AGENCY
  Agency name:            {{agency_name}}
  BP2MI / P3MI licence:   {{agency_license}}
  Agency address:         {{agency_address}}

PARTICULARS OF THE VIOLATION
  Deployment date:                     {{deployment_date}}
  Unauthorised fee collected (IDR):    {{recruitment_fee_amount_idr}}
  Salary-deduction repayment terms:    {{salary_deduction_terms}}
  Months of salary withheld:           {{months_withheld}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - UU 18/2017 (Protection of Indonesian Migrant Workers) on
    prohibited fees and pre-departure obligations
  - BP2MI Regulation 09/2020 on the limited list of recoverable cost
    components (excludes most placement/training charges)
  - ILO C181 Art. 7 and ILO C189 where domestic work is involved

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests BP2MI to investigate the P3MI agency,
suspend or revoke the licence, order refund of all unauthorised
fees, and coordinate with the destination-country labour authority
on cross-border enforcement.

Signature: ________________________    Date: __________
"""

_TEMPLATE_BD_BMET_BODY = """COMPLAINT TO BMET
Bureau of Manpower, Employment and Training, Bangladesh
Overseas Employment and Migrants Act 2013
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

BANGLADESHI MIGRANT WORKER (subject)
  Anonymized identifier:  {{worker_name}}
  Destination country:    {{destination_country}}
  Sector:                 {{sector}}
  Passport prefix:        {{worker_passport_prefix}}

LICENSED RECRUITING AGENT
  Agent name:             {{agency_name}}
  BMET licence no.:       {{agency_license}}
  Agency address:         {{agency_address}}

PARTICULARS OF THE VIOLATION
  Deployment date:                       {{deployment_date}}
  Recruitment cost collected (BDT):      {{recruitment_fee_amount_bdt}}
  Bilateral ceiling (G2G+ MoU):          {{recruitment_fee_cap_bdt}}
  Family / third-party payments:         {{family_payment_amount}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - Overseas Employment and Migrants Act 2013 (Bangladesh): fee
    limits, recruiter licensing, worker-protection provisions
  - Bangladesh-Malaysia G2G+ MoU (where applicable): worker share
    of recruitment cost capped, employer pays pre-departure costs
  - ILO C181 Art. 7

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests BMET to investigate, suspend or cancel the
Recruiting Agent's licence, order refund of excess fees, and
coordinate with the destination-country labour authority on
cross-border enforcement.

Signature: ________________________    Date: __________
"""

_TEMPLATE_VN_DOLAB_BODY = """COMPLAINT TO DOLAB
Department of Overseas Labour, Vietnam
Decree 38/2020/ND-CP
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

VIETNAMESE MIGRANT WORKER (subject)
  Anonymized identifier:  {{worker_name}}
  Destination country:    {{destination_country}}
  Sector:                 {{sector}}
  Passport prefix:        {{worker_passport_prefix}}

LICENSED SENDING AGENCY
  Agency name:            {{agency_name}}
  DOLAB licence no.:      {{agency_license}}
  Agency address:         {{agency_address}}

PARTICULARS OF THE VIOLATION
  Deployment date:                        {{deployment_date}}
  Service fee collected (USD):            {{recruitment_fee_amount_usd}}
  Statutory cap (Decree 38/2020/ND-CP):   {{recruitment_fee_cap_usd}}
  Brokerage fee (monthly):                {{monthly_brokerage_usd}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - Decree 38/2020/ND-CP (Vietnam) on fee categories and ceilings
  - Employment Service Act (Taiwan) where applicable: caps on
    monthly broker fees by year of service
  - ILO C181 Art. 7

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests DOLAB to investigate, suspend or revoke the
sending agency's licence, order refund of excess service fees and
brokerage, and coordinate with the destination-country labour
authority on cross-border enforcement.

Signature: ________________________    Date: __________
"""

_TEMPLATE_NGO_SURVIVOR_NARRATIVE_BODY = """SURVIVOR NARRATIVE -- NGO INTAKE
For internal case-management + (with consent) onward referral
Filing date: {{filed_date}}

CASEWORKER:    {{complainant_name}}
ORGANISATION:  {{complainant_org}}
CONTACT:       {{complainant_contact}}

SURVIVOR ANONYMIZED ID:  {{survivor_anon_id}}
LANGUAGES SPOKEN:        {{languages_spoken}}
COUNTRY OF ORIGIN:       {{country_of_origin}}
CURRENT LOCATION:        {{current_general_location}}
AGE CATEGORY:            {{age_category}}

CONSENT + SAFETY STATUS (filled BEFORE any disclosure detail)
  Is the survivor safe to disclose now?       {{is_safe_to_disclose}}
  Is a controlling third party present?       {{controlling_third_party_status}}
  Interpreter (professional, not companion):  {{interpreter_status}}
  Mandatory-reporting limits disclosed:       {{mandatory_reporting_disclosed_yes_no}}
  Survivor has consented to this record:      {{consent_to_record_yes_no}}
  Onward referral consent (per provider):     {{onward_referral_consent_summary}}

[The narrative below is the survivor's account, recorded in
the survivor's own words and pacing. The caseworker has not
asked for chronological order; trauma narratives are
fragmentary by nature and forcing order re-traumatises.
Caseworker NOTES are bracketed; survivor's WORDS are not.]

PHASE 1 -- RECRUITMENT
[The survivor describes the recruitment context.]
{{recruitment_narrative}}

[Caseworker note: indicators observed in this phase:]
  - Deception (different role / wage promised):  {{recruit_deception_yes_no}}
  - Abuse of vulnerability:                      {{recruit_abuse_vulnerability_yes_no}}
  - Recruitment-fee charged:                     {{recruit_fee_charged_yes_no}}
  - Recruitment channel:                         {{recruit_channel}}

PHASE 2 -- DEPLOYMENT / JOURNEY
[The survivor describes the journey + arrival.]
{{deployment_narrative}}

[Caseworker note: indicators observed in this phase:]
  - Document retention on arrival:               {{doc_retention_arrival_yes_no}}
  - Restriction of movement on arrival:          {{movement_restriction_arrival_yes_no}}
  - Different contract on arrival:               {{contract_substitution_yes_no}}

PHASE 3 -- EXPLOITATION
[The survivor describes the work and living conditions.]
{{exploitation_narrative}}

[Caseworker note: indicators observed in this phase:]
  - Withholding of wages:                        {{wage_withholding_yes_no}}
  - Excessive overtime:                          {{excessive_overtime_yes_no}}
  - Isolation:                                   {{isolation_yes_no}}
  - Physical or sexual violence:                 {{physical_sexual_violence_yes_no}}
  - Intimidation or threats:                     {{intimidation_threats_yes_no}}
  - Debt bondage:                                {{debt_bondage_yes_no}}
  - Abusive working / living conditions:         {{abusive_conditions_yes_no}}

PHASE 4 -- ESCAPE / SUPPORT
[The survivor describes how they left + current support.]
{{escape_support_narrative}}

VALIDATION FROM CASEWORKER (pre-filled)
"What you have described is real. You are not to blame. The
agreement you signed under deception, debt-pressure, or abuse
of vulnerability is not legally binding consent under the
Palermo Protocol Art. 3(b). Multiple ILO Forced-Labour
Indicators apply to your situation. You have rights regardless
of immigration status or contract clause."

CONTROLLING LAW (for any future formal proceeding)
  - UN Palermo Protocol Art. 3 (act / means / purpose) +
    Art. 3(b) consent irrelevance
  - ILO 11 Forced Labour Indicators (2012)
  - ILO Convention 181 Art. 7 (no worker-side fees, direct
    or indirect)
  - ILO Convention 189 Art. 9 (passport retention prohibited)
  - {{corridor_specific_origin_statute}}
  - {{corridor_specific_destination_statute}}

SURVIVOR-LED NEXT STEPS (only with consent)
{{survivor_led_next_steps}}

CASEWORKER REFERRAL PATHS (proposed; survivor may decline)
  1. NGO shelter / safehouse:           {{ngo_shelter_referral}}
  2. Origin-country embassy / POLO:     {{embassy_polo_referral}}
  3. Destination labour authority:      {{destination_labour_referral}}
  4. Legal-aid for civil restitution:   {{legal_aid_referral}}
  5. Medical / mental-health support:   {{medical_mh_referral}}
  6. Survivor peer-support network:     {{peer_support_referral}}

Caseworker signature: ________________________   Date: {{filed_date}}
"""


_TEMPLATE_WORKER_FIRST_CONTACT_SCRIPT_BODY = """WORKER FIRST-CONTACT SCRIPT (WhatsApp / SMS / Encrypted Chat)
Designed for use by NGO advocate / peer helper / community trusted
person. Worker may be in unsafe location. KEEP MESSAGES SHORT.
Filing date: {{filed_date}}

ADVOCATE:      {{complainant_name}}
ORGANISATION:  {{complainant_org}}
LANGUAGE:      {{primary_language}}

OPENING (turn 1)
"Hello. My name is {{advocate_first_name_only}}. I work with
{{complainant_org}}. We help migrant workers. Are you safe to
text right now? Yes or No."

[If 'No' -> immediately send corridor-emergency contact:
{{corridor_emergency_one_liner}}.]

[If 'Yes' -> continue with turn 2.]

TURN 2 -- BASIC SAFETY CHECK
"Thank you. I need to ask a few questions. You do not have to
answer if you do not feel safe. Anything you say I keep
private. Police, immigration, and your employer will not see
this."

  - Are you in {{destination_country}}?
  - Do you have your passport with you?
  - Do you have your phone with you all day?
  - Can you go outside alone?

TURN 3 -- LISTEN
"Take your time. Tell me what you want me to know."

[Pause. Let the worker reply at their pace. Do NOT push for
chronological order. Do NOT ask 'what happened' as the first
question -- it re-traumatises. Use 'what is most on your mind'
instead.]

TURN 4 -- VALIDATION (pre-filled)
"What you are describing is real. You are not stupid for
coming. You did not agree to this. There are rules that say
your passport must be with you (ILO C189 Art. 9). There are
rules that say you cannot be charged training fees in
{{destination_country}} (controlling statute:
{{worker_side_fee_statute}}). You have rights even without
papers."

TURN 5 -- IMMEDIATE NEEDS TRIAGE
"What do you need first?"
  1. Get to a safe place
  2. Get my passport back
  3. Get my unpaid wages
  4. Go home to {{country_of_origin}}
  5. Talk to someone about what happened
  6. Other / I do not know

TURN 6 -- BASED ON ANSWER, ROUTE
[Caseworker fills in the corridor-specific contact for the
chosen option. Each contact is a verified NGO + government +
embassy / POLO from the contacts pack.]

If 1: {{safe_place_contact}}
If 2: {{document_recovery_contact}}
If 3: {{wage_recovery_contact}}
If 4: {{repatriation_contact}}
If 5: {{psychosocial_contact}}

TURN 7 -- WHAT THE WORKER CAN DO RIGHT NOW
"While we work on this, you can:
  - Take photos of your contract, your passport, your room,
    your work site. Save them somewhere safe (different phone,
    cloud account with strong password, email to a trusted
    friend).
  - Take screenshots of any message from your employer or
    recruiter. Date matters.
  - Keep a simple log: date / what happened / who was there /
    how you felt.
  - Do not confront your employer or recruiter. We will help
    you plan that step.
  - If you need to delete this conversation for your safety,
    delete it. We will remember. You are not alone."

TURN 8 -- CLOSE
"I will reach out again in {{follow_up_window}}. If something
changes before then, text or call this number:
{{advocate_contact}}. You can also reach the
{{corridor_specific_hotline}} at {{corridor_hotline_number_or_verify}}.
You did the right thing by reaching out. Take care."

ADVOCATE NOTES (internal)
{{advocate_internal_notes}}
"""


_TEMPLATE_JOURNALIST_TIP_BODY = """JOURNALIST TIP / ANONYMIZED CASE BRIEF
For investigative-journalism partners (Guardian + Reuters +
ProPublica + BBC + Al Jazeera + national investigative desks)
Filing date: {{filed_date}}

FROM:    {{complainant_name}}
         {{complainant_org}}
         {{complainant_contact}}

TO:      {{journalist_outlet}}
         Attn: {{journalist_name}}

RE:      Anonymized case brief, request for investigation
         partnership

This tip is provided on the record with respect to the
underlying public-record statutes and patterns; all victim-
specific facts are anonymized and presented in aggregate
form to protect survivor identity. Specific victim names,
employer names, and other identifying details are withheld
pending an editorial decision and survivor consent.

EXECUTIVE SUMMARY
{{executive_summary}}

PATTERN
{{pattern_description}}

NUMBERS (de-identified, ranges where appropriate)
  Affected workers (range):              {{affected_workers_range}}
  Corridor:                              {{corridor}}
  Sector:                                {{sector}}
  Period of conduct:                     {{period_of_conduct}}
  Estimated worker-paid sum (USD range): {{worker_paid_usd_range}}
  Repeat-violator pattern (Y / N):       {{repeat_violator_yes_no}}

REGULATORY POSTURE
  Origin-country regulator:        {{origin_regulator}}
  Action taken to date:            {{origin_action_to_date}}
  Destination-country regulator:   {{destination_regulator}}
  Action taken to date:            {{destination_action_to_date}}
  Outstanding referrals / complaints: {{outstanding_referrals}}

VERIFICATION QUESTIONS (for the journalist's reporting)
  1. {{verification_question_1}}
  2. {{verification_question_2}}
  3. {{verification_question_3}}
  4. {{verification_question_4}}
  5. {{verification_question_5}}

PRIMARY-SOURCE DOCUMENTS AVAILABLE (on request, subject to
survivor consent + redaction)
{{available_documents}}

NAMED ENTITIES (public-record only -- regulators / NGOs /
court filings)
{{named_public_entities}}

STATUTORY FRAMEWORK
  - UN Palermo Protocol Art. 3
  - {{controlling_origin_statute}}
  - {{controlling_destination_statute}}
  - ILO Convention 181 Art. 7 + 2019 Definition of
    Recruitment Fees
  - {{supply_chain_or_sectoral_framework}}

NGO ETHICAL OPERATIONAL CONSTRAINTS
  - Survivor identity protected unless / until the survivor
    affirms publication consent in writing
  - Trafficker / employer name to be released only when:
    (a) public-record source already names the entity, OR
    (b) survivor consents and the journalist accepts the
        defamation-risk burden after their own diligence
  - No payment to the survivor for participation in the
    story; reasonable expenses + accommodation acceptable
  - Survivor's right to withdraw at any time before
    publication

The undersigned is willing to support background interviews,
review draft text for factual accuracy regarding public-record
elements, and (with survivor consent) facilitate an interview
with the survivor through a trauma-informed protocol.

Signature:

{{complainant_name}}
{{complainant_org}}
{{complainant_contact}}

Date: {{filed_date}}
"""


_TEMPLATE_EMPLOYER_WAGE_DEMAND_BODY = """DIRECT EMPLOYER WAGE ARREARS DEMAND LETTER
Migrant Worker -- Pre-litigation Demand for Payment
Filing date: {{filed_date}}

TO:      {{employer_name}}
         {{employer_address}}
         Attn: {{employer_attention}}

CC:      {{destination_country_labour_authority}}
         {{worker_origin_country_embassy_or_polo}}

RE:      DEMAND for payment of unpaid wages owed to
         {{worker_name}} (anonymized identifier),
         {{worker_nationality}} migrant worker, period
         {{wage_period}}.

Dear Sir / Madam,

We represent {{worker_name}}, a {{worker_nationality}} migrant
worker who was / is employed by you under
{{contract_reference}}. We write to formally demand payment of
wages owed for work actually performed during the period
{{wage_period}}, which to date you have failed to pay.

WAGES OWED
  Period of underpayment:           {{wage_period}}
  Hours actually worked:            {{hours_actually_worked}}
  Statutory minimum wage applicable: {{statutory_min_wage}}
  Agreed contract wage:             {{contract_wage}}
  Wages actually paid:              {{wages_actually_paid}}
  Outstanding wages:                {{wages_outstanding_local}}
  Currency:                         {{currency}}
  Equivalent in USD (informational): {{wages_outstanding_usd}}

CONTROLLING LAW
  1. {{destination_wage_statute}} requires payment of wages in
     full and on time. Failure to pay is a statutory violation
     subject to civil penalty and -- in cases of wilful
     non-payment -- criminal liability.
  2. ILO Convention 95 Article 12 requires wages to be paid
     regularly, in legal tender, directly to the worker.
  3. ILO Forced Labour Indicator 8 (withholding of wages) is
     one of the eleven ILO operational indicators of forced
     labour (ILO Special Action Programme to Combat Forced
     Labour, 2012).
  4. UN Palermo Protocol Art. 3 -- withholding of wages used
     as a means of control constitutes trafficking in persons.

DEMAND FOR PAYMENT (within 10 calendar days from receipt of
this letter):
  1. Full payment of {{wages_outstanding_local}} to the worker
     via {{preferred_payment_channel}};
  2. Written confirmation that no further wages are being
     withheld;
  3. Written undertaking that no retaliation will be taken
     against the worker or the worker's family for asserting
     this demand;
  4. Copies of all wage records, timesheets, deduction
     authorisations, and bank-transfer records for the period
     in question.

FAILURE TO COMPLY by {{compliance_deadline}} will result in:
  (a) Formal complaint to {{destination_country_labour_authority}}
      including request for civil penalty + interest;
  (b) Civil claim in {{civil_court_or_tribunal}} for
      principal sum + pre-judgment interest + statutory
      damages + reasonable legal expense;
  (c) Concurrent complaint to the worker's origin-country
      labour authority for parallel investigation and
      sanctions where applicable;
  (d) Notification to the worker's national consulate /
      embassy / POLO for record;
  (e) Where wilful non-payment + accompanying indicators are
      present, referral for trafficking investigation under
      {{trafficking_statute}}.

The worker is represented by {{complainant_name}},
{{complainant_org}}. All correspondence concerning this
matter should be directed to {{complainant_contact}}. The
worker reserves all rights and remedies under destination-
country law, origin-country law, and international law.

Sincerely,

{{complainant_name}}
{{complainant_org}}
{{complainant_contact}}

Date: {{filed_date}}

cc: as above
"""


_TEMPLATE_SUPPLIER_AUDIT_FINDING_BODY = """BUYER -> SUPPLIER AUDIT FINDING LETTER
Pre-CSDDD / UK MSA / Lieferkettengesetz / Transparency Act
Compliance Remediation Sequence
Filing date: {{filed_date}}

FROM:    {{buyer_company_name}}
         Attn: {{buyer_compliance_officer}}
         {{buyer_address}}

TO:      {{supplier_company_name}}
         Attn: {{supplier_contact}}
         {{supplier_address}}

RE:      Audit findings of {{audit_type}} conducted
         {{audit_date_range}} at {{supplier_facility_name}}
         in {{supplier_facility_country}}. Findings include
         indicators of forced labour, recruitment-fee
         violations, and / or document retention requiring
         remediation under our supplier code of conduct and
         applicable supply-chain due-diligence statutes.

I.   AUDIT METHODOLOGY
The audit was conducted between {{audit_date_range}} by
{{audit_provider}}. The methodology covered worker
interviews ({{n_worker_interviews}} workers), management
interviews, document review (employment contracts, payroll,
recruitment-agreement, working-time records,
accommodation), facility walkthrough, recruitment-channel
tracing, and verification against the {{recruitment_country}}
licensing registry.

II.  FINDINGS OF NON-CONFORMANCE
{{findings_summary}}

Specifically:

(A) RECRUITMENT-FEE VIOLATION
   Workers reported paying recruitment-related costs to
   recruiters in {{recruitment_country}}, including
   {{recruitment_fee_categories}} totalling an average of
   {{recruitment_fee_average_usd}} per worker.
   Statutory standard: the employer-pays-principle of ILO
   C181 Art. 7 + 2019 Definition + IRIS Standard requires
   that workers shall not be charged any fee or cost for
   recruitment. Violation is a Tier-1 finding.

(B) DOCUMENT RETENTION
   {{document_retention_findings}}
   Statutory standard: ILO C189 Art. 9 + ILO Forced Labour
   Indicator 7 prohibit retention of identity / travel
   documents by employer / sponsor. Violation is a Tier-1
   finding.

(C) WORKING-TIME VIOLATIONS
   {{working_time_findings}}
   Statutory standard: {{destination_working_time_statute}}.

(D) WAGE VIOLATIONS
   {{wage_findings}}
   Statutory standard: {{destination_wage_statute}}.

(E) OTHER FINDINGS
   {{other_findings}}

III. REMEDIATION REQUIRED

(A) RECRUITMENT-FEE REIMBURSEMENT
   The supplier shall, within {{reimbursement_deadline_days}}
   days, reimburse all affected workers the full amount of
   recruitment-related fees paid, plus any reasonable
   interest. Reimbursement shall be paid directly to the
   worker via {{preferred_payment_channel}}.

(B) DOCUMENT RETURN
   The supplier shall, within 5 days, return all retained
   identity / travel documents to the affected workers and
   confirm in writing that no future retention will occur.

(C) POLICY + PROCEDURE
   The supplier shall, within {{policy_deadline_days}} days,
   adopt and submit for review: (i) a written employer-pays-
   principle policy; (ii) a written document-retention
   prohibition policy; (iii) a written worker grievance
   procedure aligned with UNGP 31 effectiveness criteria.

(D) MONITORING + REPORTING
   The supplier shall participate in monthly remediation
   monitoring with {{remediation_partner}} until the
   findings are closed.

IV.  COMPLIANCE FRAMEWORK
The findings + remediation requirements are issued under:
  - {{buyer_supplier_code_of_conduct}}
  - UK Modern Slavery Act 2015 Sec. 54 (if applicable)
  - EU CSDDD (Regulation 2024/1760, when in force from 2026)
  - France Loi de Vigilance 2017
  - Germany Lieferkettengesetz 2021
  - Norway Transparency Act 2021
  - US UFLPA + 19 USC 1307 (if any goods enter US market)
  - EU Forced Labour Regulation 2024/3015 (when in force
    end-2027)
  - UN Guiding Principles on Business and Human Rights (2011)
  - OECD Guidelines for MNEs (2023 revision)
  - IRIS Standard alignment commitment

V.   ESCALATION
Failure to meet remediation deadlines will result in:
  1. Escalation to {{buyer_chief_compliance_officer}};
  2. Suspension of new purchase orders for affected facility;
  3. Disclosure in the buyer's annual modern slavery
     statement to UK Government Modern Slavery Statement
     Registry + comparable EU / AU registries where
     applicable;
  4. Possible business termination + reporting of the
     supplier to {{regulator_or_industry_initiative}};
  5. Where applicable, support of affected workers' direct
     restitution claim under origin-country agency-bond +
     destination-country labour-tribunal pathways.

This letter is issued without prejudice to the buyer's other
rights under the supplier agreement and applicable law.

Sincerely,

{{buyer_compliance_officer}}
{{buyer_company_name}}

Date: {{filed_date}}

cc: as above
"""


_TEMPLATE_UNGP_OECD_REMEDIATION_REQUEST_BODY = """UN GUIDING PRINCIPLES / OECD NCP REMEDIATION REQUEST
To a Multinational Enterprise -- Pillar III Access-to-Remedy
Filing date: {{filed_date}}

FROM:    {{complainant_name}}
         {{complainant_org}}
         {{complainant_contact}}

TO:      {{multinational_enterprise_name}}
         Attn: {{mne_contact}}
         {{mne_address}}

CC:      National Contact Point (NCP), {{ncp_country}}
         {{ncp_address}}
         OECD Secretariat, Global Affairs Division

RE:      Pillar III Access-to-Remedy request under UN Guiding
         Principles on Business and Human Rights (2011) +
         filing notice under OECD Guidelines for Multinational
         Enterprises (2023 revision) National Contact Point
         Specific Instance process.

This communication is submitted on behalf of {{worker_name}}
(anonymized identifier), {{worker_nationality}} migrant
worker. The worker is affected by adverse human-rights
impacts in the {{mne_company_name}} value chain, as detailed
below.

I.   AFFECTED PARTIES
   Anonymized worker:           {{worker_name}}
   Nationality:                 {{worker_nationality}}
   Country of recruitment:      {{country_of_recruitment}}
   Sector:                      {{sector}}
   Direct employer:             {{direct_employer_name}}
   Tier in MNE value chain:     {{value_chain_tier}}
   Period of harm:              {{period_of_harm}}

II.  NATURE OF THE ADVERSE IMPACT
{{nature_of_adverse_impact}}

III. MNE NEXUS
The MNE's nexus to the harm under UNGP 13 is:
{{ungp_nexus_description}}
The MNE is therefore expected under UNGP 22 to:
  - Identify + assess the actual + potential adverse impacts
  - Integrate findings + take appropriate action
  - Track effectiveness of the response
  - Communicate externally about how the response is
    addressing the impact
  - Provide for / cooperate in legitimate remediation through
    grievance mechanisms aligned with UNGP 31 effectiveness
    criteria

IV.  PRIOR REQUESTS + RESPONSES
{{prior_requests_summary}}

V.   REMEDIATION REQUESTED (UNGP 22 + Pillar III)
The complainant requests the MNE to:
  1. Convene a remediation dialogue within 30 days;
  2. Engage with affected worker via trauma-informed +
     survivor-led process facilitated by {{complainant_org}};
  3. Provide recruitment-fee reimbursement to affected
     worker plus any documented dependants;
  4. Take supplier-side corrective action documented in
     writing;
  5. Disclose remediation outcome in the MNE's next annual
     human-rights or modern-slavery statement;
  6. Establish or strengthen an operational-level grievance
     mechanism aligned with UNGP 31 effectiveness criteria
     (legitimate, accessible, predictable, equitable,
     transparent, rights-compatible, source of continuous
     learning, based on engagement and dialogue).

VI.  CONCURRENT NCP FILING
A concurrent Specific Instance filing under the OECD
Guidelines for MNEs (2023 revision) is being submitted with
the NCP at {{ncp_country}}. The complainant requests good-
offices mediation under the NCP process. The MNE's
participation in the NCP process is voluntary but expected
under the OECD framework.

VII. STATUTORY + FRAMEWORK CITATIONS
   - UN Guiding Principles on Business and Human Rights
     (HRC Resolution 17/4, 2011)
   - OECD Guidelines for Multinational Enterprises on
     Responsible Business Conduct (2023 revision)
   - {{country_of_origin_due_diligence_statute_if_any}}
   - {{country_of_destination_due_diligence_statute_if_any}}
   - UK Modern Slavery Act 2015 + France Loi de Vigilance
     2017 + Germany Lieferkettengesetz 2021 + Norway
     Transparency Act 2021 + EU CSDDD 2024 + EU Forced
     Labour Regulation 2024
   - ILO Convention 181 Art. 7

VIII. RESERVATION OF RIGHTS
This request is made without prejudice to the affected
worker's other rights under origin-country, destination-
country, and international law, including but not limited
to labour-tribunal restitution, criminal trafficking
investigation, and supply-chain enforcement (UFLPA / EU FLR
/ CBP WRO).

Respectfully submitted,

{{complainant_name}}
{{complainant_org}}
{{complainant_contact}}

Date: {{filed_date}}

cc: as above
"""


_TEMPLATE_PH_HK_FDH_FEE_REFUND_DEMAND_BODY = """RECRUITMENT FEE REFUND DEMAND LETTER
Philippines to Hong Kong Foreign Domestic Helper Corridor
Filing date: {{filed_date}}

TO:    {{agency_name}} (Philippine licensed recruitment agency)
       {{agency_address}}
       Attn: {{agency_principal_or_officer}}
       DMW Recruitment Agency Licence: {{agency_license_no}}

       and

       {{hk_agency_name}} (Hong Kong-side employment agency, if applicable)
       {{hk_agency_address}}
       HK EA Licence: {{hk_ea_license_no}}

CC:    Department of Migrant Workers (DMW) Anti-Illegal Recruitment Branch
       Hong Kong Labour Department, Employment Agencies Administration (EAA)
       Philippine Migrant Workers Office, Hong Kong

RE:    DEMAND FOR REFUND OF UNAUTHORISED FEES collected from
       {{worker_name}} (anonymized identifier), Filipino Household
       Service Worker deployed to Hong Kong on {{deployment_date}}.

Dear Sir / Madam,

We represent {{worker_name}}, a Filipino Household Service Worker
(HSW) deployed to Hong Kong by your agency under POEA / DMW licence
referenced above. We write to formally demand the immediate refund
of all fees collected from the worker in violation of Philippine
and Hong Kong law.

PARTICULARS OF THE UNAUTHORISED COLLECTION
  Total amount paid by the worker (PHP):   {{total_paid_php}}
  Breakdown of charges:
    - Training fee:                         {{training_fee_php}}
    - Medical examination fee:              {{medical_fee_php}}
    - Processing / documentation fee:       {{processing_fee_php}}
    - Placement fee (any label):            {{placement_fee_php}}
    - Other (specify):                      {{other_fees_php}}
  Date(s) of collection:                    {{collection_dates}}
  Receipts issued / not issued:             {{receipt_status}}
  Currency received by agency:              PHP

CONTROLLING LAW
  1. POEA Memorandum Circular No. 14 of 2017 prohibits Philippine
     licensed recruitment agencies from charging ANY placement fee
     to Filipino HSWs deployed to Hong Kong, REGARDLESS OF LABEL.
     This includes training fees, medical fees, processing fees,
     documentation fees, or any other charge.
  2. ILO Convention 181 Article 7(1) prohibits private employment
     agencies from charging fees DIRECTLY OR INDIRECTLY, in whole
     or in part, to workers. The 2019 ILO Definition of Recruitment
     Fees and Related Costs enumerates training fees, medical
     examination fees, orientation / training fees, equipment, and
     travel during recruitment as worker-prohibited costs.
  3. Republic Act 8042 (Migrant Workers Act) as amended by RA 10022
     declares illegal recruitment, including charging amounts in
     excess of those allowed by law, a criminal offence punishable
     by 12 years to life imprisonment and fines up to PHP 5 million.
  4. Hong Kong Employment Agency Regulations Cap. 57A Reg. 2 caps
     commission from a worker at 10% of first-month wages; ANY
     additional Hong Kong-side collection from the worker beyond
     this cap is an EA misconduct under Cap. 57A Reg. 13.

DEMAND FOR REMEDY (within 14 calendar days from receipt of this
letter):
  1. Full refund of PHP {{total_paid_php}} to {{worker_name}} via
     {{preferred_refund_channel}};
  2. Written confirmation that the worker has no continuing financial
     obligation to your agency or any common-control affiliate;
  3. Written undertaking not to retaliate against the worker, the
     worker's family, the worker's destination employer, or any
     advocate involved in this matter;
  4. Copies of all collection receipts and the agency's audit
     records for the worker's deployment cycle.

FAILURE TO COMPLY by {{compliance_deadline}} will result in:
  (a) Formal complaint to the DMW Anti-Illegal Recruitment Branch
      under RA 8042 / RA 10022 for illegal recruitment;
  (b) Concurrent complaint to the Hong Kong Labour Department EAA
      under Cap. 57A for EA misconduct;
  (c) Civil money-claim case before the National Labor Relations
      Commission (NLRC) for refund plus interest plus damages;
  (d) Notification to Philippine Migrant Workers Office Hong Kong
      and Bureau of Immigration for record;
  (e) Publication in the public DMW recruitment-agency monitoring
      registry as a non-compliant agency.

The worker is represented by {{complainant_name}}, {{complainant_org}}.
All correspondence concerning this matter should be directed to
{{complainant_contact}}. The worker reserves all rights and remedies
under Philippine, Hong Kong, and international law.

Sincerely,

{{complainant_name}}
{{complainant_org}}
{{complainant_contact}}

Date: {{filed_date}}

cc: as above
"""


_TEMPLATE_PASSPORT_RETURN_DEMAND_BODY = """PASSPORT + IDENTITY DOCUMENT RETURN DEMAND LETTER
Migrant Worker -- Foreign Employer / Sponsor / Recruitment Agency
Filing date: {{filed_date}}

TO:    {{respondent_name}} (employer / sponsor / agency)
       {{respondent_address}}
       Attn: {{respondent_attention}}

CC:    {{destination_country_labour_authority}}
       {{worker_origin_country_embassy_or_polo}}
       International Labour Organization (ILO) Hotline for Forced Labour

RE:    DEMAND for the immediate return of passport, identity
       documents, and travel documents of {{worker_name}}
       (anonymized identifier), {{worker_nationality}} migrant
       worker employed at {{worksite_or_household}}.

Dear Sir / Madam,

We represent {{worker_name}}, a {{worker_nationality}} migrant
worker. We are formally writing to demand the immediate return of
the worker's passport, identity documents, and any other travel /
identity documentation that you, your household, your sponsoring
entity, your recruitment agency, or your common-control affiliate
is currently retaining.

DOCUMENTS UNLAWFULLY RETAINED
  - Passport number prefix:                {{passport_prefix}}
  - Issuing country:                       {{worker_nationality}}
  - Date of retention:                     {{retention_date}}
  - Current location of documents:         {{document_current_location}}
  - Conditions imposed for return:         {{conditions_imposed}}

CONTROLLING LAW (each independently sufficient to require
return)
  1. ILO Convention 189 Article 9 (Domestic Workers Convention):
     "Each Member shall take measures to ensure that domestic
     workers are entitled to keep in their possession their travel
     and identity documents." Restrictions and document retention
     by employers are PROHIBITED regardless of any employment
     contract clause to the contrary.
  2. ILO Forced Labour Indicator 7 (Retention of Identity
     Documents): the retention of identity documents by an employer
     is one of the eleven ILO operational indicators of forced
     labour (ILO Special Action Programme to Combat Forced Labour,
     2012).
  3. UN Protocol to Prevent, Suppress and Punish Trafficking in
     Persons (Palermo Protocol) Article 3: the retention of
     identity documents is a recognised MEANS of trafficking in
     persons.
  4. Destination-country statutory prohibition:
     {{destination_statute_citation}}.
  5. Vienna Convention on Consular Relations Article 5(d): the
     worker's national consulate retains the right to issue
     replacement travel documents notwithstanding the unlawful
     retention.

DEMAND FOR REMEDY (within 5 calendar days from receipt of this
letter):
  1. Return ALL retained documents to the worker directly, or
     into the worker's authorised representative's hands;
  2. Confirm in writing that no further retention will occur;
  3. Confirm that no retaliation will be taken against the worker
     or the worker's family for asserting this right;
  4. Pay any out-of-pocket costs the worker has incurred in
     obtaining replacement documents (if any).

FAILURE TO COMPLY by {{compliance_deadline}} will result in:
  (a) Formal complaint to {{destination_country_labour_authority}}
      under {{destination_statute_citation}};
  (b) Issuance by the worker's national consulate of a replacement
      travel document; the worker will use that document
      regardless of your continued retention of the originals;
  (c) Concurrent notification to the worker's origin-country
      labour authority for parallel investigation and sanctions
      against any common-control agency;
  (d) Inclusion of the document-retention conduct as a Palermo
      Protocol means in any trafficking investigation;
  (e) Civil claim for damages including reasonable legal expense.

The worker is currently {{worker_current_safety_status}}. Any
attempt at retaliation against the worker for asserting this
right will be documented and added to the record.

Sincerely,

{{complainant_name}}
{{complainant_org}}
{{complainant_contact}}

Date: {{filed_date}}

cc: as above
"""


_TEMPLATE_T_VISA_AFFIDAVIT_BODY = """SUPPORTING AFFIDAVIT FOR FORM I-914
T NONIMMIGRANT VISA APPLICATION -- VICTIM OF SEVERE FORM OF TRAFFICKING IN PERSONS
United States Citizenship and Immigration Services (USCIS) Vermont Service Center

DECLARANT: {{worker_name}} (Affiant)
File no:   I-914 -- (assigned on filing)
Date:      {{filed_date}}

I, {{worker_name}}, declare under penalty of perjury under the
laws of the United States of America that the following is true
and correct to the best of my knowledge and recollection:

1. IDENTITY AND BACKGROUND
   I am a national of {{country_of_origin}}, born in
   {{year_of_birth}}. My native language is {{native_language}}.
   I came to the United States on {{us_entry_date}} on a
   {{visa_status_at_entry}} visa. Before coming to the United
   States, I was a {{prior_occupation}} in {{country_of_origin}}.

2. RECRUITMENT AND DECEPTION
   In {{recruitment_year}}, {{trafficker_name_or_anonymized}}
   ("the trafficker"), {{trafficker_relationship_to_me}}, recruited
   me through {{recruitment_channel}}. I was promised
   {{promised_terms}}. The trafficker said I would
   {{promised_living_situation}}. Based on those promises I
   agreed to come to the United States.

3. JOURNEY TO THE UNITED STATES
   The trafficker arranged my travel. {{travel_arrangements_summary}}.
   When I arrived in the United States on {{us_entry_date}}, the
   trafficker took possession of my passport and identity documents.
   I was told that I was now obligated to repay {{debt_amount}}
   for travel and documentation costs.

4. NATURE OF THE EXPLOITATION ON ARRIVAL
   On arrival the trafficker brought me to {{first_us_location}},
   where I was housed at {{housing_address_general}}. The actual
   work was {{actual_work_type}}, which is different from what was
   promised in section 2. I was required to work {{hours_per_day}}
   hours per day, {{days_per_week}} days per week. I was paid
   {{actual_compensation}}, much less than promised. I was not
   free to leave because {{reasons_unable_to_leave}}.

5. INDICATORS OF FORCED LABOR / SEVERE FORM OF TRAFFICKING
   I was subject to the following conditions, each of which
   constitutes an indicator of a severe form of trafficking
   under 22 USC 7102(11) and the ILO operational indicators:
     - Restriction of movement: {{movement_restriction_details}}
     - Isolation: {{isolation_details}}
     - Retention of identity documents: {{document_retention_details}}
     - Withholding of wages: {{wage_withholding_details}}
     - Debt bondage: {{debt_bondage_details}}
     - Threats or intimidation: {{threats_details}}
     - Physical or sexual abuse (only if applicable):
       {{abuse_details}}

6. ESCAPE OR RESCUE
   I was able to leave the trafficking situation on
   {{escape_date}} when {{escape_circumstances}}. Since that
   date I have been receiving services from {{service_provider_org}}.

7. PHYSICAL PRESENCE ON ACCOUNT OF TRAFFICKING
   I remain physically present in the United States on account
   of the trafficking situation I have just described. I have
   not departed the United States since arrival. I have
   cooperated with reasonable law-enforcement requests in the
   following manner: {{law_enforcement_cooperation_summary}}.

8. EXTREME HARDSHIP UPON REMOVAL
   Removal of the affiant to {{country_of_origin}} would result
   in extreme hardship involving unusual and severe harm
   because {{extreme_hardship_reasons}}.

9. SUPPORTING EVIDENCE
   I have attached the following supporting evidence:
     - {{supporting_evidence_list}}

10. FAMILY MEMBERS REQUESTING DERIVATIVE STATUS
    {{derivative_family_members_list_or_none}}

11. STATUTORY FRAMEWORK
    This declaration is submitted in support of Form I-914
    pursuant to:
      - Trafficking Victims Protection Act of 2000 + reauthorisations
      - 22 USC 7101 - 7113 + 22 USC 7102(11) (definitions)
      - 8 CFR 214.11 (T Nonimmigrant Status regulations)
      - 18 USC 1581 - 1592 (criminal trafficking provisions)
      - UN Palermo Protocol (Article 3 definition of trafficking
        in persons; Article 3(b) consent irrelevance)

I declare under penalty of perjury under the laws of the
United States of America that the foregoing is true and
correct.

Executed at {{place_of_execution}}, this {{filed_date}}.

_____________________________________
{{worker_name}}, Declarant
Submitted by:
{{complainant_name}}
{{complainant_org}}
{{complainant_contact}}
"""


_TEMPLATE_ANTI_RETALIATION_TRO_BODY = """REQUEST FOR INTERIM ANTI-RETALIATION ORDER
Migrant Worker -- Destination-Country Labour Tribunal
Filing date: {{filed_date}}

CASE / FILE NUMBER: {{case_file_number}}
TRIBUNAL:           {{tribunal_name}}
JURISDICTION:       {{jurisdiction_name}}

PETITIONER:   {{worker_name}} (anonymized identifier), through
              {{complainant_name}}, {{complainant_org}}.

RESPONDENT:   {{respondent_name}} (employer / sponsor / agency).

I.   NATURE OF THE REQUEST
The petitioner respectfully requests an INTERIM ORDER
restraining the respondent and any agent, affiliate, or person
acting in concert with the respondent from retaliating against
the petitioner in any manner during the pendency of the
underlying complaint, including but not limited to:
   (a) termination of employment without statutory cause;
   (b) cancellation, revocation, or non-renewal of the
       petitioner's visa, work permit, or sponsorship;
   (c) eviction or denial of employer-provided housing;
   (d) initiation or threat of immigration enforcement;
   (e) refusal to return the petitioner's identity documents;
   (f) threats or contact with the petitioner's family in
       the country of origin;
   (g) defamation or blacklisting through industry channels.

II.  GROUNDS FOR THE REQUEST
The petitioner has filed a substantive complaint against the
respondent concerning {{underlying_complaint_summary}}. The
respondent has demonstrated a likelihood of retaliation through
{{evidence_of_retaliation_likelihood}}. Without an interim
order, the petitioner will suffer irreparable harm including
{{specific_irreparable_harm}}.

III. CONTROLLING LAW
   - ILO Convention 190 Article 6 (violence and harassment
     including retaliation)
   - ILO Convention 181 Article 8 (adequate protection for
     migrant workers)
   - Palermo Protocol Article 3 (retaliation and threats as a
     means of trafficking)
   - {{jurisdiction_specific_anti_retaliation_statute}}

IV.  PETITIONER'S COMPLIANCE WITH PROCEDURAL REQUIREMENTS
   - Petitioner has notice-given to the respondent on
     {{notice_date}}.
   - Petitioner has provided to the tribunal a copy of the
     underlying complaint as Exhibit A.
   - Petitioner has provided sworn declaration of the facts as
     Exhibit B.
   - Petitioner has provided evidence of likelihood of
     retaliation as Exhibit C.

V.   RELIEF REQUESTED
The petitioner respectfully requests:
   1. Immediate interim order prohibiting the conduct listed in
      Section I, effective on issuance and remaining in force
      until the underlying complaint is finally resolved;
   2. Direction to the respondent to deliver the petitioner's
      identity documents to the tribunal registrar pending
      resolution;
   3. Direction to the destination-country immigration
      authority that the petitioner's status will not be
      adversely affected by the respondent's actions during
      the pendency of the complaint;
   4. Reservation of all further remedies including damages
      for any retaliation that has already occurred.

VI.  SUMMARY EVIDENCE
{{incident_summary}}

Respectfully submitted,

{{complainant_name}}
{{complainant_org}}
{{complainant_contact}}

Date: {{filed_date}}
"""


_TEMPLATE_WITNESS_STATEMENT_BODY = """WITNESS STATEMENT TO LAW ENFORCEMENT
Trafficking Investigation -- Voluntary Witness
Filing date: {{filed_date}}

WITNESS: {{witness_name}} (anonymized identifier where appropriate)
Relationship to victim: {{relationship_to_victim}}
Witness contact: {{witness_contact}}

INVESTIGATING AUTHORITY: {{investigating_authority}}
Case / file number: {{case_file_number}}
Designated officer: {{designated_officer}}

I, {{witness_name}}, hereby state voluntarily and without coercion
the following matters within my personal knowledge. I understand
that this statement may be used in criminal, immigration, or
labour proceedings against persons responsible for the trafficking
described below.

1. CONTEXT OF OBSERVATION
   I have known the victim, {{victim_name_or_anonymized}}, since
   {{when_known}}. Our relationship is {{relationship_to_victim}}.
   I observed the conduct described below at {{observation_location}}
   during the period {{observation_period}}.

2. RECRUITMENT
   I observed the following concerning recruitment of the
   victim: {{recruitment_observations}}. The recruiter or agent
   responsible was {{recruiter_name_or_description}}.

3. DEPLOYMENT AND DESTINATION
   The victim was sent to {{destination_country}} on
   {{deployment_date_approx}}. The destination employer was
   {{destination_employer_name_or_description}}. The sector was
   {{sector}}.

4. INDICATORS OBSERVED
   I observed the following conditions that may constitute
   indicators of forced labour under ILO operational indicators
   and trafficking under the Palermo Protocol:
     - Restriction of movement: {{movement_observations}}
     - Isolation: {{isolation_observations}}
     - Retention of identity documents: {{document_observations}}
     - Withholding of wages: {{wage_observations}}
     - Debt bondage: {{debt_observations}}
     - Physical violence or threats: {{violence_observations}}
     - Other indicators: {{other_observations}}

5. SPECIFIC EVENTS WITNESSED
   {{specific_events_witnessed}}

6. EVIDENCE THE WITNESS CAN PROVIDE
   {{available_evidence_list}}

7. OTHER WITNESSES KNOWN TO THE DECLARANT
   {{other_witnesses_list}}

8. PROTECTION CONCERNS OF THE WITNESS
   {{witness_protection_concerns}}

9. STATUTORY FRAMEWORK
   This statement is provided in support of investigation under:
     - {{controlling_criminal_statute}}
     - UN Palermo Protocol Art. 3
     - ILO Indicators of Forced Labour (2012)
     - Destination-country labour-protection statute:
       {{destination_statute}}

I declare that the foregoing is true to the best of my
knowledge. I am willing to be contacted at the address above
for further information.

_____________________________________
{{witness_name}}
Witness signature                  Date: {{filed_date}}

Witnessed by (caseworker / officer):
{{complainant_name}}
{{complainant_org}}
{{complainant_contact}}
"""


_TEMPLATE_RESTITUTION_CALCULATION_BODY = """RESTITUTION CALCULATION WORKSHEET + DEMAND
Migrant Worker -- Combined Origin / Destination Restitution Claim
Filing date: {{filed_date}}

CASE / FILE NUMBER: {{case_file_number}}
CLAIMANT:           {{worker_name}} (anonymized identifier)
THROUGH:            {{complainant_name}}, {{complainant_org}}

RESPONDENT(S):      {{respondents_list}}

I.   SUMMARY OF CLAIM
Claimant seeks restitution in the principal sum of
{{principal_amount_local_currency}} ({{principal_amount_local_currency}}),
plus interest, costs, and statutory damages, on the bases
itemised below.

II.  ITEMISED RESTITUTION CALCULATION

A.   Unauthorised recruitment fees collected (worker-pay
     prohibited under controlling statute):
       Training fee:                       {{training_fee_local}}
       Medical fee:                        {{medical_fee_local}}
       Processing / documentation fee:     {{processing_fee_local}}
       Placement fee (any label):          {{placement_fee_local}}
       Other (specify):                    {{other_fee_local}}
     SUBTOTAL (A):                         {{fee_subtotal_local}}

B.   Unpaid wages + statutory minimum-wage shortfall:
       Period of underpayment:             {{underpayment_period}}
       Months unpaid (full or partial):    {{months_unpaid}}
       Statutory minimum wage applicable:  {{statutory_min_wage}}
       Actual wages received:              {{actual_wages_received}}
       Hours worked beyond statutory cap:  {{overtime_hours}}
       Overtime owed under destination law: {{overtime_owed}}
     SUBTOTAL (B):                         {{wages_subtotal_local}}

C.   Illegal deductions (housing / food / loan / kickback):
       Housing deductions exceeding cap:   {{housing_excess}}
       Loan / advance repayment deducted:  {{loan_deduction_amount}}
       Equipment / training cost charged:  {{equipment_charged}}
       Other illegal deductions:           {{other_deductions}}
     SUBTOTAL (C):                         {{deduction_subtotal_local}}

D.   Repatriation costs (employer-pays-principle):
       Air ticket cost charged to worker:  {{airfare_charged}}
       Other repatriation costs charged:   {{other_repat_costs}}
     SUBTOTAL (D):                         {{repat_subtotal_local}}

E.   Statutory damages and interest:
       Pre-judgment interest rate:         {{prejudgment_interest_rate}}
       Statutory damages provision:        {{statutory_damages_basis}}
       Liquidated damages (if applicable): {{liquidated_damages}}
     SUBTOTAL (E):                         {{damages_subtotal_local}}

PRINCIPAL CLAIM (A + B + C + D + E):       {{principal_total_local}}
Equivalent in USD (informational):         {{principal_total_usd}}

III. CONTROLLING LAW (each independently supporting items A-E)
   - ILO Convention 181 Art. 7 (no worker-side fees)
   - ILO Convention 95 Art. 8 + 9 (wage protection)
   - {{origin_country_fee_cap_statute}}
   - {{destination_country_wage_statute}}
   - {{destination_country_overtime_statute}}
   - {{employer_pays_principle_basis}}
   - {{prejudgment_interest_authority}}

IV.  EVIDENCE OF CLAIM
{{evidence_list}}

V.   RELIEF REQUESTED
The claimant requests:
   1. Order for payment of {{principal_total_local}} to claimant
      in {{preferred_payment_channel}} within {{payment_deadline}}
      days of order;
   2. Pre-judgment interest from {{interest_start_date}};
   3. Post-judgment interest until paid in full;
   4. Statutory damages where authorised by the applicable
      statute;
   5. Recovery of reasonable legal expense;
   6. Anti-retaliation interim order during pendency;
   7. Any other relief the tribunal deems just and equitable.

Respectfully submitted,

{{complainant_name}}
{{complainant_org}}
{{complainant_contact}}

Date: {{filed_date}}
"""


_TEMPLATE_COMPOUND_SCAM_AFFIDAVIT_BODY = """VICTIM IDENTIFICATION AFFIDAVIT
Sihanoukville / Bavet / Myawaddy / Bokeo Cyber-Fraud Compound -- Combined Trafficking + Forced Criminal Activity Victim

Filing date: {{filed_date}}
File reference: {{file_reference}}

DECLARANT: {{worker_name}} (anonymized identifier)
Country of citizenship: {{country_of_citizenship}}
Year of birth:          {{year_of_birth}}
Native language:        {{native_language}}

INVESTIGATING / ASSISTING AUTHORITIES:
   {{origin_country_embassy_or_polo}}
   INTERPOL Project Storm Coordination Group
   UNODC Southeast Asia Cyber-Fraud Trafficking Response
   IOM Regional Office Bangkok
   {{destination_country_law_enforcement}}

I, {{worker_name}}, declare under oath that the following is true
and correct to the best of my knowledge:

1. RECRUITMENT
   In {{recruitment_year}} I was contacted via {{recruitment_channel}}
   by {{recruiter_handle_or_anonymized}} offering a position as
   {{advertised_role}} in {{advertised_destination}} with promised
   monthly compensation of {{advertised_compensation}}. The
   recruiter said {{recruiter_specific_promises}}. Based on those
   promises I agreed to travel.

2. JOURNEY
   The recruiter arranged my travel. I left {{country_of_citizenship}}
   on {{departure_date}} on a {{visa_status_at_departure}} visa /
   travel document. The route I took was {{travel_route}}.

3. ARRIVAL AND CONTROL
   On arrival at {{arrival_location}} I was met by {{handler_description}}.
   My passport, phone, and personal belongings were taken from me
   immediately. I was transported to {{compound_location_description}},
   where I was confined to a guarded compound. The compound was
   {{compound_physical_description}}.

4. NATURE OF FORCED CRIMINAL ACTIVITY
   I was forced to {{forced_criminal_activity_type}}. Specifically I
   was required to {{daily_required_activity}}. I worked
   {{hours_per_day}} hours per day, {{days_per_week}} days per
   week. I was paid {{actual_compensation_at_compound}}. Daily
   quotas were enforced through {{enforcement_mechanism}}.

5. ABUSE AND COERCION
   I was subject to the following abuse and coercion:
     - Restriction of movement:    {{movement_restriction_details}}
     - Document retention:         {{document_retention_details}}
     - Violence or threats:        {{violence_details}}
     - Debt bondage:               {{debt_details}}
     - Isolation:                  {{isolation_details}}
     - Sexual abuse (if applicable): {{sexual_abuse_details}}
     - Forced participation in fraud against third-party victims:
       {{forced_fraud_details}}

6. ESCAPE OR RELEASE
   I was able to leave the compound on {{escape_date}} by means
   of {{escape_circumstances}}. Since then I have been receiving
   support from {{service_provider}}.

7. NON-CRIMINALISATION REQUEST
   Under Palermo Protocol Article 3 + ASEAN ACTIP Article 14(7) +
   destination-country law where applicable, the declarant is a
   victim of trafficking in persons. Where the declarant was
   coerced into participating in fraud against third parties,
   the declarant requests non-criminalisation under the
   destination-country trafficking-victim non-prosecution
   framework and {{destination_country_non_criminalisation_statute}}.

8. INDICATORS OF TRAFFICKING (Palermo Protocol Article 3)
   ACT:    Recruitment + transportation + harbouring + receipt
           (Sections 1-3 above).
   MEANS:  Deception (advertised role differed from actual);
           abuse of position of vulnerability; coercion;
           document retention; debt-bondage.
   PURPOSE: Forced labour + forced criminal activity. Consent
           is irrelevant under Article 3(b).

9. REQUEST FOR SERVICES
   The declarant requests:
     - Immediate consular protection + safe-passage to the
       origin country;
     - Medical + psychological assessment + ongoing care;
     - Non-criminalisation under destination-country
       framework;
     - Cross-border evidence-preservation cooperation with the
       INTERPOL Project Storm Group, UNODC SE Asia Cyber-Fraud
       Response, and {{origin_country_law_enforcement}};
     - Reintegration support upon return.

10. CORRELATIVE EVIDENCE
    {{available_evidence_list}}

I, {{worker_name}}, declare under penalty of perjury that the
foregoing is true and correct.

_____________________________________
{{worker_name}}
Declarant signature              Date: {{filed_date}}

Witnessed by (caseworker / consular officer):
{{complainant_name}}
{{complainant_org}}
{{complainant_contact}}
"""


_TEMPLATE_KR_EPS_BODY = """COMPLAINT TO KOREA EMPLOYMENT PERMIT SYSTEM (EPS)
Ministry of Employment and Labor (MOEL) -- E-9 Worker Investigation
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker / Embassy POLO)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

MIGRANT WORKER (subject)
  Anonymized identifier:   {{worker_name}}
  Country of origin:       {{country_of_origin}}
  ARC prefix:              {{arc_prefix}}
  E-9 visa start date:     {{visa_start_date}}
  Sector:                  {{sector}}

EMPLOYER + WORKPLACE
  Employer name:             {{employer_name}}
  Business registration no:  {{employer_brn}}
  Worksite address (city):   {{worksite_city}}
  EPS-issuing agency:        {{eps_issuing_agency}}

PARTICULARS OF THE VIOLATION
  Unpaid wages (KRW):                {{unpaid_wages_krw}}
  Months of withheld salary:         {{months_withheld}}
  Recruitment / training fee (KRW):  {{recruitment_fee_amount}}
  Employer-paid principle violated:  {{employer_pays_violation}}
  Workplace transfer denied:         {{workplace_transfer_denied_yes_no}}
  Severance pay (toejikgeum) denied: {{severance_denied_yes_no}}
  Document retention:                {{document_retention_yes_no}}
  Restriction of movement:           {{movement_restriction_yes_no}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - Act on the Employment etc. of Foreign Workers (EPS Act,
    2003) provisions on employer-pays-principle + workplace
    transfer for employer fault
  - Labor Standards Act provisions on wages + severance pay
    + working hours + rest
  - National Health Insurance Act + Industrial Accident
    Compensation Insurance Act coverage for E-9 workers
  - ILO C181 Art. 7 + Palermo Protocol Art. 3 (if
    trafficking indicators)

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests Korea MOEL Employment Centre and
Labour Inspectorate investigation, recovery of unpaid wages
+ severance pay, employer sanctions (suspension from EPS
employment authority), and where applicable workplace
transfer authorisation for employer fault under the EPS
Act. Coordination requested with worker's origin-country
embassy + Korea Migrants' Centre + ARWB.

Signature: ________________________    Date: __________
"""


_TEMPLATE_TW_MOL_BODY = """COMPLAINT TO TAIWAN MINISTRY OF LABOR (MOL)
Employment Services Act + Workforce Development Agency Investigation
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker / Embassy office)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

MIGRANT WORKER (subject)
  Anonymized identifier:    {{worker_name}}
  Country of origin:        {{country_of_origin}}
  ARC number prefix:        {{arc_prefix}}
  Sector:                   {{sector}}
  Caregiver / factory / fishing / construction: {{worker_category}}

EMPLOYER + BROKER
  Employer / household:       {{employer_name}}
  Employer business reg:      {{employer_id}}
  Brokerage agency name:      {{tw_broker_name}}
  Brokerage licence number:   {{tw_broker_license}}
  Origin-country counterpart: {{origin_country_agency}}

PARTICULARS OF THE VIOLATION
  Unpaid wages (TWD):                {{unpaid_wages_twd}}
  Months of withheld salary:         {{months_withheld}}
  Brokerage fee exceeded cap:        {{brokerage_fee_excess}}
  Service-fee deduction exceeded:    {{service_fee_excess}}
  Document retention:                {{document_retention_yes_no}}
  Restriction of movement:           {{movement_restriction_yes_no}}
  Live-in caregiver no-rest-day:     {{caregiver_no_rest_day_yes_no}}
  Working hours per day / week:      {{hours_per_day_week}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - Employment Services Act (ESA, 1992 as amended) including
    service-fee + brokerage-fee caps + transfer rules
  - Labor Standards Act provisions on wages + hours + rest +
    occupational safety
  - Domestic / Caregiver regulations under MOL + Council of
    Labor Affairs
  - 1955 Hire-Purchase Agreement and Recruitment of Foreign
    Workers Regulations
  - ILO C181 Art. 7 + ILO C189 (caregiver context) + Palermo
    Protocol Art. 3

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests MOL Workforce Development Agency
investigation, broker licence suspension / revocation where
applicable, refund of overcharges, recovery of unpaid
wages, and worker employer-transfer authorisation where
employer fault is established. Coordination requested with
Hope Workers' Center + worker's origin-country POLO / MWO /
KDEI / DOLAB / embassy.

Signature: ________________________    Date: __________
"""


_TEMPLATE_SG_MOM_BODY = """COMPLAINT TO SINGAPORE MINISTRY OF MANPOWER (MOM)
Employment of Foreign Manpower Act (EFMA) + Employment Act Investigation
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker / Embassy office)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

MIGRANT WORKER (subject)
  Anonymized identifier:    {{worker_name}}
  Country of origin:        {{country_of_origin}}
  Work permit number prefix: {{work_permit_prefix}}
  Sector:                   {{sector}}
  FDW / Construction / Marine / Process: {{worker_category}}

EMPLOYER + AGENCY
  Employer / household name:      {{employer_name}}
  Employer UEN:                   {{employer_uen}}
  EA agency name:                 {{ea_agency_name}}
  EA licence number:              {{ea_license_number}}
  Origin-country counterpart:     {{origin_country_agency}}

PARTICULARS OF THE VIOLATION
  Unpaid wages (SGD):              {{unpaid_wages_sgd}}
  Months of withheld salary:       {{months_withheld}}
  Agency fee exceeded cap:         {{agency_fee_excess}}
  Loan / advance deduction abuse:  {{loan_deduction_abuse}}
  Document retention:              {{document_retention_yes_no}}
  Restriction of movement:         {{movement_restriction_yes_no}}
  Hours per day (FDW context):     {{fdw_hours_per_day}}
  Weekly rest day (FDW):           {{fdw_rest_day_yes_no}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - Employment of Foreign Manpower Act (EFMA, Cap. 91A)
    including security-bond + medical insurance obligations
  - Employment Act (Cap. 91) wage + leave + hours provisions
  - Employment Agencies Act (Cap. 92) + Code of Practice
    for Employment Agencies
  - Settling-In Programme + FDW Code obligations
  - ILO C181 Art. 7 + ILO C189 (FDW context) + Palermo
    Protocol Art. 3

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests MOM mediation, formal investigation,
EA licence suspension where applicable, refund of overcharges,
recovery of unpaid wages, and where appropriate referral to
Tripartite Alliance for Dispute Management (TADM). For FDW
cases, coordination with HOME + AIDHA + worker's origin-
country POLO / MWO / KDEI / SLBFE / embassy.

Signature: ________________________    Date: __________
"""


_TEMPLATE_IL_PIBA_BODY = """COMPLAINT TO ISRAEL POPULATION + IMMIGRATION + BORDER AUTHORITY (PIBA)
Foreign Workers Law 1991 / Bilateral Agreement Investigation
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker / Embassy)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

MIGRANT WORKER (subject)
  Anonymized identifier:    {{worker_name}}
  Country of origin:        {{country_of_origin}}
  B/1 visa number prefix:   {{b1_visa_prefix}}
  Sector:                   {{sector}}
  Caregiver / agriculture / construction: {{worker_category}}

EMPLOYER + RECRUITMENT
  Employer name:              {{employer_name}}
  Employer ID number:         {{employer_id}}
  Recruitment agency (IL):    {{il_agency_name}}
  Recruitment agency licence: {{il_agency_license}}
  Origin-country counterpart: {{origin_country_agency}}

PARTICULARS OF THE VIOLATION
  Unpaid wages (NIS):                  {{unpaid_wages_nis}}
  Months of withheld salary:           {{months_withheld}}
  Recruitment fee exceeded cap:        {{recruitment_fee_excess}}
  Document retention:                  {{document_retention_yes_no}}
  Restriction of movement (geo+sector): {{movement_restriction_yes_no}}
  Caregiver no-rest-day:               {{caregiver_no_rest_day_yes_no}}
  Hours per day / week:                {{hours_per_day_week}}
  GBV / harassment indicators:         {{gbv_indicators_yes_no}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - Israel Foreign Workers Law 1991 + 2016 amendments on
    recruitment-fee regulation + complaint pathway
  - Bilateral Agreement framework (Israel-Nepal, Israel-Sri
    Lanka, Israel-Philippines, Israel-Moldova) recruitment
    fee caps
  - Hours of Work and Rest Law 1951
  - Israel Law for the Prevention of Sexual Harassment 1998
  - ILO C181 Art. 7 + ILO C189 + ILO C190 + Palermo
    Protocol Art. 3

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests PIBA investigation, recruitment-
agency licence sanctions where applicable, refund of
overcharges, recovery of unpaid wages, employer-change
authorisation where employer fault is established. The
complainant requests coordination with Kav LaOved (Workers
Hotline) + Hotline for Refugees and Migrants + worker's
origin-country POLO / MWO / DoFE / embassy. For caregiver
cases involving GBV, immediate safety planning + shelter
referral via Israeli NGO partners.

Signature: ________________________    Date: __________
"""


_TEMPLATE_CA_SAWP_BODY = """COMPLAINT TO CANADA SAWP LIAISON SERVICE + IRCC + ESDC
Seasonal Agricultural Worker Programme (SAWP) Investigation
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker / Liaison Officer)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

SAWP WORKER (subject)
  Anonymized identifier:    {{worker_name}}
  Country of origin:        {{country_of_origin}}
  SAWP cohort year:         {{sawp_year}}
  Work permit number:       {{work_permit_no}}
  Sector:                   {{sector}}

EMPLOYER + LIAISON OFFICER
  Farm employer name:        {{employer_name}}
  Province + region:         {{province_region}}
  Employer LMIA number:      {{lmia_no}}
  Liaison officer name:      {{liaison_officer_name}}
  Origin-country counterpart: {{origin_country_agency}}

PARTICULARS OF THE VIOLATION
  Unpaid wages (CAD):                  {{unpaid_wages_cad}}
  Hours per day / week:                {{hours_per_day_week}}
  Housing standards concern:           {{housing_concern}}
  Health and safety concern:           {{health_safety_concern}}
  Anti-retaliation concern:            {{anti_retaliation_concern}}
  Document retention:                  {{document_retention_yes_no}}
  Excess deductions:                   {{excess_deductions}}
  Threat of non-recall / blacklist:    {{threat_no_recall_yes_no}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - CA SAWP MOU (Mexico-Canada, Caribbean-Canada -- Jamaica,
    Trinidad and Tobago, Barbados, OECS)
  - Immigration and Refugee Protection Act (IRPA) +
    Regulations
  - Canada Labour Code Part III (federal jurisdiction)
  - Provincial Employment Standards Acts + Occupational
    Health and Safety Acts
  - ILO C97 + C143 + C181 + C188 (where applicable) +
    Palermo Protocol Art. 3 + 4

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests Liaison Service intervention,
ESDC Integrity Services + IRCC inspection, employer
remediation, recovery of unpaid wages, anti-retaliation
interim order, and worker employer-transfer authorisation
under the SAWP MOU where employer fault is established.
Coordination requested with Justicia for Migrant Workers
Canada + Canadian Council for Refugees + worker's origin-
country counterpart Liaison Service (Mexico Embassy Mexican
Consulate or Caribbean Community / CARICOM Secretariat).

Signature: ________________________    Date: __________
"""


_TEMPLATE_SA_MHRSD_BODY = """COMPLAINT TO SAUDI MINISTRY OF HUMAN RESOURCES + SOCIAL DEVELOPMENT (MHRSD)
Friendly Settlement -- Labour / Domestic Worker Bylaw
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker / Embassy POLO)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

MIGRANT WORKER (subject)
  Anonymized identifier:    {{worker_name}}
  Country of origin:        {{country_of_origin}}
  Iqama / residence number: {{worker_iqama_prefix}}
  Sector:                   {{sector}}

EMPLOYER / SPONSOR + RECRUITMENT AGENCY
  Employer / sponsor name:        {{employer_name}}
  Sponsor commercial register no: {{sponsor_register_no}}
  Saudi recruitment agency:       {{sa_agency_name}}
  Musaned contract number:        {{musaned_contract_no}}

PARTICULARS OF THE VIOLATION
  Unpaid wages (SAR):             {{unpaid_wages_sar}}
  Months of withheld salary:      {{months_withheld}}
  Recruitment fee paid (USD/SAR): {{recruitment_fee_amount}}
  Passport / document retention:  {{document_retention_yes_no}}
  Restriction of movement:        {{movement_restriction_yes_no}}
  Working hours per day:          {{hours_per_day}}
  Weekly rest day (Y / N):        {{weekly_rest_day_yes_no}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - Saudi Labor Law (Royal Decree M/51) provisions on
    wage protection (Sec. 90) and termination procedures
  - Domestic Workers Bylaw (Ministerial Decision 310 of
    1434 H / 2013) on hours, rest, leave, employer
    obligations
  - Wage Protection System (WPS) coverage obligation
  - ILO C181 Art. 7 + ILO C189 (where applicable) +
    Palermo Protocol Art. 3 (if trafficking indicators)

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests Friendly Settlement at the Labour
Office, with binding determination by the Labour Court if not
resolved. Coordination requested with POLO / Migrant Worker
Office of the worker's origin country. Where Saudi Mobility
Initiative (2021) Tasreeh / Tasreeh Atharia conditions are
met (unpaid wages 90+ days, physical abuse, no valid work
permit), the worker requests employer-change permission.

Signature: ________________________    Date: __________
"""


_TEMPLATE_UAE_MOHRE_BODY = """COMPLAINT TO UAE MINISTRY OF HUMAN RESOURCES + EMIRATISATION (MoHRE)
Tawasul / Tadbeer Service Request
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker / Embassy POLO)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

MIGRANT WORKER (subject)
  Anonymized identifier:   {{worker_name}}
  Country of origin:       {{country_of_origin}}
  Emirates ID prefix:      {{emirates_id_prefix}}
  Sector:                  {{sector}}

EMPLOYER / SPONSOR
  Employer name:              {{employer_name}}
  Trade licence number:       {{employer_trade_licence}}
  Tadbeer / Esna'ad centre:   {{tadbeer_centre_name}}
  MoHRE work permit number:   {{mohre_permit_no}}

PARTICULARS OF THE VIOLATION
  Unpaid wages (AED):                  {{unpaid_wages_aed}}
  Months of withheld salary:           {{months_withheld}}
  Recruitment fee paid (USD / AED):    {{recruitment_fee_amount}}
  Passport / document retention:       {{document_retention_yes_no}}
  Restriction of movement:             {{movement_restriction_yes_no}}
  Hours per day / rest day:            {{hours_per_day_rest}}
  Living conditions concern:           {{living_conditions_concern}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - UAE Federal Decree-Law 33/2021 on Regulating Labour
    Relations (non-domestic worker)
  - UAE Federal Decree-Law 9/2022 on Domestic Workers
    (where applicable)
  - Wage Protection System obligations (MOMRA)
  - Tadbeer / Esna'ad service obligations under MoHRE
    domestic-worker regulation
  - Post-2022 employer-change-without-NOC framework
    where conditions are met

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests amicable settlement via Tawasul (up
to 14 days non-domestic / 7 days domestic). If unresolved,
referral to Labour Court (non-domestic) or Family Court
(domestic). The complainant requests coordination with the
worker's origin-country POLO / Migrant Worker Office /
embassy.

Signature: ________________________    Date: __________
"""


_TEMPLATE_QATAR_MOL_BODY = """COMPLAINT TO QATAR MINISTRY OF LABOUR (MoL)
Labour Dispute Resolution Committee + Workers' Support and Insurance Fund
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker / Embassy POLO)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

MIGRANT WORKER (subject)
  Anonymized identifier:    {{worker_name}}
  Country of origin:        {{country_of_origin}}
  QID prefix:               {{qid_prefix}}
  Sector:                   {{sector}}

EMPLOYER + WORK CONTRACT
  Employer / kafeel name:    {{employer_name}}
  Employer CR number:        {{employer_cr_no}}
  Work permit number:        {{work_permit_no}}
  Contract start date:       {{contract_start_date}}

PARTICULARS OF THE VIOLATION
  Unpaid wages (QAR):           {{unpaid_wages_qar}}
  Months of withheld salary:    {{months_withheld}}
  WPS-paid (Y / N):             {{wps_paid_yes_no}}
  Minimum-wage shortfall:       {{min_wage_shortfall}}
  Housing / food allowance:     {{housing_food_status}}
  Passport / document retention: {{document_retention_yes_no}}
  Post-2020 NOC conditions met: {{noc_abolished_conditions}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - Qatar Law 14/2004 (Labour Law)
  - Qatar Law 15/2017 on Domestic Workers (where applicable)
  - Wage Protection System obligations
  - Non-discriminatory minimum wage QAR 1,000 + housing +
    food allowance (Council of Ministers Decision 25/2020)
  - Post-2020 NOC abolition (Council of Ministers Decision
    51/2020); worker may change employer freely after
    labour-contract end
  - ILO C181 Art. 7; ILO C190; Palermo Protocol Art. 3 (if
    trafficking indicators)

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests preliminary conciliation at the
MoL Dispute Settlement Department (7-day target). If
unresolved, the complainant requests referral to the Labour
Dispute Resolution Committee (3-week binding decision). The
complainant requests interim payment from the Workers'
Support and Insurance Fund pending resolution. Coordination
requested with POLO / Migrant Worker Office of the worker's
origin country.

Signature: ________________________    Date: __________
"""


_TEMPLATE_AU_FWO_BODY = """COMPLAINT TO AUSTRALIAN FAIR WORK OMBUDSMAN (FWO)
Migrant Worker Investigation -- Fair Work Act 2009
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker / union official)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

MIGRANT WORKER (subject)
  Anonymized identifier:   {{worker_name}}
  Country of origin:       {{country_of_origin}}
  Visa subclass + status:  {{visa_subclass_status}}
  Australian visa label:   {{visa_label_prefix}}

EMPLOYER / SPONSOR
  Employer name:                {{employer_name}}
  Sponsor ABN:                  {{sponsor_abn}}
  Worksite address (state):     {{worksite_state}}
  TSS 482 / PALM nomination:    {{nomination_no}}

PARTICULARS OF THE VIOLATION
  Unpaid wages (AUD):                  {{unpaid_wages_aud}}
  Underpayment vs. award rate:         {{award_underpayment}}
  Sham contracting indicators:         {{sham_contracting_yes_no}}
  Excess deductions (housing / loan):  {{excess_deductions}}
  Hours per week worked:               {{hours_per_week}}
  Passport / document retention:       {{document_retention_yes_no}}
  Threat of visa cancellation:         {{threat_visa_cancel_yes_no}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - Fair Work Act 2009 (minimum wage + award compliance +
    record-keeping + non-discrimination + anti-bullying)
  - Migration Act 1958 (sponsorship obligations; sham
    contracting)
  - Modern Slavery Act 2018 (reporting + supply-chain due
    diligence where applicable to corporate respondent)
  - AU PALM Code of Conduct (where worker is PALM-scheme)
  - ILO C181 Art. 7; ILO C189; Palermo Protocol Art. 3

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests FWO assistance pathway including
mediation, formal investigation, compliance notices,
infringement notices, and where appropriate Federal Court /
Federal Circuit Court litigation under the Fair Work Act.
Coordination requested with Migrant Workers Centre VIC / NSW
+ Anti-Slavery Australia (UTS Faculty of Law) + AFP if
trafficking offences are identified.

Signature: ________________________    Date: __________
"""


_TEMPLATE_UK_NRM_REFERRAL_BODY = """UK NATIONAL REFERRAL MECHANISM (NRM) REFERRAL FORM
First Responder Organisation -- Single Competent Authority Submission
Filing date: {{filed_date}}

FIRST RESPONDER ORGANISATION
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  FRO status:     {{fro_status}}
  Contact:        {{complainant_contact}}

POTENTIAL VICTIM (subject)
  Anonymized identifier:  {{worker_name}}
  Nationality:            {{nationality}}
  Date of birth (year):   {{year_of_birth}}
  Age category:           {{age_category}}
  Gender:                 {{gender}}
  Languages:              {{languages_spoken}}

EXPLOITATION TYPE
  Sexual exploitation (Y/N):            {{sex_exploit_yes_no}}
  Labour exploitation (Y/N):            {{labour_exploit_yes_no}}
  Domestic servitude (Y/N):             {{dom_servitude_yes_no}}
  Criminal exploitation (Y/N):          {{criminal_exploit_yes_no}}
  Organ removal (Y/N):                  {{organ_removal_yes_no}}

TRAFFICKER / EXPLOITER PROFILE
  Trafficker network description:       {{trafficker_description}}
  Country of recruitment:               {{country_of_recruitment}}
  Journey route:                        {{journey_route}}
  Current location:                     {{current_uk_location}}

INDICATORS PRESENT
  Recruitment indicators:               {{recruitment_indicators}}
  Travel indicators:                    {{travel_indicators}}
  Exploitation indicators:              {{exploitation_indicators}}
  Restriction-of-movement indicators:   {{movement_indicators}}
  Document retention:                   {{document_retention_yes_no}}
  Debt-bondage indicators:              {{debt_bondage_yes_no}}

CONSENT + CURRENT SUPPORT
  Potential victim consent given:       {{victim_consent_yes_no}}
  Recovery and Reflection needed:       {{rr_period_needed_yes_no}}
  Safehouse needed:                     {{safehouse_needed_yes_no}}
  Children involved:                    {{children_involved_yes_no}}

CASE NARRATIVE
{{incident_summary}}

STATUTORY FRAMEWORK CITED
  - Modern Slavery Act 2015 (UK)
  - Council of Europe Convention on Action against
    Trafficking in Human Beings (CETS 197)
  - EU Anti-Trafficking Directive 2011/36/EU (residual
    applicability where relevant)
  - Palermo Protocol Art. 3
  - Children Act 1989 / 2004 (if applicable to a child)
  - National Crime Agency MSHTU guidance

RELIEF + REFERRAL REQUESTED
{{relief_requested}}

The First Responder Organisation requests Reasonable Grounds
decision from the Single Competent Authority (SCA) within 5
working days. If positive, the potential victim accesses 30+
days Recovery and Reflection plus NRM-funded support
(safehouse, casework, financial support, healthcare access).
Conclusive Grounds decision to follow on balance of
probabilities.

Signature: ________________________    Date: __________
"""


_TEMPLATE_POLARIS_HOTLINE_REFERRAL_BODY = """POLARIS NATIONAL HUMAN TRAFFICKING HOTLINE -- CASEWORKER REFERRAL SUMMARY
1-888-373-7888  |  Text BeFree to 233733  |  Web chat
Filing date: {{filed_date}}

CASEWORKER (referring NGO / clinician)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

POTENTIAL VICTIM (subject)
  Anonymized identifier:  {{worker_name}}
  Languages:              {{languages_spoken}}
  Country of origin:      {{country_of_origin}}
  Age category:           {{age_category}}
  Current US location:    {{current_us_location}}

CASE OVERVIEW
  Trafficking type (sex / labour / mixed):   {{trafficking_type}}
  Industry / sector:                         {{sector}}
  Recruitment country:                       {{country_of_recruitment}}
  Trafficker relationship to victim:         {{trafficker_relationship}}
  US duration:                               {{us_duration}}
  Immigration status (if known):             {{immigration_status}}

INDICATORS REPORTED (ILO / Palermo / Polaris Typology)
  Force / coercion indicators:               {{coercion_indicators}}
  Document retention:                        {{document_retention_yes_no}}
  Debt-bondage indicators:                   {{debt_bondage_yes_no}}
  Restriction of movement:                   {{movement_indicators}}
  Threats (deportation / family / harm):     {{threats_reported}}
  Wages owed (USD):                          {{wages_owed_usd}}

CASE NARRATIVE
{{incident_summary}}

VICTIM GOALS (caller-led)
  Stated goal of contact:                    {{victim_stated_goal}}
  Wants law-enforcement involvement (Y/N):   {{wants_le_involvement_yes_no}}
  Wants T-Visa / U-Visa exploration:         {{wants_t_or_u_visa_yes_no}}
  Wants medical / mental-health support:     {{wants_medical_support_yes_no}}
  Wants shelter:                             {{wants_shelter_yes_no}}
  Wants legal-aid for civil restitution:     {{wants_legal_aid_yes_no}}

CASEWORKER ACTIONS TAKEN
{{caseworker_actions}}

LOCAL SERVICE PROVIDER RECOMMENDATIONS (Polaris directory)
{{recommended_service_providers}}

STATUTORY FRAMEWORK
  - US TVPRA 22 USC 7102 + 18 USC 1581-1592
  - California Labor Code Sec. 244 (immigration status
    irrelevant for wage claims; applies in state-level
    equivalent statutes elsewhere)
  - State-level victim-restitution + crime-victim statutes
  - HHS Office on Trafficking in Persons (OTIP) victim
    services framework

RELIEF + REFERRAL REQUESTED
{{relief_requested}}

The caseworker requests Polaris hotline intake support
including: warm-handoff to local service providers, T-Visa
+ U-Visa legal-aid referral via Polaris partner network,
crisis intervention if active danger, and entry of
de-identified outcome data into the Counter-Trafficking
Data Collaborative (CTDC) only with the victim's consent.

Signature: ________________________    Date: __________
"""


_TEMPLATE_CBP_E_ALLEGATIONS_BODY = """U.S. CUSTOMS AND BORDER PROTECTION (CBP) -- E-ALLEGATION SUBMISSION
Forced Labor Allegation under 19 U.S.C. 1307 / Withhold Release Order (WRO) Petition
Filing date: {{filed_date}}

SUBMITTER (NGO / researcher / journalist / labour expert)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

SUBJECT MERCHANDISE
  Product name + HTSUS code:    {{product_name_htsus}}
  Country of origin:            {{country_of_origin}}
  Importer name (if known):     {{importer_name}}
  Manufacturer name:            {{manufacturer_name}}
  Manufacturer address:         {{manufacturer_address}}
  Tier of supply chain:         {{supply_chain_tier}}

INDICATORS OF FORCED LABOUR
  ILO indicators observed (incl. evidence):  {{ilo_indicators}}
  Palermo Protocol indicators:               {{palermo_indicators}}
  Worker testimony references:               {{worker_testimony_refs}}
  Audit + investigative documentation:       {{audit_documentation}}
  UFLPA Entity List linkage (if any):        {{uflpa_entity_list_linkage}}

FACTUAL BASIS
{{factual_basis_summary}}

EVIDENCE PROVIDED
{{evidence_list}}

STATUTORY VIOLATIONS ALLEGED
  - 19 U.S.C. 1307 (prohibition on importation of merchandise
    produced by forced labour, indentured labour, convict
    labour, or child labour)
  - Tariff Act of 1930 Section 307
  - Uyghur Forced Labor Prevention Act (UFLPA, 2021) where
    Xinjiang / UFLPA Entity List linkage exists
  - Trafficking Victims Protection Reauthorization Act
    (TVPRA) 22 U.S.C. 7102

RELIEF REQUESTED
The submitter requests CBP Forced Labor Division to:
1. Open formal review of the named merchandise + manufacturer
2. Apply the 'reasonably indicates' standard to issue a
   Withhold Release Order (WRO) preventing importation
3. Coordinate with US ICE Homeland Security Investigations
   on related trafficking + smuggling prosecution under
   18 USC 1589 / 1590 / 1591 / 1592 where appropriate
4. Coordinate with the Department of State + USTR on
   sectoral + diplomatic engagement
5. Where UFLPA rebuttable presumption applies, require the
   importer to rebut with clear and convincing evidence

Signature: ________________________    Date: __________
"""


_TEMPLATE_US_DOL_WHD_BODY = """COMPLAINT TO THE U.S. DEPARTMENT OF LABOR
Wage and Hour Division -- H-2A / MSPA Investigation
Filing date: {{filed_date}}

COMPLAINANT (NGO caseworker)
  Name:           {{complainant_name}}
  Organisation:   {{complainant_org}}
  Contact:        {{complainant_contact}}

H-2A WORKER (subject)
  Anonymized identifier:  {{worker_name}}
  Country of recruitment: {{country_of_origin}}
  H-2A visa case number:  {{worker_visa_case}}

EMPLOYER / LABOR CONTRACTOR
  Employer name:            {{employer_name}}
  Farm labor contractor:    {{labor_contractor_name}}
  ETA H-2A case number:     {{eta_case_number}}
  Worksite location:        {{worksite_location}}

PARTICULARS OF THE VIOLATION
  Recruitment fees collected (USD):  {{recruitment_fee_amount_usd}}
  Visa fees collected from worker:   {{visa_fees_usd}}
  Border-crossing costs charged:     {{border_costs_usd}}
  Promised wage rate (AEWR):         {{promised_wage_rate}}
  Actual wage rate paid:             {{actual_wage_rate}}

INCIDENT SUMMARY
{{incident_summary}}

STATUTORY VIOLATIONS ALLEGED
  - 20 CFR 655.135(j): prohibition on collection of recruitment,
    visa, border-crossing, or related fees from H-2A workers
  - Trafficking Victims Protection Reauthorization Act (TVPRA),
    22 U.S.C. 7102 (forced labor; debt bondage)
  - Migrant and Seasonal Agricultural Worker Protection Act (MSPA)
    disclosure and prohibited-fee provisions where applicable

ILO FORCED-LABOUR INDICATORS
{{ilo_indicators}}

EVIDENCE AVAILABLE
{{evidence_list}}

RELIEF REQUESTED
{{relief_requested}}

The complainant requests the Wage and Hour Division to investigate,
order full restitution of all prohibited fees, assess civil money
penalties under 29 U.S.C. 1853, refer the matter to the Department
of Justice for trafficking review where warranted, and coordinate
with the Mexican consulate on victim support.

Signature: ________________________    Date: __________
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
    relevance_indicators: tuple[str, ...] = ()

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
            "relevance_indicators": list(template_relevance_indicators(self)),
            "sample_bundle_url": f"/api/templates/sample-bundle/{self.id}",
            "walkthrough": [
                "Load this template's synthetic example bundle.",
                "Extract complaint facts and ILO indicators from the bundle.",
                "Ask Gemma 4 which complaint or referral paths fit.",
                "Fill required fields with bundle hints, Gemma gaps, and manual edits.",
            ],
        }


_CANONICAL_TEMPLATE_INDICATORS: tuple[str, ...] = (
    "fee_camouflage",
    "fee_bondage",
    "salary_deduction",
    "debt_bondage",
    "passport_retention",
    "document_control",
    "retaliation_risk",
    "jurisdiction_shopping",
    "wage_theft",
    "deceptive_recruitment",
    "movement_restriction",
    "isolation",
    "abuse_of_vulnerability",
    "excessive_overtime",
    "withheld_wages",
    "case_signal",
)

_TEMPLATE_RELEVANCE_DEFAULTS: dict[str, tuple[str, ...]] = {
    "hk_ld_fdh_complaint": (
        "fee_camouflage", "fee_bondage", "salary_deduction",
        "wage_theft", "passport_retention", "retaliation_risk",
    ),
    "ph_dmw_complaint": (
        "fee_camouflage", "fee_bondage", "debt_bondage",
        "deceptive_recruitment", "passport_retention",
    ),
    "iom_referral": (
        "debt_bondage", "movement_restriction", "isolation",
        "abuse_of_vulnerability", "document_control",
    ),
    "ngo_intake": (
        "fee_camouflage", "fee_bondage", "salary_deduction",
        "debt_bondage", "passport_retention", "document_control",
        "retaliation_risk", "wage_theft", "deceptive_recruitment",
        "movement_restriction", "isolation", "abuse_of_vulnerability",
        "excessive_overtime", "withheld_wages", "case_signal",
    ),
}

_TEMPLATE_INDICATOR_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("fee", ("fee_camouflage", "fee_bondage")),
    ("placement", ("fee_camouflage", "fee_bondage")),
    ("deduction", ("salary_deduction", "withheld_wages")),
    ("salary", ("salary_deduction", "wage_theft")),
    ("wage", ("wage_theft", "withheld_wages")),
    ("debt", ("debt_bondage",)),
    ("passport", ("passport_retention", "document_control")),
    ("document", ("document_control",)),
    ("identity", ("document_control",)),
    ("retaliation", ("retaliation_risk",)),
    ("threat", ("retaliation_risk",)),
    ("contract substitution", ("deceptive_recruitment",)),
    ("deceptive", ("deceptive_recruitment",)),
    ("movement", ("movement_restriction",)),
    ("confinement", ("movement_restriction", "isolation")),
    ("isolation", ("isolation",)),
    ("vulnerability", ("abuse_of_vulnerability",)),
    ("overtime", ("excessive_overtime",)),
)


def _normalize_template_indicator(value: Any) -> str | None:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    raw = re.sub(r"[^a-z0-9_]+", "", raw)
    return raw if raw in _CANONICAL_TEMPLATE_INDICATORS else None


def template_relevance_indicators(template: TemplateSpec) -> tuple[str, ...]:
    """Return canonical indicator tags used by the batch-fill selector.

    Existing registry entries predate explicit relevance metadata. Keep
    the dataclass field for custom templates, provide high-signal
    defaults for the flagship templates, then infer conservative tags
    from labels/summary/body for the broader built-in catalog.
    """
    explicit = [
        norm for norm in (
            _normalize_template_indicator(v)
            for v in (template.relevance_indicators or ())
        )
        if norm
    ]
    if explicit:
        return tuple(dict.fromkeys(explicit))
    if template.id in _TEMPLATE_RELEVANCE_DEFAULTS:
        return _TEMPLATE_RELEVANCE_DEFAULTS[template.id]
    haystack = " ".join([
        template.id,
        template.title,
        template.jurisdiction,
        template.audience,
        template.summary,
        template.body[:2000],
        " ".join(f.label for f in template.fields),
    ]).lower()
    inferred: list[str] = []
    for needle, indicators in _TEMPLATE_INDICATOR_KEYWORDS:
        if needle in haystack:
            inferred.extend(indicators)
    return tuple(dict.fromkeys(inferred or ["case_signal"]))


def bundle_ilo_indicators(bundle: dict) -> tuple[str, ...]:
    """Canonical ILO indicator tuple from a process/template bundle."""
    intel = (bundle or {}).get("intelligence") or {}
    raw = intel.get("ilo_indicators") or []
    if isinstance(raw, str):
        raw = re.split(r"[,;\s]+", raw)
    out = [
        norm for norm in (_normalize_template_indicator(v) for v in raw)
        if norm
    ]
    return tuple(dict.fromkeys(out))


def select_relevant_templates_for_bundle(
    bundle: dict,
    *,
    templates: Optional[dict[str, TemplateSpec]] = None,
) -> list[TemplateSpec]:
    """Select templates whose relevance indicators overlap the bundle."""
    indicators = set(bundle_ilo_indicators(bundle))
    if not indicators:
        return []
    registry = templates or TEMPLATES_REGISTRY
    return [
        spec for spec in registry.values()
        if indicators.intersection(template_relevance_indicators(spec))
    ]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_TEMPLATE_FEE_REFUND_LOAN_VOID_BODY = 'RECRUITMENT FEE REFUND + DEBT-BONDAGE LOAN VOID DEMAND\nMigrant Worker -- Recruitment Agency / Employer / Linked Lender\nFiling date: {{filed_date}}\n\nTO:    {{respondent_name}} (recruitment agency / employer / lender)\n       {{respondent_address}}\nCC:    {{labour_authority}}\n       {{embassy_polo}}\n       International Labour Organization (ILO) Hotline for Forced Labour\n\nRE:    DEMAND to (1) REFUND the unlawful recruitment / placement fee,\n       (2) declare VOID the linked salary-advance loan as debt bondage,\n       and (3) CEASE all wage deductions -- {{worker_name}}\n       ({{worker_nationality}}), {{origin_country}} to {{destination_country}}.\n\n1. FACTS. The worker was charged {{fee_amount}}, labelled a\n   "{{fee_label}}", as a condition of placement, and bound to a linked\n   salary-advance loan of {{loan_amount}} repaid via monthly deductions\n   of {{deduction_amount}} from wages earned in {{destination_country}}.\n\n2. THE CHARGE IS UNLAWFUL REGARDLESS OF ITS LABEL. Under ILO C181 Art. 7\n   the employer -- not the worker -- bears recruitment costs. Relabelling\n   a placement fee as a "{{fee_label}}" does not change its substance\n   ({{corridor_statute}}). The worker-funded loan plus wage deduction is\n   the textbook ILO debt-bondage pattern (ILO C029 + P029; ILO Forced\n   Labour Indicator 4; ILO C095 Art. 8 on permissible wage deductions).\n\n3. CONSENT IS IRRELEVANT. A signature obtained as a condition of work\n   does not cure a coercive means (Palermo Protocol Art. 3(b)).\n\n4. DEMAND. Within {{response_days}} days: refund {{fee_amount}} in full;\n   declare the {{loan_amount}} loan void and cease all deductions; return\n   any documents held; and confirm in writing. Failing this, the matter\n   will be referred to {{labour_authority}} and {{embassy_polo}}.\n\nSigned, {{filer_name}} ({{filer_role}})\nOn behalf of {{worker_name}} (anonymized identifier).'

_TEMPLATE_CONTRACT_SUBSTITUTION_COMPLAINT_BODY = 'CONTRACT SUBSTITUTION COMPLAINT\nMigrant Worker -- Origin-Signed Contract vs Arrival Substitution\nFiling date: {{filed_date}}\n\nTO:    {{labour_tribunal}} (destination-country labour authority / tribunal)\nCC:    {{embassy_polo}}\n       {{recruitment_agency}} (origin recruitment agency)\n\nRE:    Complaint of unlawful CONTRACT SUBSTITUTION affecting\n       {{worker_name}} ({{worker_nationality}}), deployed\n       {{origin_country}} to {{destination_country}}.\n\n1. THE ORIGIN CONTRACT. On {{signing_date}} the worker signed, at origin,\n   an employment contract providing {{origin_signed_terms}} (monthly wage\n   {{origin_signed_wage}}).\n\n2. THE ARRIVAL SUBSTITUTION. On arrival in {{destination_country}} on\n   {{arrival_date}}, the employer {{respondent_name}} presented a\n   different contract providing only {{arrival_substituted_wage}} and\n   {{arrival_worse_terms}}, and {{document_control}}.\n\n3. LEGAL CHARACTER. Substituting the origin-signed contract for worse\n   terms on arrival is the ILO deception indicator (Indicator 2) and a\n   Palermo Protocol Art. 3 trafficking "means". The origin-signed contract\n   is the enforceable benchmark (IRIS Standard; Dhaka Principles for\n   Migration with Dignity, Principle 2). A signature obtained on arrival\n   under duress does not cure the substitution.\n\n4. RELIEF SOUGHT. Enforcement of the origin-signed terms; payment of the\n   wage differential; return of any retained documents; and inspection of\n   {{respondent_name}} under {{destination_statute}}.\n\nFiled by {{filer_name}} ({{filer_role}}) on behalf of {{worker_name}}.'


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

    # --------- Corridor complaint templates (added 2026-05-21) --------
    "np_dofe_complaint": TemplateSpec(
        id="np_dofe_complaint",
        title="Nepal DoFE Complaint (Foreign Employment Act)",
        jurisdiction="Nepal",
        audience="Department of Foreign Employment (DoFE) / Foreign Employment Tribunal",
        summary=(
            "Complaint against a Nepali manpower agency for collection of "
            "recruitment service charges exceeding the Foreign Employment "
            "Rules 2008 ceiling. Aligns with FEA 2007 sections 21-25 and "
            "ILO C181 Art. 7."
        ),
        body=_TEMPLATE_NP_DOFE_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("destination_country", "Destination country", True, "intelligence.corridor"),
            _f("worker_passport_prefix", "Worker passport prefix (e.g., 12345****)", False),
            _f("agency_name", "Licensed manpower agency name", True, "intelligence.agencies[0]"),
            _f("agency_license", "DoFE licence number", True),
            _f("agency_address", "Agency address", False),
            _f("deployment_date", "Deployment date", True, "intelligence.deployment_date"),
            _f("recruitment_fee_amount_npr", "Service charge collected (NPR)", True, "intelligence.payments_npr"),
            _f("recruitment_fee_cap_npr", "Statutory ceiling (NPR)", True),
            _f("document_fees_npr", "Document fees collected (NPR)", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO forced-labour indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "id_bp2mi_complaint": TemplateSpec(
        id="id_bp2mi_complaint",
        title="Indonesia BP2MI Complaint (UU 18/2017)",
        jurisdiction="Indonesia",
        audience="BP2MI (Badan Pelindungan Pekerja Migran Indonesia)",
        summary=(
            "Complaint against a P3MI-licensed Indonesian placement agency "
            "for unauthorised fee collection or salary-deduction repayment "
            "schemes. Aligns with UU 18/2017 and BP2MI Regulation 09/2020."
        ),
        body=_TEMPLATE_ID_BP2MI_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("destination_country", "Destination country", True, "intelligence.corridor"),
            _f("sector", "Sector (e.g., domestic work)", False, "intelligence.sector"),
            _f("worker_passport_prefix", "Worker passport prefix", False),
            _f("agency_name", "Licensed P3MI agency name", True, "intelligence.agencies[0]"),
            _f("agency_license", "BP2MI / P3MI licence number", True),
            _f("agency_address", "Agency address", False),
            _f("deployment_date", "Deployment date", True, "intelligence.deployment_date"),
            _f("recruitment_fee_amount_idr", "Unauthorised fee collected (IDR)", True),
            _f("salary_deduction_terms", "Salary-deduction terms (months / percent)", False),
            _f("months_withheld", "Months of salary withheld", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO forced-labour indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "bd_bmet_complaint": TemplateSpec(
        id="bd_bmet_complaint",
        title="Bangladesh BMET Complaint (Overseas Employment Act 2013)",
        jurisdiction="Bangladesh",
        audience="BMET (Bureau of Manpower, Employment and Training)",
        summary=(
            "Complaint against a BMET-licensed Recruiting Agent for "
            "collection of recruitment costs exceeding bilateral G2G+ "
            "ceilings. Aligns with the Overseas Employment and Migrants "
            "Act 2013 and ILO C181 Art. 7."
        ),
        body=_TEMPLATE_BD_BMET_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("destination_country", "Destination country", True, "intelligence.corridor"),
            _f("sector", "Sector", False, "intelligence.sector"),
            _f("worker_passport_prefix", "Worker passport prefix", False),
            _f("agency_name", "Licensed Recruiting Agent name", True, "intelligence.agencies[0]"),
            _f("agency_license", "BMET licence number", True),
            _f("agency_address", "Agency address", False),
            _f("deployment_date", "Deployment date", True, "intelligence.deployment_date"),
            _f("recruitment_fee_amount_bdt", "Recruitment cost collected (BDT)", True),
            _f("recruitment_fee_cap_bdt", "Bilateral ceiling (BDT)", True),
            _f("family_payment_amount", "Family / third-party payments", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO forced-labour indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "vn_dolab_complaint": TemplateSpec(
        id="vn_dolab_complaint",
        title="Vietnam DOLAB Complaint (Decree 38/2020/ND-CP)",
        jurisdiction="Vietnam",
        audience="DOLAB (Department of Overseas Labour)",
        summary=(
            "Complaint against a DOLAB-licensed Vietnamese sending agency "
            "for collection of service fees and brokerage exceeding the "
            "Decree 38/2020/ND-CP cap. Cross-applies the destination's "
            "Employment Service Act where Taiwan-side broker fees are at "
            "issue."
        ),
        body=_TEMPLATE_VN_DOLAB_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("destination_country", "Destination country", True, "intelligence.corridor"),
            _f("sector", "Sector (e.g., factory, caregiver)", False, "intelligence.sector"),
            _f("worker_passport_prefix", "Worker passport prefix", False),
            _f("agency_name", "Licensed sending agency name", True, "intelligence.agencies[0]"),
            _f("agency_license", "DOLAB licence number", True),
            _f("agency_address", "Agency address", False),
            _f("deployment_date", "Deployment date", True, "intelligence.deployment_date"),
            _f("recruitment_fee_amount_usd", "Service fee collected (USD)", True),
            _f("recruitment_fee_cap_usd", "Statutory cap (USD)", True),
            _f("monthly_brokerage_usd", "Monthly brokerage fee (USD)", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO forced-labour indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "us_dol_whd_complaint": TemplateSpec(
        id="us_dol_whd_complaint",
        title="U.S. DOL Wage and Hour Division Complaint (H-2A / MSPA)",
        jurisdiction="United States",
        audience="U.S. Department of Labor (Wage and Hour Division)",
        summary=(
            "Complaint against a U.S. employer and / or farm labor "
            "contractor for collection of prohibited recruitment, visa, "
            "or border-crossing fees from an H-2A worker. Aligns with "
            "20 CFR 655.135(j), the TVPRA, and MSPA."
        ),
        body=_TEMPLATE_US_DOL_WHD_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("country_of_origin", "Country of recruitment", True, "intelligence.country_of_origin"),
            _f("worker_visa_case", "H-2A visa case number (last 4)", False),
            _f("employer_name", "U.S. employer of record", True, "intelligence.employers[0]"),
            _f("labor_contractor_name", "Farm labor contractor (if any)", False),
            _f("eta_case_number", "ETA H-2A case number", False),
            _f("worksite_location", "Worksite state and county", True),
            _f("recruitment_fee_amount_usd", "Recruitment fees collected (USD)", True),
            _f("visa_fees_usd", "Visa fees collected from worker (USD)", False),
            _f("border_costs_usd", "Border-crossing costs charged (USD)", False),
            _f("promised_wage_rate", "Promised wage rate (AEWR)", False),
            _f("actual_wage_rate", "Actual wage rate paid", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO forced-labour indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "sa_mhrsd_complaint": TemplateSpec(
        id="sa_mhrsd_complaint",
        title="Saudi MHRSD Complaint (Labour Law M/51 + Domestic Workers Bylaw)",
        jurisdiction="Saudi Arabia",
        audience="Ministry of Human Resources and Social Development",
        summary=(
            "Complaint against a Saudi employer / sponsor for unpaid "
            "wages, document retention, restriction of movement, or "
            "Domestic Workers Bylaw violations. Aligns with Royal "
            "Decree M/51 + Ministerial Decision 310/1434 H + Wage "
            "Protection System + Saudi Mobility Initiative 2021."
        ),
        body=_TEMPLATE_SA_MHRSD_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("worker_iqama_prefix", "Iqama / residence number prefix", False),
            _f("sector", "Sector (domestic / construction / hospitality)", True, "intelligence.sector"),
            _f("employer_name", "Employer / sponsor name", True, "intelligence.employers[0]"),
            _f("sponsor_register_no", "Sponsor commercial register number", False),
            _f("sa_agency_name", "Saudi recruitment agency", False, "intelligence.agencies[0]"),
            _f("musaned_contract_no", "Musaned contract number", False),
            _f("unpaid_wages_sar", "Unpaid wages (SAR)", True),
            _f("months_withheld", "Months of withheld salary", False),
            _f("recruitment_fee_amount", "Recruitment fee paid (USD/SAR)", False),
            _f("document_retention_yes_no", "Passport / document retention (Y/N)", True),
            _f("movement_restriction_yes_no", "Restriction of movement (Y/N)", True),
            _f("hours_per_day", "Working hours per day", False),
            _f("weekly_rest_day_yes_no", "Weekly rest day provided (Y/N)", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO forced-labour indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "uae_mohre_complaint": TemplateSpec(
        id="uae_mohre_complaint",
        title="UAE MoHRE Complaint (Federal Decree-Law 33/2021 + 9/2022)",
        jurisdiction="United Arab Emirates",
        audience="Ministry of Human Resources and Emiratisation (MoHRE)",
        summary=(
            "Complaint against a UAE employer / sponsor / Tadbeer / "
            "Esna'ad centre for unpaid wages, recruitment-fee abuse, "
            "document retention, or domestic-worker violations. Aligns "
            "with Federal Decree-Law 33/2021 + Federal Decree-Law "
            "9/2022 + WPS + Tadbeer regulation."
        ),
        body=_TEMPLATE_UAE_MOHRE_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("emirates_id_prefix", "Emirates ID prefix", False),
            _f("sector", "Sector", True, "intelligence.sector"),
            _f("employer_name", "Employer name", True, "intelligence.employers[0]"),
            _f("employer_trade_licence", "Employer trade licence number", False),
            _f("tadbeer_centre_name", "Tadbeer / Esna'ad centre (if domestic)", False),
            _f("mohre_permit_no", "MoHRE work permit number", False),
            _f("unpaid_wages_aed", "Unpaid wages (AED)", True),
            _f("months_withheld", "Months of withheld salary", False),
            _f("recruitment_fee_amount", "Recruitment fee paid (USD/AED)", False),
            _f("document_retention_yes_no", "Document retention (Y/N)", True),
            _f("movement_restriction_yes_no", "Restriction of movement (Y/N)", True),
            _f("hours_per_day_rest", "Hours per day / rest day status", False),
            _f("living_conditions_concern", "Living conditions concern (describe)", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "qatar_mol_complaint": TemplateSpec(
        id="qatar_mol_complaint",
        title="Qatar MoL Complaint (Law 14/2004 + 15/2017 + Workers' Support Fund)",
        jurisdiction="Qatar",
        audience="Ministry of Labour + Workers' Support and Insurance Fund",
        summary=(
            "Complaint against a Qatari employer / kafeel for unpaid "
            "wages, WPS non-compliance, minimum-wage shortfall, "
            "housing / food allowance denial, or document retention. "
            "Aligns with Law 14/2004 + Law 15/2017 + post-2020 "
            "non-discriminatory minimum wage + NOC abolition."
        ),
        body=_TEMPLATE_QATAR_MOL_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("qid_prefix", "QID prefix", False),
            _f("sector", "Sector", True, "intelligence.sector"),
            _f("employer_name", "Employer / kafeel name", True, "intelligence.employers[0]"),
            _f("employer_cr_no", "Employer commercial register number", False),
            _f("work_permit_no", "Work permit number", False),
            _f("contract_start_date", "Contract start date", False),
            _f("unpaid_wages_qar", "Unpaid wages (QAR)", True),
            _f("months_withheld", "Months of withheld salary", False),
            _f("wps_paid_yes_no", "WPS-paid (Y/N)", True),
            _f("min_wage_shortfall", "Minimum-wage shortfall (QAR/month)", False),
            _f("housing_food_status", "Housing / food allowance status", False),
            _f("document_retention_yes_no", "Document retention (Y/N)", True),
            _f("noc_abolished_conditions", "Post-2020 NOC conditions met", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "au_fwo_complaint": TemplateSpec(
        id="au_fwo_complaint",
        title="Australian Fair Work Ombudsman (FWO) Complaint (Migrant Worker)",
        jurisdiction="Australia",
        audience="Fair Work Ombudsman + Migrant Workers Centre + Anti-Slavery Australia",
        summary=(
            "Complaint against an Australian employer / sponsor for "
            "unpaid wages, award underpayment, sham contracting, "
            "excess deductions, or visa-status threats against a "
            "migrant worker. Aligns with Fair Work Act 2009 + "
            "Migration Act 1958 + Modern Slavery Act 2018 + PALM "
            "Code of Conduct."
        ),
        body=_TEMPLATE_AU_FWO_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker / union official name", True),
            _f("complainant_org", "Organisation", True),
            _f("complainant_contact", "Contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("visa_subclass_status", "Visa subclass and status (TSS 482 / PALM / Student / etc.)", True),
            _f("visa_label_prefix", "Visa label prefix (anonymized)", False),
            _f("employer_name", "Employer name", True, "intelligence.employers[0]"),
            _f("sponsor_abn", "Sponsor ABN", False),
            _f("worksite_state", "Worksite state", True),
            _f("nomination_no", "Nomination number (TSS 482 / PALM)", False),
            _f("unpaid_wages_aud", "Unpaid wages (AUD)", True),
            _f("award_underpayment", "Underpayment vs. award rate (describe)", False),
            _f("sham_contracting_yes_no", "Sham contracting indicators (Y/N)", False),
            _f("excess_deductions", "Excess deductions (housing / loan)", False),
            _f("hours_per_week", "Hours per week", False),
            _f("document_retention_yes_no", "Document retention (Y/N)", True),
            _f("threat_visa_cancel_yes_no", "Threat of visa cancellation (Y/N)", True),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "uk_nrm_referral": TemplateSpec(
        id="uk_nrm_referral",
        title="UK National Referral Mechanism (NRM) Referral",
        jurisdiction="United Kingdom",
        audience="Single Competent Authority (SCA) + First Responder Organisations",
        summary=(
            "First Responder Organisation NRM referral to the UK SCA "
            "for adult or child potential victim of trafficking / "
            "modern slavery. Aligns with Modern Slavery Act 2015, "
            "Council of Europe Convention CETS 197, and the Palermo "
            "Protocol."
        ),
        body=_TEMPLATE_UK_NRM_REFERRAL_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "First Responder name", True),
            _f("complainant_org", "First Responder Organisation", True),
            _f("fro_status", "FRO status (Police / NCA / GLAA / Border Force / NGO)", True),
            _f("complainant_contact", "Contact", True),
            _f("worker_name", "Potential victim anonymized ID", True, "people[0].label"),
            _f("nationality", "Nationality", True),
            _f("year_of_birth", "Year of birth", False),
            _f("age_category", "Age category (child / adult)", True),
            _f("gender", "Gender", False),
            _f("languages_spoken", "Languages spoken", False),
            _f("sex_exploit_yes_no", "Sexual exploitation (Y/N)", True),
            _f("labour_exploit_yes_no", "Labour exploitation (Y/N)", True),
            _f("dom_servitude_yes_no", "Domestic servitude (Y/N)", True),
            _f("criminal_exploit_yes_no", "Criminal exploitation (Y/N)", False),
            _f("organ_removal_yes_no", "Organ removal (Y/N)", False),
            _f("trafficker_description", "Trafficker network description", False),
            _f("country_of_recruitment", "Country of recruitment", False),
            _f("journey_route", "Journey route", False),
            _f("current_uk_location", "Current UK location", False),
            _f("recruitment_indicators", "Recruitment indicators", False),
            _f("travel_indicators", "Travel indicators", False),
            _f("exploitation_indicators", "Exploitation indicators", False),
            _f("movement_indicators", "Restriction-of-movement indicators", False),
            _f("document_retention_yes_no", "Document retention (Y/N)", True),
            _f("debt_bondage_yes_no", "Debt bondage indicators (Y/N)", True),
            _f("victim_consent_yes_no", "Potential victim consent given (Y/N)", True),
            _f("rr_period_needed_yes_no", "Recovery and Reflection needed (Y/N)", True),
            _f("safehouse_needed_yes_no", "Safehouse needed (Y/N)", True),
            _f("children_involved_yes_no", "Children involved (Y/N)", True),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("relief_requested", "Referral + support requested", True),
        ),
    ),

    "polaris_hotline_referral": TemplateSpec(
        id="polaris_hotline_referral",
        title="Polaris US National Human Trafficking Hotline -- Caseworker Referral",
        jurisdiction="United States",
        audience="Polaris Project + 1-888-373-7888 hotline + BeFree text-line",
        summary=(
            "Caseworker referral to the US National Human Trafficking "
            "Hotline. Caller-led design; the victim defines the goal "
            "of the contact. Aligns with US TVPRA + 18 USC "
            "1581-1592 + California Labor Code Sec. 244 + HHS OTIP "
            "framework."
        ),
        body=_TEMPLATE_POLARIS_HOTLINE_REFERRAL_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / clinic", True),
            _f("complainant_contact", "Contact", True),
            _f("worker_name", "Potential victim anonymized ID", True, "people[0].label"),
            _f("languages_spoken", "Languages", False),
            _f("country_of_origin", "Country of origin", False, "intelligence.country_of_origin"),
            _f("age_category", "Age category", True),
            _f("current_us_location", "Current US location (city / state only)", True),
            _f("trafficking_type", "Trafficking type (sex / labour / mixed)", True),
            _f("sector", "Industry / sector", False, "intelligence.sector"),
            _f("country_of_recruitment", "Recruitment country", False),
            _f("trafficker_relationship", "Trafficker relationship to victim", False),
            _f("us_duration", "Duration in US", False),
            _f("immigration_status", "Immigration status (if known)", False),
            _f("coercion_indicators", "Force / coercion indicators", False),
            _f("document_retention_yes_no", "Document retention (Y/N)", False),
            _f("debt_bondage_yes_no", "Debt-bondage indicators (Y/N)", False),
            _f("movement_indicators", "Restriction of movement", False),
            _f("threats_reported", "Threats reported", False),
            _f("wages_owed_usd", "Wages owed (USD)", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("victim_stated_goal", "Victim's stated goal of contact", True),
            _f("wants_le_involvement_yes_no", "Wants law enforcement (Y/N)", True),
            _f("wants_t_or_u_visa_yes_no", "Wants T-Visa / U-Visa exploration (Y/N)", True),
            _f("wants_medical_support_yes_no", "Wants medical / MH support (Y/N)", True),
            _f("wants_shelter_yes_no", "Wants shelter (Y/N)", True),
            _f("wants_legal_aid_yes_no", "Wants legal-aid for civil restitution (Y/N)", True),
            _f("caseworker_actions", "Caseworker actions taken", True),
            _f("recommended_service_providers", "Recommended local service providers", False),
            _f("relief_requested", "Relief + referral requested", True),
        ),
    ),

    "cbp_e_allegation": TemplateSpec(
        id="cbp_e_allegation",
        title="US CBP e-Allegation -- Forced-Labour Withhold Release Order Petition",
        jurisdiction="United States",
        audience="US Customs and Border Protection (CBP) Forced Labor Division",
        summary=(
            "Submission to CBP e-Allegations Online Trade Violation "
            "Reporting platform requesting investigation and possible "
            "Withhold Release Order under 19 USC 1307 against "
            "merchandise produced with forced labour. Aligns with "
            "Tariff Act of 1930 Section 307 + UFLPA + TVPRA."
        ),
        body=_TEMPLATE_CBP_E_ALLEGATIONS_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Submitter name", True),
            _f("complainant_org", "Submitter organisation", True),
            _f("complainant_contact", "Contact", True),
            _f("product_name_htsus", "Product name + HTSUS code", True),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("importer_name", "Importer name (if known)", False),
            _f("manufacturer_name", "Manufacturer name", True),
            _f("manufacturer_address", "Manufacturer address", False),
            _f("supply_chain_tier", "Tier of supply chain (Tier 1 / 2 / 3 / raw)", False),
            _f("ilo_indicators", "ILO forced-labour indicators observed", True, "intelligence.ilo_indicators"),
            _f("palermo_indicators", "Palermo Protocol indicators", False),
            _f("worker_testimony_refs", "Worker testimony references", False),
            _f("audit_documentation", "Audit + investigative documentation", False),
            _f("uflpa_entity_list_linkage", "UFLPA Entity List linkage (if any)", False),
            _f("factual_basis_summary", "Factual basis summary", True, "intelligence.case_brief"),
            _f("evidence_list", "Evidence provided", True, "intelligence.evidence_edges"),
        ),
    ),

    "kr_eps_complaint": TemplateSpec(
        id="kr_eps_complaint",
        title="Korea Employment Permit System (EPS) Complaint (E-9 Worker)",
        jurisdiction="South Korea",
        audience="Ministry of Employment and Labor (MOEL) + Labour Inspectorate",
        summary=(
            "Complaint against a Korean employer for unpaid wages, "
            "severance pay denial, workplace-transfer denial, or "
            "employer-pays-principle violation. Aligns with EPS Act "
            "+ Labor Standards Act + bilateral EPS-TOPIK MoU "
            "framework."
        ),
        body=_TEMPLATE_KR_EPS_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("arc_prefix", "Alien Registration Card prefix", False),
            _f("visa_start_date", "E-9 visa start date", False),
            _f("sector", "Sector", True, "intelligence.sector"),
            _f("employer_name", "Employer name", True, "intelligence.employers[0]"),
            _f("employer_brn", "Business registration number", False),
            _f("worksite_city", "Worksite city", True),
            _f("eps_issuing_agency", "EPS-issuing agency (HRD Service of Korea)", False),
            _f("unpaid_wages_krw", "Unpaid wages (KRW)", True),
            _f("months_withheld", "Months of withheld salary", False),
            _f("recruitment_fee_amount", "Recruitment / training fee (KRW)", False),
            _f("employer_pays_violation", "Employer-pays-principle violation (describe)", False),
            _f("workplace_transfer_denied_yes_no", "Workplace transfer denied (Y/N)", False),
            _f("severance_denied_yes_no", "Severance pay (toejikgeum) denied (Y/N)", False),
            _f("document_retention_yes_no", "Document retention (Y/N)", True),
            _f("movement_restriction_yes_no", "Restriction of movement (Y/N)", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "tw_mol_complaint": TemplateSpec(
        id="tw_mol_complaint",
        title="Taiwan MOL Complaint (Employment Services Act + Caregiver Regs)",
        jurisdiction="Taiwan",
        audience="Ministry of Labor (MOL) + Workforce Development Agency",
        summary=(
            "Complaint against a Taiwanese employer or broker for "
            "service-fee overcharge, brokerage-fee cap violations, "
            "live-in caregiver no-rest-day, or document retention. "
            "Aligns with Employment Services Act + Labor Standards "
            "Act + Hire-Purchase / Foreign Worker Regulations."
        ),
        body=_TEMPLATE_TW_MOL_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("arc_prefix", "ARC number prefix", False),
            _f("sector", "Sector", True, "intelligence.sector"),
            _f("worker_category", "Worker category (caregiver / factory / fishing / construction)", True),
            _f("employer_name", "Employer / household name", True, "intelligence.employers[0]"),
            _f("employer_id", "Employer business registration ID", False),
            _f("tw_broker_name", "Taiwan brokerage agency", False, "intelligence.agencies[0]"),
            _f("tw_broker_license", "Brokerage licence number", False),
            _f("origin_country_agency", "Origin-country counterpart agency", False),
            _f("unpaid_wages_twd", "Unpaid wages (TWD)", True),
            _f("months_withheld", "Months of withheld salary", False),
            _f("brokerage_fee_excess", "Brokerage fee excess over cap (describe)", False),
            _f("service_fee_excess", "Service-fee deduction excess (describe)", False),
            _f("document_retention_yes_no", "Document retention (Y/N)", True),
            _f("movement_restriction_yes_no", "Restriction of movement (Y/N)", False),
            _f("caregiver_no_rest_day_yes_no", "Caregiver no-rest-day (Y/N)", False),
            _f("hours_per_day_week", "Working hours per day / week", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "sg_mom_complaint": TemplateSpec(
        id="sg_mom_complaint",
        title="Singapore MOM Complaint (EFMA + Employment Act + EA Code)",
        jurisdiction="Singapore",
        audience="Ministry of Manpower (MOM) + Tripartite Alliance for Dispute Management",
        summary=(
            "Complaint against a Singapore employer or employment "
            "agency for unpaid wages, agency-fee cap violations, "
            "FDW Code violations, or document retention. Aligns with "
            "EFMA Cap. 91A + Employment Act Cap. 91 + Employment "
            "Agencies Act Cap. 92."
        ),
        body=_TEMPLATE_SG_MOM_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("work_permit_prefix", "Work permit number prefix", False),
            _f("sector", "Sector", True, "intelligence.sector"),
            _f("worker_category", "Worker category (FDW / Construction / Marine / Process)", True),
            _f("employer_name", "Employer / household name", True, "intelligence.employers[0]"),
            _f("employer_uen", "Employer UEN", False),
            _f("ea_agency_name", "EA agency name", False, "intelligence.agencies[0]"),
            _f("ea_license_number", "EA licence number", False),
            _f("origin_country_agency", "Origin-country counterpart agency", False),
            _f("unpaid_wages_sgd", "Unpaid wages (SGD)", True),
            _f("months_withheld", "Months of withheld salary", False),
            _f("agency_fee_excess", "Agency fee excess over cap", False),
            _f("loan_deduction_abuse", "Loan / advance deduction abuse", False),
            _f("document_retention_yes_no", "Document retention (Y/N)", True),
            _f("movement_restriction_yes_no", "Restriction of movement (Y/N)", False),
            _f("fdw_hours_per_day", "Hours per day (FDW)", False),
            _f("fdw_rest_day_yes_no", "Weekly rest day (FDW, Y/N)", False),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "il_piba_complaint": TemplateSpec(
        id="il_piba_complaint",
        title="Israel PIBA Complaint (Foreign Workers Law 1991 + Bilateral Agreement)",
        jurisdiction="Israel",
        audience="Population, Immigration and Border Authority (PIBA) + Kav LaOved",
        summary=(
            "Complaint against an Israeli employer / recruitment "
            "agency for recruitment-fee cap violation, document "
            "retention, caregiver no-rest-day, or GBV / harassment. "
            "Aligns with Foreign Workers Law 1991 + 2016 amendments "
            "+ Bilateral Agreement framework."
        ),
        body=_TEMPLATE_IL_PIBA_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("b1_visa_prefix", "B/1 visa number prefix", False),
            _f("sector", "Sector", True, "intelligence.sector"),
            _f("worker_category", "Worker category (caregiver / agriculture / construction)", True),
            _f("employer_name", "Employer name", True, "intelligence.employers[0]"),
            _f("employer_id", "Employer ID number", False),
            _f("il_agency_name", "Israel recruitment agency", False, "intelligence.agencies[0]"),
            _f("il_agency_license", "Recruitment agency licence", False),
            _f("origin_country_agency", "Origin-country counterpart agency", False),
            _f("unpaid_wages_nis", "Unpaid wages (NIS)", True),
            _f("months_withheld", "Months of withheld salary", False),
            _f("recruitment_fee_excess", "Recruitment fee excess over cap", False),
            _f("document_retention_yes_no", "Document retention (Y/N)", True),
            _f("movement_restriction_yes_no", "Restriction of movement (geo+sector, Y/N)", False),
            _f("caregiver_no_rest_day_yes_no", "Caregiver no-rest-day (Y/N)", False),
            _f("hours_per_day_week", "Hours per day / week", False),
            _f("gbv_indicators_yes_no", "GBV / harassment indicators (Y/N)", True),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),

    "ngo_survivor_narrative": TemplateSpec(
        id="ngo_survivor_narrative",
        title="NGO Survivor Narrative -- Trauma-Informed Intake (4 phases)",
        jurisdiction="Cross-border",
        audience="NGO caseworker + (with consent) onward referral",
        summary=(
            "Pre-filled four-phase survivor narrative intake "
            "template covering recruitment, deployment, "
            "exploitation, escape / support. Pre-fills the "
            "consent + safety status check + caseworker "
            "validation paragraph + Palermo Protocol + ILO 11 "
            "Indicators framework. Madlibs style -- ILO indicator "
            "checkboxes + narrative-by-phase blocks + 6 referral "
            "paths."
        ),
        body=_TEMPLATE_NGO_SURVIVOR_NARRATIVE_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Contact", True),
            _f("survivor_anon_id", "Survivor anonymized ID", True, "people[0].label"),
            _f("languages_spoken", "Languages spoken", False),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("current_general_location", "Current general location (city / region only)", False),
            _f("age_category", "Age category (child / adult)", True),
            _f("is_safe_to_disclose", "Safe to disclose now (Y/N)", True),
            _f("controlling_third_party_status", "Controlling third party present (describe)", True),
            _f("interpreter_status", "Interpreter (professional / not companion)", True),
            _f("mandatory_reporting_disclosed_yes_no", "Mandatory-reporting limits disclosed (Y/N)", True),
            _f("consent_to_record_yes_no", "Consent to record (Y/N)", True),
            _f("onward_referral_consent_summary", "Onward-referral consent summary", True),
            _f("recruitment_narrative", "Recruitment narrative (survivor's words)", True),
            _f("recruit_deception_yes_no", "Recruitment deception (Y/N)", True),
            _f("recruit_abuse_vulnerability_yes_no", "Abuse of vulnerability at recruitment (Y/N)", True),
            _f("recruit_fee_charged_yes_no", "Recruitment fee charged (Y/N)", True),
            _f("recruit_channel", "Recruitment channel", False),
            _f("deployment_narrative", "Deployment / journey narrative", True),
            _f("doc_retention_arrival_yes_no", "Document retention on arrival (Y/N)", True),
            _f("movement_restriction_arrival_yes_no", "Movement restriction on arrival (Y/N)", True),
            _f("contract_substitution_yes_no", "Different contract on arrival (Y/N)", True),
            _f("exploitation_narrative", "Exploitation narrative", True),
            _f("wage_withholding_yes_no", "Withholding of wages (Y/N)", True),
            _f("excessive_overtime_yes_no", "Excessive overtime (Y/N)", True),
            _f("isolation_yes_no", "Isolation (Y/N)", True),
            _f("physical_sexual_violence_yes_no", "Physical or sexual violence (Y/N)", True),
            _f("intimidation_threats_yes_no", "Intimidation or threats (Y/N)", True),
            _f("debt_bondage_yes_no", "Debt bondage (Y/N)", True),
            _f("abusive_conditions_yes_no", "Abusive working / living conditions (Y/N)", True),
            _f("escape_support_narrative", "Escape / support narrative", True),
            _f("corridor_specific_origin_statute", "Corridor-specific origin statute", True),
            _f("corridor_specific_destination_statute", "Corridor-specific destination statute", True),
            _f("survivor_led_next_steps", "Survivor-led next steps", True),
            _f("ngo_shelter_referral", "NGO shelter / safehouse referral", False),
            _f("embassy_polo_referral", "Embassy / POLO referral", False),
            _f("destination_labour_referral", "Destination labour authority referral", False),
            _f("legal_aid_referral", "Legal-aid referral", False),
            _f("medical_mh_referral", "Medical / mental-health referral", False),
            _f("peer_support_referral", "Survivor peer-support referral", False),
        ),
    ),

    "worker_first_contact_script": TemplateSpec(
        id="worker_first_contact_script",
        title="Worker First-Contact Script (WhatsApp / SMS / Encrypted Chat)",
        jurisdiction="Cross-border",
        audience="NGO advocate / peer helper -- worker who may be in unsafe location",
        summary=(
            "Pre-filled 8-turn first-contact script for use by NGO "
            "advocate or peer helper communicating with a migrant "
            "worker via WhatsApp / SMS / Signal / Line. Pre-fills the "
            "safety check + validation + immediate-needs triage + "
            "evidence preservation steps. Madlibs style -- short "
            "turns to keep readable on small screens with limited "
            "data; corridor + language blanks only."
        ),
        body=_TEMPLATE_WORKER_FIRST_CONTACT_SCRIPT_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Advocate name", True),
            _f("complainant_org", "Organisation", True),
            _f("primary_language", "Primary language for outreach", True),
            _f("advocate_first_name_only", "Advocate first name only", True),
            _f("destination_country", "Destination country", True),
            _f("corridor_emergency_one_liner", "Corridor-emergency one-liner (if unsafe)", True),
            _f("worker_side_fee_statute", "Worker-side fee statute (corridor-specific)", True),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("safe_place_contact", "Safe-place contact (option 1)", False),
            _f("document_recovery_contact", "Document-recovery contact (option 2)", False),
            _f("wage_recovery_contact", "Wage-recovery contact (option 3)", False),
            _f("repatriation_contact", "Repatriation contact (option 4)", False),
            _f("psychosocial_contact", "Psychosocial contact (option 5)", False),
            _f("follow_up_window", "Follow-up window (e.g. 24h / 3 days / weekly)", True),
            _f("advocate_contact", "Advocate contact (callable / textable)", True),
            _f("corridor_specific_hotline", "Corridor-specific hotline name", True),
            _f("corridor_hotline_number_or_verify", "Hotline number (or 'verify via contacts pack')", True),
            _f("advocate_internal_notes", "Advocate internal notes", False),
        ),
    ),

    "journalist_tip_brief": TemplateSpec(
        id="journalist_tip_brief",
        title="Journalist Tip / Anonymized Case Brief (investigative outlets)",
        jurisdiction="Cross-border",
        audience="Investigative journalist (Guardian / Reuters / ProPublica / BBC / Al Jazeera / national outlets)",
        summary=(
            "Pre-filled journalist-tip case brief covering pattern, "
            "de-identified numbers, regulatory posture, verification "
            "questions, primary-source documents (subject to consent), "
            "named public-record entities, statutory framework, and "
            "NGO ethical operational constraints. Madlibs style -- "
            "pre-fills the safe-conduct + survivor-protection + "
            "defamation-burden language; only case-specific facts "
            "blank."
        ),
        body=_TEMPLATE_JOURNALIST_TIP_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Submitter name", True),
            _f("complainant_org", "Organisation", True),
            _f("complainant_contact", "Contact", True),
            _f("journalist_outlet", "Journalist outlet", True),
            _f("journalist_name", "Journalist name", True),
            _f("executive_summary", "Executive summary", True, "intelligence.case_brief"),
            _f("pattern_description", "Pattern description", True),
            _f("affected_workers_range", "Affected workers (range)", True),
            _f("corridor", "Corridor", True, "intelligence.corridor"),
            _f("sector", "Sector", True, "intelligence.sector"),
            _f("period_of_conduct", "Period of conduct", True),
            _f("worker_paid_usd_range", "Estimated worker-paid sum (USD range)", False),
            _f("repeat_violator_yes_no", "Repeat-violator pattern (Y/N)", False),
            _f("origin_regulator", "Origin-country regulator", True),
            _f("origin_action_to_date", "Origin regulator action to date", False),
            _f("destination_regulator", "Destination-country regulator", True),
            _f("destination_action_to_date", "Destination regulator action to date", False),
            _f("outstanding_referrals", "Outstanding referrals / complaints", False),
            _f("verification_question_1", "Verification question 1", True),
            _f("verification_question_2", "Verification question 2", True),
            _f("verification_question_3", "Verification question 3", True),
            _f("verification_question_4", "Verification question 4", False),
            _f("verification_question_5", "Verification question 5", False),
            _f("available_documents", "Available primary-source documents", True),
            _f("named_public_entities", "Named public-record entities", False),
            _f("controlling_origin_statute", "Controlling origin statute", True),
            _f("controlling_destination_statute", "Controlling destination statute", True),
            _f("supply_chain_or_sectoral_framework", "Supply-chain or sectoral framework", False),
        ),
    ),

    "employer_wage_demand": TemplateSpec(
        id="employer_wage_demand",
        title="Direct Employer Wage Arrears Demand Letter",
        jurisdiction="Destination-country",
        audience="Foreign employer / sponsor -- pre-litigation",
        summary=(
            "Pre-filled direct demand letter to foreign employer for "
            "unpaid wages. Cites destination-country wage statute + "
            "ILO C95 Art. 12 + ILO Indicator 8 (withholding of "
            "wages) + Palermo Protocol Art. 3. Itemised wage "
            "calculation + 10-day compliance deadline + 5-tier "
            "escalation. Madlibs style -- statutory framework + "
            "relief blocks pre-built; only worker-specific + "
            "destination-country blanks remain."
        ),
        body=_TEMPLATE_EMPLOYER_WAGE_DEMAND_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("employer_name", "Employer name", True, "intelligence.employers[0]"),
            _f("employer_address", "Employer address", False),
            _f("employer_attention", "Attention person", False),
            _f("destination_country_labour_authority", "Destination labour authority", True),
            _f("worker_origin_country_embassy_or_polo", "Worker's origin embassy / POLO", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("worker_nationality", "Worker nationality", True, "intelligence.country_of_origin"),
            _f("contract_reference", "Contract reference", True),
            _f("wage_period", "Wage period / period of underpayment", True),
            _f("hours_actually_worked", "Hours actually worked", True),
            _f("statutory_min_wage", "Statutory minimum wage applicable", True),
            _f("contract_wage", "Agreed contract wage", True),
            _f("wages_actually_paid", "Wages actually paid", True),
            _f("wages_outstanding_local", "Outstanding wages (local currency)", True),
            _f("currency", "Currency", True),
            _f("wages_outstanding_usd", "Outstanding wages (USD equivalent)", False),
            _f("destination_wage_statute", "Destination-country wage statute", True),
            _f("preferred_payment_channel", "Preferred payment channel", True),
            _f("compliance_deadline", "Compliance deadline (10 days from receipt)", True),
            _f("civil_court_or_tribunal", "Civil court or labour tribunal", True),
            _f("trafficking_statute", "Trafficking statute (for referral)", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "Organisation", True),
            _f("complainant_contact", "Contact", True),
        ),
    ),

    "supplier_audit_finding_letter": TemplateSpec(
        id="supplier_audit_finding_letter",
        title="Buyer -> Supplier Audit Finding Letter (CSDDD / UK MSA / Lieferkettengesetz)",
        jurisdiction="Cross-border supply-chain",
        audience="Supplier compliance officer + buyer compliance officer",
        summary=(
            "Pre-filled buyer-to-supplier audit-finding letter with "
            "Tier-1 forced-labour findings (recruitment-fee violation, "
            "document retention, working-time, wage violations). "
            "Pre-cites the supplier code of conduct + UK MSA + EU "
            "CSDDD + France Loi de Vigilance + Germany "
            "Lieferkettengesetz + Norway Transparency Act + US UFLPA "
            "+ 19 USC 1307 + EU Forced Labour Regulation + UNGP + "
            "OECD MNE Guidelines + IRIS Standard. Madlibs style -- "
            "remediation requirements + escalation sequence pre-"
            "built; only audit-finding blanks remain."
        ),
        body=_TEMPLATE_SUPPLIER_AUDIT_FINDING_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("buyer_company_name", "Buyer company name", True),
            _f("buyer_compliance_officer", "Buyer compliance officer", True),
            _f("buyer_address", "Buyer address", False),
            _f("supplier_company_name", "Supplier company name", True),
            _f("supplier_contact", "Supplier contact", True),
            _f("supplier_address", "Supplier address", False),
            _f("audit_type", "Audit type (Tier 1 / Tier 2 / unannounced / follow-up)", True),
            _f("audit_date_range", "Audit date range", True),
            _f("supplier_facility_name", "Supplier facility name", True),
            _f("supplier_facility_country", "Facility country", True),
            _f("audit_provider", "Audit provider", True),
            _f("n_worker_interviews", "Number of worker interviews", False),
            _f("recruitment_country", "Recruitment country", True),
            _f("findings_summary", "Findings summary", True),
            _f("recruitment_fee_categories", "Recruitment-fee categories observed", True),
            _f("recruitment_fee_average_usd", "Average recruitment fee per worker (USD)", True),
            _f("document_retention_findings", "Document-retention findings", False),
            _f("working_time_findings", "Working-time findings", False),
            _f("destination_working_time_statute", "Destination working-time statute", False),
            _f("wage_findings", "Wage findings", False),
            _f("destination_wage_statute", "Destination wage statute", False),
            _f("other_findings", "Other findings", False),
            _f("reimbursement_deadline_days", "Reimbursement deadline (days)", True),
            _f("preferred_payment_channel", "Preferred payment channel", False),
            _f("policy_deadline_days", "Policy + procedure deadline (days)", True),
            _f("remediation_partner", "Remediation monitoring partner", False),
            _f("buyer_supplier_code_of_conduct", "Buyer supplier code of conduct reference", True),
            _f("buyer_chief_compliance_officer", "Buyer chief compliance officer", False),
            _f("regulator_or_industry_initiative", "Regulator or industry-initiative for reporting", False),
        ),
    ),

    "ungp_oecd_remediation_request": TemplateSpec(
        id="ungp_oecd_remediation_request",
        title="UNGP / OECD NCP Remediation Request (Pillar III Access to Remedy)",
        jurisdiction="Cross-border",
        audience="Multinational enterprise (MNE) + NCP",
        summary=(
            "Pre-filled UNGP Pillar III access-to-remedy request to "
            "an MNE plus concurrent OECD NCP Specific Instance filing. "
            "Cites UNGP HRC Resolution 17/4 (2011) + UNGP 13 + 22 + "
            "31 effectiveness criteria + OECD Guidelines for MNEs "
            "(2023 revision) + UK MSA + France Loi de Vigilance + "
            "Germany Lieferkettengesetz + Norway Transparency Act + "
            "EU CSDDD + EU FLR. Madlibs style -- 8 numbered sections "
            "with pre-built remediation requests + reservation of "
            "rights."
        ),
        body=_TEMPLATE_UNGP_OECD_REMEDIATION_REQUEST_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Counsel / caseworker name", True),
            _f("complainant_org", "Organisation", True),
            _f("complainant_contact", "Contact", True),
            _f("multinational_enterprise_name", "MNE name", True),
            _f("mne_contact", "MNE contact", True),
            _f("mne_address", "MNE address", False),
            _f("ncp_country", "National Contact Point country", True),
            _f("ncp_address", "NCP address", False),
            _f("worker_name", "Affected worker anonymized ID", True, "people[0].label"),
            _f("worker_nationality", "Worker nationality", True, "intelligence.country_of_origin"),
            _f("country_of_recruitment", "Country of recruitment", True),
            _f("sector", "Sector", True, "intelligence.sector"),
            _f("direct_employer_name", "Direct employer name", True, "intelligence.employers[0]"),
            _f("value_chain_tier", "Tier in MNE value chain", True),
            _f("period_of_harm", "Period of harm", True),
            _f("nature_of_adverse_impact", "Nature of adverse impact", True),
            _f("ungp_nexus_description", "UNGP 13 nexus description (caused / contributed / linked)", True),
            _f("mne_company_name", "MNE company name", True),
            _f("prior_requests_summary", "Prior requests + responses summary", False),
            _f("country_of_origin_due_diligence_statute_if_any", "Origin-country due-diligence statute (if any)", False),
            _f("country_of_destination_due_diligence_statute_if_any", "Destination-country due-diligence statute (if any)", False),
        ),
    ),

    "ph_hk_fdh_fee_refund_demand": TemplateSpec(
        id="ph_hk_fdh_fee_refund_demand",
        title="PH-HK FDH Recruitment Fee Refund Demand (POEA MC 14-2017)",
        jurisdiction="Philippines / Hong Kong",
        audience="Philippine licensed recruitment agency + HK-side EA",
        summary=(
            "Pre-filled demand letter for refund of unauthorised "
            "training / medical / processing / placement fees "
            "collected from a Filipino HSW deployed to Hong Kong. "
            "Cites POEA MC 14-2017, ILO C181 Art. 7 + 2019 "
            "Definition, RA 8042 / RA 10022, HK Cap. 57A Reg. 2 + "
            "13. Madlibs style -- only worker-specific blanks remain."
        ),
        body=_TEMPLATE_PH_HK_FDH_FEE_REFUND_DEMAND_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("agency_name", "Philippine licensed recruitment agency", True, "intelligence.agencies[0]"),
            _f("agency_address", "Agency address", False),
            _f("agency_principal_or_officer", "Agency principal / officer name", False),
            _f("agency_license_no", "DMW recruitment agency licence", True),
            _f("hk_agency_name", "Hong Kong-side EA (if applicable)", False),
            _f("hk_agency_address", "HK EA address", False),
            _f("hk_ea_license_no", "HK EA licence", False),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("deployment_date", "Deployment date", True, "intelligence.deployment_date"),
            _f("total_paid_php", "Total amount paid by worker (PHP)", True),
            _f("training_fee_php", "Training fee (PHP)", False),
            _f("medical_fee_php", "Medical examination fee (PHP)", False),
            _f("processing_fee_php", "Processing / documentation fee (PHP)", False),
            _f("placement_fee_php", "Placement fee (PHP)", False),
            _f("other_fees_php", "Other fees (PHP)", False),
            _f("collection_dates", "Date(s) of collection", True),
            _f("receipt_status", "Receipts issued / not issued", False),
            _f("preferred_refund_channel", "Preferred refund channel", True),
            _f("compliance_deadline", "Compliance deadline (14 days from receipt)", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
        ),
    ),

    "passport_return_demand": TemplateSpec(
        id="passport_return_demand",
        title="Passport + Identity Document Return Demand (ILO C189 Art. 9)",
        jurisdiction="Cross-border",
        audience="Foreign employer / sponsor / recruitment agency",
        summary=(
            "Pre-filled demand letter for the immediate return of "
            "passport + identity documents retained by an employer / "
            "sponsor / recruitment agency. Cites ILO C189 Art. 9, "
            "ILO Forced Labour Indicator 7, Palermo Protocol Art. 3, "
            "and the destination-country statutory prohibition. "
            "Madlibs style -- only worker-specific + destination-"
            "country blanks remain."
        ),
        body=_TEMPLATE_PASSPORT_RETURN_DEMAND_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("respondent_name", "Respondent name (employer / sponsor / agency)", True, "intelligence.employers[0]"),
            _f("respondent_address", "Respondent address", False),
            _f("respondent_attention", "Attention person", False),
            _f("destination_country_labour_authority", "Destination-country labour authority", True),
            _f("worker_origin_country_embassy_or_polo", "Worker's origin-country embassy / POLO", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("worker_nationality", "Worker nationality", True, "intelligence.country_of_origin"),
            _f("worksite_or_household", "Worksite or household", True),
            _f("passport_prefix", "Passport number prefix", False),
            _f("retention_date", "Date of retention", True),
            _f("document_current_location", "Current location of documents", False),
            _f("conditions_imposed", "Conditions imposed for return", False),
            _f("destination_statute_citation", "Destination-country statutory prohibition (e.g. HK Cap. 57 Sec. 32)", True),
            _f("compliance_deadline", "Compliance deadline (5 days from receipt)", True),
            _f("worker_current_safety_status", "Worker current safety status", True),
            _f("complainant_name", "Caseworker name", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Caseworker contact", True),
        ),
    ),

    "t_visa_affidavit": TemplateSpec(
        id="t_visa_affidavit",
        title="T-Visa (I-914) Supporting Affidavit -- Severe Form of Trafficking",
        jurisdiction="United States",
        audience="USCIS Vermont Service Center",
        summary=(
            "Pre-filled supporting affidavit for Form I-914 T-Visa "
            "application. Cites TVPA + 22 USC 7102(11) severe form "
            "definition + 8 CFR 214.11 + 18 USC 1581-1592 + Palermo "
            "Protocol. Madlibs style -- 11 numbered paragraphs with "
            "embedded legal framework; only worker-specific narrative "
            "blanks remain."
        ),
        body=_TEMPLATE_T_VISA_AFFIDAVIT_BODY,
        fields=(
            _f("filed_date", "Filing date / execution date", True),
            _f("worker_name", "Declarant name", True, "people[0].label"),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("year_of_birth", "Year of birth", False),
            _f("native_language", "Native language", False),
            _f("us_entry_date", "US entry date", True),
            _f("visa_status_at_entry", "Visa status at entry", False),
            _f("prior_occupation", "Prior occupation in country of origin", False),
            _f("recruitment_year", "Recruitment year", True),
            _f("trafficker_name_or_anonymized", "Trafficker name (anonymized if needed)", True),
            _f("trafficker_relationship_to_me", "Trafficker relationship to declarant", True),
            _f("recruitment_channel", "Recruitment channel", True),
            _f("promised_terms", "Terms promised at recruitment", True),
            _f("promised_living_situation", "Promised living situation", False),
            _f("travel_arrangements_summary", "Travel arrangements summary", True),
            _f("debt_amount", "Debt amount asserted on arrival", False),
            _f("first_us_location", "First US location", True),
            _f("housing_address_general", "Housing address (general / anonymized)", False),
            _f("actual_work_type", "Actual work type", True),
            _f("hours_per_day", "Hours per day required", False),
            _f("days_per_week", "Days per week required", False),
            _f("actual_compensation", "Actual compensation received", False),
            _f("reasons_unable_to_leave", "Reasons unable to leave", True),
            _f("movement_restriction_details", "Movement restriction details", False),
            _f("isolation_details", "Isolation details", False),
            _f("document_retention_details", "Document retention details", False),
            _f("wage_withholding_details", "Wage withholding details", False),
            _f("debt_bondage_details", "Debt bondage details", False),
            _f("threats_details", "Threats details", False),
            _f("abuse_details", "Abuse details (only if applicable)", False),
            _f("escape_date", "Escape / rescue date", True),
            _f("escape_circumstances", "Escape circumstances", True),
            _f("service_provider_org", "Current service provider organisation", True),
            _f("law_enforcement_cooperation_summary", "Law-enforcement cooperation summary", True),
            _f("extreme_hardship_reasons", "Extreme hardship reasons upon removal", True),
            _f("supporting_evidence_list", "Supporting evidence list", True),
            _f("derivative_family_members_list_or_none", "Family members requesting derivative status (or none)", False),
            _f("place_of_execution", "Place of execution", True),
            _f("complainant_name", "Submitter name", True),
            _f("complainant_org", "Submitter organisation", True),
            _f("complainant_contact", "Submitter contact", True),
        ),
    ),

    "anti_retaliation_tro": TemplateSpec(
        id="anti_retaliation_tro",
        title="Anti-Retaliation Interim Order Request (Destination Labour Tribunal)",
        jurisdiction="Destination-country labour tribunal",
        audience="Labour tribunal / labour court / migrant-worker tribunal",
        summary=(
            "Pre-filled interim-order request restraining employer / "
            "sponsor / agency from retaliating against migrant worker "
            "during the pendency of an underlying complaint. Cites "
            "ILO C190 Art. 6 + C181 Art. 8 + Palermo Protocol + "
            "jurisdiction-specific anti-retaliation statute. Madlibs "
            "style -- 6 numbered sections with embedded relief, "
            "evidence, and procedural compliance."
        ),
        body=_TEMPLATE_ANTI_RETALIATION_TRO_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("case_file_number", "Case / file number", True),
            _f("tribunal_name", "Tribunal name", True),
            _f("jurisdiction_name", "Jurisdiction name", True),
            _f("worker_name", "Petitioner anonymized ID", True, "people[0].label"),
            _f("respondent_name", "Respondent name", True, "intelligence.employers[0]"),
            _f("underlying_complaint_summary", "Underlying complaint summary", True, "intelligence.case_brief"),
            _f("evidence_of_retaliation_likelihood", "Evidence of likelihood of retaliation", True),
            _f("specific_irreparable_harm", "Specific irreparable harm", True),
            _f("jurisdiction_specific_anti_retaliation_statute", "Jurisdiction-specific anti-retaliation statute", True),
            _f("notice_date", "Notice given date", True),
            _f("incident_summary", "Summary evidence", True),
            _f("complainant_name", "Caseworker / counsel name", True),
            _f("complainant_org", "Organisation", True),
            _f("complainant_contact", "Contact", True),
        ),
    ),

    "witness_statement": TemplateSpec(
        id="witness_statement",
        title="Voluntary Witness Statement -- Trafficking Investigation",
        jurisdiction="Cross-border",
        audience="Investigating law-enforcement / labour authority",
        summary=(
            "Pre-filled voluntary witness statement for trafficking "
            "investigation. Cites controlling criminal statute + "
            "Palermo Protocol Art. 3 + ILO indicators (2012) + "
            "destination-country labour statute. Madlibs style -- "
            "9 numbered sections capturing context, recruitment, "
            "deployment, ILO indicators, specific events, available "
            "evidence, other witnesses, witness protection, and "
            "statutory framework."
        ),
        body=_TEMPLATE_WITNESS_STATEMENT_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("witness_name", "Witness name (anonymized if needed)", True),
            _f("relationship_to_victim", "Relationship to victim", True),
            _f("witness_contact", "Witness contact", True),
            _f("investigating_authority", "Investigating authority", True),
            _f("case_file_number", "Case / file number", True),
            _f("designated_officer", "Designated officer", False),
            _f("victim_name_or_anonymized", "Victim name (anonymized)", True),
            _f("when_known", "When known", True),
            _f("observation_location", "Observation location", True),
            _f("observation_period", "Observation period", True),
            _f("recruitment_observations", "Recruitment observations", True),
            _f("recruiter_name_or_description", "Recruiter name / description", True),
            _f("destination_country", "Destination country", True),
            _f("deployment_date_approx", "Approximate deployment date", True),
            _f("destination_employer_name_or_description", "Destination employer name / description", True),
            _f("sector", "Sector", True, "intelligence.sector"),
            _f("movement_observations", "Movement-restriction observations", False),
            _f("isolation_observations", "Isolation observations", False),
            _f("document_observations", "Document-retention observations", False),
            _f("wage_observations", "Wage-withholding observations", False),
            _f("debt_observations", "Debt-bondage observations", False),
            _f("violence_observations", "Violence / threats observations", False),
            _f("other_observations", "Other indicator observations", False),
            _f("specific_events_witnessed", "Specific events witnessed", True),
            _f("available_evidence_list", "Available evidence list", True, "intelligence.evidence_edges"),
            _f("other_witnesses_list", "Other witnesses known to declarant", False),
            _f("witness_protection_concerns", "Witness protection concerns", False),
            _f("controlling_criminal_statute", "Controlling criminal statute", True),
            _f("destination_statute", "Destination-country labour statute", True),
            _f("complainant_name", "Caseworker / officer name", True),
            _f("complainant_org", "Organisation", True),
            _f("complainant_contact", "Contact", True),
        ),
    ),

    "restitution_calculation": TemplateSpec(
        id="restitution_calculation",
        title="Restitution Calculation Worksheet + Demand (Multi-Source)",
        jurisdiction="Cross-border",
        audience="Destination labour tribunal + origin-country agency bond + civil court",
        summary=(
            "Pre-filled itemised restitution calculation worksheet "
            "covering 5 categories of recoverable loss: (A) "
            "unauthorised recruitment fees, (B) unpaid wages + "
            "min-wage shortfall + overtime, (C) illegal deductions, "
            "(D) repatriation costs, (E) statutory damages + "
            "interest. Cites ILO C181 + C95, origin-country fee-cap "
            "statute, destination wage + overtime statutes. Madlibs "
            "style -- itemised arithmetic + statutory authority + "
            "relief blocks pre-built."
        ),
        body=_TEMPLATE_RESTITUTION_CALCULATION_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("case_file_number", "Case / file number", True),
            _f("worker_name", "Claimant anonymized ID", True, "people[0].label"),
            _f("respondents_list", "Respondent(s) list", True),
            _f("principal_amount_local_currency", "Principal amount (local currency)", True),
            _f("training_fee_local", "Training fee (local currency)", False),
            _f("medical_fee_local", "Medical fee (local currency)", False),
            _f("processing_fee_local", "Processing / documentation fee (local currency)", False),
            _f("placement_fee_local", "Placement fee (local currency)", False),
            _f("other_fee_local", "Other fees (local currency)", False),
            _f("fee_subtotal_local", "Fee subtotal A (local currency)", True),
            _f("underpayment_period", "Period of underpayment", True),
            _f("months_unpaid", "Months unpaid", True),
            _f("statutory_min_wage", "Statutory minimum wage applicable", True),
            _f("actual_wages_received", "Actual wages received", True),
            _f("overtime_hours", "Overtime hours beyond statutory cap", False),
            _f("overtime_owed", "Overtime owed under destination law", False),
            _f("wages_subtotal_local", "Wages subtotal B (local currency)", True),
            _f("housing_excess", "Housing deductions exceeding cap", False),
            _f("loan_deduction_amount", "Loan / advance repayment deducted", False),
            _f("equipment_charged", "Equipment / training cost charged", False),
            _f("other_deductions", "Other illegal deductions", False),
            _f("deduction_subtotal_local", "Deduction subtotal C (local currency)", True),
            _f("airfare_charged", "Air ticket cost charged to worker", False),
            _f("other_repat_costs", "Other repatriation costs charged", False),
            _f("repat_subtotal_local", "Repatriation subtotal D (local currency)", True),
            _f("prejudgment_interest_rate", "Pre-judgment interest rate", False),
            _f("statutory_damages_basis", "Statutory damages basis", False),
            _f("liquidated_damages", "Liquidated damages (if applicable)", False),
            _f("damages_subtotal_local", "Damages subtotal E (local currency)", True),
            _f("principal_total_local", "Principal claim total (local currency)", True),
            _f("principal_total_usd", "Equivalent in USD", False),
            _f("origin_country_fee_cap_statute", "Origin-country fee-cap statute", True),
            _f("destination_country_wage_statute", "Destination-country wage statute", True),
            _f("destination_country_overtime_statute", "Destination-country overtime statute", False),
            _f("employer_pays_principle_basis", "Employer-pays-principle basis (e.g. ILO C181 Art. 7)", True),
            _f("prejudgment_interest_authority", "Pre-judgment interest authority", False),
            _f("evidence_list", "Evidence of claim", True, "intelligence.evidence_edges"),
            _f("preferred_payment_channel", "Preferred payment channel", True),
            _f("payment_deadline", "Payment deadline (days)", True),
            _f("interest_start_date", "Pre-judgment interest start date", False),
            _f("complainant_name", "Counsel / caseworker name", True),
            _f("complainant_org", "Organisation", True),
            _f("complainant_contact", "Contact", True),
        ),
    ),

    "compound_scam_victim_affidavit": TemplateSpec(
        id="compound_scam_victim_affidavit",
        title="Compound-Scam (Sihanoukville / Bavet / Myawaddy / Bokeo) Victim Affidavit",
        jurisdiction="Cross-border (INTERPOL Project Storm coverage)",
        audience="Origin-country embassy + INTERPOL Project Storm + UNODC + IOM + destination law-enforcement",
        summary=(
            "Pre-filled victim-identification affidavit for the "
            "compound-trafficking + cyber-fraud / pig-butchering "
            "ecosystem in Sihanoukville Cambodia + Bavet Cambodia + "
            "Myawaddy Myanmar + Bokeo Laos. Cites Palermo Protocol "
            "Article 3 + ASEAN ACTIP Article 14(7) non-criminalisation "
            "+ destination-country trafficking-victim non-prosecution "
            "framework. Madlibs style -- 10 numbered sections covering "
            "recruitment, journey, control, forced criminal activity, "
            "abuse, escape, non-criminalisation request, indicators, "
            "service request, and evidence."
        ),
        body=_TEMPLATE_COMPOUND_SCAM_AFFIDAVIT_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("file_reference", "File reference", True),
            _f("worker_name", "Declarant anonymized ID", True, "people[0].label"),
            _f("country_of_citizenship", "Country of citizenship", True, "intelligence.country_of_origin"),
            _f("year_of_birth", "Year of birth", False),
            _f("native_language", "Native language", False),
            _f("origin_country_embassy_or_polo", "Origin-country embassy / POLO", True),
            _f("destination_country_law_enforcement", "Destination-country law enforcement", True),
            _f("recruitment_year", "Recruitment year", True),
            _f("recruitment_channel", "Recruitment channel (LinkedIn / Telegram / Facebook / etc.)", True),
            _f("recruiter_handle_or_anonymized", "Recruiter handle (anonymized)", True),
            _f("advertised_role", "Advertised role", True),
            _f("advertised_destination", "Advertised destination", True),
            _f("advertised_compensation", "Advertised monthly compensation", True),
            _f("recruiter_specific_promises", "Recruiter-specific promises", False),
            _f("departure_date", "Departure date", True),
            _f("visa_status_at_departure", "Visa status at departure", False),
            _f("travel_route", "Travel route", True),
            _f("arrival_location", "Arrival location", True),
            _f("handler_description", "Handler description", True),
            _f("compound_location_description", "Compound location description", True),
            _f("compound_physical_description", "Compound physical description", True),
            _f("forced_criminal_activity_type", "Forced criminal activity type (pig-butchering / phishing / etc.)", True),
            _f("daily_required_activity", "Daily required activity", True),
            _f("hours_per_day", "Hours per day", True),
            _f("days_per_week", "Days per week", True),
            _f("actual_compensation_at_compound", "Actual compensation at compound", True),
            _f("enforcement_mechanism", "Enforcement mechanism (violence / fine / debt)", True),
            _f("movement_restriction_details", "Movement restriction details", True),
            _f("document_retention_details", "Document retention details", True),
            _f("violence_details", "Violence / threats details", False),
            _f("debt_details", "Debt details", False),
            _f("isolation_details", "Isolation details", False),
            _f("sexual_abuse_details", "Sexual abuse details (if applicable)", False),
            _f("forced_fraud_details", "Forced fraud details (third-party victims)", True),
            _f("escape_date", "Escape date", True),
            _f("escape_circumstances", "Escape circumstances", True),
            _f("service_provider", "Current service provider", True),
            _f("destination_country_non_criminalisation_statute", "Destination-country non-criminalisation statute", True),
            _f("origin_country_law_enforcement", "Origin-country law enforcement", True),
            _f("available_evidence_list", "Available evidence list", True, "intelligence.evidence_edges"),
            _f("complainant_name", "Caseworker / consular officer name", True),
            _f("complainant_org", "Organisation", True),
            _f("complainant_contact", "Contact", True),
        ),
    ),

    "ca_sawp_complaint": TemplateSpec(
        id="ca_sawp_complaint",
        title="Canada SAWP Liaison Service + IRCC + ESDC Complaint",
        jurisdiction="Canada",
        audience="Liaison Service + ESDC Integrity Services + IRCC + Justicia for Migrant Workers",
        summary=(
            "Complaint against a Canadian farm employer (SAWP "
            "scheme) for unpaid wages, housing standards violations, "
            "health and safety concerns, anti-retaliation violations, "
            "or threat of non-recall. Aligns with SAWP MOU + IRPA + "
            "Canada Labour Code Part III + provincial ESA / OHSA."
        ),
        body=_TEMPLATE_CA_SAWP_BODY,
        fields=(
            _f("filed_date", "Filing date", True),
            _f("complainant_name", "Caseworker / Liaison Officer", True),
            _f("complainant_org", "NGO / organisation", True),
            _f("complainant_contact", "Contact", True),
            _f("worker_name", "Worker anonymized ID", True, "people[0].label"),
            _f("country_of_origin", "Country of origin", True, "intelligence.country_of_origin"),
            _f("sawp_year", "SAWP cohort year", True),
            _f("work_permit_no", "Work permit number", False),
            _f("sector", "Sector (horticulture / poultry / etc.)", True, "intelligence.sector"),
            _f("employer_name", "Farm employer name", True, "intelligence.employers[0]"),
            _f("province_region", "Province + region", True),
            _f("lmia_no", "Employer LMIA number", False),
            _f("liaison_officer_name", "Liaison officer (origin-country)", False),
            _f("origin_country_agency", "Origin-country counterpart", False),
            _f("unpaid_wages_cad", "Unpaid wages (CAD)", True),
            _f("hours_per_day_week", "Hours per day / week", False),
            _f("housing_concern", "Housing standards concern (describe)", False),
            _f("health_safety_concern", "Health and safety concern (describe)", False),
            _f("anti_retaliation_concern", "Anti-retaliation concern (describe)", False),
            _f("document_retention_yes_no", "Document retention (Y/N)", True),
            _f("excess_deductions", "Excess deductions (housing / loan / etc.)", False),
            _f("threat_no_recall_yes_no", "Threat of non-recall / blacklist (Y/N)", True),
            _f("incident_summary", "Case narrative", True, "intelligence.case_brief"),
            _f("ilo_indicators", "ILO indicators observed", False, "intelligence.ilo_indicators"),
            _f("evidence_list", "Evidence available", False, "intelligence.evidence_edges"),
            _f("relief_requested", "Relief requested", True),
        ),
    ),
    "recruitment_fee_refund_and_loan_void_demand": TemplateSpec(
        id="recruitment_fee_refund_and_loan_void_demand",
        title="Recruitment Fee Refund + Debt-Bondage Loan Void Demand",
        jurisdiction="Cross-border",
        audience="Recruitment agency / employer / linked lender",
        summary="Pre-filled demand to refund an unlawful recruitment fee (whatever its label), void the linked salary-advance loan as debt bondage, and cease wage deductions. Cites ILO C181 Art. 7, C029/P029, C095, and Palermo Art. 3(b).",
        body=_TEMPLATE_FEE_REFUND_LOAN_VOID_BODY,
        fields=(
            _f('filed_date', 'Filed date', True),
            _f('respondent_name', 'Respondent name', True, 'intelligence.employers[0]'),
            _f('respondent_address', 'Respondent address', False),
            _f('labour_authority', 'Labour authority', True),
            _f('embassy_polo', 'Embassy polo', True),
            _f('worker_name', 'Worker name', True, 'people[0].label'),
            _f('worker_nationality', 'Worker nationality', True, 'people[0].nationality'),
            _f('origin_country', 'Origin country', True),
            _f('destination_country', 'Destination country', True),
            _f('fee_amount', 'Fee amount', True),
            _f('fee_label', 'Fee label', True),
            _f('loan_amount', 'Loan amount', True),
            _f('deduction_amount', 'Deduction amount', False),
            _f('corridor_statute', 'Corridor statute', True),
            _f('response_days', 'Response days', False),
            _f('filer_name', 'Filer name', True),
            _f('filer_role', 'Filer role', False),
        ),
        relevance_indicators=("debt_bondage", "withholding_of_wages", "deception"),
    ),
    "contract_substitution_complaint": TemplateSpec(
        id="contract_substitution_complaint",
        title="Contract Substitution Complaint (origin-signed vs arrival)",
        jurisdiction="Cross-border",
        audience="Destination-country labour authority / tribunal",
        summary="Complaint that the destination employer substituted the origin-signed contract for worse terms on arrival -- the ILO deception indicator and a Palermo Art. 3 means. Seeks enforcement of the origin terms + the wage differential.",
        body=_TEMPLATE_CONTRACT_SUBSTITUTION_COMPLAINT_BODY,
        fields=(
            _f('filed_date', 'Filed date', True),
            _f('labour_tribunal', 'Labour tribunal', True),
            _f('embassy_polo', 'Embassy polo', True),
            _f('recruitment_agency', 'Recruitment agency', False, 'intelligence.agencies[0]'),
            _f('worker_name', 'Worker name', True, 'people[0].label'),
            _f('worker_nationality', 'Worker nationality', True, 'people[0].nationality'),
            _f('origin_country', 'Origin country', True),
            _f('destination_country', 'Destination country', True),
            _f('signing_date', 'Signing date', True),
            _f('origin_signed_terms', 'Origin signed terms', False),
            _f('origin_signed_wage', 'Origin signed wage', True),
            _f('arrival_date', 'Arrival date', True),
            _f('respondent_name', 'Respondent name', True, 'intelligence.employers[0]'),
            _f('arrival_substituted_wage', 'Arrival substituted wage', True),
            _f('arrival_worse_terms', 'Arrival worse terms', False),
            _f('document_control', 'Document control', False),
            _f('destination_statute', 'Destination statute', True),
            _f('filer_name', 'Filer name', True),
            _f('filer_role', 'Filer role', False),
        ),
        relevance_indicators=("deception", "contract_substitution", "abuse_of_vulnerability"),
    ),
}


# Track which templates came from the initial registry so
# clear_custom_templates() can roll back to the built-in set after
# tests. Custom templates registered via register_template() are not
# in this set.
_BUILTIN_TEMPLATE_IDS: frozenset[str] = frozenset(TEMPLATES_REGISTRY.keys())


def register_template(spec: TemplateSpec, *, overwrite: bool = False) -> None:
    """Add a custom template to the live registry.

    Refuses by default if ``spec.id`` already exists -- explicit
    ``overwrite=True`` is required to replace a built-in. This makes
    accidental drift loud: a tenant who adds a custom HK Labour
    Department complaint with different field wording must opt in
    to the overwrite.

    Templates added via this function are picked up automatically
    by ``register_template_routes(app)`` because the route handler
    reads ``TEMPLATES_REGISTRY`` at request time, not at registration.

    Raises ``ValueError`` on duplicate-without-overwrite or when
    ``spec`` is not a ``TemplateSpec``.
    """
    if not isinstance(spec, TemplateSpec):
        raise ValueError(
            f"register_template expects a TemplateSpec, got {type(spec).__name__}"
        )
    if spec.id in TEMPLATES_REGISTRY and not overwrite:
        raise ValueError(
            f"template id={spec.id!r} already registered (built-in or custom). "
            f"Pass overwrite=True to replace it."
        )
    TEMPLATES_REGISTRY[spec.id] = spec


def clear_custom_templates() -> int:
    """Roll the registry back to the built-in set. Returns the number
    of custom templates that were removed. Built-in templates are
    never touched. Useful for tests that register a temporary
    template and need to restore the default state."""
    custom_ids = [
        tid for tid in TEMPLATES_REGISTRY if tid not in _BUILTIN_TEMPLATE_IDS
    ]
    for tid in custom_ids:
        del TEMPLATES_REGISTRY[tid]
    return len(custom_ids)


def is_builtin_template(template_id: str) -> bool:
    """True if the template id was part of the initial registry
    (not added at runtime via register_template)."""
    return template_id in _BUILTIN_TEMPLATE_IDS


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
    # Scrub kernel paths, RUN_IDs, ZIP/JSONL filenames, synthetic case
    # folder names. The complaint template Gemma is about to draft is
    # NGO/regulator-facing — kernel staging metadata in the body would
    # be embarrassing and unprofessional.
    text = _clean_for_knowledge_fact(text)
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
    *,
    bundle_excerpt: Optional[str] = None,
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

    # Pass 1: deterministic source hints from the bundle. Bundle-derived
    # values are scrubbed because the process bundle may carry kernel
    # paths and synthetic case folder names that should never appear in
    # an NGO/regulator-facing complaint body.
    for field in template.fields:
        if field.source_hint:
            value = bundle_field_hint(bundle, field.source_hint)
            if value:
                filled[field.id] = _clean_for_knowledge_fact(str(value))
                provenance[field.id] = "bundle_hint"

    # Pass 2: manual fields override (caseworker has final say). Manual
    # entries are NOT scrubbed — the caseworker is authoritative and
    # may need to enter a literal path/ID for case tracking.
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
            shared_excerpt = (
                bundle_excerpt
                if bundle_excerpt is not None
                else bundle_excerpt_for_template(bundle)
            )
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
                f"CASE BUNDLE EXCERPT:\n{shared_excerpt}\n\n"
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
                        # Gemma occasionally echoes a path/ID from the
                        # bundle excerpt into its proposed value;
                        # scrub before writing into the complaint body.
                        filled[fid] = _clean_for_knowledge_fact(sval)
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


def gemma_fill_batch(
    templates: list[TemplateSpec],
    bundle: dict,
    manual_fields_by_id: dict,
    gemma_call: Optional[Callable[..., Any]] = None,
) -> dict:
    """Fill multiple templates while sharing one bundle excerpt.

    Each template still gets its own Gemma call through
    ``gemma_fill_template``. The expensive/sensitive bundle excerpt is
    computed once and passed into every fill so the batch has the same
    source context and tests can lock the reuse contract.
    """
    shared_excerpt = bundle_excerpt_for_template(bundle or {})
    drafts: list[dict] = []
    manual_by_id = manual_fields_by_id or {}
    for template in templates:
        manual = manual_by_id.get(template.id) or {}
        if not isinstance(manual, dict):
            manual = {}
        filled, meta = gemma_fill_template(
            template,
            bundle or {},
            manual,
            gemma_call=gemma_call,
            bundle_excerpt=shared_excerpt,
        )
        drafts.append({
            "template_id": template.id,
            "template": template.summary_payload(),
            "rendered": render_template(template.body, filled),
            "field_values": filled,
            "manual_fields": manual,
            "provenance": meta.get("per_field", {}),
            "used_gemma": meta.get("used_gemma", False),
            "gemma_error": meta.get("__gemma_error"),
            "noise_scrubbed_before_gemma": True,
        })
    return {
        "drafts": drafts,
        "shared_excerpt_chars": len(shared_excerpt),
    }


def dry_run_fill_template(template: TemplateSpec, bundle: dict) -> dict:
    """Preview the deterministic bundle-hint pass without Gemma.

    The response intentionally mirrors the provenance buckets used by
    ``gemma_fill_template`` so templates.html can color field cards
    before spending a model call.
    """
    field_sources: dict[str, str] = {}
    n_bundle_hits = 0
    for field in template.fields:
        value = (
            bundle_field_hint(bundle, field.source_hint)
            if field.source_hint else None
        )
        if value:
            field_sources[field.id] = "bundle_hint"
            n_bundle_hits += 1
        else:
            field_sources[field.id] = "missing"
    n_fields = len(template.fields)
    return {
        "field_sources": field_sources,
        "n_bundle_hits": n_bundle_hits,
        "n_missing": n_fields - n_bundle_hits,
        "n_optional": sum(1 for field in template.fields if not field.required),
        "n_required": sum(1 for field in template.fields if field.required),
    }


_FACT_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_FACT_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d[\d ()\-.]{7,}\d)(?!\w)"
)
_FACT_ID_RE = re.compile(
    r"\b(?:passport|hkid|id|license|licence)\s*(?:no\.?|number|#)?\s*"
    r"[:=-]?\s*[A-Z0-9][A-Z0-9\-]{4,}\b",
    re.I,
)


def _template_fact_text(value: Any, *, limit: int = 260) -> str:
    """Sanitize local fact-card text before the Templates page displays it."""
    text = _clean_for_knowledge_fact(str(value or ""))
    text = _FACT_EMAIL_RE.sub("[email redacted]", text)
    text = _FACT_PHONE_RE.sub("[phone redacted]", text)
    text = _FACT_ID_RE.sub("[identifier redacted]", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    head = text[:limit].rsplit(" ", 1)[0].strip()
    return head or text[:limit].strip()


def _template_amount_text(payment: Any) -> str:
    if not isinstance(payment, dict):
        return _template_fact_text(payment, limit=120)
    amount = payment.get("amount") or payment.get("value") or payment.get("total")
    currency = payment.get("currency") or payment.get("ccy") or ""
    kind = (
        payment.get("type") or payment.get("category")
        or payment.get("purpose") or "payment"
    )
    parts = [str(kind)]
    if amount not in (None, ""):
        parts.append(str(amount))
    if currency:
        parts.append(str(currency))
    return _template_fact_text(" ".join(parts), limit=140)


def _bundle_list(bundle: dict, key: str) -> list:
    intel = (bundle or {}).get("intelligence") or {}
    value = intel.get(key)
    if value is None:
        value = (bundle or {}).get(key)
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def extract_template_knowledge_facts(bundle: dict) -> list[dict]:
    """Return non-explosive fact candidates useful for complaint routing.

    This is deliberately a routing/review aid, not a public knowledge-object
    publisher. It summarizes indicators, payments, evidence edges, and a short
    sanitized case brief without returning people/entity lists.
    """
    bundle = bundle or {}
    intel = bundle.get("intelligence") or {}
    facts: list[dict] = []
    indicators = list(bundle_ilo_indicators(bundle))
    if indicators:
        facts.append({
            "fact_type": "ilo_indicator_set",
            "label": "ILO indicators observed",
            "statement": ", ".join(indicators),
            "source": "intelligence.ilo_indicators",
            "pii_status": "no_direct_identifiers",
        })
    case_brief = intel.get("case_brief")
    if case_brief:
        facts.append({
            "fact_type": "case_narrative_summary",
            "label": "Complaint narrative signal",
            "statement": _template_fact_text(case_brief, limit=320),
            "source": "intelligence.case_brief",
            "pii_status": "redacted_excerpt",
        })
    for idx, payment in enumerate(_bundle_list(bundle, "payments")[:5], start=1):
        statement = _template_amount_text(payment)
        if statement:
            facts.append({
                "fact_type": "payment_or_deduction",
                "label": f"Payment signal {idx}",
                "statement": statement,
                "source": "payments",
                "pii_status": "amount_only_or_redacted",
            })
    for idx, edge in enumerate(_bundle_list(bundle, "evidence_edges")[:6], start=1):
        if isinstance(edge, dict):
            raw = (
                edge.get("summary") or edge.get("text") or edge.get("label")
                or edge.get("evidence") or edge
            )
            indicator = edge.get("indicator") or edge.get("type")
        else:
            raw = edge
            indicator = ""
        statement = _template_fact_text(raw, limit=260)
        if statement:
            facts.append({
                "fact_type": "evidence_edge",
                "label": f"Evidence signal {idx}",
                "statement": statement,
                "source": "intelligence.evidence_edges",
                "indicator": _template_fact_text(indicator, limit=80),
                "pii_status": "redacted_excerpt",
            })
    return facts[:14]


def _sample_context_for_template(template: TemplateSpec) -> dict:
    haystack = " ".join([
        template.id,
        template.title,
        template.jurisdiction,
        template.audience,
        template.summary,
    ]).lower()
    context = {
        "origin": "source country",
        "destination": template.jurisdiction,
        "corridor": "SRC-DST",
        "sector": "migrant work",
        "worker": "W.A.",
        "employer": "Sample destination employer",
        "agency": "Sample sending agency",
        "amount": "USD 1200 equivalent",
    }
    if "hong kong" in haystack or "_hk" in haystack or "fdh" in haystack:
        context.update({
            "origin": "Philippines",
            "destination": "Hong Kong",
            "corridor": "PH-HK",
            "sector": "domestic work",
            "employer": "Sample household employer",
            "agency": "Sample HK employment agency",
            "amount": "HKD 9800",
        })
    elif "philippines" in haystack or "dmw" in haystack or "poea" in haystack:
        context.update({
            "origin": "Philippines",
            "destination": "Gulf destination",
            "corridor": "PH-GCC",
            "sector": "hospitality",
            "agency": "Sample Philippine recruitment agency",
            "amount": "PHP 78000",
        })
    elif "nepal" in haystack or "dofe" in haystack:
        context.update({
            "origin": "Nepal",
            "destination": "Malaysia",
            "corridor": "NP-MY",
            "sector": "security work",
            "agency": "Sample Nepali manpower agency",
            "amount": "NPR 180000",
        })
    elif "indonesia" in haystack or "bp2mi" in haystack:
        context.update({
            "origin": "Indonesia",
            "destination": "Taiwan",
            "corridor": "ID-TW",
            "sector": "factory work",
            "agency": "Sample P3MI placement agency",
            "amount": "IDR 22000000",
        })
    elif "bangladesh" in haystack or "bmet" in haystack:
        context.update({
            "origin": "Bangladesh",
            "destination": "Malaysia",
            "corridor": "BD-MY",
            "sector": "construction",
            "agency": "Sample BMET recruiting agent",
            "amount": "BDT 420000",
        })
    elif "vietnam" in haystack or "dolab" in haystack:
        context.update({
            "origin": "Vietnam",
            "destination": "Taiwan",
            "corridor": "VN-TW",
            "sector": "manufacturing",
            "agency": "Sample DOLAB licensed enterprise",
            "amount": "VND 65000000",
        })
    elif "united states" in haystack or "h-2a" in haystack:
        context.update({
            "origin": "Mexico",
            "destination": "United States",
            "corridor": "MX-US",
            "sector": "agriculture",
            "employer": "Sample farm employer",
            "agency": "Sample farm labor contractor",
            "amount": "USD 1850",
        })
    elif "iom" in haystack or "referral" in haystack:
        context.update({
            "origin": "Indonesia",
            "destination": "Malaysia",
            "corridor": "ID-MY",
            "sector": "domestic work",
            "amount": "USD 950 equivalent",
        })
    return context


def template_sample_bundle(template: TemplateSpec) -> dict:
    """Synthetic, downloadable example bundle for one template."""
    indicators = list(template_relevance_indicators(template))
    context = _sample_context_for_template(template)
    case_brief = (
        f"Synthetic example: an anonymized {context['origin']} worker in "
        f"{context['destination']} reports recruitment fees, salary deductions, "
        f"and document-control pressure connected to {context['sector']}. "
        f"The bundle is designed to exercise {template.title} and may also "
        "surface adjacent complaint or referral routes."
    )
    people = [
        {
            "label": context["worker"],
            "role": "worker",
            "pii_status": "synthetic_initials_only",
        },
        {
            "label": "C.W.",
            "role": "caseworker",
            "pii_status": "synthetic_initials_only",
        },
    ]
    entities = {
        "nationality": [context["origin"]],
        "employer": [context["employer"]],
        "agency": [context["agency"]],
        "address": [f"{context['destination']} worksite address withheld"],
        "destination_country": [context["destination"]],
        "origin_country": [context["origin"]],
        "sector": [context["sector"]],
    }
    payments = [
        {
            "type": "recruitment_fee_or_debt",
            "amount": context["amount"],
            "timing": "pre-departure and post-arrival",
            "source": "synthetic_sample",
        },
        {
            "type": "salary_deduction_or_wage_shortfall",
            "amount": "amount disputed",
            "timing": "first three months",
            "source": "synthetic_sample",
        },
    ]
    evidence_edges = [
        {
            "indicator": indicators[0] if indicators else "case_signal",
            "summary": (
                "Message and receipt excerpts indicate fees or deductions "
                "linked to continued placement."
            ),
            "source_ref": f"sample::{template.id}::fee",
        },
        {
            "indicator": (
                "passport_retention"
                if "passport_retention" in indicators
                else "document_control"
            ),
            "summary": (
                "Worker states identity documents or contract papers were "
                "controlled by the employer, agency, or broker."
            ),
            "source_ref": f"sample::{template.id}::documents",
        },
    ]
    intelligence = {
        "case_brief": case_brief,
        "summary": {
            "n_rows_total": 9,
            "n_people_detected": len(people),
            "n_typed_edges": len(evidence_edges),
        },
        "corridor": context["corridor"],
        "sector": context["sector"],
        "ilo_indicators": indicators,
        "people": people,
        "entities": entities,
        "payments": payments,
        "journey_points": [
            {"stage": "recruitment", "place": context["origin"]},
            {"stage": "employment", "place": context["destination"]},
        ],
        "evidence_edges": evidence_edges,
        "complaint_readiness": {
            "target_template_id": template.id,
            "reviewer_action": (
                "Use the recommendation step, inspect missing fields, then "
                "edit before download."
            ),
        },
    }
    bundle = {
        "schema_version": "duecare.template_sample_bundle.v1",
        "run_id": f"template_sample_{template.id}",
        "_meta": {
            "synthetic": True,
            "contains_real_pii": False,
            "target_template_id": template.id,
        },
        "config": {
            "source": "template_sample",
            "target_template": template.id,
            "recommended_template_ids": [template.id],
            "jurisdiction": template.jurisdiction,
        },
        "summary": intelligence["summary"],
        "people": people,
        "entities": entities,
        "payments": payments,
        "intelligence": intelligence,
    }
    bundle["knowledge_fact_candidates"] = extract_template_knowledge_facts(bundle)
    bundle["intelligence"]["knowledge_fact_candidates"] = bundle[
        "knowledge_fact_candidates"
    ]
    return bundle


def _gemma_recommendation_items(parsed: Any) -> list[dict]:
    if not isinstance(parsed, dict):
        return []
    raw = parsed.get("recommendations")
    items: list[dict] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                tid = item.get("template_id") or item.get("id")
                reason = item.get("reason") or item.get("rationale") or ""
                items.append({"template_id": tid, "reason": reason})
            elif isinstance(item, str):
                items.append({"template_id": item, "reason": ""})
    for key in ("template_ids", "templates", "complaint_template_ids"):
        raw_ids = parsed.get(key)
        if isinstance(raw_ids, str):
            raw_ids = [raw_ids]
        if isinstance(raw_ids, list):
            for tid in raw_ids:
                if isinstance(tid, dict):
                    items.append({
                        "template_id": tid.get("template_id") or tid.get("id"),
                        "reason": tid.get("reason") or tid.get("rationale") or "",
                    })
                else:
                    items.append({"template_id": tid, "reason": ""})
    tid = parsed.get("template_id")
    if tid:
        items.append({"template_id": tid, "reason": parsed.get("reason") or ""})
    return items


def recommend_templates_for_bundle(
    bundle: dict,
    *,
    gemma_call: Optional[Callable[..., Any]] = None,
    max_results: int = 8,
) -> dict:
    """Recommend complaint/referral templates from bundle facts.

    Deterministic indicator overlap is the floor. Gemma can add or promote
    templates, but invalid template IDs are ignored and deterministic matches
    are never pruned.
    """
    bundle = bundle or {}
    indicators = set(bundle_ilo_indicators(bundle))
    facts = extract_template_knowledge_facts(bundle)
    rows: dict[str, dict] = {}

    def add_template(
        template: TemplateSpec,
        *,
        source: str,
        score: int,
        reason: str,
    ) -> None:
        rel = set(template_relevance_indicators(template))
        matched = sorted(indicators.intersection(rel))
        existing = rows.get(template.id)
        if existing:
            existing["score"] = max(existing["score"], score)
            existing["source"] = (
                existing["source"] if existing["source"] == source else "both"
            )
            if reason and reason not in existing["reason"]:
                existing["reason"] = (existing["reason"] + " " + reason).strip()
            return
        rows[template.id] = {
            "template_id": template.id,
            "title": template.title,
            "jurisdiction": template.jurisdiction,
            "audience": template.audience,
            "score": score,
            "source": source,
            "matched_indicators": matched,
            "reason": _template_fact_text(reason, limit=220),
            "template": template.summary_payload(),
        }

    for spec in select_relevant_templates_for_bundle(bundle):
        matches = set(template_relevance_indicators(spec)).intersection(indicators)
        reason = (
            "Deterministic overlap with bundle indicators: "
            + ", ".join(sorted(matches))
        )
        add_template(
            spec,
            source="deterministic",
            score=70 + min(25, 5 * len(matches)),
            reason=reason,
        )

    used_gemma = False
    gemma_error: Optional[str] = None
    if gemma_call is not None:
        options = [
            {
                "template_id": t.id,
                "title": t.title,
                "jurisdiction": t.jurisdiction,
                "audience": t.audience,
                "summary": t.summary,
                "relevance_indicators": list(template_relevance_indicators(t)),
            }
            for t in TEMPLATES_REGISTRY.values()
        ]
        prompt = (
            "You are choosing appropriate complaint or referral templates for "
            "an anonymized migrant-worker case bundle. Use only template_id "
            "values from TEMPLATE OPTIONS. Do not invent facts. Recommend "
            "one to six templates, with a short reason for each. Return JSON "
            "only: {\"recommendations\":[{\"template_id\":\"...\","
            "\"reason\":\"...\"}]}.\n\n"
            f"CASE BUNDLE EXCERPT:\n{bundle_excerpt_for_template(bundle)}\n\n"
            "SANITIZED FACT CANDIDATES:\n"
            f"{json.dumps(facts, ensure_ascii=False)[:1800]}\n\n"
            "TEMPLATE OPTIONS:\n"
            f"{json.dumps(options, ensure_ascii=False)[:5200]}"
        )
        try:
            raw = gemma_call(prompt, max_new_tokens=900, temperature=0.2)
            used_gemma = True
            raw_text = raw if isinstance(raw, str) else json.dumps(raw, default=str)
            parsed = safe_json_extract(raw_text)
            for item in _gemma_recommendation_items(parsed):
                tid = str(item.get("template_id") or "").strip()
                spec = TEMPLATES_REGISTRY.get(tid)
                if spec is None:
                    continue
                add_template(
                    spec,
                    source="gemma",
                    score=92,
                    reason=str(item.get("reason") or "Gemma selected this route."),
                )
        except Exception as e:  # noqa: BLE001
            gemma_error = f"{type(e).__name__}: {str(e)[:120]}"

    if not rows:
        fallback = next(
            (
                spec for spec in TEMPLATES_REGISTRY.values()
                if "ngo" in spec.id.lower() or "ngo" in spec.title.lower()
            ),
            None,
        )
        if fallback is not None:
            add_template(
                fallback,
                source="fallback",
                score=40,
                reason=(
                    "No strong indicator overlap was found; start with the "
                    "generic intake pathway and add facts manually."
                ),
            )

    recommendations = sorted(
        rows.values(),
        key=lambda row: (-row["score"], row["title"].lower()),
    )[:max_results]
    return {
        "schema_version": "duecare.template.recommendations.v1",
        "used_gemma": used_gemma,
        "gemma_error": gemma_error,
        "bundle_indicators": sorted(indicators),
        "knowledge_fact_candidates": facts,
        "recommendations": recommendations,
    }


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
    from fastapi import Body
    from fastapi.responses import JSONResponse

    @app.get("/api/templates/list")
    def api_templates_list():
        """List all registered NGO complaint / referral templates."""
        return {
            "templates": [t.summary_payload() for t in TEMPLATES_REGISTRY.values()],
        }

    @app.get("/api/templates/sample-bundle/{template_id}")
    def api_templates_sample_bundle(template_id: str):
        """Return one synthetic, template-specific example bundle."""
        template = TEMPLATES_REGISTRY.get((template_id or "").strip())
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
        return template_sample_bundle(template)

    @app.post("/api/templates/recommend")
    def api_templates_recommend(body: dict = Body(...)):
        """Extract routing facts and recommend complaint/referral templates."""
        body = body or {}
        bundle = body.get("bundle") or {}
        use_gemma = parse_bool(body.get("use_gemma"), default=True)
        raw_max = body.get("max_results", 8)
        try:
            max_results = max(1, min(20, int(raw_max)))
        except Exception:
            max_results = 8
        gemma_call = (
            getattr(app.state, "gemma_call", None) if use_gemma else None
        )
        return recommend_templates_for_bundle(
            bundle,
            gemma_call=gemma_call,
            max_results=max_results,
        )

    @app.post("/api/templates/dry-run-fill")
    def api_templates_dry_run_fill(body: dict = Body(...)):
        """Run only the deterministic bundle-hint pass for a template."""
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
        return dry_run_fill_template(template, body.get("bundle") or {})

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
            # Provenance flag: bundle text fed into Gemma + any value
            # auto-filled from the bundle was passed through the shared
            # noise scrub so kernel run IDs, /kaggle/working/... paths,
            # ZIP/JSONL filenames, and synthetic case folder names
            # cannot leak into the final complaint body.
            "noise_scrubbed_before_gemma": True,
        }

    @app.post("/api/templates/fill-batch")
    def api_templates_fill_batch(body: dict = Body(...)):
        """Fill multiple templates from one case bundle.

        Additive route: /api/templates/fill remains unchanged. The
        batch route validates every requested template id up front,
        computes the bundle excerpt once, then runs the same
        gemma_fill_template primitive once per template.
        """
        body = body or {}
        raw_ids = body.get("template_ids") or []
        if isinstance(raw_ids, str):
            raw_ids = [x.strip() for x in raw_ids.split(",") if x.strip()]
        template_ids = [
            str(tid or "").strip()
            for tid in raw_ids
            if str(tid or "").strip()
        ]
        unknown = [
            tid for tid in template_ids
            if tid not in TEMPLATES_REGISTRY
        ]
        if unknown:
            return JSONResponse(
                {
                    "status": "unknown_template",
                    "message": (
                        f"No template registered for id={unknown[0]!r}. "
                        f"Call /api/templates/list for the available set."
                    ),
                    "available": list(TEMPLATES_REGISTRY.keys()),
                },
                status_code=404,
            )
        templates = [TEMPLATES_REGISTRY[tid] for tid in template_ids]
        bundle = body.get("bundle") or {}
        manual_fields = body.get("manual_fields") or {}
        if not isinstance(manual_fields, dict):
            manual_fields = {}
        use_gemma = parse_bool(body.get("use_gemma"), default=True)
        gemma_call = (
            getattr(app.state, "gemma_call", None) if use_gemma else None
        )
        return gemma_fill_batch(
            templates,
            bundle,
            manual_fields,
            gemma_call=gemma_call,
        )

    # -----------------------------------------------------------------
    # Draft persistence (saves rendered templates to a local
    # /kaggle/working/templates/drafts/ directory so reviewers can come
    # back to a draft across page reloads). The reviewer is responsible
    # for anonymizing before saving -- the page banner already says
    # this. Drafts are local only; no remote calls.
    # -----------------------------------------------------------------

    import hashlib as _hashlib
    import json as _json
    import pathlib as _pathlib
    import time as _time

    def _drafts_root() -> _pathlib.Path | None:
        candidates = [
            _pathlib.Path("/kaggle/working/templates/drafts"),
            _pathlib.Path(".duecare-template-drafts"),
        ]
        for root in candidates:
            try:
                root.mkdir(parents=True, exist_ok=True)
                return root
            except Exception:
                continue
        return None

    def _draft_id() -> str:
        ts = _time.strftime("%Y-%m-%dT%H-%M-%SZ", _time.gmtime())
        suffix = _hashlib.sha256(
            f"{ts}_{_time.time_ns()}".encode("utf-8")
        ).hexdigest()[:8]
        return f"draft_{ts}_{suffix}"

    def _safe_draft_id(draft_id: str) -> str | None:
        """Reject any draft_id that isn't a stable slug -- defense
        against ../traversal or absolute paths in the path
        parameter."""
        import re as _re_local
        if not draft_id or not _re_local.fullmatch(
            r"draft_[0-9A-Za-z_\-]{8,64}", draft_id
        ):
            return None
        return draft_id

    @app.post("/api/templates/drafts")
    def api_templates_drafts_save(body: dict = Body(...)):
        """Persist a rendered template draft locally so the reviewer
        can come back to it. Idempotent on identical content (a
        re-save replaces the existing file)."""
        body = body or {}
        template_id = (body.get("template_id") or "").strip()
        rendered = str(body.get("rendered") or "")
        template = TEMPLATES_REGISTRY.get(template_id)
        if template is None:
            return JSONResponse(
                {
                    "status": "unknown_template",
                    "message": (
                        f"No template registered for id={template_id!r}."
                    ),
                },
                status_code=404,
            )
        if not rendered.strip():
            return JSONResponse(
                {
                    "status": "empty_draft",
                    "message": "rendered must be a non-empty string.",
                },
                status_code=400,
            )
        root = _drafts_root()
        if root is None:
            return JSONResponse(
                {
                    "status": "no_writable_root",
                    "message": (
                        "Could not find a writable drafts directory; "
                        "/kaggle/working and .duecare-template-drafts "
                        "both unavailable."
                    ),
                },
                status_code=500,
            )
        draft_id = _draft_id()
        saved_at = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
        payload = {
            "schema_version": "duecare.template.draft.v1",
            "draft_id": draft_id,
            "template_id": template_id,
            "title": template.title,
            "saved_at": saved_at,
            "rendered": rendered,
            "field_values": body.get("field_values") or {},
            "manual_fields": body.get("manual_fields") or {},
            "run_id": str(body.get("run_id") or ""),
        }
        path = root / f"{draft_id}.json"
        path.write_text(
            _json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {
            "status": "saved",
            "draft_id": draft_id,
            "saved_at": saved_at,
            "path": str(path),
            "bytes": path.stat().st_size,
        }

    @app.get("/api/templates/drafts")
    def api_templates_drafts_list():
        """List every saved draft, newest first."""
        root = _drafts_root()
        if root is None:
            return {"drafts": [], "drafts_root": None}
        entries: list[dict] = []
        for p in sorted(root.glob("draft_*.json"), reverse=True):
            try:
                doc = _json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            entries.append({
                "draft_id": doc.get("draft_id"),
                "template_id": doc.get("template_id"),
                "title": doc.get("title"),
                "saved_at": doc.get("saved_at"),
                "run_id": doc.get("run_id"),
                "bytes": p.stat().st_size,
            })
        return {"drafts": entries, "drafts_root": str(root)}

    @app.get("/api/templates/drafts/{draft_id}")
    def api_templates_drafts_get(draft_id: str):
        """Retrieve a single saved draft by id."""
        sid = _safe_draft_id(draft_id)
        if sid is None:
            return JSONResponse(
                {"status": "bad_draft_id"}, status_code=400
            )
        root = _drafts_root()
        if root is None:
            return JSONResponse(
                {"status": "no_writable_root"}, status_code=500
            )
        path = root / f"{sid}.json"
        if not path.exists():
            return JSONResponse(
                {"status": "not_found", "draft_id": sid},
                status_code=404,
            )
        try:
            doc = _json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return JSONResponse(
                {
                    "status": "unreadable",
                    "draft_id": sid,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                status_code=500,
            )
        return doc

    @app.delete("/api/templates/drafts/{draft_id}")
    def api_templates_drafts_delete(draft_id: str):
        """Delete a saved draft."""
        sid = _safe_draft_id(draft_id)
        if sid is None:
            return JSONResponse(
                {"status": "bad_draft_id"}, status_code=400
            )
        root = _drafts_root()
        if root is None:
            return JSONResponse(
                {"status": "no_writable_root"}, status_code=500
            )
        path = root / f"{sid}.json"
        if not path.exists():
            return JSONResponse(
                {"status": "not_found", "draft_id": sid},
                status_code=404,
            )
        path.unlink()
        return {"status": "deleted", "draft_id": sid}


__all__ = [
    "TEMPLATES_REGISTRY",
    "TemplateField",
    "TemplateSpec",
    "bundle_ilo_indicators",
    "bundle_excerpt_for_template",
    "bundle_field_hint",
    "clear_custom_templates",
    "dry_run_fill_template",
    "extract_template_knowledge_facts",
    "gemma_fill_batch",
    "gemma_fill_template",
    "is_builtin_template",
    "parse_bool",
    "recommend_templates_for_bundle",
    "register_template",
    "register_template_routes",
    "render_template",
    "safe_json_extract",
    "select_relevant_templates_for_bundle",
    "template_sample_bundle",
    "template_relevance_indicators",
]
