# Anonymization Policy for Duecare Examples

> Mandatory reading before adding ANY new example content (social
> media post, screenshot, message excerpt, document scan, narrative)
> to the Duecare submission. Per `.claude/rules/10_safety_gate.md`,
> the submission ships to the public and any leak is a P0.

## TL;DR

1. **Default to fully synthetic.** Use Gemma to generate a fictional
   example that mirrors the exploitation pattern, then label it
   `(composite)`.
2. **If using real content as a template:** run it through
   `scripts/redact_pii.py` first, then apply manual review.
3. **Never commit** raw harvested data (`data/drive_*`, scraping
   caches, OCR outputs) — these are gitignored.
4. **Screenshots = SVG render of synthetic text**, not photographs.

## What is PII for this project

Per `.claude/rules/10_safety_gate.md`:

**Critical (must redact):**
- Real given names, family names of individuals
- Passport / visa / national ID numbers (real)
- Phone numbers (unless on the public-NGO whitelist below)
- Personal email addresses
- Bank account numbers, IBANs
- Home addresses (street + number)
- Dates of birth (year-only is OK if useful context)

**Generalizable (rewrite at lower precision):**
- Specific cities → "a city in [country]"
- Specific employers/agencies → "a recruitment agency" UNLESS in
  public court record with case number

**Allowed verbatim:**
- Public NGO names (Polaris, IJM, ECPAT, POEA, BP2MI, MfMW HK,
  Anti-Racism Movement Beirut, etc.)
- Public hotline phone numbers (verify on official site;
  whitelist in `scripts/redact_pii.py`)
- Statute names + section numbers (ILO C029 §1, RA 8042 §6(j), etc.)
- Court cases that are AT LEAST one of: in published reporters,
  cited in NGO reports, or already on the org's public website

## How to add a new example

### Step 1 — Decide which path

| Source of inspiration | Path |
|---|---|
| Pure pattern from your head | A. Synthetic-from-scratch |
| Real social media post you want to reference | B. Redact-then-rewrite |
| Real legal document with pattern you need | C. Extract-pattern-only |

### Path A: Synthetic-from-scratch (preferred)

Use the loaded Gemma in any chat-playground notebook. Prompt:

```
Generate a synthetic example of a [SCENARIO TYPE — e.g., recruiter
WhatsApp message offering a no-fee Hong Kong domestic worker
position with hidden 90% APR loan financing]. Use these constraints:

- All names must be clearly composite (e.g., "Maria Santos", "Sita
  Tamang", "Md. Rafiqul Islam"). Tag each with "(composite)" on
  first appearance.
- All phone numbers from the +63-555 / +852-555 / +62-555 reserved-
  for-fiction range, marked "(synthetic)".
- Addresses generalized: "[redacted street], Mid-Levels, HK
  (composite)".
- Passport / national ID numbers must be obviously sequential
  (AB1234567, 1234567890123) and tagged "(synthetic)".
- Currency amounts can be realistic.
- Statute / ILO citations must be REAL (these aren't PII).
- Length: ~150-300 words.

Generate the example.
```

Save the output. Verify with `scripts/redact_pii.py --input
new_example.txt --dry-run`. Should show 0 unflagged hits.

### Path B: Redact-then-rewrite

Worst-case path; only if Path A doesn't capture a specific real
pattern you need.

```bash
# 1. Save the raw post to a SCRATCH file (NOT in the repo)
cp /tmp/raw_post.txt /tmp/scratch_redact.txt

# 2. Auto-redact
python scripts/redact_pii.py \
    --input /tmp/scratch_redact.txt \
    --output /tmp/redacted.txt \
    --audit /tmp/audit.json

# 3. Synthesize composite content into the placeholders
python scripts/redact_pii.py \
    --input /tmp/redacted.txt \
    --synthesize \
    --output /tmp/synthetic.txt

# 4. MANUAL REVIEW. Read every line. Anything that LOOKS real
#    (turn of phrase, internal jargon, date+location combo) →
#    rewrite. Pattern fidelity matters; identifying details don't.

# 5. Move the cleaned version into the JSON example file with
#    "[COMPOSITE EXAMPLE]" prefix.
rm /tmp/scratch_redact.txt /tmp/redacted.txt /tmp/synthetic.txt
```

### Path C: Extract-pattern-only

For real legal documents (e.g., a HK Court of First Instance
judgment that has the case number AND is published). The pattern is
fair to use; the parties' names are NOT once names go beyond what's
in the published reporter.

- Cite the case: `Ong v. Lim [2024] HKCFI 1234` (number + court)
- Reference the pattern in your own words, do not quote the
  document directly
- Don't include party names beyond the reporter's first-name
  initials if any party requested anonymization

## Screenshots

**Real screenshots are not allowed in this submission.** Even with
faces blurred, screenshots leak: timestamps, app version, device
chrome, contact list edges, friend reaction counts. All of those
fingerprint a real account.

Instead: render synthetic equivalents as SVG with composite text.
See `_classifier_examples.json` for the existing pattern — every
"screenshot" there is a base64-encoded SVG with rendered text, not a
photo.

To add a new SVG screenshot:

1. Generate the synthetic text content (Path A above)
2. Sketch the layout in HTML/SVG manually
3. Convert to base64 and embed:
   ```python
   import base64
   svg = '<svg xmlns="http://www.w3.org/2000/svg" ...>...</svg>'
   data_uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
   ```
4. Verify by decoding + grepping for any real-name fragments:
   ```bash
   python -c "
   import base64
   svg = base64.b64decode('<paste b64 here>').decode()
   import re
   suspect = re.findall(r'[A-Z][a-z]+\s+[A-Z][a-z]+', svg)
   print(suspect)
   "
   ```

## Public-NGO hotline whitelist

These phone numbers are ALLOWED to appear verbatim. They are
institutional lines published on the organization's official
website. New additions must be cross-referenced before whitelisting.
The full list is in `scripts/redact_pii.py:PUBLIC_HOTLINE_PREFIXES`.

| Number | Org | Source |
|---|---|---|
| +63-2-8721-1144 | POEA Anti-Illegal Recruitment Branch | poea.gov.ph |
| +852-2522-8264 | Mission for Migrant Workers HK | mfmw.com.hk |
| +62-21-2924-4800 | BP2MI Crisis Center | bp2mi.go.id |
| +977-1-4-433-401 | DoFE Nepal | dofe.gov.np |
| +880-2-984-9925 | BMET Bangladesh | bmet.gov.bd |
| +94-11-263-9277 | SLBFE Sri Lanka | slbfe.lk |
| +961-71-700-844 | Anti-Racism Movement Beirut | armlebanon.org |
| +965-2245-3636 | Kuwait Society for Human Rights | kuwaithumanrights.org |
| 1-866-487-9243 | Polaris US National Trafficking Hotline | polarisproject.org |
| +66 2 245 2380 | Issara Institute Thailand | issarainstitute.org |

## Reserved-for-fiction phone ranges

Use these prefixes when generating synthetic numbers:

- `+1-555-01XX` — RFC 5737 / E.164 reserved test range (US)
- `+63-555-XXXX` — clearly synthetic (PH 555 is unused for mobile)
- `+852-555-XXXX` — clearly synthetic (HK 555 is unused)
- `+62-555-XXXX` — clearly synthetic (ID 555 unused)
- Test domains: `example.com`, `example.org`, `example.invalid`

## Audit cadence

Run before every commit that touches example data:

```bash
# Quick scan of the chat package (where examples live)
python scripts/redact_pii.py --scan packages/duecare-llm-chat/src

# Should report 0 real hits; counts in JSON examples are
# typically false-positive (Python decorators register as
# social_handle, etc.)
```

Run before every wheel push:

```bash
# Check the generated wheel doesn't ship anything new
python -c "
import zipfile, re
with zipfile.ZipFile('kaggle/chat-playground/wheels/duecare_llm_chat-0.1.0-py3-none-any.whl') as z:
    for n in z.namelist():
        if n.endswith(('.json', '.py', '.html')):
            content = z.read(n).decode('utf-8', errors='ignore')
            for known_name in ['Jessica Sumpio', 'Nicole Cruz', 'Melly Wong', 'Wang Tzu', 'Funnylen Tanamor']:
                if known_name in content:
                    print(f'LEAK: {n} contains {known_name!r}')
                    break
"
```

## What to do if you find a leak

1. **Stop**. Don't commit anything else until contained.
2. **Audit scope**: `git log -S "leaked-name"` to find when it
   entered.
3. **Untrack**: `git rm --cached <file>` and `.gitignore` the path.
4. **Commit the removal** with a clear message ("untrack PII; see
   docs/anonymization_policy.md").
5. **Force-push history rewrite** ONLY if (a) the repo is public
   AND (b) the leak is critical PII (real names + identifying
   details). For low-severity items, the in-history copy is
   acceptable provided the latest commit is clean.
6. **If history-rewrite chosen**: `git filter-repo --path <path>
   --invert-paths`, force-push, notify any forks.
