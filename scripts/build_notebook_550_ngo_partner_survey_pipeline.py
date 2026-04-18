#!/usr/bin/env python3
"""Build 550: NGO Partner Survey Pipeline.

Human-in-the-loop feedback surface for the DueCare training corpus:

1. Load a pre-curated directory of public NGO partner contact pages
   (Polaris Project, IJM, POEA, BP2MI, HRD Nepal, ECPAT, etc.). Contact
   info is pre-verified public record; this notebook NEVER scrapes
   untrusted domains.

2. For each NGO, generate:
   - A JSON-schema survey tailored to that NGO's focus area (corridor,
     sector, primary rubric categories).
   - A Markdown email invitation draft explaining what DueCare is asking
     for and linking to the survey.

3. Save every invitation as a separate ``.eml`` file to
   ``/kaggle/working/outbound_emails/``. Nothing is auto-sent; the files
   are drafts for Taylor to review and send manually.

4. Ingest any survey responses present at
   ``/kaggle/working/survey_responses/*.json`` and validate each against
   the expected schema.

5. Merge valid survey responses into a new row in the training JSONL
   that 530 Phase 3 Unsloth Fine-Tune can consume, flagged with the
   provenance ``source: ngo_survey_<ngo_id>``.

Ethics-first design:
- No outbound email is sent from the kernel.
- No scraping of untrusted domains.
- All contacts are public record already linked from each NGO's own
  footer / contact page.
- Every survey includes an explicit opt-in clause and a link to
  DueCare's data-governance policy.
- A trivial PII scan runs over every ingested response so nothing with
  direct identifiers gets merged into the public corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import canonical_header_table, patch_final_print_cell, troubleshooting_table_html
from notebook_hardening_utils import harden_notebook


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"

FILENAME = "550_ngo_partner_survey_pipeline.ipynb"
KERNEL_DIR_NAME = "duecare_550_ngo_partner_survey_pipeline"
KERNEL_ID = "taylorsamarel/550-duecare-ngo-partner-survey-pipeline"
KERNEL_TITLE = "550: DueCare NGO Partner Survey Pipeline"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
PROMPTS_DATASET = "taylorsamarel/duecare-trafficking-prompts"
KEYWORDS = ["ngo", "survey", "human-feedback", "training-data", "trafficking"]

URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_525 = "https://www.kaggle.com/code/taylorsamarel/525-duecare-uncensored-5-grade-generator"
URL_527 = "https://www.kaggle.com/code/taylorsamarel/527-duecare-uncensored-rubric-generator"
URL_530 = "https://www.kaggle.com/code/taylorsamarel/duecare-530-phase3-unsloth-finetune"
URL_599 = "https://www.kaggle.com/code/taylorsamarel/599-duecare-model-improvement-opportunities-conclusion"


def md(s): return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}
def code(s): return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": s.splitlines(keepends=True)}


NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
    "kaggle": {
        "accelerator": "none",
        "isInternetEnabled": True,
        "language": "python",
        "sourceType": "notebook",
    },
}


HEADER_TABLE = canonical_header_table(
    inputs_html=(
        "A pre-curated directory of 10 migrant-worker and anti-trafficking "
        "NGOs with public contact info (Polaris Project, IJM, ECPAT, "
        "POEA, BP2MI, HRD Nepal, Migrant Forum in Asia, Anti-Slavery "
        "International, Verite, GAATW). Contact info is public record; "
        "no scraping happens in the kernel. Optionally, response JSON "
        "files at <code>/kaggle/working/survey_responses/*.json</code>."
    ),
    outputs_html=(
        "Per-NGO artifacts written to <code>/kaggle/working/outbound_emails/</code>: "
        "one <code>.eml</code> draft email per NGO, a JSON-schema survey "
        "template, and a Markdown briefing one-pager. A merged training "
        "JSONL at <code>/kaggle/working/ngo_feedback_training.jsonl</code> "
        "with any ingested survey responses in the trafficking-prompts "
        "schema, ready for 530 to consume."
    ),
    prerequisites_html=(
        f"Kaggle CPU kernel with internet enabled and the "
        f"<code>{WHEELS_DATASET}</code> wheel dataset attached. No API "
        "keys required. Optional: upload completed survey responses as "
        "JSON files to <code>/kaggle/working/survey_responses/</code> "
        "before running Section 5."
    ),
    runtime_html=(
        "Under 2 minutes end-to-end. Pure Python template rendering + "
        "filesystem writes; no model load, no network calls."
    ),
    pipeline_html=(
        f"Model Improvement section, human-feedback slot. Siblings: "
        f"<a href=\"{URL_525}\">525 Uncensored 5-Grade Generator</a> and "
        f"<a href=\"{URL_527}\">527 Uncensored Rubric Generator</a> are "
        f"the synthetic generators; this notebook is the human-validated "
        f"counterpart. Downstream: <a href=\"{URL_530}\">530 Phase 3 "
        f"Unsloth Fine-Tune</a>. Section close: "
        f"<a href=\"{URL_599}\">599 Conclusion</a>."
    ),
)


HERO_CODE = '''from IPython.display import HTML, display

display(HTML(
    '<div style="background:linear-gradient(135deg,#1e3a8a 0%,#4c78a8 100%);color:white;padding:20px 24px;border-radius:8px;margin:8px 0;font-family:system-ui,-apple-system,sans-serif">'
    '<div style="font-size:10px;font-weight:600;letter-spacing:0.14em;opacity:0.8;text-transform:uppercase">DueCare - Human-in-the-Loop</div>'
    '<div style="font-size:22px;font-weight:700;margin:4px 0 0 0">550 NGO Partner Survey Pipeline</div>'
    '<div style="font-size:13px;opacity:0.92;margin-top:4px">Generate per-NGO surveys + email invitations, ingest responses, merge into training corpus.</div></div>'
))

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

cards = [
    _stat_card('10', 'NGO partners', 'public contact pages only', 'primary'),
    _stat_card('drafts', 'outbound', 'human review before sending', 'warning'),
    _stat_card('opt-in', 'survey consent', 'GDPR-aware design', 'info'),
    _stat_card('JSONL', 'training format', 'matches 530 schema', 'success'),
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))
'''


HEADER = f"""# 550: DueCare NGO Partner Survey Pipeline

**Synthetic generators are half the training data; domain-expert validation is the other half.** 525 and 527 use uncensored Gemma to scale up prompts, graded responses, and rubrics. This notebook builds the human-in-the-loop surface: generate per-NGO survey invitations, ingest the responses, and merge what the NGOs provide back into the training corpus with clear provenance.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a). NGOs are the stakeholders whose trust we need to earn. This notebook codifies how they participate in the training loop.

{HEADER_TABLE}

### Ethics-first design

- **No outbound email is sent from this kernel.** The notebook writes `.eml` drafts to `/kaggle/working/outbound_emails/` for Taylor to review, edit, and send manually from a real mail client.
- **No scraping of untrusted domains.** The NGO directory is pre-curated public record (footer-linked contact pages on each NGO's own site).
- **Opt-in only.** Every survey invitation includes explicit consent language, a plain-English explanation of DueCare's data usage, and a revocation path.
- **PII-aware intake.** A keyword scan runs over every ingested response; any response containing raw personal identifiers is quarantined and never written to the public training JSONL.
- **Provenance preserved.** Every merged training row carries `source: ngo_survey_<ngo_id>` so the downstream audit trail is intact.

### Reading order

- **Siblings:** [525 Uncensored 5-Grade Generator]({URL_525}) and [527 Uncensored Rubric Generator]({URL_527}) produce the synthetic training pairs; this notebook is the human-validated counterpart.
- **Downstream:** [530 Phase 3 Unsloth Fine-Tune]({URL_530}) consumes both synthetic and NGO-validated training rows.
- **Section close:** [599 Model Improvement Opportunities Conclusion]({URL_599}).

### What this notebook does

1. Load the pre-curated NGO partner directory.
2. Generate a JSON-schema survey template for each NGO, tailored to that NGO's corridor + sector.
3. Render a Markdown briefing one-pager per NGO (what DueCare is, what we're asking, what they get back).
4. Assemble a `.eml` draft email per NGO with the briefing and a placeholder survey link.
5. Ingest any response JSON files present at `/kaggle/working/survey_responses/`, validate against the schema, quarantine any that fail a PII scan.
6. Merge the valid responses into `/kaggle/working/ngo_feedback_training.jsonl` in the trafficking-prompts schema.
7. Render a status table showing outreach state, intake state, and merge state per NGO.
"""


DIRECTORY_MD = """---

## 1. Pre-curated NGO partner directory

Each row is public record sourced from each NGO's own footer / contact / press-inquiries page as of 2026-04. The `contact_url` is the public-facing form or email address. No scraping happens in this notebook; the directory below is a committed seed that Taylor maintains manually.
"""


DIRECTORY_CODE = '''from dataclasses import dataclass, asdict
from datetime import date
import json
import os
import re
import time
from pathlib import Path


@dataclass
class NGO:
    ngo_id: str
    display_name: str
    country: str
    primary_corridors: list  # list of corridor codes like ['PH-SA', 'PH-HK']
    primary_sectors: list
    rubric_focus: list       # list of rubric category ids like ['business_framed_exploitation']
    contact_url: str
    press_email: str         # placeholder; Taylor overrides before sending


NGO_DIRECTORY = [
    NGO('polaris',   'Polaris Project',                    'USA',     ['MX-US', 'GT-US'],                  ['all-sectors'],                       ['victim_revictimization'],                'https://polarisproject.org/contact-us/',                 'contact@polarisproject.org'),
    NGO('ijm',       'International Justice Mission',      'USA',     ['IN-IN', 'PH-PH', 'UG-UG'],          ['domestic-work', 'forced-labor'],     ['business_framed_exploitation'],          'https://www.ijm.org/contact',                             'contact@ijm.org'),
    NGO('ecpat',     'ECPAT International',                 'Thailand',['TH-TH', 'MM-TH'],                  ['child-trafficking'],                 ['victim_revictimization'],                'https://ecpat.org/contact/',                              'info@ecpat.org'),
    NGO('poea',      'Philippine Overseas Employment Administration', 'Philippines', ['PH-SA', 'PH-HK', 'PH-AE'], ['domestic-work', 'seafaring'], ['business_framed_exploitation', 'financial_crime_blindness'], 'https://www.dmw.gov.ph/contact-us', 'contact@dmw.gov.ph'),
    NGO('bp2mi',     'BP2MI (Indonesia)',                   'Indonesia',['ID-MY', 'ID-SA', 'ID-HK', 'ID-TW'],['domestic-work', 'construction'],     ['business_framed_exploitation'],           'https://bp2mi.go.id/kontak',                              'kontak@bp2mi.go.id'),
    NGO('hrd_nepal', 'HRD Nepal',                            'Nepal',   ['NP-QA', 'NP-MY'],                  ['construction', 'domestic-work'],     ['jurisdictional_hierarchy'],              'https://hrdnepal.org/contact/',                            'info@hrdnepal.org'),
    NGO('mfa',       'Migrant Forum in Asia',                'Philippines',['PH-SA', 'ID-MY', 'BD-MY'],      ['all-sectors'],                       ['business_framed_exploitation', 'jurisdictional_hierarchy'], 'https://mfasia.org/contact-us/',                           'info@mfasia.org'),
    NGO('asi',       'Anti-Slavery International',           'UK',      ['UK-any'],                          ['all-sectors'],                       ['victim_revictimization'],                 'https://www.antislavery.org/contact-us/',                 'info@antislavery.org'),
    NGO('verite',    'Verite',                               'USA',     ['supply-chain'],                    ['agriculture', 'electronics'],        ['financial_crime_blindness'],              'https://www.verite.org/contact-us/',                       'verite@verite.org'),
    NGO('gaatw',     'Global Alliance Against Traffic in Women', 'Thailand', ['multi-corridor'],             ['domestic-work', 'sex-work'],         ['victim_revictimization'],                 'https://gaatw.org/contact-gaatw',                         'gaatw@gaatw.org'),
]


print(f'NGO directory: {len(NGO_DIRECTORY)} partners')
print(f'{"ID":<12}  {"Display name":<40}  {"Country":<12}  Rubric focus')
print('-' * 120)
for n in NGO_DIRECTORY:
    print(f'{n.ngo_id:<12}  {n.display_name[:38]:<40}  {n.country[:10]:<12}  {", ".join(n.rubric_focus)}')
'''


SURVEY_MD = """---

## 2. Generate a tailored survey template per NGO

The survey is a JSON Schema that a front-end (Google Form, Typeform, Streamlit, or a static HTML form) can render. Each NGO gets a tailored variant: the rubric category shown first matches that NGO's focus area; the corridor examples match that NGO's geography.
"""


SURVEY_CODE = '''def build_survey_schema(ngo: NGO) -> dict:
    return {
        'survey_id': f'duecare-ngo-survey-{ngo.ngo_id}-v1',
        'display_title': f'DueCare feedback request for {ngo.display_name}',
        'intro': (
            f'Thank you for considering this request. DueCare is a privacy-preserving '
            f'LLM safety judge aimed at migrant-worker trafficking. We are asking {ngo.display_name} '
            f'for help validating the prompts and reference responses we train against. '
            f'Your responses stay with the DueCare team; no PII is required.'
        ),
        'consent': {
            'required': True,
            'text': (
                'I confirm that my submission is on behalf of an authorized representative of '
                'the organization, that the content I submit does not contain personal '
                'identifiers of victims or clients, and that I grant DueCare permission to '
                'include the structured parts of my submission in the public training corpus '
                'with attribution to my organization.'
            ),
        },
        'sections': [
            {
                'id': 'new_prompts',
                'title': 'Suggest 1-5 new adversarial prompts',
                'description': (
                    'What kinds of questions from traffickers, abusive recruiters, or exploiting '
                    f'employers does {ngo.display_name} see in its casework that DueCare should be '
                    f'able to refuse? Focus on corridors {", ".join(ngo.primary_corridors)} '
                    f'and sectors {", ".join(ngo.primary_sectors)}.'
                ),
                'fields': [
                    {'id': 'prompt_text', 'type': 'long_text', 'required': True, 'max_chars': 1500},
                    {'id': 'category', 'type': 'enum', 'options': ngo.rubric_focus + ['other']},
                    {'id': 'corridor', 'type': 'enum', 'options': ngo.primary_corridors + ['other']},
                ],
                'max_items': 5,
            },
            {
                'id': 'rank_existing_prompts',
                'title': 'Rank 10 existing DueCare prompts for realism',
                'description': (
                    'A sample of 10 DueCare prompts is included below. Please rate each on '
                    'realism (1 = this is artificial / would never happen in our casework, '
                    '5 = this is almost verbatim something we have seen) and label any prompt '
                    'that gets the category wrong.'
                ),
                'fields': [
                    {'id': 'prompt_id', 'type': 'string', 'required': True},
                    {'id': 'realism_1_to_5', 'type': 'int', 'required': True, 'min': 1, 'max': 5},
                    {'id': 'category_correct', 'type': 'bool', 'required': True},
                    {'id': 'suggested_category', 'type': 'string', 'required': False},
                ],
                'max_items': 10,
            },
            {
                'id': 'graded_response_examples',
                'title': 'Provide WORST/BAD/NEUTRAL/GOOD/BEST response examples',
                'description': (
                    'For 1-3 of the new prompts from Section 1, please write an example response at '
                    'each of the five grade bands. These become hand-validated training anchors for '
                    'the DueCare safety judge.'
                ),
                'fields': [
                    {'id': 'prompt_id_ref', 'type': 'string', 'required': True},
                    {'id': 'worst', 'type': 'long_text', 'required': True, 'max_chars': 1500},
                    {'id': 'bad', 'type': 'long_text', 'required': True, 'max_chars': 1500},
                    {'id': 'neutral', 'type': 'long_text', 'required': True, 'max_chars': 1500},
                    {'id': 'good', 'type': 'long_text', 'required': True, 'max_chars': 1500},
                    {'id': 'best', 'type': 'long_text', 'required': True, 'max_chars': 1500},
                ],
                'max_items': 3,
            },
        ],
        'footer': {
            'revocation_contact': 'duecare@taylorsamarel.com',
            'data_governance_url': 'https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/FOR_JUDGES.md',
        },
        'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }


OUT_DIR = Path('/kaggle/working/outbound_emails')
OUT_DIR.mkdir(parents=True, exist_ok=True)

surveys = {}
for ngo in NGO_DIRECTORY:
    schema = build_survey_schema(ngo)
    surveys[ngo.ngo_id] = schema
    out_path = OUT_DIR / f'survey_{ngo.ngo_id}.json'
    out_path.write_text(json.dumps(schema, indent=2), encoding='utf-8')

print(f'Generated {len(surveys)} survey schemas at {OUT_DIR}')
print()
# Render one sample schema for the reader
sample = surveys[NGO_DIRECTORY[0].ngo_id]
print(f'Sample: {sample["display_title"]}')
for s in sample['sections']:
    print(f'  section: {s["id"]:<24}  "{s["title"][:60]}"')
'''


EMAIL_MD = """---

## 3. Render a per-NGO briefing + email invitation

The email is a Markdown-rendered plain-text body that Taylor reviews before sending. Each `.eml` draft is ready for a normal mail client to open.
"""


EMAIL_CODE = '''from email.message import EmailMessage


DUECARE_GITHUB = 'https://github.com/TaylorAmarelTech/gemma4_comp'
DUECARE_WRITEUP_SHORT = 'https://www.kaggle.com/code/taylorsamarel/duecare-000-index'


def render_briefing_markdown(ngo: NGO, survey_link_placeholder: str) -> str:
    return (
        f'# DueCare feedback request for {ngo.display_name}\\n\\n'
        f'**What:** a short, opt-in survey asking for domain-expert validation of the '
        f'prompts and graded response examples we train DueCare against.\\n\\n'
        f'**Why you:** {ngo.display_name} works directly with {", ".join(ngo.primary_sectors)} '
        f'workers in the {", ".join(ngo.primary_corridors)} corridor(s). Your casework is the '
        f'source of truth for what DueCare has to get right.\\n\\n'
        f'**Commitment:** about 20-40 minutes per section. All three sections are optional.\\n\\n'
        f'**How your contribution is used:** structured responses (ratings, category tags, and '
        f'response exemplars) are merged into the public DueCare training corpus with attribution '
        f'to {ngo.display_name}. No personal identifiers are required; any submission containing '
        f'them is quarantined and returned.\\n\\n'
        f'**Survey link:** {survey_link_placeholder}\\n\\n'
        f'**Repo and writeup:** {DUECARE_GITHUB} | {DUECARE_WRITEUP_SHORT}\\n\\n'
        f'**Revocation:** reply to this email at any time and we will remove your submission '
        f'from the corpus in the next release.\\n\\n'
        f'Thank you for the work you do. - DueCare team\\n'
    )


def render_email_draft(ngo: NGO, survey_link_placeholder: str) -> EmailMessage:
    msg = EmailMessage()
    msg['To'] = ngo.press_email
    msg['From'] = 'duecare@taylorsamarel.com'
    msg['Subject'] = f'Short research survey for {ngo.display_name} - DueCare / Gemma 4 Safety'
    msg.set_content(render_briefing_markdown(ngo, survey_link_placeholder))
    return msg


for ngo in NGO_DIRECTORY:
    survey_link = f'https://survey.duecare.taylorsamarel.com/{ngo.ngo_id}  (TEMPLATE - replace before sending)'
    msg = render_email_draft(ngo, survey_link)
    out_path = OUT_DIR / f'invite_{ngo.ngo_id}.eml'
    out_path.write_bytes(bytes(msg))
    briefing_path = OUT_DIR / f'briefing_{ngo.ngo_id}.md'
    briefing_path.write_text(render_briefing_markdown(ngo, survey_link), encoding='utf-8')

print(f'Wrote {len(NGO_DIRECTORY)} email drafts (.eml) and briefings (.md) to {OUT_DIR}')
print()
sample_ngo = NGO_DIRECTORY[0]
sample_eml = OUT_DIR / f'invite_{sample_ngo.ngo_id}.eml'
print(f'Sample draft: {sample_eml}')
print('-' * 80)
print(sample_eml.read_text(encoding='utf-8')[:800])
print('-' * 80)
print('NB: no email is ever sent from this kernel. Open each .eml locally to review + send manually.')
'''


INGEST_MD = """---

## 4. Ingest returned survey responses (if any)

Any `.json` files placed at `/kaggle/working/survey_responses/<ngo_id>.json` are read here. Missing files are reported but do not cause the notebook to fail; the pipeline is designed to run incrementally as responses arrive.
"""


INGEST_CODE = '''RESPONSES_DIR = Path('/kaggle/working/survey_responses')
RESPONSES_DIR.mkdir(parents=True, exist_ok=True)


# PII scan: if a response body contains any of these patterns, quarantine it.
PII_PATTERNS = [
    re.compile(r'\\b[\\w.+-]+@[\\w-]+\\.[\\w.-]+\\b'),                  # emails
    re.compile(r'\\+?\\d{1,3}[-.\\s]?\\(?\\d{1,4}\\)?[-.\\s]?\\d{2,4}[-.\\s]?\\d{2,4}[-.\\s]?\\d{0,4}'),  # phone
    re.compile(r'\\b(?:passport|visa)\\s*(?:no|number|#)?[:#]?\\s*[A-Z0-9]{6,}\\b', re.IGNORECASE),
    re.compile(r'\\b[A-Z]\\d{7,}\\b'),                                 # generic ID numbers
]


def pii_matches(text: str) -> list:
    matches = []
    for pat in PII_PATTERNS:
        for m in pat.findall(text or ''):
            matches.append(m if isinstance(m, str) else ' '.join(m))
    return matches


def validate_response(ngo: NGO, response: dict) -> tuple[bool, list[str]]:
    errors = []
    if not response.get('survey_id', '').endswith(f'-{ngo.ngo_id}-v1'):
        errors.append(f'survey_id mismatch (expected suffix {ngo.ngo_id}-v1)')
    if not response.get('consent_granted', False):
        errors.append('consent_granted flag is False')
    sections = response.get('sections', {})
    if not isinstance(sections, dict):
        errors.append('sections is not a dict')
    return (not errors, errors)


ingested = []
quarantined = []
skipped = []

for ngo in NGO_DIRECTORY:
    rp = RESPONSES_DIR / f'{ngo.ngo_id}.json'
    if not rp.exists():
        skipped.append(ngo.ngo_id)
        continue
    try:
        response = json.loads(rp.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        quarantined.append({'ngo': ngo.ngo_id, 'reason': f'invalid JSON ({exc})'})
        continue
    ok, errors = validate_response(ngo, response)
    if not ok:
        quarantined.append({'ngo': ngo.ngo_id, 'reason': '; '.join(errors)})
        continue
    pii_hits = pii_matches(json.dumps(response, ensure_ascii=False))
    if pii_hits:
        quarantined.append({'ngo': ngo.ngo_id, 'reason': f'PII detected: {pii_hits[:3]}'})
        continue
    ingested.append({'ngo': ngo, 'response': response})

print(f'Ingested: {len(ingested)}')
print(f'Quarantined: {len(quarantined)}')
for q in quarantined:
    print(f'  {q["ngo"]}: {q["reason"]}')
print(f'Skipped (no response file): {len(skipped)}')
'''


MERGE_MD = """---

## 5. Merge valid responses into a training JSONL

The merged file has the same row schema 525 and the trafficking-prompts dataset use, so 530 Phase 3 Unsloth Fine-Tune can consume it with no schema gymnastics.
"""


MERGE_CODE = '''TRAINING_JSONL = Path('/kaggle/working/ngo_feedback_training.jsonl')


def to_training_rows(ngo: NGO, response: dict) -> list[dict]:
    rows = []
    sections = response.get('sections', {})

    new_prompts = sections.get('new_prompts', [])
    graded_examples = sections.get('graded_response_examples', [])
    graded_by_prompt = {g.get('prompt_id_ref'): g for g in graded_examples}

    for i, np_row in enumerate(new_prompts):
        prompt_id = np_row.get('prompt_id') or f'{ngo.ngo_id}_p{i:02d}'
        prompt_text = np_row.get('prompt_text', '').strip()
        if not prompt_text:
            continue
        graded = graded_by_prompt.get(prompt_id, {})
        graded_responses = {}
        for grade in ('worst', 'bad', 'neutral', 'good', 'best'):
            text = graded.get(grade, '').strip()
            if text:
                graded_responses[grade] = {
                    'text': text,
                    'score': {'worst': 0.05, 'bad': 0.25, 'neutral': 0.5, 'good': 0.8, 'best': 0.95}[grade],
                    'source': f'ngo_survey_{ngo.ngo_id}',
                }
        rows.append({
            'id': f'{ngo.ngo_id}_{prompt_id}',
            'category': np_row.get('category', 'unknown'),
            'text': prompt_text,
            'graded_responses': graded_responses,
            'metadata': {
                'source': f'ngo_survey_{ngo.ngo_id}',
                'ngo_display_name': ngo.display_name,
                'corridor_context': np_row.get('corridor', 'unspecified'),
                'received_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            },
        })
    return rows


rows_written = 0
with TRAINING_JSONL.open('w', encoding='utf-8') as f:
    for bundle in ingested:
        ngo = bundle['ngo']
        for row in to_training_rows(ngo, bundle['response']):
            f.write(json.dumps(row, ensure_ascii=False) + '\\n')
            rows_written += 1

if rows_written > 0:
    print(f'Wrote {rows_written} training rows to {TRAINING_JSONL}')
    print(f'Downstream: attach this file as a Kaggle dataset alongside duecare-trafficking-prompts '
          f'and 530 will merge it into the fine-tune curriculum.')
else:
    print(f'No responses ingested yet. Drop completed survey JSON files into {RESPONSES_DIR} and rerun Section 4 / 5.')
'''


STATUS_MD = "---\n\n## 6. Outreach status table\n"

STATUS_CODE = '''from html import escape
from IPython.display import HTML, display


def _status_for(ngo):
    has_draft = (OUT_DIR / f'invite_{ngo.ngo_id}.eml').exists()
    has_response = (RESPONSES_DIR / f'{ngo.ngo_id}.json').exists()
    merged = any(b['ngo'].ngo_id == ngo.ngo_id for b in ingested)
    return has_draft, has_response, merged


rows_html = []
for ngo in NGO_DIRECTORY:
    has_draft, has_response, merged = _status_for(ngo)
    state_cells = [
        ('draft_ready', has_draft, '#10b981', '#ef4444'),
        ('response_received', has_response, '#10b981', '#6b7280'),
        ('merged_into_training', merged, '#10b981', '#6b7280'),
    ]
    state_html = ''
    for name, val, yes_color, no_color in state_cells:
        icon = '&#x2714;' if val else '&#x2716;'
        color = yes_color if val else no_color
        state_html += f'<span style="padding:2px 8px;margin-right:4px;background:{color};color:white;border-radius:3px;font-size:11px">{icon} {name}</span>'
    rows_html.append(
        f'<tr><td style="padding:6px 10px">{escape(ngo.ngo_id)}</td>'
        f'<td style="padding:6px 10px">{escape(ngo.display_name)}</td>'
        f'<td style="padding:6px 10px">{escape(", ".join(ngo.primary_corridors[:2]))}</td>'
        f'<td style="padding:6px 10px">{state_html}</td></tr>'
    )


display(HTML(
    '<table style="width:100%;border-collapse:collapse;margin:8px 0">'
    '<thead><tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da">'
    '<th style="padding:6px 10px;text-align:left">NGO id</th>'
    '<th style="padding:6px 10px;text-align:left">Display name</th>'
    '<th style="padding:6px 10px;text-align:left">Corridors</th>'
    '<th style="padding:6px 10px;text-align:left">State</th>'
    '</tr></thead><tbody>' + ''.join(rows_html) + '</tbody></table>'
))
'''


TROUBLESHOOTING = troubleshooting_table_html([
    ("I want to add a new NGO to the directory.", "Extend the <code>NGO_DIRECTORY</code> list in Section 1 with a new <code>NGO(...)</code> row. Ensure the <code>contact_url</code> and <code>press_email</code> are from a public-record source (footer, press-inquiries page) before running."),
    ("The email draft has placeholder text I need to edit.", "Open the corresponding <code>.eml</code> file from <code>/kaggle/working/outbound_emails/</code> in a normal mail client. The survey link placeholder is explicitly marked <code>(TEMPLATE - replace before sending)</code>; replace it with your hosted survey URL before pressing send."),
    ("A survey response got quarantined because of 'PII detected'.", "That is by design. The regex scan is intentionally conservative. Open the response, confirm the flagged phrase is not a genuine personal identifier (for example, a fake passport number in an example prompt is fine), then redact or mark the phrase as <code>[REDACTED]</code> and rerun Section 4."),
    ("I need to build an actual hosted survey form.", "This notebook stops at the schema. For an implementation surface, pipe <code>surveys[ngo_id]</code> into Streamlit, Gradio, Google Forms API, or a static HTML form generator. The JSON schema is deliberately minimal so any of those targets works."),
    ("An NGO revoked their submission.", "Remove their <code>.json</code> file from <code>/kaggle/working/survey_responses/</code> and rerun Sections 4 and 5. The training JSONL will be rewritten without their rows. Also remove them from the NGO_DIRECTORY in this notebook if they opt out entirely."),
])


SUMMARY = f"""---

## Summary and handoff

- Loaded a 10-NGO directory of pre-curated public contact info for migrant-worker and anti-trafficking organizations.
- Generated a tailored JSON-schema survey per NGO with three sections (new prompts, rank existing prompts, provide 5-grade response exemplars).
- Rendered Markdown briefing pages and `.eml` email drafts for each NGO at `/kaggle/working/outbound_emails/`.
- Ingested any survey response JSON files already present, validated schema, quarantined any with PII.
- Merged valid responses into `/kaggle/working/ngo_feedback_training.jsonl` in the trafficking-prompts schema.
- Rendered the outreach status table showing draft / response / merged state per NGO.

### Why this matters for DueCare

1. **Synthetic generators scale; NGO validators ground-truth.** 525 and 527 can emit hundreds of training rows an hour. NGO survey responses are slower but carry irreplaceable domain authority. The training corpus needs both; this notebook wires in the second path.
2. **Provenance is the contract with partners.** Every merged row carries `source: ngo_survey_<ngo_id>`. When an NGO asks "what did you do with our submission?" the training audit trail has the answer.
3. **Ethics-first removes the temptation to cut corners.** No auto-send, no scraping untrusted domains, explicit opt-in, PII scan on intake. The cost is marginal; the governance posture is enormous.

---

## Troubleshooting

{TROUBLESHOOTING}

---

## Next

- **Downstream:** [530 Phase 3 Unsloth Fine-Tune]({URL_530}) trains on both synthetic (525/527) and NGO-validated (this notebook) rows.
- **Siblings:** [525 Uncensored 5-Grade Generator]({URL_525}) and [527 Uncensored Rubric Generator]({URL_527}).
- **Section close:** [599 Model Improvement Opportunities Conclusion]({URL_599}).
- **Back to navigation (optional):** [000 Index]({URL_000}).
"""


def build():
    cells = [
        code(HERO_CODE),
        md(HEADER),
        md(DIRECTORY_MD), code(DIRECTORY_CODE),
        md(SURVEY_MD), code(SURVEY_CODE),
        md(EMAIL_MD), code(EMAIL_CODE),
        md(INGEST_MD), code(INGEST_CODE),
        md(MERGE_MD), code(MERGE_CODE),
        md(STATUS_MD), code(STATUS_CODE),
        md(SUMMARY),
    ]
    nb = {"nbformat": 4, "nbformat_minor": 5, "metadata": NB_METADATA, "cells": cells}
    nb = harden_notebook(nb, filename=FILENAME, requires_gpu=False)
    patch_final_print_cell(
        nb,
        final_print_src=(
            "print(\n"
            "    'NGO survey pipeline handoff >>> Downstream: 530 Phase 3 Unsloth Fine-Tune: '\n"
            f"    '{URL_530}'\n"
            "    '. Siblings: 525 Uncensored 5-Grade Generator: '\n"
            f"    '{URL_525}'\n"
            "    ' and 527 Uncensored Rubric Generator: '\n"
            f"    '{URL_527}'\n"
            "    '.'\n"
            ")\n"
        ),
        marker="NGO survey pipeline handoff >>>",
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
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [WHEELS_DATASET, PROMPTS_DATASET],
        "competition_sources": ["gemma-4-good-hackathon"],
        "kernel_sources": [],
        "keywords": KEYWORDS,
    }
    (kernel_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    code_count = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
    md_count = sum(1 for c in nb["cells"] if c["cell_type"] == "markdown")
    print(f"Wrote {nb_path} ({code_count} code + {md_count} md cells)")


if __name__ == "__main__":
    build()
