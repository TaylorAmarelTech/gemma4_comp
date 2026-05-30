# Civil-society & authoritative-source intelligence (2026-05-29)

> Open-web research pass on the sources Taylor named (Mission for Migrant
> Workers, HELP for Domestic Workers, The Mekong Club, US TIP) plus adjacent
> authoritative reporting, to expand DueCare's trafficking-indicator catalog,
> modus-operandi coverage, and benchmark prompt grounding.
>
> Everything here is **public, cited reporting**. Nothing in this file is PII.
> Derived benchmark prompts are synthetic composites grounded in these patterns,
> never copies of any real case (rule 10).

## Sources reviewed

| Source | Focus | Key resource |
|---|---|---|
| **US State Dept – Trafficking in Persons Report (2024/2025)** | Global tiering, definitions, emerging trends | state.gov/reports/2024-trafficking-in-persons-report |
| **The Mekong Club** (HK) | Private-sector / financial-services anti-slavery; scam-center typologies | themekongclub.org/tools, "Unmasking Scam Centers" (2024/25) |
| **Mission for Migrant Workers** (HK) | Migrant domestic-worker casework + service reports | MFMW 2021 Service Report |
| **HELP for Domestic Workers** (HK, est. 1989) | Free legal counsel for foreign domestic workers | helpfordomesticworkers.org |
| **Justice Centre Hong Kong** | "Coming Clean" — forced-labour prevalence among HK MDWs | justicecentre.org.hk |
| **ILO / Walk Free** | Global Estimates of Modern Slavery; 11 forced-labour indicators | ilo.org |

## Consolidated indicator set

**ILO's 11 forced-labour indicators** (already the spine of the rubric): abuse of
vulnerability, deception, restriction of movement, isolation, physical/sexual
violence, intimidation & threats, retention of identity documents, withholding of
wages, debt bondage, abusive working/living conditions, excessive overtime.

**US TIP "means" of coercion** (force / fraud / coercion), expanded:
threats of serious harm, **debt manipulation**, withholding of pay, **confiscation
of identity documents**, psychological coercion, **reputational harm**, manipulation
of addictive substances, **threats to other people** (e.g. family back home).

## Modus-operandi catalog (detection-worthy patterns)

### 1. Recruitment-fee debt bondage — Hong Kong FDW mechanism (concrete)
- Legal commission cap is **10% of first-month salary**; agencies may charge nothing else.
- Reality: a Rights Exposure/Oxfam study found **70% of Filipino domestic workers paid a
  placement fee averaging ~US$1,459 — ~25x the legal maximum**.
- Mechanism: workers sign **IOUs or post-dated cheques** pre-departure; the "debt" is then
  **sold to Hong Kong collection agencies**; receipts for payment are routinely **denied**.
- MFMW 2021: **1 in 3** clients were victims of illegal recruitment / overcharging;
  **2 in 5** had no private room (live-in isolation).

### 2. Contract substitution & document control
- Original contract replaced on arrival with worse terms (lower pay, longer hours).
- **Passport + employment contract confiscated** by agency/employer on arrival ("safekeeping").
- Live-in model isolates the worker inside a private household, away from authorities.

### 3. Cyber-scam compounds (the major emerging MO — Mekong Club + US TIP)
Forced criminality: ~**120,000 forced in Myanmar + ~100,000 in Cambodia** (OHCHR 2023);
Americans lost **>=US$10B** to SE-Asia scams in 2024 (US Treasury). Five phases:
**recruitment -> transportation -> harboring/receipt -> forced criminality -> money laundering.**
- **Recruitment**: fake high-salary IT / customer-service jobs advertised on Facebook/Instagram/
  Telegram, targeting educated, computer-literate young people; lured to Bangkok then moved to
  compounds in Myanmar/Cambodia/Laos.
- **Control**: confinement, passport + phone confiscation, **debt bondage** for "training"/travel/
  accommodation, **12-18-hour days with scam-quota KPIs**; missing targets -> fines, food
  deprivation, beatings; communication monitored; pay withheld or eaten by fabricated fines;
  threats of being **re-sold** to another compound; scripted "pig-butchering" crypto/romance/
  investment personas.
- **Laundering**: scam-controlled crypto wallets, **money mules** (forced cash withdrawals),
  **smurfing** (many small deposits -> large withdrawals), synthetic-identity bank accounts.

### 4. Money mule / financial-laundering camouflage (Mekong Club financial typologies)
Behavioural / demographic / transactional red flags banks watch for: newly-created wallets
with high volume; small-deposit/large-withdrawal smurfing; transactions tied to known scam
regions; a frontline customer showing fear/confusion during a large cash withdrawal (a forced
mule). Relevant to DueCare's `financial_obfuscation_detection` dimensions.

### 5. Forced/fraudulent military recruitment (emerging — US TIP 2024)
Coercion/deception to recruit foreign nationals as fighters for Russia's war in Ukraine — a new
"means" pattern worth a corpus scenario, distinct from labour exploitation.

## Corridor & sector notes
- **PH/ID -> HK** (domestic work): the fee-debt + contract-substitution + live-in-isolation stack above.
- **Regional -> MM/KH/LA** (scam compounds): cross-border deception via Thailand; victims from across
  Asia and increasingly Africa/Latin America.
- Mekong Club sector typologies with real money/people flows: domestic servitude, fishing,
  construction, agriculture, textiles, **plus** the new "scam labour camp" sector.

## How this feeds DueCare
1. **Benchmark prompts** — synthetic composites grounded in MOs the corpus under-covers:
   cyber-scam-compound recruitment & escape, forced money-mule withdrawal, HK FDW IOU/collection-
   agency debt, contract substitution on arrival, forced military recruitment. (Generated separately;
   composite-only.)
2. **GREP rules** — new euphemism/red-flag phrases: "training fee" + confinement, "you owe us for
   your travel", scam-quota/KPI punishment language, "safekeeping" of passport, post-dated cheque /
   IOU pre-departure, "we will sell your contract".
3. **RAG documents** — short grounded notes: HK 10%-commission cap + collection-agency mechanism,
   scam-compound 5-phase typology, money-mule red flags, US TIP coercive-means list.
4. **Grading dimensions** — the new `manipulation_resistance`, `financial_obfuscation_detection`,
   and `scheme_detection` groups already align; a `forced_criminality` scheme tag is worth adding.

## Citations
- US TIP 2024/2025 — https://www.state.gov/reports/2024-trafficking-in-persons-report/ ; HK narrative https://2021-2025.state.gov/reports/2024-trafficking-in-persons-report/hong-kong/
- The Mekong Club — tools https://themekongclub.org/tools/ ; "Unmasking Scam Centers: Typologies, Tactics and Targeted Industries" https://themekongclub.org/unmasking-scam-centers-typologies-tactics-and-targeted-industries/ ; financial typologies https://www.gcffc.org/articles-and-publications/modern-slavery-typologies-for-financial-services-providers-by-the-mekong-club
- Mission for Migrant Workers 2021 Service Report (via Wikipedia/MigrationPolicy summaries)
- HELP for Domestic Workers — https://www.migrationpolicy.org/article/maid-hong-kong-protecting-foreign-domestic-workers ; DWJI placement-fee law brief https://dwji.org/wp-content/uploads/2024/02/Hong-Kong-FDW-Placement-Fee-Law.pdf
- Justice Centre HK "Coming Clean" — https://www.justicecentre.org.hk (forced-labour prevalence among MDWs)
- Scam-compound reporting — Amnesty International (2025), US Treasury OFAC actions, UN OHCHR (2023), ProPublica/PBS
