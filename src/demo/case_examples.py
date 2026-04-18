"""Built-in migration case bundle examples for the DueCare demo."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import CaseExampleSummary, MigrationCaseRequest


_CASE_EXAMPLES: dict[str, dict[str, Any]] = {
    "employment_agency_case": {
        "title": "Employment agency misconduct",
        "summary": "Agency receipts, recruiter pressure, and contract clauses showing worker-paid fees and passport control.",
        "case_categories": [
            "employment_agency_misconduct",
            "worker_fee_overcharge",
            "document_retention",
        ],
        "request": {
            "case_id": "case-agency-001",
            "corridor": "PH_HK",
            "documents": [
                {
                    "document_id": "agency-01",
                    "title": "Atlas recruitment receipt",
                    "context": "receipt",
                    "captured_at": "2026-01-05",
                    "text": (
                        "Atlas Recruitment Services official receipt. Worker paid placement fee 85000 PHP "
                        "plus documentation charge 12000 PHP for Hong Kong deployment."
                    ),
                },
                {
                    "document_id": "agency-02",
                    "title": "Recruiter chat pressure",
                    "context": "chat",
                    "captured_at": "2026-01-08",
                    "text": (
                        "Atlas recruiter message: pay the remaining balance today or deployment is cancelled. "
                        "We will keep your passport with the agency until the account is settled."
                    ),
                },
                {
                    "document_id": "agency-03",
                    "title": "Agency-side contract notice",
                    "context": "agency_record",
                    "captured_at": "2026-01-12",
                    "text": (
                        "North Harbor Manpower Services memo. Salary deductions of HKD 2500 per month will "
                        "continue for seven months to clear training and processing charges."
                    ),
                },
            ],
        },
    },
    "overcharging_case": {
        "title": "Layered overcharging and deductions",
        "summary": "Multiple recruitment charges split across receipts, ledgers, and worker statements.",
        "case_categories": [
            "worker_fee_overcharge",
            "employment_agency_misconduct",
        ],
        "request": {
            "case_id": "case-overcharge-001",
            "corridor": "PH_SA",
            "documents": [
                {
                    "document_id": "overcharge-01",
                    "title": "Recruitment fee ledger",
                    "context": "receipt",
                    "captured_at": "2026-02-02",
                    "text": (
                        "NorthBridge Manpower fee ledger: placement fee 25000 PHP, medical fee 9000 PHP, "
                        "airport assistance 6000 PHP, documentation fee 15000 PHP, insurance processing 4000 PHP."
                    ),
                },
                {
                    "document_id": "overcharge-02",
                    "title": "Salary deduction schedule",
                    "context": "contract",
                    "captured_at": "2026-02-10",
                    "text": (
                        "Worker agrees that payroll deduction of 1800 SAR will be collected for eight months "
                        "to recover agency charges and predeparture services."
                    ),
                },
                {
                    "document_id": "overcharge-03",
                    "title": "Worker statement on hidden fees",
                    "context": "narrative",
                    "captured_at": "2026-02-12",
                    "text": (
                        "Worker statement: the agency said the original price was zero-fee, then added new "
                        "processing and service charges each week before departure."
                    ),
                },
            ],
        },
    },
    "medical_clinic_case": {
        "title": "Medical clinic fee abuse",
        "summary": "Clinic invoice and recruiter instructions that route recruitment costs through mandatory medical exams.",
        "case_categories": [
            "medical_clinic_fee_abuse",
            "worker_fee_overcharge",
        ],
        "request": {
            "case_id": "case-medical-001",
            "corridor": "PH_SG",
            "documents": [
                {
                    "document_id": "medical-01",
                    "title": "Clinic invoice",
                    "context": "medical_record",
                    "captured_at": "2026-03-04",
                    "text": (
                        "Harborview Medical Clinic invoice for pre-employment exam, x-ray package, fit-to-work "
                        "certificate, and repeat laboratory screening. Total due from worker: 14500 PHP."
                    ),
                },
                {
                    "document_id": "medical-02",
                    "title": "Agency instruction message",
                    "context": "chat",
                    "captured_at": "2026-03-05",
                    "text": (
                        "Recruiter message: use Harborview Medical Clinic only. No medical result will be released "
                        "until you pay the full clinic fee and extra laboratory charge."
                    ),
                },
                {
                    "document_id": "medical-03",
                    "title": "Worker interview note",
                    "context": "narrative",
                    "captured_at": "2026-03-08",
                    "text": (
                        "Worker said the agency sent her back twice for new tests and each visit added another "
                        "medical fee before deployment could continue."
                    ),
                },
            ],
        },
    },
    "money_lender_case": {
        "title": "Money lender debt pressure",
        "summary": "Loan documents and collection messages showing high-interest debt tied to migration and payroll deductions.",
        "case_categories": [
            "money_lender_debt_pressure",
            "worker_fee_overcharge",
        ],
        "request": {
            "case_id": "case-lender-001",
            "corridor": "PH_HK",
            "documents": [
                {
                    "document_id": "lender-01",
                    "title": "Promissory note",
                    "context": "debt_note",
                    "captured_at": "2026-04-01",
                    "text": (
                        "Golden Bridge Lending Corporation promissory note. Principal 70000 PHP, annual interest 68 percent, "
                        "repayment through salary deductions once the worker arrives in Hong Kong."
                    ),
                },
                {
                    "document_id": "lender-02",
                    "title": "Collection chat",
                    "context": "chat",
                    "captured_at": "2026-04-06",
                    "text": (
                        "Lender collection message: if you miss two deductions we will report you to the agency and employer. "
                        "Your passport release and deployment clearance will stop until the loan is repaid."
                    ),
                },
                {
                    "document_id": "lender-03",
                    "title": "Payroll deduction advice",
                    "context": "document",
                    "captured_at": "2026-04-09",
                    "text": (
                        "Payroll collection advice showing monthly deductions from wages to Golden Bridge Lending for debt repayment, "
                        "interest, and collection fees."
                    ),
                },
            ],
        },
    },
    "legal_packet_case": {
        "title": "NGO legal packet and interrogatory prep",
        "summary": "Interview notes, police correspondence, written questions, employer response, and receipts assembled into an answer-ready legal intake packet.",
        "case_categories": [
            "employment_agency_misconduct",
            "worker_fee_overcharge",
            "document_retention",
        ],
        "request": {
            "case_id": "case-legal-001",
            "corridor": "PH_HK",
            "documents": [
                {
                    "document_id": "legal-01",
                    "title": "Worker interview summary",
                    "context": "narrative",
                    "captured_at": "2026-05-01",
                    "text": (
                        "Interview narrative. Worker says Bright Harbor Recruitment promised a zero-fee Hong Kong caregiving job, then demanded 92000 PHP in placement, medical, and processing charges. "
                        "The recruiter said the passport would stay with the agency office until the balance was cleared."
                    ),
                },
                {
                    "document_id": "legal-02",
                    "title": "Police report acknowledgement",
                    "context": "government_letter",
                    "captured_at": "2026-05-06",
                    "text": (
                        "Police report acknowledgement. The reporting worker states that Bright Harbor Recruitment collected 92000 PHP before departure and refused to return the passport when the worker asked to cancel deployment. "
                        "The report requests receipts, contract copies, and recruiter messages."
                    ),
                },
                {
                    "document_id": "legal-03",
                    "title": "Written interrogatory template",
                    "context": "legal_intake",
                    "captured_at": "2026-05-08",
                    "text": (
                        "Written interrogatory template for migrant worker intake. Identify the recruiter and agency, list all fees paid, describe who held the passport, state the dates of payment and contract signing, and identify every supporting receipt, chat export, employer letter, and police report."
                    ),
                },
                {
                    "document_id": "legal-04",
                    "title": "Employer response letter",
                    "context": "government_letter",
                    "captured_at": "2026-05-10",
                    "text": (
                        "Employer letter to labor office. The agency advised that salary deductions would continue after arrival to recover recruitment and medical costs, and that the passport was still being held by the agency pending account clearance."
                    ),
                },
                {
                    "document_id": "legal-05",
                    "title": "Agency official receipt",
                    "context": "receipt",
                    "captured_at": "2026-05-02",
                    "text": (
                        "Official receipt from Bright Harbor Recruitment Services. Worker paid 65000 PHP placement fee, 17000 PHP medical fee, and 10000 PHP processing charge for Hong Kong deployment."
                    ),
                },
            ],
        },
    },
}


def list_case_examples() -> list[CaseExampleSummary]:
    """Return metadata for bundled case examples."""
    items: list[CaseExampleSummary] = []
    for example_id, payload in _CASE_EXAMPLES.items():
        request = payload["request"]
        items.append(
            CaseExampleSummary(
                id=example_id,
                title=str(payload["title"]),
                summary=str(payload.get("summary", "")),
                corridor=str(request.get("corridor", "")),
                document_count=len(request.get("documents", [])),
                case_categories=list(payload.get("case_categories", [])),
            )
        )
    return items


def get_case_example(example_id: str) -> MigrationCaseRequest:
    """Return one bundled migration-case request by ID."""
    try:
        payload = deepcopy(_CASE_EXAMPLES[example_id]["request"])
    except KeyError as exc:
        raise KeyError(example_id) from exc
    return MigrationCaseRequest(**payload)
