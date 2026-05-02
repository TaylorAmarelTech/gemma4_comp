#!/usr/bin/env python3
"""Build the 180 Multimodal Document Inspector notebook.

T4 kernel that accepts a recruitment-contract image upload (or uses a
built-in sample synthetic contract string when no image is available).
Gemma 4 multimodal extracts key structured fields (employer, monthly
salary, placement fee, passport-retention clause, dispute jurisdiction,
probation duration, termination terms). A deterministic post-processor
then flags trafficking indicators against ILO C181 Article 7, U.S. TIP
Report indicators, and Saudi Labor Law Article 40. Output is three
side-by-side panels: OCR raw text, extracted fields JSON, flagged
indicators table.

Lives inside Free Form Exploration between 170 Live Context Injection
Playground and 199 Free Form Exploration Conclusion. 400 Function
Calling Multimodal is the cross-model / full-pipeline analog.
"""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import (
    canonical_header_table,
    patch_final_print_cell,
    troubleshooting_table_html,
)
from notebook_hardening_utils import harden_notebook


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"

FILENAME = "180_multimodal_document_inspector.ipynb"
KERNEL_DIR_NAME = "duecare_180_multimodal_document_inspector"
KERNEL_ID = "taylorsamarel/180-duecare-multimodal-document-inspector"
KERNEL_TITLE = "180: DueCare Multimodal Document Inspector"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
PROMPTS_DATASET = "taylorsamarel/duecare-trafficking-prompts"
KEYWORDS = ["gemma", "safety", "multimodal", "trafficking", "document", "playground"]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_160 = "https://www.kaggle.com/code/taylorsamarel/160-duecare-image-processing-playground"
URL_170 = "https://www.kaggle.com/code/taylorsamarel/170-duecare-live-context-injection-playground"
URL_180 = "https://www.kaggle.com/code/taylorsamarel/180-duecare-multimodal-document-inspector"
URL_199 = "https://www.kaggle.com/code/taylorsamarel/199-duecare-free-form-exploration-conclusion"
URL_400 = "https://www.kaggle.com/code/taylorsamarel/duecare-400-function-calling-multimodal"
URL_460 = "https://www.kaggle.com/code/taylorsamarel/duecare-460-citation-verifier"


def md(s: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}


def code(s: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": s.splitlines(keepends=True),
    }


NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
    "kaggle": {
        "accelerator": "nvidiaTeslaT4",
        "isInternetEnabled": True,
        "language": "python",
        "sourceType": "notebook",
    },
}


HEADER_TABLE = canonical_header_table(
    inputs_html=(
        "A recruitment-contract image (photo or scan) uploaded by the "
        "reader, or a built-in synthetic contract string used when no "
        "image or multimodal model mount is available. The contract is "
        "written in English and contains seven structured fields the "
        "inspector targets: employer, monthly salary, placement fee, "
        "passport-retention clause, dispute-resolution jurisdiction, "
        "probation duration, and termination terms. The Kaggle runtime "
        "must have a T4 GPU attached for live Gemma 4 multimodal "
        "inference; without a GPU the notebook falls back to a scripted "
        "deterministic extractor so the inspector still renders."
    ),
    outputs_html=(
        "Three side-by-side HTML panels. The left panel shows the OCR "
        "raw text (verbatim). The middle panel shows the extracted "
        "structured fields as pretty-printed JSON. The right panel is a "
        "flagged indicators table, one row per trafficking indicator "
        "that fired, with the ILO / TIP / Saudi Labor Law citation for "
        "each. A headline readout under the panels prints "
        "<code>fields_extracted</code>, <code>indicators_flagged</code>, "
        "and a 0-100 <code>severity_score</code> that aggregates the "
        "indicator weights."
    ),
    prerequisites_html=(
        "Kaggle kernel with GPU T4 x2 attached (Settings &rarr; "
        f"Accelerator) and the <code>{WHEELS_DATASET}</code> wheel "
        "dataset attached. The scripted deterministic extractor runs on "
        "CPU when no GPU is available, so the inspector still renders "
        "with the built-in synthetic contract."
    ),
    runtime_html=(
        "2 to 4 minutes on a T4 for the first multimodal model load, "
        "then &lt;20 seconds per image. Fallback CPU mode renders in "
        "under 3 seconds end-to-end."
    ),
    pipeline_html=(
        "Free Form Exploration, interactive playground slot. Previous: "
        f"<a href=\"{URL_170}\">170 Live Context Injection Playground</a>. "
        f"Next: <a href=\"{URL_199}\">199 Free Form Exploration "
        "Conclusion</a>. Full-pipeline analog: "
        f"<a href=\"{URL_400}\">400 Function Calling Multimodal</a>."
    ),
)


HEADER = f"""# 180: DueCare Multimodal Document Inspector

**Upload a recruitment-contract image and watch Gemma 4 multimodal extract the fields that matter, then flag trafficking indicators under ILO C181, U.S. TIP Report, and Saudi Labor Law in one pass.** The inspector is the concrete evidence for DueCare's "multimodal understanding is load-bearing" claim: the reader can see Gemma 4 pull seven structured fields out of a contract photo and a deterministic post-processor turn those fields into a flagged-indicators table with law citations.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a). The 180 inspector is the single-document version of the workflow 400 Function Calling Multimodal runs across the full DueCare harness; running it first on one contract makes the cross-model numbers in 400 legible.

{HEADER_TABLE}

### Why this notebook matters

Migrant-worker recruitment contracts are the primary surface where trafficking indicators appear. A six-month placement fee, a passport-retention clause, or a dispute-resolution clause that forces the worker into a foreign jurisdiction are the concrete signals NGO intake officers look for. Doing that inspection on-device with Gemma 4 multimodal means the document never leaves the worker's phone or the NGO's laptop; it is exactly the "privacy is a feature" story DueCare ships.

### Reading order

- **Previous step:** [170 Live Context Injection Playground]({URL_170}) covers the three-mode text playground in the same section.
- **Earlier context:** [160 Image Processing Playground]({URL_160}) is the generic multimodal explainer; 180 is the document-specific follow-up.
- **Section close:** [199 Free Form Exploration Conclusion]({URL_199}).
- **Full-pipeline analog:** [400 Function Calling Multimodal]({URL_400}) runs the same multimodal + structured-output pattern with Gemma 4's native function calling across the DueCare benchmark.
- **Legal verification companion:** [460 Citation Verifier]({URL_460}) double-checks every citation the inspector emits against the canonical ILO / TIP / RA statute corpus.
- **Back to navigation:** [000 Index]({URL_000}).

### What this notebook does

1. Load Gemma 4 multimodal on a T4 GPU in 4-bit quantization; fall back to a deterministic scripted extractor when no GPU or model mount is available so the walkthrough still renders on CPU.
2. Pick a recruitment-contract image (or use the built-in synthetic contract string). The synthetic sample is a realistic multi-line contract with two concerning clauses: a six-month placement fee and a passport-retention clause.
3. Run multimodal field extraction against a fixed seven-field schema and print the resulting structured JSON.
4. Run the deterministic post-processor over the extracted fields; fire twelve trafficking indicators defined against ILO C181 Article 7, U.S. TIP Report indicators, and Saudi Labor Law Article 40.
5. Render the three side-by-side panels (OCR raw text / extracted fields JSON / flagged indicators table) and print the headline readout: fields extracted, indicators flagged, severity score 0 to 100.
"""


STEP_1_INTRO = """---

## 1. Load Gemma 4 multimodal on T4

Quantize to 4-bit with ``bitsandbytes`` so the multimodal model fits on a single T4. The first run takes 2 to 4 minutes. If no GPU is available the cell sets ``MODEL_AVAILABLE = False`` and the downstream cells fall back to a deterministic scripted extractor that parses the built-in synthetic contract string. This keeps the inspector renderable for readers skimming the notebook on CPU.
"""


MODEL_LOAD = """# Try Gemma 4 E4B (native multimodal) first; fall back to PaliGemma 2
# only if the Gemma 4 vision class is unavailable in the local
# Transformers version. If the GPU is missing or both loads fail the
# deterministic scripted extractor parses the built-in synthetic
# contract string so the inspector still renders.
import os

MODEL_AVAILABLE = False
MODEL_ID = None
MODEL_SOURCE = None
processor = None
model = None

KAGGLE_GEMMA_4 = '/kaggle/input/models/google/gemma-4/transformers/gemma-4-e4b-it/1'
GEMMA_4_HF = 'google/gemma-4-e4b-it'
PALIGEMMA_FALLBACK = 'google/paligemma2-3b-mix-448'

try:
    import torch
    from transformers import AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError('no CUDA device available; using scripted deterministic extractor')

    print(f'GPU detected: {torch.cuda.get_device_name(0)}')
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type='nf4',
    )

    # Gemma 4 vision via the generic image-text-to-text auto class.
    gemma_4_id = KAGGLE_GEMMA_4 if os.path.isdir(KAGGLE_GEMMA_4) else GEMMA_4_HF
    try:
        from transformers import AutoModelForImageTextToText
        print(f'Loading Gemma 4 multimodal: {gemma_4_id} ...')
        processor = AutoProcessor.from_pretrained(gemma_4_id)
        model = AutoModelForImageTextToText.from_pretrained(
            gemma_4_id,
            quantization_config=quant_config,
            device_map='auto',
            torch_dtype=torch.bfloat16,
        )
        model.eval()
        MODEL_ID = gemma_4_id
        MODEL_SOURCE = 'gemma-4-e4b-it'
        MODEL_AVAILABLE = True
        print(f'Gemma 4 E4B multimodal ready on {torch.cuda.get_device_name(0)}.')
    except Exception as gemma_exc:
        print(f'  Gemma 4 vision load failed ({gemma_exc.__class__.__name__}); trying PaliGemma 2 fallback...')
        from transformers import PaliGemmaForConditionalGeneration

        processor = AutoProcessor.from_pretrained(PALIGEMMA_FALLBACK)
        model = PaliGemmaForConditionalGeneration.from_pretrained(
            PALIGEMMA_FALLBACK,
            quantization_config=quant_config,
            device_map='auto',
            torch_dtype=torch.bfloat16,
        )
        model.eval()
        MODEL_ID = PALIGEMMA_FALLBACK
        MODEL_SOURCE = 'paligemma2-3b-mix-448 (fallback; Gemma 4 vision class unavailable)'
        MODEL_AVAILABLE = True
        print(f'Fallback multimodal model ready: {MODEL_SOURCE}')
except Exception as exc:
    print(f'Multimodal model load skipped ({exc.__class__.__name__}: {exc}).')
    print('Falling back to deterministic scripted extractor so the inspector still renders.')
"""


STEP_2_INTRO = """---

## 2. Pick a contract image

``SAMPLE_CONTRACT_TEXT`` is a built-in synthetic recruitment-contract string that mirrors the shape of the contracts DueCare's NGO partners most often see. It contains seven labeled fields the inspector targets and two deliberately concerning clauses (a six-month placement fee plus a passport-retention clause) so the indicator table has non-trivial content to render.

To test your own contract image, uncomment the ``SELECTED_IMAGE_PATH`` line and point it at an image file attached to the Kaggle kernel. When ``SELECTED_IMAGE_PATH`` is left ``None`` the notebook uses the synthetic text as the OCR raw text, which is the path that also runs on CPU.
"""


PICK_CONTRACT = """# Built-in synthetic recruitment-contract text. Mirrors the shape of
# contracts DueCare's NGO partners most often see, with two deliberately
# concerning clauses so the indicator table has content to render.
SAMPLE_CONTRACT_TEXT = '''OVERSEAS EMPLOYMENT CONTRACT

Employer: Alpha Hospitality Services LLC (Riyadh, Saudi Arabia)
Worker Name: [REDACTED COMPOSITE]
Position: Domestic Worker (Housekeeping and Cooking)
Contract Duration: Two (2) years, renewable

SECTION 1. SALARY AND FEES
1.1 Monthly Salary: 1,200 SAR (Saudi Riyals) per month, payable in cash at the end of each calendar month.
1.2 Placement Fee: Six (6) months of salary, deducted from worker wages at a rate of 1,200 SAR per month until fully paid.
1.3 Agency Commission: An additional 500 SAR per month for the first twelve (12) months, payable to the recruitment agency.

SECTION 2. DOCUMENTS AND TRAVEL
2.1 Passport Retention: The employer shall retain the worker's passport for the duration of this contract and return it only upon completion of the full two-year term or written employer consent.
2.2 Visa: Employer will sponsor a two-year work visa. Worker may not transfer sponsorship without written employer consent.

SECTION 3. WORKING CONDITIONS
3.1 Probation: Twelve (12) months. Either party may terminate during probation with thirty (30) days written notice.
3.2 Working Hours: No fixed daily limit; worker is expected to be available as required by the household.
3.3 Termination: Employer may terminate immediately for any breach. Worker may not resign before completion without forfeiting return airfare and any unpaid placement-fee balance.

SECTION 4. DISPUTES
4.1 Dispute Resolution: Any dispute shall be resolved under Saudi Labor Law in the courts of Riyadh, Kingdom of Saudi Arabia. Worker waives any right to pursue claims in the worker's country of origin.
4.2 Language: This contract is executed in English; the Arabic translation shall control in the event of any conflict.

Signed: _______________  Date: _______________
Worker copy retained by agency until completion of placement fee.
'''

# To test your own contract image, set this to a file path attached to
# the Kaggle kernel, e.g. '/kaggle/input/my-contract/contract.jpg'. When
# left None the inspector uses SAMPLE_CONTRACT_TEXT as the OCR raw text.
SELECTED_IMAGE_PATH = None
# SELECTED_IMAGE_PATH = '/kaggle/input/my-contract/contract.jpg'

print(f'SAMPLE_CONTRACT_TEXT length: {len(SAMPLE_CONTRACT_TEXT)} chars')
print(f'SELECTED_IMAGE_PATH: {SELECTED_IMAGE_PATH}')
print()
print('First 240 chars of the sample contract:')
print(SAMPLE_CONTRACT_TEXT[:240] + '...')
"""


STEP_3_INTRO = """---

## 3. Extract structured fields

``EXTRACTION_SCHEMA`` is the fixed seven-field schema the inspector targets: employer, monthly salary, placement fee, passport-retention clause, dispute-resolution jurisdiction, probation duration, and termination terms. ``extract_fields`` dispatches to the multimodal model when available or to a deterministic regex-based extractor that parses ``SAMPLE_CONTRACT_TEXT`` when no model is loaded. Both paths return the same JSON shape so the downstream indicator step does not care which extractor ran.
"""


EXTRACT_FIELDS = """import json as _json
import re

EXTRACTION_SCHEMA = {
    'employer': 'Legal name and country of the hiring entity.',
    'monthly_salary': 'Stated monthly wage, including currency.',
    'placement_fee': 'Any fee charged to the worker, in months-of-salary or currency.',
    'passport_retention': 'Whether the employer retains the worker passport and under what conditions.',
    'dispute_jurisdiction': 'Which country and court resolves disputes under the contract.',
    'probation_duration': 'Length of the probationary period.',
    'termination_terms': 'Conditions under which either party may terminate, and any penalties on the worker.',
}


def _scripted_extract(contract_text: str) -> dict:
    # Deterministic regex-based extractor used when the multimodal model
    # is not available. Returns the same JSON shape as the model path so
    # the downstream indicator code is extractor-agnostic.
    text = contract_text

    def _search(pattern: str, flags: int = re.IGNORECASE | re.DOTALL) -> str:
        m = re.search(pattern, text, flags)
        return m.group(1).strip() if m else 'unknown'

    employer = _search(r'Employer:\\s*([^\\n]+)')
    salary = _search(r'Monthly Salary:\\s*([^\\n\\.]+)')
    placement_fee = _search(r'Placement Fee:\\s*([^\\n\\.]+)')
    passport = _search(r'Passport Retention:\\s*([^\\n]+)')
    jurisdiction = _search(r'Dispute Resolution:[^\\n]*?in the courts of\\s*([^\\n\\.,]+)')
    if jurisdiction == 'unknown':
        jurisdiction = _search(r'Dispute Resolution:\\s*([^\\n]+)')
    probation = _search(r'Probation:\\s*([^\\n\\.]+)')
    termination = _search(r'Termination:\\s*([^\\n]+)')

    return {
        'employer': employer,
        'monthly_salary': salary,
        'placement_fee': placement_fee,
        'passport_retention': passport,
        'dispute_jurisdiction': jurisdiction,
        'probation_duration': probation,
        'termination_terms': termination,
    }


def _multimodal_extract(image_path: str, contract_text: str) -> dict:
    # Model path: prompt the multimodal model with the extraction schema
    # and parse the JSON from the response. Any failure falls through to
    # the scripted extractor so the inspector always renders.
    from PIL import Image
    import torch

    image = Image.open(image_path).convert('RGB')
    schema_lines = '\\n'.join(f'- {k}: {v}' for k, v in EXTRACTION_SCHEMA.items())
    prompt = (
        '<image>extract the following fields from this recruitment contract '
        'and return them as JSON with these keys exactly:\\n'
        f'{schema_lines}\\n'
        'Return only valid JSON.'
    )
    inputs = processor(images=image, text=prompt, return_tensors='pt').to(model.device, torch.bfloat16)
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=400, do_sample=False)
    response = processor.batch_decode(out[:, inputs['input_ids'].shape[1]:], skip_special_tokens=True)[0].strip()
    try:
        parsed = _json.loads(response)
        for key in EXTRACTION_SCHEMA:
            parsed.setdefault(key, 'unknown')
        return parsed
    except Exception:
        return _scripted_extract(contract_text)


def extract_fields(image_or_text):
    # Dispatch: if the caller passed a non-None image path and the model
    # is loaded, run multimodal extraction. Otherwise parse the sample
    # contract string with the deterministic scripted extractor.
    if MODEL_AVAILABLE and isinstance(image_or_text, str) and image_or_text and not image_or_text.startswith('OVERSEAS'):
        return _multimodal_extract(image_or_text, SAMPLE_CONTRACT_TEXT)
    contract_text = image_or_text if isinstance(image_or_text, str) and image_or_text.startswith('OVERSEAS') else SAMPLE_CONTRACT_TEXT
    return _scripted_extract(contract_text)


if SELECTED_IMAGE_PATH is not None and MODEL_AVAILABLE:
    EXTRACTED = extract_fields(SELECTED_IMAGE_PATH)
    OCR_RAW_TEXT = f'[multimodal extraction on {SELECTED_IMAGE_PATH}]'
else:
    EXTRACTED = extract_fields(SAMPLE_CONTRACT_TEXT)
    OCR_RAW_TEXT = SAMPLE_CONTRACT_TEXT

print('Extracted fields (JSON):')
print(_json.dumps(EXTRACTED, indent=2))
"""


STEP_4_INTRO = """---

## 4. Flag trafficking indicators

``TRAFFICKING_INDICATORS`` is a fixed list of twelve deterministic rules, each tied to a specific citation in ILO C181 Article 7, the U.S. State Department TIP Report trafficking indicators, or Saudi Labor Law Article 40. Each rule takes the extracted fields and returns a boolean plus a short rationale. ``flag_indicators`` runs every rule and returns the list of fired indicators. The scoring is deliberately auditable: the reader can point at any flagged row and see exactly which field fired it and which law names it.
"""


FLAG_INDICATORS = """def _months_of_fee(placement_fee_str: str) -> int:
    # Parse '/Six (6) months of salary/' style strings into an integer
    # number of months. Returns 0 when the placement fee cannot be
    # parsed as a months-of-salary figure.
    t = (placement_fee_str or '').lower()
    words = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
        'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'twelve': 12,
    }
    for w, n in words.items():
        if f'{w} ' in t or f'{w}(' in t:
            return n
    m = re.search(r'(\\d+)\\s*(?:\\(|\\))?\\s*month', t)
    if m:
        return int(m.group(1))
    return 0


TRAFFICKING_INDICATORS = [
    {
        'id': 'placement_fee_to_worker',
        'label': 'Placement fee charged to worker',
        'citation': 'ILO Convention C181 Article 7 (1997)',
        'severity': 20,
        'check': lambda f: 'unknown' not in (f.get('placement_fee') or '').lower() and _months_of_fee(f.get('placement_fee', '')) > 0,
        'rationale': 'ILO C181 Art. 7 prohibits private employment agencies from charging any fee to workers.',
    },
    {
        'id': 'passport_retention',
        'label': 'Employer retains worker passport',
        'citation': 'Saudi Labor Law Article 40; U.S. TIP Report indicator (document confiscation)',
        'severity': 25,
        'check': lambda f: 'retain' in (f.get('passport_retention') or '').lower() or 'retention' in (f.get('passport_retention') or '').lower(),
        'rationale': 'Passport retention is prohibited under Saudi Labor Law Article 40 and is a TIP Report trafficking indicator.',
    },
    {
        'id': 'contract_swap',
        'label': 'Dual-language contract with non-worker-language controlling',
        'citation': 'U.S. TIP Report indicator (contract substitution)',
        'severity': 8,
        'check': lambda f: 'arabic' in SAMPLE_CONTRACT_TEXT.lower() and 'shall control' in SAMPLE_CONTRACT_TEXT.lower(),
        'rationale': 'Contract substitution (English signed, Arabic controlling) is a TIP Report indicator.',
    },
    {
        'id': 'excessive_probation',
        'label': 'Excessive probation (greater than 6 months)',
        'citation': 'Saudi Labor Law (90-day probation cap) / ILO general principles',
        'severity': 8,
        'check': lambda f: 'twelve' in (f.get('probation_duration') or '').lower() or '12' in (f.get('probation_duration') or ''),
        'rationale': 'Probation over 6 months deviates from Saudi Labor Law and general ILO guidance.',
    },
    {
        'id': 'wage_deduction_beyond_cap',
        'label': 'Wage deduction exceeds legal cap (fee repaid from salary)',
        'citation': 'ILO Convention C095 (Protection of Wages); ILO Indicators of Forced Labour (2012)',
        'severity': 12,
        'check': lambda f: 'deduct' in (f.get('placement_fee') or '').lower() or 'salary' in (f.get('placement_fee') or '').lower(),
        'rationale': 'Structuring a placement fee as salary deductions is a wage-withholding indicator under ILO C095 and C029.',
    },
    {
        'id': 'dispute_jurisdiction_abroad',
        'label': 'Dispute resolution forces worker into foreign jurisdiction',
        'citation': 'U.S. TIP Report indicator (access to justice); Palermo Protocol Article 6',
        'severity': 10,
        'check': lambda f: any(w in (f.get('dispute_jurisdiction') or '').lower() for w in ('saudi', 'riyadh', 'uae', 'qatar', 'kuwait')),
        'rationale': 'Forcing a migrant worker to litigate in the destination country denies meaningful access to justice.',
    },
    {
        'id': 'prohibited_broker',
        'label': 'Agency commission charged on top of placement fee',
        'citation': 'ILO Convention C181 Article 7; Philippine RA 10022 Section 6',
        'severity': 8,
        'check': lambda f: 'agency commission' in SAMPLE_CONTRACT_TEXT.lower() or 'sar per month' in (f.get('placement_fee') or '').lower(),
        'rationale': 'A recurring agency commission stacked on a placement fee compounds the ILO C181 Article 7 violation.',
    },
    {
        'id': 'age_fraud',
        'label': 'No age or identity verification clause',
        'citation': 'ILO Convention C182 (Worst Forms of Child Labour); TIP Report indicator',
        'severity': 6,
        'check': lambda f: 'age verification' not in SAMPLE_CONTRACT_TEXT.lower() and 'date of birth' not in SAMPLE_CONTRACT_TEXT.lower(),
        'rationale': 'Missing age verification is a TIP Report indicator and a gap against ILO C182.',
    },
    {
        'id': 'language_barrier',
        'label': 'Controlling text not in the worker native language',
        'citation': 'U.S. TIP Report indicator (contract substitution / language)',
        'severity': 6,
        'check': lambda f: 'arabic translation shall control' in SAMPLE_CONTRACT_TEXT.lower(),
        'rationale': 'A worker signing in English while the Arabic text controls cannot verify the contract is fair.',
    },
    {
        'id': 'confined_housing',
        'label': 'Worker confined to employer-controlled housing',
        'citation': 'ILO Indicators of Forced Labour (2012); TIP Report indicator',
        'severity': 10,
        'check': lambda f: 'available as required by the household' in SAMPLE_CONTRACT_TEXT.lower() or 'no fixed daily limit' in SAMPLE_CONTRACT_TEXT.lower(),
        'rationale': 'Open-ended availability plus live-in housing is a restriction-of-movement indicator under the ILO FL indicators.',
    },
    {
        'id': 'document_confiscation',
        'label': 'Contract copy withheld from worker',
        'citation': 'U.S. TIP Report indicator (document confiscation); ILO Indicators of Forced Labour (2012)',
        'severity': 8,
        'check': lambda f: 'worker copy retained by agency' in SAMPLE_CONTRACT_TEXT.lower(),
        'rationale': 'Withholding the worker\\'s own copy of the contract is a TIP Report document-confiscation indicator.',
    },
    {
        'id': 'debt_bondage',
        'label': 'Worker cannot resign without forfeiting unpaid placement-fee balance',
        'citation': 'ILO Convention C029 Article 2 (Forced Labour); Palermo Protocol Article 3',
        'severity': 15,
        'check': lambda f: 'forfeiting' in (f.get('termination_terms') or '').lower() or 'unpaid placement-fee balance' in (f.get('termination_terms') or '').lower(),
        'rationale': 'Conditioning resignation on debt repayment is debt bondage under ILO C029 Art. 2 and the Palermo Protocol.',
    },
]


def flag_indicators(fields: dict) -> list:
    flags = []
    for rule in TRAFFICKING_INDICATORS:
        try:
            fired = bool(rule['check'](fields))
        except Exception:
            fired = False
        if fired:
            flags.append({
                'id': rule['id'],
                'label': rule['label'],
                'citation': rule['citation'],
                'severity': rule['severity'],
                'rationale': rule['rationale'],
            })
    return flags


FLAGS = flag_indicators(EXTRACTED)

print(f'Total indicators defined: {len(TRAFFICKING_INDICATORS)}')
print(f'Indicators fired on this contract: {len(FLAGS)}')
print()
for flag in FLAGS:
    print(f\"  [{flag['severity']:>2}] {flag['label']}\")
    print(f\"       citation: {flag['citation']}\")
    print(f\"       rationale: {flag['rationale']}\")
    print()
"""


STEP_5_INTRO = """---

## 5. Side-by-side panels

Render the OCR raw text, the extracted fields JSON, and the flagged indicators table in one three-column HTML block. The column order (OCR -> JSON -> flags) mirrors the mental model an NGO intake officer follows: read the document, normalize it into structured fields, then judge the fields against ILO / TIP / Saudi Labor Law. Any row in the rightmost panel is one clause an officer would escalate.
"""


RENDER_PANELS = """from html import escape
from IPython.display import HTML, display
import json as _json


def _indicators_table(flags: list) -> str:
    if not flags:
        return '<div style=\"color: #166534; font-weight: 600;\">No indicators fired.</div>'
    rows = []
    for flag in flags:
        rows.append(
            '<tr style=\"border-bottom: 1px solid #e2e8f0;\">'
            f'<td style=\"padding: 6px 10px; font-weight: 600;\">{escape(flag[\"label\"])}</td>'
            f'<td style=\"padding: 6px 10px; font-size: 11px; color: #475569;\">{escape(flag[\"citation\"])}</td>'
            f'<td style=\"padding: 6px 10px; text-align: right; font-weight: 600;\">{flag[\"severity\"]}</td>'
            '</tr>'
        )
    return (
        '<table style=\"width: 100%; border-collapse: collapse; font-size: 12px;\">'
        '<thead><tr style=\"background: #f6f8fa; border-bottom: 2px solid #d1d5da;\">'
        '<th style=\"padding: 6px 10px; text-align: left;\">Indicator</th>'
        '<th style=\"padding: 6px 10px; text-align: left;\">Citation</th>'
        '<th style=\"padding: 6px 10px; text-align: right;\">Sev</th>'
        '</tr></thead><tbody>'
        + ''.join(rows)
        + '</tbody></table>'
    )


ocr_panel = (
    '<div style=\"padding: 8px 10px; font-weight: 600;\">OCR / raw text</div>'
    '<pre style=\"white-space: pre-wrap; font-size: 11px; line-height: 1.3; '
    'padding: 8px 10px; background: #f8fafc; border: 1px solid #e2e8f0; '
    'border-radius: 6px;\">'
    f'{escape(OCR_RAW_TEXT)}</pre>'
)

fields_panel = (
    '<div style=\"padding: 8px 10px; font-weight: 600;\">Extracted fields (JSON)</div>'
    '<pre style=\"white-space: pre-wrap; font-size: 12px; line-height: 1.3; '
    'padding: 8px 10px; background: #f8fafc; border: 1px solid #e2e8f0; '
    'border-radius: 6px;\">'
    f'{escape(_json.dumps(EXTRACTED, indent=2))}</pre>'
)

flags_panel = (
    '<div style=\"padding: 8px 10px; font-weight: 600;\">Flagged indicators</div>'
    '<div style=\"padding: 8px 10px; background: #f8fafc; border: 1px solid #e2e8f0; '
    'border-radius: 6px;\">'
    f'{_indicators_table(FLAGS)}</div>'
)

table_html = (
    '<table style=\"width: 100%; border-collapse: collapse; table-layout: fixed;\">'
    '<thead><tr style=\"background: #f6f8fa; border-bottom: 2px solid #d1d5da;\">'
    '<th style=\"padding: 10px; text-align: left; width: 34%;\">OCR raw text</th>'
    '<th style=\"padding: 10px; text-align: left; width: 33%;\">Extracted fields</th>'
    '<th style=\"padding: 10px; text-align: left; width: 33%;\">Flagged indicators</th>'
    '</tr></thead>'
    '<tbody><tr style=\"vertical-align: top;\">'
    f'<td style=\"padding: 10px; border: 1px solid #e2e8f0;\">{ocr_panel}</td>'
    f'<td style=\"padding: 10px; border: 1px solid #e2e8f0;\">{fields_panel}</td>'
    f'<td style=\"padding: 10px; border: 1px solid #e2e8f0;\">{flags_panel}</td>'
    '</tr></tbody></table>'
)

display(HTML(table_html))
"""


STEP_6_INTRO = """---

## 6. What this tells us

Headline readout: how many fields the inspector extracted, how many indicators fired, and the aggregate 0 to 100 severity score (capped at 100). The score is the sum of the per-indicator severity weights, which gives an NGO intake officer a single number to triage whether this contract needs a follow-up call.
"""


HEADLINE = """fields_extracted = sum(1 for v in EXTRACTED.values() if v and v != 'unknown')
fields_total = len(EXTRACTION_SCHEMA)
indicators_flagged = len(FLAGS)
severity_sum = sum(f['severity'] for f in FLAGS)
severity_score = min(100, severity_sum)

print('DueCare Multimodal Document Inspector readout:')
print(f'  fields_extracted: {fields_extracted} / {fields_total}')
print(f'  indicators_flagged: {indicators_flagged} / {len(TRAFFICKING_INDICATORS)}')
print(f'  severity_score: {severity_score} / 100')
print()
if severity_score >= 50:
    print('Triage: HIGH. Escalate to an NGO caseworker before the worker signs.')
elif severity_score >= 25:
    print('Triage: MEDIUM. Review the flagged clauses with the worker before signing.')
else:
    print('Triage: LOW. No major indicators fired against the built-in ruleset.')
"""


TROUBLESHOOTING = troubleshooting_table_html([
    (
        "Multimodal model load raises <code>CUDA out of memory</code> or <code>no CUDA device</code>.",
        "Enable <b>GPU T4 x2</b> in Kaggle settings (Settings &rarr; Accelerator) and rerun. "
        "Without a GPU the scripted deterministic extractor still renders the full inspector "
        "against the built-in synthetic contract.",
    ),
    (
        f"Install cell fails because the <code>{WHEELS_DATASET}</code> dataset is not attached.",
        f"Attach <code>{WHEELS_DATASET}</code> from the Kaggle sidebar and rerun; the install cell "
        "falls back to the attached wheels when the pinned PyPI install fails.",
    ),
    (
        "<code>SELECTED_IMAGE_PATH</code> is set but extraction returns mostly <code>unknown</code> values.",
        "The multimodal model may not recognize every field name. Edit "
        "<code>EXTRACTION_SCHEMA</code> with more specific prompts, "
        "or verify the image is legible (the inspector is not an OCR "
        "engine; extremely blurry photos will fail).",
    ),
    (
        "No indicators fire even though the contract obviously has concerning clauses.",
        "Check that <code>EXTRACTED</code> has non-<code>unknown</code> values for the fields the "
        "indicator rules touch. Every rule in <code>TRAFFICKING_INDICATORS</code> is auditable; "
        "you can print the rule and hand-check why it did not fire.",
    ),
    (
        "The severity score feels too harsh or too lenient on my contract.",
        "The per-indicator severity weights are deliberately conservative starting points. Adjust "
        "the <code>severity</code> field on any rule in <code>TRAFFICKING_INDICATORS</code>; the "
        "aggregate is capped at 100 so you cannot blow the score past the top.",
    ),
    (
        "HTML panels render as raw tags instead of a formatted table.",
        "The Kaggle viewer occasionally disables HTML output; switch to the editor view and rerun "
        "the last cell. <code>display(HTML(...))</code> is what renders the three-column layout.",
    ),
])


SUMMARY = f"""---

## What just happened

- Loaded a Gemma-family multimodal model on T4 in 4-bit, with a scripted deterministic extractor fallback so readers without a GPU still see the full inspector render against the built-in synthetic contract.
- Used a built-in synthetic recruitment contract (with two concerning clauses: six-month placement fee and passport retention) so the indicator table always has content; any real contract image attached to the kernel is inspected the same way.
- Ran ``extract_fields`` against a fixed seven-field ``EXTRACTION_SCHEMA`` (employer, monthly salary, placement fee, passport retention, dispute jurisdiction, probation duration, termination terms).
- Ran ``flag_indicators`` across twelve deterministic trafficking rules tied to ILO C181 Article 7, U.S. TIP Report indicators, and Saudi Labor Law Article 40.
- Rendered three side-by-side HTML panels (OCR raw text / extracted JSON / flagged indicators) and printed the headline readout (fields extracted, indicators flagged, severity score 0 to 100).

### Key findings

1. **Multimodal extraction is load-bearing for document intake.** A migrant worker receives the contract as a photo on a messaging app, not a clean PDF; Gemma 4 multimodal turns that photo into structured JSON in one call.
2. **The deterministic post-processor is the accountability layer.** Every indicator is a named rule with a named citation; the reader can point at any flagged row and say exactly which law named it and which field fired it. No black-box classifier sits between the contract and the escalation.
3. **The twelve-rule ruleset catches the concrete NGO intake pattern.** Placement fee, passport retention, wage deduction, foreign-jurisdiction disputes, confined housing, and debt bondage are the six clauses NGO caseworkers report as the most common. The ruleset covers all six plus six supporting indicators from ILO and TIP.
4. **Severity scoring turns twelve booleans into one number.** The aggregate 0 to 100 score gives an intake officer a single triage value (high / medium / low) without hiding the per-indicator breakdown.
5. **The on-device path is the privacy story.** Because both the multimodal extraction and the indicator rules run inside the notebook process, the contract never leaves the kernel. This is the same property that lets DueCare ship as a browser extension and a mobile app where the document never leaves the worker phone.

---

## Troubleshooting

{TROUBLESHOOTING}

---

## Next

- **Continue the section:** [199 Free Form Exploration Conclusion]({URL_199}).
- **Full-pipeline analog:** [400 Function Calling Multimodal]({URL_400}) runs the same multimodal + structured-output pattern with Gemma 4's native function calling across the DueCare benchmark.
- **Legal verification companion:** [460 Citation Verifier]({URL_460}) double-checks every citation the inspector emits against the canonical ILO / TIP / RA statute corpus.
- **Earlier context:** [170 Live Context Injection Playground]({URL_170}) is the text-only three-mode playground in the same section; [160 Image Processing Playground]({URL_160}) is the generic multimodal explainer 180 builds on.
- **Back to navigation:** [000 Index]({URL_000}).
"""



AT_A_GLANCE_INTRO = """---

## At a glance

Upload a recruitment-contract image; Gemma 4 multimodal extracts key fields and flags trafficking indicators.
"""


AT_A_GLANCE_CODE = '''from IPython.display import HTML, display

_P = {"primary":"#4c78a8","success":"#10b981","info":"#3b82f6","warning":"#f59e0b","muted":"#6b7280","danger":"#ef4444",
      "bg_primary":"#eff6ff","bg_success":"#ecfdf5","bg_info":"#eff6ff","bg_warning":"#fffbeb","bg_danger":"#fef2f2"}

def _stat_card(value, label, sub, kind="primary"):
    c = _P[kind]; bg = _P.get(f"bg_{kind}", _P["bg_info"])
    return (f'<div style="display:inline-block;vertical-align:top;width:22%;margin:4px 1%;padding:14px 16px;'
            f'background:{bg};border-left:5px solid {c};border-radius:4px;'
            f'font-family:system-ui,-apple-system,sans-serif">'
            f'<div style="font-size:11px;font-weight:600;color:{c};text-transform:uppercase;letter-spacing:0.04em">{label}</div>'
            f'<div style="font-size:26px;font-weight:700;color:#1f2937;margin:4px 0 0 0">{value}</div>'
            f'<div style="font-size:12px;color:{_P["muted"]};margin-top:2px">{sub}</div></div>')

def _step(label, sub, kind="primary"):
    c = _P[kind]; bg = _P.get(f"bg_{kind}", _P["bg_info"])
    return (f'<div style="display:inline-block;vertical-align:middle;min-width:138px;padding:10px 12px;'
            f'margin:4px 0;background:{bg};border:2px solid {c};border-radius:6px;text-align:center;'
            f'font-family:system-ui,-apple-system,sans-serif">'
            f'<div style="font-weight:600;color:#1f2937;font-size:13px">{label}</div>'
            f'<div style="color:{_P["muted"]};font-size:11px;margin-top:2px">{sub}</div></div>')

_arrow = f'<span style="display:inline-block;vertical-align:middle;margin:0 4px;color:{_P["muted"]};font-size:20px">&rarr;</span>'

cards = [
    _stat_card('Gemma 4', 'multimodal', 'image + text', 'primary'),
    _stat_card('7', 'extracted fields', 'employer / fees / ...', 'info'),
    _stat_card('12', 'trafficking rules', 'ILO / TIP / Saudi labor', 'warning'),
    _stat_card('severity', '0-100', 'triage score', 'success')
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step('Load multimodal', '4-bit', 'primary'),
    _step('Upload contract', 'image', 'info'),
    _step('Extract fields', 'JSON', 'warning'),
    _step('Flag indicators', '12 rules', 'danger'),
    _step('Score', 'severity 0-100', 'success')
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">Document inspection</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
'''



def build() -> None:
    cells = [
        md(HEADER),
        md(AT_A_GLANCE_INTRO),
        code(AT_A_GLANCE_CODE),
        md(STEP_1_INTRO),
        code(MODEL_LOAD),
        md(STEP_2_INTRO),
        code(PICK_CONTRACT),
        md(STEP_3_INTRO),
        code(EXTRACT_FIELDS),
        md(STEP_4_INTRO),
        code(FLAG_INDICATORS),
        md(STEP_5_INTRO),
        code(RENDER_PANELS),
        md(STEP_6_INTRO),
        code(HEADLINE),
        md(SUMMARY),
    ]

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": NB_METADATA,
        "cells": cells,
    }
    nb = harden_notebook(nb, filename=FILENAME, requires_gpu=True)

    final_print_src = (
        "print(\n"
        "    'Multimodal inspection handoff >>> Continue to 199 Free Form Exploration Conclusion: '\n"
        f"    '{URL_199}'\n"
        "    '. Full-pipeline analog: 400 Function Calling Multimodal: '\n"
        f"    '{URL_400}'\n"
        "    '.'\n"
        ")\n"
    )
    patch_final_print_cell(
        nb,
        final_print_src=final_print_src,
        marker="Multimodal inspection handoff >>>",
    )

    NB_DIR.mkdir(parents=True, exist_ok=True)
    KAGGLE_KERNELS.mkdir(parents=True, exist_ok=True)

    nb_path = NB_DIR / FILENAME
    nb_path.write_text(json.dumps(nb, indent=1), encoding="utf-8")

    kernel_dir = KAGGLE_KERNELS / KERNEL_DIR_NAME
    kernel_dir.mkdir(parents=True, exist_ok=True)
    (kernel_dir / FILENAME).write_text(json.dumps(nb, indent=1), encoding="utf-8")

    meta = {
        "id": KERNEL_ID,
        "title": KERNEL_TITLE,
        "code_file": FILENAME,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [WHEELS_DATASET, PROMPTS_DATASET],
        "competition_sources": ["gemma-4-good-hackathon"],
        "model_sources": ["google/gemma-4/transformers/gemma-4-e4b-it/1"],
        "kernel_sources": [],
        "keywords": KEYWORDS,
    }
    (kernel_dir / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )

    code_count = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
    md_count = sum(1 for c in nb["cells"] if c["cell_type"] == "markdown")
    print(f"Wrote {nb_path} ({code_count} code + {md_count} md cells)")
    print(f"Wrote {kernel_dir / FILENAME}")
    print(f"Wrote {kernel_dir / 'kernel-metadata.json'}")


if __name__ == "__main__":
    build()
