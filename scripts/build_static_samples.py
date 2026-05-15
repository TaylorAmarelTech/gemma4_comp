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
import html
import textwrap
import zipfile
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover - build host may lack Pillow
    Image = ImageDraw = ImageFont = None

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


# Section 1: Case-files sample bundle

CASE_FILE_README = """\
DueCare workbench - sample case bundle

This is a fully synthetic, judge-safe bundle for the Bulk File Review
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

Drop this ZIP onto Bulk File Review to see the GREP layer and entity
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


_SAMPLE_NAMES = [
    "Ana Cruz", "Maria Santos", "Liza Reyes", "Joan Garcia", "Rhea Mendoza",
    "Celia Ramos", "Nina Flores", "Grace Bautista", "Ivy Aquino", "Mila Torres",
    "Kara dela Cruz", "Sofia Navarro", "Elena Morales", "Tina Lim", "Aiza Perez",
    "Mira Castillo", "Dina Lopez", "Jessa Villanueva", "Ruby Tan", "Lea Domingo",
    "Maya Ong", "Clara Sy", "Bianca Romero", "Nora Valdez", "Ella Chua",
    "Faye Aquino", "Gina Bautista", "Hazel Ramos", "Iris Flores", "Joy Mendoza",
]

_PH_ORIGINS = [
    "Manila", "Cebu", "Davao", "Iloilo", "Quezon City", "Makati",
]

_HK_AREAS = [
    "Central", "Mong Kok", "Causeway Bay", "Sha Tin", "Kowloon", "Wan Chai",
    "Tsuen Wan", "Yuen Long", "Tuen Mun",
]


def _safe_folder(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text).strip("_")


def _draw_text_image(lines: Iterable[str], *, title: str, size=(760, 980),
                     bg=(250, 249, 244), ink=(14, 17, 22)) -> bytes:
    if Image is None:
        # Minimal valid PNG fallback. The handler only needs a media asset;
        # the tracked ZIP is normally generated with Pillow available.
        import struct
        import zlib
        width, height = 8, 8
        raw = b"".join(b"\x00" + bytes([240, 240, 230]) * width for _ in range(height))
        def chunk(kind: bytes, data: bytes) -> bytes:
            crc = zlib.crc32(kind + data) & 0xFFFFFFFF
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b"")
        )
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        small = ImageFont.truetype("arial.ttf", 20)
        mono = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font = small = mono = ImageFont.load_default()
    draw.rectangle([24, 22, size[0] - 24, 78], fill=(239, 237, 228), outline=(210, 203, 184))
    draw.text((42, 38), title, font=font, fill=ink)
    y = 112
    for raw in lines:
        line = str(raw)
        draw.text((44, y), line[:88], font=mono if ":" in line else small, fill=ink)
        y += 34
        if y > size[1] - 60:
            break
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _draw_document_photo(lines: Iterable[str], *, title: str) -> bytes:
    if Image is None:
        return _draw_text_image(lines, title=title)
    img = Image.new("RGB", (900, 1100), (220, 220, 210))
    draw = ImageDraw.Draw(img)
    draw.polygon([(120, 80), (780, 42), (824, 990), (84, 1040)], fill=(255, 255, 250), outline=(165, 160, 145))
    try:
        font = ImageFont.truetype("arial.ttf", 28)
        body = ImageFont.truetype("arial.ttf", 21)
    except Exception:
        font = body = ImageFont.load_default()
    draw.text((154, 118), title, font=font, fill=(20, 24, 30))
    y = 180
    for raw in lines:
        draw.text((154, y), str(raw)[:78], font=body, fill=(20, 24, 30))
        y += 36
        if y > 920:
            break
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=86)
    return buf.getvalue()


def _draw_messenger_screenshot(case_id: str, name: str, agency: str, amount: int, deduction: int) -> bytes:
    """Create a synthetic Messenger-style screenshot for media review demos."""
    lines = [
        f"{agency}: Your PH-HK file is ready.",
        f"{agency}: Training, medical, and processing total PHP {amount}.",
        f"{name}: Can this be deducted after I arrive in Hong Kong?",
        f"{agency}: Yes. Employer deducts HKD {deduction} monthly.",
        f"{agency}: Passport stays with employer until balance is cleared.",
        f"{name}: I thought Hong Kong placement should be zero fee.",
    ]
    if Image is None:
        return _draw_text_image(lines, title="Synthetic Facebook Messenger screenshot")

    img = Image.new("RGB", (900, 1280), (244, 245, 248))
    draw = ImageDraw.Draw(img)
    try:
        header = ImageFont.truetype("arial.ttf", 32)
        body = ImageFont.truetype("arial.ttf", 25)
        small = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        header = body = small = ImageFont.load_default()

    draw.rectangle([0, 0, 900, 112], fill=(0, 132, 255))
    draw.ellipse([34, 26, 86, 78], fill=(235, 244, 255))
    draw.text((108, 32), "Pearl Bridge Recruiter", font=header, fill=(255, 255, 255))
    draw.text((108, 72), f"Messenger thread | {case_id}", font=small, fill=(223, 239, 255))
    y = 150
    for idx, line in enumerate(lines):
        incoming = idx in {0, 1, 3, 4}
        wrapped = textwrap.wrap(line, width=42)
        bubble_h = max(54, 34 * len(wrapped) + 24)
        if incoming:
            x1, x2, fill, ink = 46, 650, (255, 255, 255), (28, 33, 40)
        else:
            x1, x2, fill, ink = 250, 854, (0, 132, 255), (255, 255, 255)
        draw.rounded_rectangle([x1, y, x2, y + bubble_h], radius=26, fill=fill, outline=(224, 226, 232))
        ty = y + 13
        for part in wrapped:
            draw.text((x1 + 24, ty), part, font=body, fill=ink)
            ty += 33
        y += bubble_h + 22
    draw.text((46, 1218), "Synthetic screenshot. No real account, person, or message.", font=small, fill=(98, 104, 116))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _draw_receipt_photo(case_id: str, name: str, agency: str, amount: int) -> bytes:
    if Image is None:
        return _draw_document_photo(
            [
                f"CASE: {case_id}",
                f"WORKER: {name}",
                f"AGENCY: {agency}",
                f"TOTAL: PHP {amount}",
                "NOTE: repayment after arrival",
            ],
            title="Synthetic receipt photo",
        )
    img = Image.new("RGB", (900, 1200), (206, 209, 201))
    draw = ImageDraw.Draw(img)
    draw.polygon([(190, 80), (725, 48), (792, 1056), (142, 1110)], fill=(255, 255, 246), outline=(164, 160, 142))
    try:
        title_font = ImageFont.truetype("arial.ttf", 30)
        body = ImageFont.truetype("arial.ttf", 23)
        small = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        title_font = body = small = ImageFont.load_default()
    y = 130
    rows = [
        "PEARL BRIDGE TRAINING CENTER",
        "OFFICIAL RECEIPT - SYNTHETIC",
        f"Case: {case_id}",
        f"Worker: {name}",
        f"Agency: {agency}",
        "Item: pre-departure training",
        "Item: medical clearance",
        "Item: processing package",
        f"TOTAL PAID: PHP {amount}",
        "Payment channel: cash / e-wallet",
        "Balance recovered after arrival",
        "Collection method: salary deduction",
    ]
    for idx, row in enumerate(rows):
        font = title_font if idx == 0 else body
        draw.text((220, y), row[:54], font=font, fill=(22, 24, 28))
        y += 48 if idx < 2 else 42
    draw.rectangle([250, 780, 430, 960], outline=(20, 24, 28), width=3)
    for gx in range(5):
        for gy in range(5):
            if (gx * 2 + gy + amount) % 3:
                draw.rectangle([265 + gx * 30, 795 + gy * 30, 284 + gx * 30, 814 + gy * 30], fill=(20, 24, 28))
    draw.text((460, 820), "QR / e-wallet", font=small, fill=(70, 74, 82))
    draw.text((460, 850), "placeholder", font=small, fill=(70, 74, 82))
    draw.text((210, 1038), "Synthetic receipt photo. Not real evidence.", font=small, fill=(95, 100, 108))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=86)
    return buf.getvalue()


def _docx_bytes(title: str, paragraphs: Iterable[str]) -> bytes:
    """Build a minimal DOCX with deterministic ZIP metadata."""
    body = []
    for paragraph in [title, *list(paragraphs)]:
        escaped = html.escape(str(paragraph), quote=True)
        body.append(f"<w:p><w:r><w:t>{escaped}</w:t></w:r></w:p>")
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(body)}<w:sectPr/></w:body>"
        "</w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        _zip_write_deterministic(zf, "[Content_Types].xml", content_types.encode("utf-8"))
        _zip_write_deterministic(zf, "_rels/.rels", rels.encode("utf-8"))
        _zip_write_deterministic(zf, "word/document.xml", document.encode("utf-8"))
    return buf.getvalue()


def _xlsx_bytes(rows: list[list[str]]) -> bytes:
    """Build a tiny XLSX payment schedule with inline string cells."""
    def col_name(idx: int) -> str:
        name = ""
        while idx:
            idx, rem = divmod(idx - 1, 26)
            name = chr(65 + rem) + name
        return name

    sheet_rows: list[str] = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        for c_idx, value in enumerate(row, start=1):
            ref = f"{col_name(c_idx)}{r_idx}"
            escaped = html.escape(str(value), quote=True)
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escaped}</t></is></c>')
        sheet_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        '</worksheet>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Payment schedule" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        _zip_write_deterministic(zf, "[Content_Types].xml", content_types.encode("utf-8"))
        _zip_write_deterministic(zf, "_rels/.rels", rels.encode("utf-8"))
        _zip_write_deterministic(zf, "xl/workbook.xml", workbook.encode("utf-8"))
        _zip_write_deterministic(zf, "xl/_rels/workbook.xml.rels", wb_rels.encode("utf-8"))
        _zip_write_deterministic(zf, "xl/worksheets/sheet1.xml", worksheet.encode("utf-8"))
    return buf.getvalue()


def _scan_pdf_bytes(case_id: str, name: str, amount: int) -> bytes:
    # Intentionally scan-like: valid PDF wrapper with no extractable text
    # stream. The process harness queues it for OCR and Gemma 4 vision.
    body = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Contents 4 0 R >> endobj\n"
        "4 0 obj << /Length 0 >> stream\n\nendstream endobj\n"
        "%% synthetic scanned receipt placeholder\n"
        f"%% case={case_id}; worker={name}; visible_total_php={amount}\n"
        "%%EOF\n"
    )
    return body.encode("ascii")


def build_case_files_zip() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        readme = """\
DueCare Bulk File Review sample case bundle

Fully synthetic PH to HK case-folder bundle for the Gemma 4 Good demo.
It mirrors a realistic local intake folder: each person has text records,
CSV histories, and media-like evidence under a client-style folder path.

Included evidence types:
- recruiter chat transcripts
- complaints and police-style summaries
- ID-card records
- location, travel, and payment CSVs
- DOCX worker intake forms
- legacy DOC/RTF notes from an older case system
- XLSX payment schedules
- EML email handoff records
- PNG screenshots of recruiter chats
- Facebook Messenger-style PNG screenshots
- JPEG receipt photos
- JPEG document photos
- scan-like PDF receipts queued for OCR and Gemma 4 vision

All names, phones, agencies, employers, locations, and amounts are
fictional composites. Not real evidence.
"""
        _zip_write_deterministic(zf, "README.txt", readme.encode("utf-8"))
        for idx, name in enumerate(_SAMPLE_NAMES, start=1):
            case_id = f"DC-PH-HK-{idx:03d}"
            safe_name = _safe_folder(name)
            root = f"case_folders/{case_id}_{safe_name}"
            origin = _PH_ORIGINS[idx % len(_PH_ORIGINS)]
            area = _HK_AREAS[idx % len(_HK_AREAS)]
            agency = f"Pearl Bridge Manpower {idx % 5 + 1}"
            employer = f"Hong Kong Household {idx:03d}"
            base_fee = 35000 + (idx % 9) * 5000
            deduction = 1200 + (idx % 7) * 180
            phone = f"+63 917 000 {idx:04d}"
            chat = f"""\
case_id: {case_id}
worker_name: {name}
agency: {agency}
corridor: PH-HK
date: 2026-02-{(idx % 25) + 1:02d}
Recruiter: For Hong Kong placement, training and medical fees total PHP {base_fee}.
Recruiter: You can pay after arrival through salary deduction of HKD {deduction}.
Recruiter: Employer will keep passport for safekeeping until repayment is complete.
Worker: POEA says Hong Kong domestic worker placement should be zero fee.
Recruiter: This is not a placement fee, it is a processing loan and payment plan.
contact_phone: {phone}
"""
            complaint = f"""\
case_id: {case_id}
complainant: {name}
agency: {agency}
employer: {employer}
complaint date 2026-03-{(idx % 25) + 1:02d}
{name} reports PHP {base_fee} in training, medical, and processing charges.
The worker reports salary deduction in Hong Kong, passport retention, and pressure not to file a complaint.
Relevant references: POEA MC 14-2017; ILO C181; Hong Kong Employment Ordinance Cap. 57.
"""
            police = f"""\
case_id: {case_id}
incident report
subject: {name}
locations: {origin}, Hong Kong, {area}
reported indicators: passport retention, salary deduction, loan or debt, placement fee.
case officer note: preserve recruiter chat screenshots, receipts, remittance slips, and contract photos.
"""
            id_card = f"""\
case_id: {case_id}
worker_name: {name}
origin_city: {origin}
destination: Hong Kong
assigned_area: {area}
passport_status: employer safekeeping reported
synthetic_phone: {phone}
"""
            location_csv = (
                "case_id,date,location,event\n"
                f"{case_id},2026-02-01,{origin},pre-departure training\n"
                f"{case_id},2026-02-14,Manila,agency office\n"
                f"{case_id},2026-03-01,Hong Kong,arrival\n"
                f"{case_id},2026-03-04,{area},employer household\n"
            )
            payment_csv = (
                "case_id,date,amount,currency,purpose,recipient\n"
                f"{case_id},2026-02-10,{base_fee},PHP,training medical processing,{agency}\n"
                f"{case_id},2026-03-31,{deduction},HKD,salary deduction,{agency}\n"
                f"{case_id},2026-04-30,{deduction},HKD,salary deduction,{agency}\n"
            )
            travel_csv = (
                "case_id,date,from,to,carrier,note\n"
                f"{case_id},2026-02-28,{origin},Manila,bus,pre-departure\n"
                f"{case_id},2026-03-01,Manila,Hong Kong,flight,arrival for domestic work\n"
            )
            _zip_write_deterministic(zf, f"{root}/chats/person_{idx:03d}_messages.txt", chat.encode("utf-8"))
            _zip_write_deterministic(zf, f"{root}/complaints/person_{idx:03d}_complaint.txt", complaint.encode("utf-8"))
            _zip_write_deterministic(zf, f"{root}/police_reports/person_{idx:03d}_police_report.txt", police.encode("utf-8"))
            _zip_write_deterministic(zf, f"{root}/id_cards/person_{idx:03d}_id_card.txt", id_card.encode("utf-8"))
            _zip_write_deterministic(zf, f"{root}/location_history/person_{idx:03d}_locations.csv", location_csv.encode("utf-8"))
            _zip_write_deterministic(zf, f"{root}/payment_history/person_{idx:03d}_payments.csv", payment_csv.encode("utf-8"))
            _zip_write_deterministic(zf, f"{root}/travel_history/person_{idx:03d}_travel.csv", travel_csv.encode("utf-8"))
            if idx <= 18:
                img = _draw_text_image(
                    [
                        f"case_id: {case_id}",
                        f"worker: {name}",
                        f"agency: {agency}",
                        f"fee demand: PHP {base_fee}",
                        f"salary deduction: HKD {deduction}",
                        "passport held for safekeeping",
                        "payment due after arrival in Hong Kong",
                    ],
                    title="Synthetic recruiter chat screenshot",
                )
                _zip_write_deterministic(zf, f"{root}/screenshots/chat_fee_{idx:03d}.png", img)
            if idx <= 12:
                intake_docx = _docx_bytes(
                    f"Worker intake form - {case_id}",
                    [
                        f"case_id: {case_id}",
                        f"worker_name: {name}",
                        f"agency: {agency}",
                        f"origin: {origin}; destination: Hong Kong; assigned area: {area}",
                        f"reported fee: PHP {base_fee} for training, medical, and processing",
                        f"repayment plan: HKD {deduction} salary deduction after arrival",
                        "reported concern: passport held by employer for safekeeping",
                        "caseworker note: explain zero-fee rule, retaliation risk, and safe referral options.",
                    ],
                )
                _zip_write_deterministic(zf, f"{root}/intake_forms/worker_intake_{idx:03d}.docx", intake_docx)
            if idx <= 10:
                messenger = _draw_messenger_screenshot(case_id, name, agency, base_fee, deduction)
                _zip_write_deterministic(zf, f"{root}/facebook_messenger/thread_fee_{idx:03d}.png", messenger)
                receipt_photo = _draw_receipt_photo(case_id, name, agency, base_fee)
                _zip_write_deterministic(zf, f"{root}/receipt_photos/fee_receipt_{idx:03d}.jpeg", receipt_photo)
            if idx <= 12:
                photo = _draw_document_photo(
                    [
                        f"CASE: {case_id}",
                        f"WORKER: {name}",
                        f"AGENCY: {agency}",
                        f"TOTAL FEES: PHP {base_fee}",
                        "CLAUSE: repayment by salary deduction",
                        "DOCUMENT CUSTODY: passport held by employer",
                    ],
                    title="Synthetic contract photo",
                )
                _zip_write_deterministic(zf, f"{root}/document_photos/contract_photo_{idx:03d}.jpg", photo)
            if idx <= 10:
                _zip_write_deterministic(zf, f"{root}/scans/receipt_scan_{idx:03d}.pdf", _scan_pdf_bytes(case_id, name, base_fee))
            if idx <= 5:
                schedule = _xlsx_bytes([
                    ["case_id", "worker", "agency", "amount", "currency", "deduction", "note"],
                    [case_id, name, agency, str(base_fee), "PHP", f"HKD {deduction}", "salary deduction after arrival"],
                    [case_id, name, agency, "0", "PHP", "passport retained", "document control concern"],
                ])
                _zip_write_deterministic(zf, f"{root}/spreadsheets/payment_schedule_{idx:03d}.xlsx", schedule)
            if idx <= 4:
                legacy_doc = (
                    r"{\rtf1\ansi "
                    f"Legacy intake note for {case_id}. "
                    f"Worker {name} reports Pearl Bridge Manpower charged PHP {base_fee}. "
                    r"Passport retention and salary deduction reported. "
                    r"Caseworker should preserve screenshots and receipts.}"
                )
                _zip_write_deterministic(zf, f"{root}/legacy_case_system/case_note_{idx:03d}.doc", legacy_doc.encode("utf-8"))
                email = (
                    f"From: caseworker{idx}@example.invalid\n"
                    "To: supervisor@example.invalid\n"
                    f"Subject: Synthetic intake handoff {case_id}\n"
                    "Date: Fri, 15 May 2026 10:00:00 +0800\n\n"
                    f"Please review {case_id}. {name} reports PHP {base_fee} in recruitment-related fees, "
                    f"post-arrival salary deductions of HKD {deduction}, and passport safekeeping by employer. "
                    "Attachments in the local folder include chat screenshots, receipt photos, and payment schedule."
                )
                _zip_write_deterministic(zf, f"{root}/emails/intake_handoff_{idx:03d}.eml", email.encode("utf-8"))
            if idx <= 2:
                html_report = f"""\
<!doctype html>
<html><body>
<h1>Synthetic evidence index {case_id}</h1>
<p>Worker: {html.escape(name)}</p>
<p>Agency: {html.escape(agency)}</p>
<p>Fee pattern: PHP {base_fee} training, medical, and processing charges.</p>
<p>Risk signals: salary deduction, passport retention, possible fee camouflage.</p>
</body></html>
"""
                _zip_write_deterministic(zf, f"{root}/web_exports/evidence_index_{idx:03d}.html", html_report.encode("utf-8"))
    out = OUT / "case_files_sample.zip"
    out.write_bytes(buf.getvalue())
    print(f"wrote {out}  ({out.stat().st_size:,} bytes)")


# Section 2: Knowledge object sample (single envelope)
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


# Section 3: Knowledge bundle (multiple envelopes)

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
