# Legal-claim register (with freshness / recheck flags)

Generated from `configs/duecare/legal_claims.json`; freshness evaluated as of 2026-07-10. Claims flagged RECHECK are potentially outdated and must be re-verified against a primary source before a grounded answer relies on them. This is not legal advice.

**22 claims -- 5 flagged for recheck.**

| id | jurisdiction | binding | volatility | as_of | recheck_after | flag |
|---|---|---|---|---|---|---|
| `bd_overseas_employment` | BD | binding_domestic | high | 2026-07-10 | 2026-10-01 | **RECHECK** |
| `eu_forced_labour_regulation` | EU | binding_domestic | high | 2026-07-10 | 2026-12-01 | **RECHECK** |
| `np_foreign_employment_fees` | NP | binding_domestic | high | 2026-07-10 | 2026-10-01 | **RECHECK** |
| `ph_placement_fee` | PH | binding_domestic | high | 2026-07-10 | 2026-10-01 | **RECHECK** |
| `sa_kafala_reform_2025` | SA | binding_domestic | high | 2026-07-10 | 2026-10-01 | **RECHECK** |
| `rantsev_2010` | Council of Europe (ECtHR) | binding_where_applicable | low | 2026-07-10 | 2028-01-01 | ok |
| `siliadin_2005` | Council of Europe (ECtHR) | binding_where_applicable | low | 2026-07-10 | 2028-01-01 | ok |
| `hk_money_lending_cap` | HK | binding_domestic | medium | 2026-07-10 | 2027-06-01 | ok |
| `id_migrant_worker_protection` | ID | binding_domestic | medium | 2026-07-10 | 2027-06-01 | ok |
| `qa_wage_protection` | QA | binding_domestic | medium | 2026-07-10 | 2027-06-01 | ok |
| `uk_modern_slavery_act` | UK | binding_domestic | medium | 2026-07-10 | 2027-06-01 | ok |
| `kozminski_1988` | US | historical_superseded_by_statute | low | 2026-07-10 | 2028-01-01 | ok |
| `us_tvpa_1589` | US | binding_domestic | low | 2026-07-10 | 2028-01-01 | ok |
| `c029_definition` | international | binding_where_ratified | low | 2026-07-10 | 2028-01-01 | ok |
| `c029_vs_indicators` | international | non_binding_guidance | medium | 2026-07-10 | 2027-06-01 | ok |
| `ilo_indicators_2025` | international | non_binding_guidance | medium | 2026-07-10 | 2027-06-01 | ok |
| `c095_wage_deductions` | international | binding_where_ratified | low | 2026-07-10 | 2028-01-01 | ok |
| `c181_recruitment_fees` | international | binding_where_ratified | medium | 2026-07-10 | 2027-06-01 | ok |
| `c189_domestic_workers` | international | binding_where_ratified | medium | 2026-07-10 | 2027-06-01 | ok |
| `palermo_elements` | international | binding_where_ratified | low | 2026-07-10 | 2028-01-01 | ok |
| `stat_migrant_workers` | international | estimate | medium | 2026-07-10 | 2027-01-01 | ok |
| `stat_modern_slavery` | international | estimate | medium | 2026-07-10 | 2027-06-01 | ok |

## Claims
### c029_definition  (international, definition)
> The ILO Forced Labour Convention No. 29 (1930) defines forced or compulsory labour as work exacted under the menace of a penalty and for which the person has not offered themselves voluntarily.

- **Authority:** ILO Convention No. 29 (treaty) -- <https://normlex.ilo.org/dyn/nrmlx_en/f?p=NORMLEXPUB:12100:::NO:12100:P12100_ILO_CODE:C029:NO>
- **Applies to:** states that have ratified C29; gives the internationally accepted definition
- **Exceptions:** narrow C29 exclusions (e.g. compulsory military service, normal civic obligations, prison labour under conditions, emergencies)
- **Binding:** binding_where_ratified | **effective_from:** 1932-05-01 | **as_of:** 2026-07-10 | **volatility:** low
- **Recheck after 2028-01-01:** definitional and stable; re-verify only on a new protocol or authoritative reinterpretation
- **Caveats:** the DEFINITION is in C29; the operational warning SIGNS are in separate ILO indicator guidance (see c029_vs_indicators)

### c029_vs_indicators  (international, indicator_guidance)
> Debt bondage and retention of identity documents are ILO 'indicators of forced labour' (warning signs), not the C29 definition itself. They are strongest in combination and must be assessed from the victim's perspective; no single indicator is automatically conclusive.

- **Authority:** ILO Indicators of Forced Labour (2025 revised edition) (ilo_guidance) -- <https://www.ilo.org/publications/ilo-indicators-forced-labour-1>
- **Applies to:** frontline identification (inspectors, NGOs, caseworkers)
- **Exceptions:** none recorded
- **Binding:** non_binding_guidance | **effective_from:** 2025-11-01 | **as_of:** 2026-07-10 | **volatility:** medium
- **Recheck after 2027-06-01:** the indicator guidance was REVISED in 2025 (first major revision since 2012); wording/interpretation may be refined again
- **Caveats:** do NOT attribute the indicators to C29 as if the convention text lists them; the 2025 edition keeps the same 11 indicators but changes their interpretation (victim-perspective; migrant-status vulnerability; ongoing deception)

### ilo_indicators_2025  (international, indicator_guidance)
> The ILO's eleven indicators of forced labour are: abuse of vulnerability, deception, restriction of movement, isolation, physical/sexual violence, intimidation and threats, retention of identity documents, withholding of wages, debt bondage, abusive working and living conditions, and excessive overtime.

- **Authority:** ILO Indicators of Forced Labour (2025 revised edition) (ilo_guidance) -- <https://www.ilo.org/sites/default/files/2025-11/ILO%20Indicators%20of%20Forced%20Labour%202025.pdf>
- **Applies to:** identification and screening; not a legal finding
- **Exceptions:** none recorded
- **Binding:** non_binding_guidance | **effective_from:** 2025-11-01 | **as_of:** 2026-07-10 | **volatility:** medium
- **Recheck after 2027-06-01:** 2025 revised edition is current; watch for the next revision and country-specific adaptations
- **Caveats:** the 2025 edition emphasises assessing every indicator FROM THE VICTIM'S PERSPECTIVE and treats migrant status / irregular residency as an explicit vulnerability factor

### c095_wage_deductions  (international, rule)
> The ILO Protection of Wages Convention No. 95 provides that deductions from wages are permitted only under conditions and to the extent prescribed by national laws or regulations, a collective agreement, or an arbitration award. It is not a blanket bonded-labour rule.

- **Authority:** ILO Convention No. 95 (treaty) -- <https://normlex.ilo.org/dyn/nrmlx_en/f?p=NORMLEXPUB:12100:0::NO:12100:P12100_INSTRUMENT_ID:312240:NO>
- **Applies to:** states that have ratified C95; wage deduction practices
- **Exceptions:** deductions authorised by national law, collective agreement, or arbitration award
- **Binding:** binding_where_ratified | **effective_from:** 1952-09-24 | **as_of:** 2026-07-10 | **volatility:** low
- **Recheck after 2028-01-01:** convention text stable; the operative detail is national implementing law, which varies and changes
- **Caveats:** whether a specific 'security' withholding is unlawful depends on the applicable NATIONAL law, not on C95 alone; analyse forced-labour indicators (wage withholding) separately from the C95 deduction rule

### c181_recruitment_fees  (international, rule)
> The ILO Private Employment Agencies Convention No. 181 (Article 7(1)) sets a general prohibition on charging workers, directly or indirectly, recruitment fees or related costs. Article 7(2) allows the competent authority to authorise exceptions for specified categories after consultation. Binding effect depends on ratification and domestic implementation.

- **Authority:** ILO Convention No. 181, Article 7 (treaty) -- <https://www.ilo.org/resource/other/c181-private-employment-agencies-convention-1997>
- **Applies to:** private employment agencies in states that ratified C181
- **Exceptions:** Art 7(2) authorised exceptions for specified worker categories (e.g. some rules set a lower maximum fee for domestic workers/au pairs, a wage-percentage cap for artists/models/athletes, or fees payable only on successful placement)
- **Binding:** binding_where_ratified | **effective_from:** 2000-05-10 | **as_of:** 2026-07-10 | **volatility:** medium
- **Recheck after 2027-06-01:** the ILO 'Guide to private employment agencies' was revised (2025) and the ILO fair-recruitment definition of fees/related costs is actively applied; national exception lists change
- **Caveats:** do NOT state 'C181 prohibits ANY worker-paid fee' without the Art 7(2) exceptions, the ratification condition, and domestic law; the ILO general principle is 'employer pays'; the ILO fair-recruitment definition of recruitment fees and related costs (2019) is the operative detail

### c189_domestic_workers  (international, rule)
> The ILO Domestic Workers Convention No. 189 (2011), where a state has ratified and implemented it, sets minimum standards for domestic workers including the right to communicate, weekly rest, and regular payment of wages.

- **Authority:** ILO Convention No. 189 (treaty) -- <https://www.ilo.org/resource/other/c189-domestic-workers-convention-2011>
- **Applies to:** domestic workers in ratifying states
- **Exceptions:** scope and effect depend on national implementing law; not all destination states have ratified
- **Binding:** binding_where_ratified | **effective_from:** 2013-09-05 | **as_of:** 2026-07-10 | **volatility:** medium
- **Recheck after 2027-06-01:** ratification list grows over time; check whether the specific destination state is bound
- **Caveats:** many Gulf destination states have NOT ratified C189; do not assume it applies to a given corridor

### ph_placement_fee  (PH, rule)
> Philippine rules (Department of Migrant Workers, successor to POEA) impose a ZERO placement fee for household service workers / domestic workers deployed abroad, and no placement fee for workers bound for designated 'no-placement-fee' destination countries. Some other land-based categories may historically be charged a placement fee capped around one month's basic salary, but the no-fee list is expanding.

- **Authority:** DMW rules; RA 10361 (Domestic Workers Act / Batas Kasambahay); DMW Advisory No. 24-2024 (administrative_rule) -- <https://dmw.gov.ph/archives/v1/resources/dsms/DMW/ISN-EXT/2024/DMW-ADVISORY-24-2024.pdf>
- **Applies to:** Filipino overseas workers by category and destination
- **Exceptions:** zero fee for domestic/household service workers; zero fee for deployment to a designated no-placement-fee country (e.g. Qatar per Qatar Law 14/2004 Art 33); possible capped placement fee for some other land-based categories
- **Binding:** binding_domestic | **effective_from:** None | **as_of:** 2026-07-10 | **volatility:** high
- **Recheck after 2026-10-01:** DMW is a young agency (replaced POEA in 2022) issuing frequent circulars/advisories; the no-placement-fee country list is actively expanding
- **Caveats:** do NOT state 'Philippine law bans ALL recruitment fees for EVERY OFW'; resolve occupation + destination + fee type + effective date first; PHP 50,000 cannot be judged excessive from the amount alone; a zero-fee category makes any placement fee impermissible, otherwise the cap depends on approved salary and the type of charge

### hk_money_lending_cap  (HK, rule)
> Under Hong Kong's Money Lenders Ordinance (Cap. 163), since 30 December 2022 the statutory interest-rate cap is 48% per year and a loan whose effective rate exceeds 36% per year is presumed to be an extortionate transaction (down from 60% and 48% respectively).

- **Authority:** Money Lenders Ordinance (Cap. 163), Hong Kong (domestic_law) -- <https://www.info.gov.hk/gia/general/202212/29/P2022122800417.htm>
- **Applies to:** loans falling within the Hong Kong Money Lenders Ordinance
- **Exceptions:** applies only if the loan is governed by HK law; a foreign loan or a later novation is not automatically within Cap. 163
- **Binding:** binding_domestic | **effective_from:** 2022-12-30 | **as_of:** 2026-07-10 | **volatility:** medium
- **Recheck after 2027-06-01:** the caps were static 1980-2022 then changed; a future review could move them again
- **Caveats:** a 68% APR loan is only presumptively extortionate IF Cap. 163 applies; keep the jurisdictional condition explicit; do not label loan-proceeds collection 'money laundering' automatically; that needs the offence elements, a proceeds nexus, jurisdiction, and mental state

### palermo_elements  (international, definition)
> Under the UN Palermo Protocol, adult trafficking requires three elements: an ACT (recruitment, transport, transfer, harbouring, receipt), a MEANS (threat, force, coercion, fraud, deception, abuse of power or of a position of vulnerability, payments to a controller), and a PURPOSE of exploitation. For a child, the MEANS element is not required.

- **Authority:** UN Protocol to Prevent, Suppress and Punish Trafficking in Persons (Palermo Protocol) (treaty) -- <https://www.unodc.org/e4j/en/tip-and-som/module-13/key-issues/international-legal-frameworks-and-definitions.html>
- **Applies to:** criminal definition of trafficking; implemented via domestic law
- **Exceptions:** the child rule drops the means element
- **Binding:** binding_where_ratified | **effective_from:** 2003-12-25 | **as_of:** 2026-07-10 | **volatility:** low
- **Recheck after 2028-01-01:** definitional; domestic implementing law varies
- **Caveats:** exploitation ALONE is insufficient for adult trafficking; report which of act/means/purpose are supported, missing, or inferred; never assert a criminal finding

### eu_forced_labour_regulation  (EU, reform)
> The EU Forced Labour Regulation (2024/3015) prohibits placing, making available on, or exporting from the EU market any product made with forced labour at any supply-chain stage. It entered into force on 13 December 2024 and BECOMES APPLICABLE on 14 December 2027.

- **Authority:** Regulation (EU) 2024/3015 (domestic_law) -- <https://single-market-economy.ec.europa.eu/single-market/goods/forced-labour-regulation_en>
- **Applies to:** products on the EU market (EU and non-EU forced labour in the supply chain)
- **Exceptions:** none recorded
- **Binding:** binding_domestic | **effective_from:** 2027-12-14 | **as_of:** 2026-07-10 | **volatility:** high
- **Recheck after 2026-12-01:** guidelines and databases are being developed before the Dec 2027 application date; do not describe it as currently enforceable
- **Caveats:** NOT yet applicable (applies 14 Dec 2027); state it as forthcoming, not in-force enforcement; a product-market ban, distinct from individual worker rights

### sa_kafala_reform_2025  (SA, reform)
> Saudi Arabia announced (June 2025) the end of its kafala sponsorship system, moving to formal contracts managed via the Qiwa digital platform, with reforms letting workers change jobs after a contract ends and leave the country after due notice.

- **Authority:** Saudi Ministry of Human Resources and Social Development (as reported) (administrative_rule) -- <https://www.walkfree.org/news/2025/saudi-arabia-ends-the-kafala-system-to-strengthen-worker-rights/>
- **Applies to:** migrant workers in Saudi Arabia (reported ~13 million)
- **Exceptions:** domestic workers are often excluded from standard labour-law protections and may not immediately benefit
- **Binding:** binding_domestic | **effective_from:** 2025-01-01 | **as_of:** 2026-07-10 | **volatility:** high
- **Recheck after 2026-10-01:** very recent reform; implementation is evolving, prior Gulf reform promises fell short, and domestic-worker coverage is uncertain; verify current status against a primary/official source before relying on it
- **Caveats:** do NOT state kafala is fully abolished in practice; describe the announced reform + implementation uncertainty + the domestic-worker carve-out; verify against an official Saudi source, not only advocacy/news reporting

### stat_migrant_workers  (international, statistic)
> The ILO estimated 169 million international migrant workers in 2019; a later 2022 estimate put migrants in destination-country labour forces at 167.7 million. Always cite the year.

- **Authority:** ILO Global Estimates on International Migrant Workers (statistic) -- <https://www.ilo.org/resource/news/international-migrants-are-vital-force-global-labour-market>
- **Applies to:** global statistic
- **Exceptions:** none recorded
- **Binding:** estimate | **effective_from:** 2022-01-01 | **as_of:** 2026-07-10 | **volatility:** medium
- **Recheck after 2027-01-01:** ILO updates these estimates periodically; a newer edition may supersede the 2019/2022 figures
- **Caveats:** never cite '169 million' without the 2019 year; the 2019 and 2022 figures measure slightly different populations

### stat_modern_slavery  (international, statistic)
> The 2021 joint global estimate put 50 million people in modern slavery on any given day: 27.6 million in forced labour and 22 million in forced marriage. This is not a trafficking count.

- **Authority:** ILO / Walk Free / IOM Global Estimates of Modern Slavery (2022, for 2021) (statistic) -- <https://www.ilo.org/publications/major-publications/global-estimates-modern-slavery-forced-labour-and-forced-marriage>
- **Applies to:** global statistic
- **Exceptions:** none recorded
- **Binding:** estimate | **effective_from:** 2022-09-01 | **as_of:** 2026-07-10 | **volatility:** medium
- **Recheck after 2027-06-01:** the next joint global estimate will supersede the 2021 figures; check for a newer edition
- **Caveats:** keep the 2021 date and the forced-labour vs forced-marriage components explicit; do not present it as a count of trafficking victims

### rantsev_2010  (Council of Europe (ECtHR), precedent)
> In Rantsev v. Cyprus and Russia (2010) the European Court of Human Rights held that human trafficking falls within the scope of Article 4 of the European Convention on Human Rights, and identified three positive state obligations: (1) put in place a legislative/administrative framework to prohibit and punish trafficking; (2) take operational measures to protect actual or potential victims in certain circumstances; and (3) investigate situations of potential trafficking.

- **Authority:** European Court of Human Rights, Rantsev v. Cyprus and Russia, App. no. 25965/04 (7 Jan 2010) (court_precedent) -- <https://sherloc.unodc.org/cld/case-law-doc/traffickingpersonscrimetype/_irb/2010/rantsev_v._cyprus_and_russia.html>
- **Applies to:** Council of Europe member states bound by the ECHR; persuasive elsewhere
- **Exceptions:** binds ECHR states; not directly binding outside the Council of Europe
- **Binding:** binding_where_applicable | **effective_from:** 2010-01-07 | **as_of:** 2026-07-10 | **volatility:** low
- **Recheck after 2028-01-01:** landmark and stable, but later ECtHR judgments refine Article 4 obligations; check for newer Grand Chamber authority
- **Caveats:** verify the holding against the primary judgment before quoting; do not state it creates obligations for non-ECHR states

### siliadin_2005  (Council of Europe (ECtHR), precedent)
> In Siliadin v. France (2005) the European Court of Human Rights held that a migrant domestic worker (a minor whose passport was taken and who was made to work unpaid, long hours) was held in 'servitude', and that Article 4 ECHR imposes positive obligations on states to criminalise and effectively punish servitude and forced labour.

- **Authority:** European Court of Human Rights, Siliadin v. France, App. no. 73316/01 (26 Jul 2005) (court_precedent) -- <https://hudoc.echr.coe.int/eng?i=001-69891>
- **Applies to:** Council of Europe member states; migrant domestic-worker exploitation
- **Exceptions:** binds ECHR states; persuasive elsewhere
- **Binding:** binding_where_applicable | **effective_from:** 2005-07-26 | **as_of:** 2026-07-10 | **volatility:** low
- **Recheck after 2028-01-01:** foundational Article 4 servitude case; check for refinements in later ECtHR jurisprudence
- **Caveats:** 'servitude' and 'forced labour' are distinct thresholds under Article 4; verify which was found before quoting

### kozminski_1988  (US, precedent)
> In United States v. Kozminski, 487 U.S. 931 (1988), the U.S. Supreme Court held that 'involuntary servitude' under 18 U.S.C. sec.241/1584 requires compulsion by physical restraint/injury or by legal coercion, and that purely psychological coercion was insufficient. This narrow reading prompted Congress to enact the broader forced-labour and trafficking definitions of the Trafficking Victims Protection Act (TVPA) 2000.

- **Authority:** U.S. Supreme Court, United States v. Kozminski, 487 U.S. 931 (1988) (court_precedent) -- <https://supreme.justia.com/cases/federal/us/487/931/>
- **Applies to:** historical interpretation of the pre-TVPA involuntary-servitude statutes
- **Exceptions:** the TVPA (2000) subsequently broadened the federal forced-labour definition to include serious harm and psychological coercion
- **Binding:** historical_superseded_by_statute | **effective_from:** 1988-06-29 | **as_of:** 2026-07-10 | **volatility:** low
- **Recheck after 2028-01-01:** stable as history; the operative CURRENT federal standard is the TVPA (18 U.S.C. sec.1589), which should be cited for present-day forced-labour analysis
- **Caveats:** do NOT cite Kozminski as the current federal forced-labour standard; it is retained as context that explains why the TVPA broadened the definition (build-upon-not-replace example)

### us_tvpa_1589  (US, rule)
> The current U.S. federal forced-labour standard, 18 U.S.C. sec.1589 (Trafficking Victims Protection Act), criminalises knowingly obtaining labour or services by any of: force or threat of force; serious harm or threats of serious harm (which expressly includes psychological, financial, or reputational harm sufficient to compel a reasonable person in the same circumstances); abuse or threatened abuse of law or legal process; or a scheme to make the person believe they or another would suffer serious harm or physical restraint. It broadened the narrow physical/legal-coercion reading of Kozminski.

- **Authority:** 18 U.S.C. sec.1589 (Trafficking Victims Protection Act) (domestic_law) -- <https://www.law.cornell.edu/uscode/text/18/1589>
- **Applies to:** US federal forced-labour prosecutions; the operative current standard
- **Exceptions:** a criminal charge requires proof of the statutory elements to a criminal standard; this is not an automatic finding
- **Binding:** binding_domestic | **effective_from:** 2000-10-28 | **as_of:** 2026-07-10 | **volatility:** low
- **Recheck after 2028-01-01:** core statute is stable; the TVPA is periodically reauthorised (TVPRA) and case law refines 'serious harm', so check for amendments
- **Caveats:** cite THIS, not Kozminski, for the current US forced-labour standard; psychological/financial coercion CAN qualify as 'serious harm' here (the key difference from Kozminski)

### bd_overseas_employment  (BD, rule)
> Bangladesh's Overseas Employment and Migrants Act 2013 governs labour migration, and the Bureau of Manpower, Employment and Training (BMET) sets migration-cost ceilings that vary by destination and worker category (for example a much lower fixed cost for female workers to several Gulf/Asia destinations, and suggested ceilings of roughly Tk 44,000-84,000 for some markets; the government-fixed cost to Saudi Arabia has been about Tk 1.65 lakh).

- **Authority:** Overseas Employment and Migrants Act 2013; Bureau of Manpower, Employment and Training (BMET) (domestic_law) -- <https://webapps.ilo.org/dyn/migpractice/docs/169/Act.pdf>
- **Applies to:** Bangladeshi migrant workers recruited through licensed agencies, by destination and category
- **Exceptions:** BMET ceilings vary by destination country and worker category and are periodically revised; the Act's cost controls are weakly enforced in practice: workers report paying far more than the ceiling (BBS survey average ~Tk 478,000; Saudi-bound ~Tk 3.5-4 lakh)
- **Binding:** binding_domestic | **effective_from:** 2013-01-01 | **as_of:** 2026-07-10 | **volatility:** high
- **Recheck after 2026-10-01:** BMET migration-cost ceilings and government-fixed costs change; verify the current per-destination ceiling against an official BMET/Probashi source
- **Caveats:** the BMET ceiling is the RULE; actual costs paid are typically far higher, so do not assume the worker was lawfully charged; verify against an official BMET source, not only news/NGO reporting

### id_migrant_worker_protection  (ID, rule)
> Indonesia's Law No. 18 of 2017 on the Protection of Indonesian Migrant Workers exempts migrant workers from paying placement fees (Article 30(1)) -- the 'zero-cost placement' policy -- and prohibits charging workers for recruitment services; the guarantee-deposit and placement costs fall on the licensed placement agency (PrEA).

- **Authority:** Law of the Republic of Indonesia No. 18 of 2017, Article 30(1) (domestic_law) -- <https://asean.org/wp-content/uploads/2016/05/Law-of-Indonesia-No-18-of-2017-on-Protection-of-Indonesian-Migrant-Workers.pdf>
- **Applies to:** Indonesian migrant workers placed abroad
- **Exceptions:** full zero-cost implementation depends on bilateral 'one-channel' agreements (e.g. with Malaysia) and destination/sector; certain components have been debated and phased; verify which costs are covered for a given corridor
- **Binding:** binding_domestic | **effective_from:** 2017-11-22 | **as_of:** 2026-07-10 | **volatility:** medium
- **Recheck after 2027-06-01:** the statute is stable but implementing regulations and bilateral one-channel agreements evolve; verify the zero-cost coverage for the specific corridor
- **Caveats:** zero-cost is the RULE; enforcement and corridor coverage vary, so do not assume the worker paid nothing; verify against the official law / BP2MI implementing regulations

### np_foreign_employment_fees  (NP, rule)
> Nepal's 'Free Visa, Free Ticket' policy (a 2015 directive under the Foreign Employment Act 2007) requires the foreign employer to bear the visa and air-ticket costs for Nepali migrant workers going to seven destinations (Oman, Bahrain, Saudi Arabia, UAE, Kuwait, Qatar, Malaysia). A Nepali recruitment agency may charge a worker a service fee not exceeding NPR 10,000, and only where the employer refuses to pay those costs.

- **Authority:** Government of Nepal 'Free Visa, Free Ticket' directive (2015) under the Foreign Employment Act 2007; Department of Foreign Employment (administrative_rule) -- <https://www.business-humanrights.org/en/latest-news/nepal-free-visa-free-ticket-policys-promise-of-reducing-recruitment-fee-charging-remains-largely-unfulfilled-says-op-ed/>
- **Applies to:** Nepali migrant workers recruited for the seven covered destination countries
- **Exceptions:** a Nepali agency may charge a service fee up to NPR 10,000 where the employer refuses to pay the visa/ticket costs; the covered-destination list can change; in practice the policy is widely under-enforced and workers report paying far more
- **Binding:** binding_domestic | **effective_from:** 2015-07-01 | **as_of:** 2026-07-10 | **volatility:** high
- **Recheck after 2026-10-01:** enforcement is weak and amounts/lists change (the Foreign Employment Welfare Fund contribution moved to NPR 1,500 for contracts up to 3 years / NPR 2,500 over 3 years on 2024-07-31); verify the NPR 10,000 cap, destination list, and welfare-fund amounts against an official Department of Foreign Employment source
- **Caveats:** the NPR 10,000 cap and 7-destination list are the RULE; in PRACTICE workers report paying USD 1,500-2,200, so do not assume the worker was lawfully charged; verify against an official DoFE/Nepal government source, not only NGO/news reporting

### qa_wage_protection  (QA, rule)
> Qatar's Labour Law No. 14 of 2004 prohibits licensed recruiting entities from collecting recruitment fees, expenses or associated costs from migrant workers (Qatar is a non-placement-fee receiving country): the recruitment agency or employer bears the cost. The same law underpins the Wage Protection System (WPS), which requires wages to be paid via electronic bank transfer as evidence of payment.

- **Authority:** Qatar Labour Law No. 14 of 2004; Wage Protection System (domestic_law) -- <https://natlex.ilo.org/dyn/natlex2/natlex2/files/download/67387/QAT67387%20Eng.pdf>
- **Applies to:** migrant workers recruited to Qatar under the Labour Law
- **Exceptions:** domestic workers are covered by a separate instrument (Law No. 15 of 2017), not the Labour Law; the no-fee rule and WPS are under-enforced in parts of the market in practice
- **Binding:** binding_domestic | **effective_from:** 2005-01-01 | **as_of:** 2026-07-10 | **volatility:** medium
- **Recheck after 2027-06-01:** Gulf labour rules and WPS coverage are periodically reformed; verify current scope + domestic-worker treatment against an official Qatari source
- **Caveats:** the employer/agency-pays rule is the RULE; workers are still charged in practice via origin-country agents, so do not assume compliance; domestic workers fall under Law 15/2017, not this Labour Law

### uk_modern_slavery_act  (UK, rule)
> The UK Modern Slavery Act 2015 criminalises slavery, servitude and forced or compulsory labour (section 1) and human trafficking (section 2); section 54 (Transparency in Supply Chains) requires a commercial organisation carrying on business in the UK with total annual turnover of at least GBP 36 million to publish an annual modern-slavery statement approved by the board and signed by a director.

- **Authority:** Modern Slavery Act 2015 (UK), sections 1, 2 and 54 (domestic_law) -- <https://www.legislation.gov.uk/ukpga/2015/30/section/54>
- **Applies to:** the criminal offences apply in the UK; section 54 applies to in-scope commercial organisations doing business in the UK
- **Exceptions:** section 54 applies only where total turnover is at least GBP 36 million; section 54 is a transparency/reporting duty, not a mandatory due-diligence or import-ban regime; the criminal offences (s.1-2) are separate
- **Binding:** binding_domestic | **effective_from:** 2015-10-29 | **as_of:** 2026-07-10 | **volatility:** medium
- **Recheck after 2027-06-01:** reform of section 54 (mandatory reporting topics, penalties, single reporting deadline) has been proposed; verify whether amendments are in force
- **Caveats:** s.54 is transparency-only; do not describe it as a due-diligence mandate or an import ban (contrast the EU Forced Labour Regulation); the GBP 36m threshold and reporting requirements may change
