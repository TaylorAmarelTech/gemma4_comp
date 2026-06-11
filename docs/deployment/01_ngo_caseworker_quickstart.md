# Path 1 — Caseworker quickstart

Read this on day 1 of a DueCare workbench pilot. It walks through
the four workflows a caseworker will use most: chat triage, document
review, complaint drafting, and safe sharing.

All worker names in examples below are composite (Maria, Ramesh,
Sita) per the project's safety-gate rule on PII.

## The workbench at a glance

When you run `duecare workbench`, the UI opens at
`http://localhost:8080`. Six pages matter for daily use:

| Page | What it does | When you use it |
|------|--------------|-----------------|
| **Chat** | Conversational triage. Paste a worker message, ask the persona to assess. | First contact with a new case |
| **Process** | Bulk file review. Drop in a ZIP of WhatsApp exports, a folder of contract PDFs, or a CSV of intake records. | Reviewing a case file or batch of intake forms |
| **Extraction** | Pull structured facts (corridor, fee amounts, statute violations, ILO indicators) out of unstructured text. | Building the case-fact card |
| **Templates** | 36 pre-filled complaint and narrative templates. Gemma 4 fills the case-specific blanks. | Drafting any formal complaint or referral |
| **Knowledge** | Lookup: corridor fee cap, NGO contact, ILO convention, statute reference. | Quick fact-check during a call |
| **Status** | What the workbench knows right now. Activity log, last sync, last fine-tune. | Daily check-in / troubleshooting |

## Workflow 1: Chat triage

You receive a WhatsApp message from a worker, peer NGO, or hotline.

1. Open the **Chat** page.
2. Set the persona to `caseworker_active` (or `ngo_intake` for first
   contact; `lawyer_research` for legal questions; full list in the
   persona selector).
3. Paste the worker's message into the chat input.
4. The workbench runs the message through:
   - **GREP layer**: 300 deterministic detection rules. Any hit
     shows up in the activity log with severity + citation +
     indicator interpretation.
   - **RAG layer**: pulls relevant knowledge documents based on
     keywords.
   - **Gemma 4**: composes a response grounded in the GREP + RAG
     evidence.
5. Read the response. The activity log on the right shows exactly
   which detection rules fired and which RAG documents informed the
   answer. If something looks wrong, you can see why.

Example case (composite — Maria, PH→HK domestic worker):

> Worker message: "My agent in Manila wants PHP 50,000 for training
> and medical, deducted from my Hong Kong salary over 6 months."

Expected workbench output:
- GREP hits: `b_fee_camouflage_training_medical` (high),
  `c_salary_deduction_for_recruitment_cost` (high)
- RAG citations: POEA MC 14-2017, HK Employment Ordinance,
  ILO C181 Art. 7
- Suggested response: explain why this is unlawful under both
  origin- and destination-country rules, refer to Mission for
  Migrant Workers HK or Damayan if she is already in HK, point to
  the PH→HK fee refund demand template

## Workflow 2: Document review

You have a recruitment contract, a scanned job ad, or a chat
screenshot from the worker.

1. Open the **Process** page.
2. Drop in the file (ZIP / CSV / JSONL / PDF / image / TXT).
3. The workbench classifies each chunk and routes it:
   - Text and extractable PDF pages → chunked locally, run through
     GREP + RAG + Gemma 4
   - Scanned PDFs and images → flagged as OCR + Gemma 4 vision work
     items. You see them queued explicitly so the UI never claims a
     scanned file has been read when it has only been queued.
4. Each chunk produces a case-fact card: extracted entities, ILO
   indicators, statute violations, suggested follow-up actions.

Example case (composite — Ramesh, NP→Qatar construction):

> Document: scanned employment contract showing salary "QAR 800/mo,
> minus QAR 200/mo for accommodation, minus QAR 150/mo for
> recruitment cost recovery".

Expected case-fact card:
- Corridor: NP → Qatar, construction sector
- Monthly net: QAR 450 (below ILO minimum-wage threshold for the
  corridor)
- Indicators: deceptive contract terms, deduction for recruitment
  cost (illegal under Nepal FEA 2007 + Qatar Law 15/2017)
- Suggested actions: file with Nepal DoFE, refer to Pravasi Nepali
  Coordination Committee, demand contract substitution proof

## Workflow 3: Complaint drafting

You have established the case facts. Now draft a formal complaint.

1. Open the **Templates** page.
2. Pick a template. The selector groups them:
   - Origin-country regulators (PH DMW, ID BP2MI, NP DoFE, BD BMET,
     VN DOLAB)
   - Destination-country regulators (HK Labour Dept, SA MHRSD, UAE
     MoHRE, Qatar MoL, US DOL WHD, AU FWO, KR EPS, TW MOL, SG MOM,
     IL PIBA, CA SAWP)
   - Referral pathways (NGO intake, IOM referral, UK NRM, Polaris
     hotline, CBP e-Allegation)
   - Specialised narrative templates (T-Visa affidavit,
     anti-retaliation TRO, witness statement, restitution
     calculation, compound-scam victim affidavit, NGO survivor
     narrative, worker first-contact script, journalist tip brief,
     supplier audit finding letter, UNGP/OECD remediation request)
3. The template loads with statute citations already filled in.
   Only the case-specific blanks are empty (`{{worker_name}}`,
   `{{contract_signing_date}}`, `{{fee_amount}}`, etc.).
4. Click **Auto-fill from case** to pull whatever the workbench
   already knows from the chat or process session. Manual overrides
   take priority over the auto-fill — that is your final-word
   guarantee.
5. For remaining blanks, hit **Verify via Gemma 4**. The model
   reads the case bundle and proposes values, with provenance tags
   (`manual` / `bundle_hint` / `gemma` / `missing`) on each field.
   Review and accept.
6. Click **Save Draft** to keep the complaint in your local case
   file. Nothing leaves the laptop.

## Workflow 4: Safe sharing

You want to refer the case to a peer NGO, file with a regulator,
or contribute the pattern to a shared knowledge hub.

1. Open the current case in the workbench.
2. Click **Share**.
3. Pick the destination:
   - Peer NGO (email export)
   - Regulator (formatted complaint)
   - Knowledge hub (anonymised pattern envelope)
4. The anonymisation gate runs. It detects PII per
   `configs/duecare/domains/trafficking/pii_spec.yaml`:
   - Names → tagged placeholder (`{{worker}}`)
   - Passport / national ID / phone → redacted
   - Cities → generalised to "a city in {country}"
   - Employer names → "a recruitment agency" unless the case is
     already in a public court record with case number
   - Country names, statute names, ILO convention numbers → kept
5. Review the redacted envelope before sending. The original PII is
   SHA-256 hashed for audit; the plaintext is not in the envelope.
6. Send. The original case stays on your laptop.

## Personas you will use most

- `caseworker_active` — for managing an open case
- `ngo_intake` — for first contact, screening, and intake
  documentation
- `lawyer_research` — for legal-research questions, statute lookups,
  precedent citations
- `worker_first_person` — when role-playing or drafting messaging
  the worker themselves will read
- `survivor_peer_advocate` — for trauma-informed framing in
  drafting

Other useful ones for specific contexts: `regulator_audit` (filing
with a regulator), `journalist_fact_check` (drafting press
materials), `peer_supporter` (helpline volunteer work),
`embassy_officer` (consular case referrals), `medical_clinician_screening`
(when health screening is part of the intake),
`financial_intelligence_unit_officer` (when financial-crime
referral makes sense).

## When the workbench is wrong

Three common failure modes and what to do:

1. **The model hallucinates a statute that does not exist.**
   - Check the activity log. If a GREP citation does not show up
     there, the model invented it. Override the template's citation
     field manually.
   - File the failure in `STATUS.md` under "rubric tuning needed for
     {corridor}". The next sync from the knowledge hub will likely
     have the corrected reference.

2. **The corridor fee cap is out of date.**
   - Open the Knowledge page, look up the corridor.
   - If the cap is stale, override in the complaint draft and note
     the source you are using.
   - File a knowledge-hub envelope flagging the update so other
     member NGOs pick up the correction. (Path 2 workflow.)

3. **A non-trafficking message is being treated as trafficking.**
   - Some GREP rules are intentionally sensitive (worker FAQ
     triggers exist precisely to prevent over-refusal). Use the
     `worker_first_person` or `peer_supporter` persona to get a
     less-alarmed framing.
   - If a specific rule is over-triggering, file it in the activity
     log and we can tune the regex.

## Where to ask for help

- Workbench bug or weird output: paste the activity log into a
  GitHub issue at `TaylorAmarelTech/gemma4_comp` (mark as a bug,
  attach screenshot, do NOT attach worker PII).
- Knowledge gap: open the corridor-tuning conversation with the
  DueCare team. We will help you author the missing rule.
- Trust-boundary question: read the trust-boundary section of
  [`01_ngo_pilot_brief.md`](01_ngo_pilot_brief.md), then ask the
  DueCare team if anything is unclear.

## See also

- [`01_ngo_pilot_brief.md`](01_ngo_pilot_brief.md) — operator-side
  decision brief
- [`02_network_hub_bootstrap.md`](02_network_hub_bootstrap.md) — if
  your NGO grows into a regional coordinator
- `.claude/rules/10_safety_gate.md` — full PII rules
- `.claude/rules/70_workbench_ui_primitives.md` — UI convention
  reference for advanced operators
