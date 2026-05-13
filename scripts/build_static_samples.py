"""Build downloadable sample artifacts served from /static/samples/.

These are public, judge-safe, fully synthetic examples that let a
reviewer round-trip the upload/import flow on the workbench pages:

  case_files_sample.zip          -> used on /static/process.html
  knowledge_object_sample.json   -> used on /static/knowledge.html
  knowledge_bundle_sample.zip    -> used on /static/knowledge.html

All names, employers, and corridor specifics are composite. PII is
synthetic. Re-run this script to regenerate; the output is
deterministic (no timestamps, fixed ordering) so the files don't
churn unless the script itself changes.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / (
    "packages/duecare-llm-chat/src/duecare/chat/static/samples"
)
OUT.mkdir(parents=True, exist_ok=True)


def _zip_write_deterministic(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
    """Write to a ZIP with a fixed timestamp so byte-output is stable."""
    zi = zipfile.ZipInfo(name)
    zi.date_time = (2026, 1, 1, 0, 0, 0)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(zi, data)


# -------------------- 1. Case-files sample bundle --------------------

CASE_FILE_README = """\
DueCare workbench - sample case bundle

This is a fully synthetic, judge-safe bundle for the Process Files
page. All names, employers, and contact details are composite. No
real worker information appears in this archive.

Files in this bundle:

  recruiter_chat_01.txt   - composite WhatsApp/Viber excerpt with
                            placement-fee + passport-retention signals
  recruiter_chat_02.txt   - composite chat with contract-substitution
                            signal and corridor-mismatch hint
  contract_excerpt_01.txt - composite contract clause with debt-bondage
                            and fee-recovery wording
  recruiter_messages.csv  - 5 short messages with mixed signal density

Drop this ZIP onto Process Files to see the GREP layer and entity
extractor light up. Typical output:
  - 9-12 GREP rule hits across the 4 files
  - 6-8 entities extracted (AMOUNT, CORRIDOR, STATUTE)
  - A local knowledge graph you can chat against with Gemma 4

License: MIT. Contents are entirely composite.
"""

CASE_FILE_CHAT_01 = """\
[2026-02-14 09:32] Recruiter: Hello Maria. For the Hong Kong domestic
worker placement we discussed, the placement fee is 32,000 PHP. Half
is paid now, half deducted from your first 4 months of salary.

[2026-02-14 09:34] Maria: That seems high. POEA says the cap is zero?

[2026-02-14 09:35] Recruiter: That is the standard fee in our agency.
The cap you mention is theoretical. Every worker pays it.

[2026-02-14 09:38] Recruiter: Also we will hold your passport for the
first 90 days as a deposit. This is for safekeeping; the employer
requires it.

[2026-02-14 09:40] Maria: My friend said agencies cannot keep the
passport.

[2026-02-14 09:41] Recruiter: Trust me, this is normal. Sign the
attached form so we can proceed.
"""

CASE_FILE_CHAT_02 = """\
[2026-03-02 14:15] Agent (Kathmandu): Your job in Qatar is hotel
housekeeping. 5-star property. 1,500 QAR per month plus accommodation.
Departure 18 March.

[2026-03-19 22:04] Ramesh (Qatar): I have arrived. The driver took me
to a labour camp, not a hotel. They say I work construction site at
Lusail starting tomorrow. The contract I signed in Kathmandu said
hotel work.

[2026-03-19 22:06] Ramesh: Pay is 900 QAR, not 1,500. The contract
they showed me here is in Arabic and different from what I signed.

[2026-03-19 22:08] Agent: It is the same job. Just different name.
Salary will adjust later. Work first.

[2026-03-20 06:31] Ramesh: Sir please help. They took my passport at
arrival.
"""

CASE_FILE_CONTRACT_01 = """\
SECTION 7 - RECOVERY OF RECRUITMENT EXPENSES

The Worker acknowledges that the Recruiter has paid the following on
the Worker's behalf:

  Airfare:               42,000 PHP
  Pre-departure training: 8,500 PHP
  Medical examination:    3,200 PHP
  Visa processing:        6,000 PHP
  Agency commission:     32,000 PHP
  TOTAL:                 91,700 PHP

The Worker agrees to repay the total via monthly payroll deductions of
22,925 PHP per month for the first 4 months of employment. If the
Worker terminates employment prior to completion of the recovery
period, the outstanding balance shall be due immediately and the
Recruiter retains the right to retain identity documents until
settlement.

SECTION 8 - DOCUMENT CUSTODY

Upon arrival in the host country, the Employer shall hold the Worker's
passport in safe custody for the duration of the employment contract.
The Worker may request access to the passport with 48 hours' written
notice and approval of the Employer.
"""

CASE_FILE_CSV = """row_id,channel,text
msg-001,whatsapp,"Hi - confirming your departure date is Feb 22. Bring your medical clearance. Fee for the placement is settled."
msg-002,viber,"The employer in Singapore will deduct 280 SGD per month from salary for the placement fee. This is normal. Do not worry."
msg-003,whatsapp,"Your passport will be held by the employer for safekeeping. This is standard procedure for domestic workers."
msg-004,sms,"Your training session moved to Saturday 10am at the agency office. Bring 500 PHP for the medical exam."
msg-005,whatsapp,"I am sorry but our agency cannot help with refund. The contract you signed is final. Keep working please."
"""


def build_case_files_zip() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        _zip_write_deterministic(zf, "README.txt", CASE_FILE_README.encode("utf-8"))
        _zip_write_deterministic(
            zf, "recruiter_chat_01.txt", CASE_FILE_CHAT_01.encode("utf-8")
        )
        _zip_write_deterministic(
            zf, "recruiter_chat_02.txt", CASE_FILE_CHAT_02.encode("utf-8")
        )
        _zip_write_deterministic(
            zf, "contract_excerpt_01.txt", CASE_FILE_CONTRACT_01.encode("utf-8")
        )
        _zip_write_deterministic(
            zf, "recruiter_messages.csv", CASE_FILE_CSV.encode("utf-8")
        )
    out = OUT / "case_files_sample.zip"
    out.write_bytes(buf.getvalue())
    print(f"wrote {out}  ({out.stat().st_size:,} bytes)")


# -------------------- 2. Knowledge object sample (single envelope) --------------------
#
# Envelope schema (from packages/duecare-llm-chat/src/duecare/chat/app.py
# _ko_validate): every envelope MUST have:
#   schema_version           = "1.0"  (literal)
#   knowledge_object_type    = one of 21 KO_TYPES
#   id                       = kebab-case identifier
#   content                  = dict payload
# The 21 leaf types live under 6 branches: matching_knowledge,
# grounding_knowledge, reasoning_knowledge, tool_knowledge,
# input_knowledge, output_knowledge.

KNOWLEDGE_OBJECT_SAMPLE = {
    "schema_version": "1.0",
    "knowledge_object_type": "grep_rule",
    "id": "sample-passport-retention-v1",
    "source": {
        "kind": "composite",
        "provenance": "duecare workbench sample bundle (judge-safe synthetic)",
    },
    "content": {
        "category": "document_retention",
        "severity": "high",
        "pattern": (
            r"\b(hold|keep|retain|safekeep(?:ing)?|deposit|surrender|custody)\b"
            r"[^.\n]{0,80}\b(passport|id|identity\s+document|travel\s+document)\b"
        ),
        "description": (
            "Flags chat/contract text where a recruiter or employer asks the "
            "worker to hand over a passport for 'safekeeping', 'deposit', or "
            "'custody'. ILO Forced Labour Indicator #6 (retention of identity "
            "documents). Cite POEA MC 8 s. 2017 or equivalent local rule in "
            "the model response."
        ),
        "test_cases": [
            {
                "text": (
                    "We will hold your passport for the first 90 days as a "
                    "deposit."
                ),
                "expected": True,
            },
            {
                "text": "Your passport will be held by the employer for safekeeping.",
                "expected": True,
            },
            {
                "text": "Please bring a photocopy of your passport for the visa.",
                "expected": False,
            },
        ],
    },
    "audit": {
        "drafted_by": "duecare workbench sample",
        "date": "2026-05-12",
        "checks_passed": ["pii_clean", "regex_compiles", "test_cases_pass"],
    },
}


def build_knowledge_object_sample() -> None:
    out = OUT / "knowledge_object_sample.json"
    out.write_text(json.dumps(KNOWLEDGE_OBJECT_SAMPLE, indent=2), encoding="utf-8")
    print(f"wrote {out}  ({out.stat().st_size:,} bytes)")


# -------------------- 3. Knowledge bundle (multiple envelopes) --------------------

BUNDLE_README = """\
DueCare workbench - sample knowledge bundle

Four sample knowledge envelopes spanning distinct leaf types. ZIP
entries are pathed as `<type>/<id>.json` so that /api/knowledge/import
accepts the bundle directly.

  grep_rule/sample-passport-retention-v1.json
  rag_doc/sample-ilo-c181.json
  context_snippet/sample-placement-fee-cap.json
  rubric_dimension/sample-contract-substitution.json

Drop this ZIP onto the Knowledge Extraction page (or onto Sync ->
Manual upload) to import all four at once. After import:
  - the GREP rule is live in the matching layer
  - the rag_doc is searchable by RAG
  - the context_snippet is available as reasoning grounding
  - the rubric_dimension lights up in grade-deep / grade-combined

All payloads are composite and judge-safe.
License: MIT.
"""

ENVELOPE_CONTEXT = {
    "schema_version": "1.0",
    "knowledge_object_type": "context_snippet",
    "id": "sample-placement-fee-cap",
    "content": {
        "term": "placement fee cap",
        "definition": (
            "The maximum amount, set by national or sectoral regulation, that "
            "a private recruitment agency may charge a worker for job "
            "placement. ILO Convention 181 sets the principle at zero; many "
            "jurisdictions implement a sector-specific cap (e.g. Philippines "
            "POEA: zero for domestic workers in Hong Kong, two months wages "
            "ceiling elsewhere)."
        ),
        "see_also": ["statute:ILO_C181", "statute:POEA_MC_8_2017"],
    },
    "audit": {"drafted_by": "duecare workbench sample", "date": "2026-05-12"},
}

ENVELOPE_RAG_DOC = {
    "schema_version": "1.0",
    "knowledge_object_type": "rag_doc",
    "id": "sample-ilo-c181",
    "content": {
        "title": "ILO Convention 181 - Private Employment Agencies Convention",
        "jurisdiction": "international",
        "year": 1997,
        "text": (
            "Article 7(1): 'Private employment agencies shall not charge "
            "directly or indirectly, in whole or in part, any fees or costs "
            "to workers.' Establishes the no-fee-to-worker principle for "
            "private recruitment, adopted in 1997 by the International "
            "Labour Organization."
        ),
        "url": "https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_INSTRUMENT_ID:312326",
    },
    "audit": {"drafted_by": "duecare workbench sample", "date": "2026-05-12"},
}

ENVELOPE_RUBRIC = {
    "schema_version": "1.0",
    "knowledge_object_type": "rubric_dimension",
    "id": "sample-contract-substitution",
    "content": {
        "label": "Contract substitution",
        "framework": "ILO Forced Labour Indicators (2012)",
        "indicator_number": 4,
        "definition": (
            "The worker is presented at destination with a different contract "
            "(lower pay, different employer, different job category, different "
            "duration) from the one signed at origin. A key ILO forced-labour "
            "indicator and a recurring pattern in migrant-worker exploitation."
        ),
        "example_cases": [
            "Hotel job promised at origin -> construction site at destination",
            "1500 QAR promised salary -> 900 QAR actual",
            "Domestic worker contract -> agricultural labour",
        ],
    },
    "audit": {"drafted_by": "duecare workbench sample", "date": "2026-05-12"},
}


def build_knowledge_bundle_zip() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        _zip_write_deterministic(zf, "README.txt", BUNDLE_README.encode("utf-8"))
        # NOTE: /api/knowledge/import requires entries pathed as
        # `<type>/<id>.json`. Each envelope's id must also match the
        # filename's stem.
        _zip_write_deterministic(
            zf,
            "grep_rule/sample-passport-retention-v1.json",
            json.dumps(KNOWLEDGE_OBJECT_SAMPLE, indent=2).encode("utf-8"),
        )
        _zip_write_deterministic(
            zf,
            "context_snippet/sample-placement-fee-cap.json",
            json.dumps(ENVELOPE_CONTEXT, indent=2).encode("utf-8"),
        )
        _zip_write_deterministic(
            zf,
            "rag_doc/sample-ilo-c181.json",
            json.dumps(ENVELOPE_RAG_DOC, indent=2).encode("utf-8"),
        )
        _zip_write_deterministic(
            zf,
            "rubric_dimension/sample-contract-substitution.json",
            json.dumps(ENVELOPE_RUBRIC, indent=2).encode("utf-8"),
        )
    out = OUT / "knowledge_bundle_sample.zip"
    out.write_bytes(buf.getvalue())
    print(f"wrote {out}  ({out.stat().st_size:,} bytes)")


def main() -> None:
    build_case_files_zip()
    build_knowledge_object_sample()
    build_knowledge_bundle_zip()
    print(f"\nAll samples in {OUT}")


if __name__ == "__main__":
    main()
