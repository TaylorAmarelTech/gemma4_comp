"""Complaint / cause-of-action template library.

Each template maps a (jurisdiction, violation_type) combo to a
fillable letter or affidavit skeleton. Used by the
`generate_complaint` tool call (during moderation) and by the
/workspace 'Generate complaint' tab (standalone use).

The templates are sanitized skeletons -- no real names, no specific
case identifiers. They cite the right statute and use the right
addressing for the relevant authority. Operators fill in the
{placeholders}.

Adding a new template:
  1. Add an entry to TEMPLATES below with a unique slug.
  2. {placeholders} in the body are auto-collected and exposed
     as form fields by the /workspace tab.
  3. The 'cites' list flows into the verdict so judges know which
     statutes the letter is based on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ComplaintTemplate:
    slug: str
    title: str
    jurisdiction: str          # 'PH', 'HK', 'international', etc.
    violation_type: str        # 'doxxing', 'fee_fraud', 'passport_retention', ...
    addressee: str             # who the letter goes to
    cites: list[str]           # KB passage IDs the template references
    body: str                  # letter body with {placeholders}
    notes: str = ""            # operator-facing guidance


TEMPLATES: list[ComplaintTemplate] = [
    # -----------------------------------------------------------------
    # PH -- Recruitment / OFW
    # -----------------------------------------------------------------
    ComplaintTemplate(
        slug="ph_dmw_illegal_recruitment",
        title="DMW Complaint -- Illegal Recruitment / Excessive Fee",
        jurisdiction="PH",
        violation_type="recruitment_fraud",
        addressee="Department of Migrant Workers (DMW), Manila",
        cites=["ph_ra8042_sec6a", "ph_ra10022", "ph_dmw_circular",
                 "ilo_c181_art7"],
        body="""
TO:    The Honorable Secretary
       Department of Migrant Workers (DMW)
       (formerly POEA)
       Ortigas Center, Mandaluyong City, Philippines

FROM:  {complainant_name_or_alias}
       {complainant_contact}
       {complainant_locale}

DATE:  {today}

RE:    Complaint for Illegal Recruitment / Excessive Placement Fee
       under RA 8042 sec 6(a) and RA 10022 against
       "{respondent_agency}"

I respectfully submit this complaint against the above-named
recruitment agency for the following violations of Philippine
law governing migrant workers:

1. EXCESSIVE PLACEMENT FEE
   The agency demanded a placement fee of {fee_amount} from me
   on or about {fee_date}. This amount exceeds the cap set by
   the DMW (formerly POEA) of one (1) month's equivalent of the
   contracted salary for skilled workers, and entirely prohibits
   any fee for domestic workers under RA 10022.

2. EVIDENCE
   {evidence_summary}

3. RELIEF SOUGHT
   I respectfully request that the DMW:
   (a) Investigate the agency's licensing status;
   (b) Order a refund of all amounts collected in excess of the
       statutory cap;
   (c) Take administrative action including license suspension
       or revocation as warranted under the Migrant Workers Act.

4. STATUTORY BASIS
   - PH RA 8042 sec 6(a) -- Migrant Workers and Overseas
     Filipinos Act
   - PH RA 10022 -- amended Migrant Workers Act prohibiting
     placement fees from workers
   - DMW (formerly POEA) Memorandum Circular establishing fee caps
   - ILO Convention C181 Article 7 -- Employer-Pays Principle

I am prepared to substantiate the foregoing under oath. I
respectfully request immediate action to prevent further harm
to other workers.

Respectfully,

{complainant_name_or_alias}
{contact_for_followup}
""".strip(),
        notes="File via DMW online complaint portal or via POLO at "
                "the destination country. Include receipts, bank "
                "transfer screenshots, and any contract documents.",
    ),

    # -----------------------------------------------------------------
    # HK -- Predatory lender / doxxing
    # -----------------------------------------------------------------
    ComplaintTemplate(
        slug="hk_pcpd_doxxing",
        title="HK Privacy Commissioner -- Doxxing Complaint (Cap. 486)",
        jurisdiction="HK",
        violation_type="doxxing",
        addressee="Office of the Privacy Commissioner for Personal Data, HK",
        cites=["hk_cap486_personal_data", "hk_cap200_crimes_intimidation",
                 "hk_cap210_blackmail"],
        body="""
TO:    The Privacy Commissioner for Personal Data (PCPD)
       12/F, Sunlight Tower
       248 Queen's Road East, Wan Chai
       Hong Kong

FROM:  {complainant_name_or_alias}
       {complainant_contact}

DATE:  {today}

RE:    Complaint for Doxxing under Personal Data (Privacy)
       Ordinance Cap. 486 (Anti-Doxxing Amendment 2021)
       against the page "{respondent_page_name}"
       on the platform "{platform}"

I respectfully submit this complaint for the unauthorised
publication of my personal data with the apparent intent to
cause me psychological harm.

1. PARTICULARS OF THE DOXXING POST(S)
   Page / publisher:  {respondent_page_name}
   Platform:          {platform}
   Date(s) posted:    {post_dates}
   URL(s):            {post_urls}

2. PERSONAL DATA UNLAWFULLY DISCLOSED
   {disclosed_data_categories}

3. INTENT TO CAUSE HARM
   The post(s) include language such as: {threatening_language_excerpt}
   and were disseminated to the page's followers with the apparent
   intent of causing psychological harm and / or coercing payment.

4. EVIDENCE
   {evidence_summary}

5. RELIEF SOUGHT
   I respectfully request the Privacy Commissioner:
   (a) Issue a Cessation Notice under section 66K to the platform
       and the page operator;
   (b) Refer the matter for criminal investigation under Cap. 486
       (max HKD 1M + 5 years' imprisonment);
   (c) Consider concurrent charges under Crimes Ordinance Cap. 200
       sec 24 (criminal intimidation) and Theft Ordinance Cap. 210
       sec 23 (blackmail) where the post demanded payment.

6. STATUTORY BASIS
   - Personal Data (Privacy) Ordinance Cap. 486 + Anti-Doxxing
     Amendment 2021
   - Crimes Ordinance Cap. 200 sec 24 -- criminal intimidation
   - Theft Ordinance Cap. 210 sec 23 -- blackmail

Respectfully,

{complainant_name_or_alias}
{contact_for_followup}
""".strip(),
        notes="File at pcpd.org.hk/complaints. The Anti-Doxxing "
                "Amendment lets PCPD issue a cessation notice "
                "directly to social-media platforms. Attach "
                "screenshots of the offending post(s) and any "
                "demand messages received.",
    ),

    ComplaintTemplate(
        slug="hk_money_lender_demand",
        title="HK Money Lender -- Cease and Desist Demand Letter",
        jurisdiction="HK",
        violation_type="predatory_lending",
        addressee="The named money lender / finance company",
        cites=["hk_money_lenders_ordinance", "hk_cap200_crimes_intimidation",
                 "hk_cap210_blackmail", "hk_cap486_personal_data"],
        body="""
TO:    The Director(s) / Compliance Officer
       {respondent_lender}
       (HK Money Lender Licence No.: {licence_no_if_known})

FROM:  {complainant_name_or_alias}
       c/o {complainant_contact}

DATE:  {today}

RE:    Demand to (a) cease harassment and disclosure of personal
       data, (b) produce a copy of the loan agreement, and (c)
       account for all sums collected, in respect of loan
       reference {loan_reference}

1. I borrowed approximately {loan_amount_hkd} HKD from your
   company on or about {loan_date}.

2. Since {harassment_start_date}, your representatives have:
   {harassment_pattern_summary}

3. Your company has further publicly disclosed my name, photograph
   and / or alleged debt status on the social-media page
   "{lender_page}", an act constituting doxxing under HK Personal
   Data (Privacy) Ordinance Cap. 486 (Anti-Doxxing Amendment 2021).

4. I HEREBY DEMAND, within fourteen (14) days of receipt of this
   letter, that your company:
   (a) IMMEDIATELY CEASE all harassment of me, my employer, my
       references, and my family members;
   (b) DELETE all public posts disclosing my personal data, on
       any platform on which they appear;
   (c) PROVIDE A COPY of the original signed loan agreement and
       a full statement of account itemising every charge;
   (d) REFUND any amounts collected in excess of the statutory
       cap of 48% APR under Money Lenders Ordinance Cap. 163;
   (e) RETURN all original documents (passport, HKID, bank
       cards) collected as security; the practice of taking
       identity documents as collateral is unenforceable.

5. Failure to comply will result in:
   (a) Complaint to the Privacy Commissioner for Personal Data
       (Cap. 486);
   (b) Criminal complaint to the Hong Kong Police Force under
       Crimes Ordinance Cap. 200 sec 24 (criminal intimidation)
       and Theft Ordinance Cap. 210 sec 23 (blackmail);
   (c) Complaint to the Money Lenders Ordinance Licensing Court
       seeking revocation of your licence.

6. PRESERVATION NOTICE
   You are hereby on notice to preserve all communications,
   payment records, and CCTV footage related to this matter.
   Spoliation will be reported to the relevant authorities.

Respectfully,

{complainant_name_or_alias}
{contact_for_followup}

cc: Privacy Commissioner for Personal Data (Cap. 486)
    Hong Kong Police Force
""".strip(),
        notes="Send by recorded delivery + email. Keep proof of "
                "receipt. The 14-day deadline is conventional and "
                "legally adequate. If the lender does not respond, "
                "the failure itself becomes evidence in the PCPD "
                "complaint.",
    ),

    # -----------------------------------------------------------------
    # International -- Platform takedown
    # -----------------------------------------------------------------
    ComplaintTemplate(
        slug="fb_platform_takedown_doxxing",
        title="Facebook / Meta -- Doxxing Takedown Request",
        jurisdiction="international",
        violation_type="doxxing",
        addressee="Meta Platforms, Inc. -- Coordinating Harm reporting",
        cites=["fb_community_standards_doxxing", "gdpr_art17_erasure",
                 "hk_cap486_personal_data", "ph_ra10173_data_privacy"],
        body="""
TO:    Meta Platforms, Inc. -- Trust & Safety
       (Coordinating Harm and Promoting Crime team)

FROM:  {complainant_name_or_alias}, on behalf of {affected_party}
       Reporter contact: {reporter_contact}

DATE:  {today}

RE:    Urgent takedown request for doxxing posts violating
       Facebook Community Standards (Coordinating Harm and
       Promoting Crime + Bullying and Harassment categories)

PAGE / PROFILE:  {respondent_page_name}
URL:             {page_url}
POSTS REPORTED:  {post_urls}

NATURE OF VIOLATION
The above page has published "wanted poster" style posts naming
private individuals (overseas Filipino / Indonesian workers in
Hong Kong), publishing their full names, passport-style
photographs, and alleged debt details. The posts are accompanied
by demands for payment ("asap pay ur overdues", "WANTED:
LENDING BANK BASED IN HONGKONG IS LOOKING FOR THIS OFW") and
encouragement to share / tag / locate the named individuals.

POLICY CITATIONS
- Coordinating Harm and Promoting Crime: prohibits posts
  exposing private individuals to physical or financial harm.
- Bullying and Harassment: prohibits unwanted public targeting
  of private individuals.
- Personally Identifiable Information: prohibits the public
  disclosure of personal data to facilitate harm.

EXTERNAL LEGAL EXPOSURE
The same conduct constitutes a criminal offence under:
- HK Personal Data (Privacy) Ordinance Cap. 486 (Anti-Doxxing
  Amendment 2021): max HKD 1M + 5 years imprisonment
- PH Data Privacy Act RA 10173: max PHP 5M + 6 years
- PH Cybercrime Prevention Act RA 10175: cyber-libel
- GDPR Article 17 (where any data subject is in the EU): right
  to erasure

REQUESTED ACTION
1. Immediate removal of the named posts pending review.
2. Suspension of the page pending investigation.
3. Permanent removal upon confirmation that the page is operated
   by an unlicensed money-lending entity using the platform for
   debt-collection harassment.

EVIDENCE
{evidence_summary}

This request is urgent because each day the posts remain live
extends the harm to the named individuals and their families.

Respectfully,

{complainant_name_or_alias}
{contact_for_followup}

cc: PH National Privacy Commission (RA 10173)
    HK Privacy Commissioner for Personal Data (Cap. 486)
""".strip(),
        notes="File via Facebook's in-app reporting + email "
                "press@fb.com if urgent. NGOs with established Trust "
                "and Safety contacts get faster turnaround. Include "
                "URLs of every offending post.",
    ),

    # -----------------------------------------------------------------
    # PH -- Passport-as-collateral
    # -----------------------------------------------------------------
    ComplaintTemplate(
        slug="ph_passport_release_demand",
        title="Demand for Release of Passport (held by agency / employer)",
        jurisdiction="PH",
        violation_type="passport_retention",
        addressee="The recruitment agency / employer holding the passport",
        cites=["ilo_c029", "palermo_protocol_art3", "ph_ra10022",
                 "ph_ra9995_anti_voyeurism"],
        body="""
TO:    {respondent_holder}

FROM:  {complainant_name_or_alias}

DATE:  {today}

RE:    DEMAND FOR IMMEDIATE RELEASE OF PASSPORT

1. My passport (Number: {passport_no_if_known}, issued by the
   Republic of the Philippines) was surrendered to / collected by
   you on or about {confiscation_date}.

2. The retention of a worker's passport by an employer or
   recruitment agency is a violation of:
   - ILO Convention C029 (Forced Labour Convention, 1930) --
     forced-labour indicator #7 (retention of identity
     documents)
   - The Palermo Protocol Article 3 -- expressly identifies
     document retention as a means of trafficking
   - Philippine RA 10022 (Migrant Workers Act, as amended) --
     prohibits document retention as a coercive practice

3. I HEREBY DEMAND that you, within seventy-two (72) hours of
   receipt of this letter, RETURN my passport to me at:
   {return_address}

4. Failure to comply will be reported to:
   - The Philippine Overseas Labor Office (POLO) at the
     destination country
   - The Department of Migrant Workers (DMW)
   - The Philippine Embassy / Consulate ({embassy})
   - Local police of the destination country, with reference to
     the Palermo Protocol implementing legislation in force

5. PRESERVATION NOTICE
   You are on notice to preserve any record (paper or
   electronic) relating to this passport, the contract under
   which I was placed, and all communications between us.

Respectfully,

{complainant_name_or_alias}
{contact_for_followup}

cc: Philippine Embassy / Consulate ({embassy})
    POLO ({destination_country})
""".strip(),
        notes="Hand-deliver if possible (with witness). Otherwise "
                "send by registered post + email. The 72-hour deadline "
                "is conventional for urgent demands. If the holder is "
                "in HK, also cite Cap. 200 sec 24 (criminal "
                "intimidation) for retention used to coerce.",
    ),

    # -----------------------------------------------------------------
    # Indonesia -- BP2MI complaint
    # -----------------------------------------------------------------
    ComplaintTemplate(
        slug="id_bp2mi_complaint",
        title="BP2MI Complaint -- Indonesian Migrant Worker (PMI)",
        jurisdiction="ID",
        violation_type="recruitment_fraud",
        addressee="Badan Pelindungan Pekerja Migran Indonesia (BP2MI)",
        cites=["ph_ra10173_data_privacy", "ilo_c181_art7", "palermo_protocol_art3"],
        body="""
KEPADA: Kepala Badan Pelindungan Pekerja Migran Indonesia (BP2MI)
        Jakarta, Indonesia

DARI:    {complainant_name_or_alias}
         {complainant_contact}

TANGGAL: {today}

PERIHAL: Pengaduan Pelanggaran Hak Pekerja Migran Indonesia (PMI)
         terhadap "{respondent_agency}"

Saya, dengan hormat, menyampaikan pengaduan terhadap perusahaan
yang disebut di atas atas pelanggaran berikut terhadap UU
Perlindungan Pekerja Migran Indonesia (UU No. 18 Tahun 2017):

1. PELANGGARAN YANG TERJADI
{violation_narrative}

2. BUKTI
{evidence_summary}

3. PERMOHONAN
Saya memohon BP2MI untuk:
   (a) Menyelidiki status lisensi P3MI tersebut;
   (b) Memerintahkan pengembalian seluruh biaya yang dipungut
       di luar batas yang ditetapkan;
   (c) Mengambil tindakan administratif termasuk pencabutan
       izin sesuai UU No. 18 Tahun 2017;
   (d) Berkoordinasi dengan KBRI / KJRI di negara penempatan
       untuk perlindungan saya.

4. DASAR HUKUM
   - UU No. 18 Tahun 2017 -- Pelindungan Pekerja Migran Indonesia
   - Konvensi ILO C181 Pasal 7 -- Prinsip Pemberi Kerja Membayar
   - Protokol Palermo Pasal 3 -- definisi perdagangan orang

Hormat saya,

{complainant_name_or_alias}
{contact_for_followup}

Tembusan: KBRI / KJRI di {destination_country}
          IOM Jakarta
""".strip(),
        notes="Submit via BP2MI Crisis Center hotline 1500-30 or "
                "online portal. Indonesian PMI workers have additional "
                "protections under UU 18/2017 and bilateral MOUs with "
                "destination countries (Malaysia, Saudi, UAE, etc.).",
    ),

    # -----------------------------------------------------------------
    # Nepal -- Foreign Employment Tribunal
    # -----------------------------------------------------------------
    ComplaintTemplate(
        slug="np_fet_complaint",
        title="Nepal FET -- Foreign Employment Tribunal Complaint",
        jurisdiction="NP",
        violation_type="recruitment_fraud",
        addressee="Foreign Employment Tribunal (FET), Nepal",
        cites=["ilo_c181_art7", "ilo_c029", "palermo_protocol_art3"],
        body="""
TO:    The Honorable Chair
       Foreign Employment Tribunal (FET)
       Foreign Employment Department
       Government of Nepal

FROM:  {complainant_name_or_alias}
       {complainant_contact}

DATE:  {today}

RE:    Complaint under the Foreign Employment Act 2007 (2064 BS)
       against "{respondent_agency}" (Recruiter Licence:
       {agency_licence_if_known})

I respectfully submit this complaint pursuant to the Foreign
Employment Act 2007 and the Foreign Employment Rules 2008.

1. RECRUITMENT FACTS
   Agency / sub-agent:  {respondent_agency}
   Destination country:  {destination_country}
   Promised position:    {position}
   Promised salary:      {promised_salary}
   Actual outcome:       {actual_outcome}

2. ALLEGED VIOLATIONS
{violation_narrative}

3. EVIDENCE
{evidence_summary}

4. RELIEF SOUGHT
   (a) Refund of all amounts collected in excess of the
       government-set fee cap;
   (b) Compensation for lost wages / unfulfilled contract;
   (c) Repatriation assistance, if applicable;
   (d) Administrative action against the agency including
       licence revocation;
   (e) Referral to the Department of Foreign Employment for
       criminal prosecution where the conduct constitutes
       trafficking under the Human Trafficking and
       Transportation (Control) Act 2007.

5. STATUTORY BASIS
   - Foreign Employment Act 2007 (Nepal)
   - Human Trafficking and Transportation (Control) Act 2007
   - ILO C029 (forced labour indicators)
   - ILO C181 Article 7 (Employer-Pays Principle)
   - Palermo Protocol Article 3

Respectfully,

{complainant_name_or_alias}
{contact_for_followup}

cc: Embassy of Nepal in {destination_country}
    HRD Nepal
""".strip(),
        notes="File at the FET office in Kathmandu OR submit through "
                "the Embassy of Nepal at the destination country. "
                "Foreign Employment Welfare Fund covers some return "
                "costs.",
    ),

    # -----------------------------------------------------------------
    # GCC -- Wage Protection System (WPS) complaint
    # -----------------------------------------------------------------
    ComplaintTemplate(
        slug="gcc_wps_wage_complaint",
        title="GCC Wage Protection System (WPS) Wage-Theft Complaint",
        jurisdiction="GCC",
        violation_type="wage_theft",
        addressee="The Ministry of Labour / WPS authority of the destination country",
        cites=["uae_decree_33_2021", "ilo_c95_wages_recovery", "ilo_c029"],
        body="""
TO:    {ministry_of_labour_name}
       {country_specific_address}

FROM:  {complainant_name_or_alias}
       {complainant_passport_country} citizen
       {complainant_contact}

DATE:  {today}

RE:    Wage Theft + Document Retention Complaint -- Wage
       Protection System (WPS) reference {wps_reference_if_known}

EMPLOYER:           {respondent_employer}
WORK LICENCE NO.:   {work_licence_no_if_known}
JOB:                {position}
CONTRACT START:     {contract_start_date}
TOTAL UNPAID WAGES: {unpaid_wages_amount}

1. CONTRACT TERMS
   I was contracted by {respondent_employer} on
   {contract_start_date} for a {contract_duration} contract
   as a {position}. The contracted monthly wage was
   {contracted_wage}.

2. ACTUAL CONDITIONS
{actual_conditions_narrative}

3. WAGE THEFT
   The total unpaid wages as of {today} amount to
   {unpaid_wages_amount}. I have not received payment via WPS
   for {months_unpaid_wps} consecutive months.

4. DOCUMENT RETENTION
   {document_retention_facts}

5. RELIEF SOUGHT
   (a) Immediate payment of all unpaid wages with statutory
       interest;
   (b) Return of my passport and all identity documents;
   (c) Permission to transfer sponsorship to a new employer
       (per the kafala reform regime in force);
   (d) Return-air-ticket if I elect to repatriate;
   (e) Investigation of the employer's WPS compliance and
       referral for sanctions.

6. STATUTORY BASIS
   - {country_specific_labor_law}
   - Wage Protection System (WPS) regulations
   - ILO C029 forced-labour indicators (passport retention,
     wage withholding)
   - ILO C95 Article 8 (wage-protection limits)

Respectfully,

{complainant_name_or_alias}
{contact_for_followup}

cc: Embassy of {complainant_passport_country} in {destination_country}
    POLO / BP2MI / FEB / BMET (origin-country labor office)
    IOM Country Office
""".strip(),
        notes="Different GCC states use different acronyms: UAE = "
                "MOHRE, Saudi = MHRSD, Qatar = MADLSA, Kuwait = PAM, "
                "Bahrain = LMRA, Oman = MOMP. WPS coverage varies; "
                "some sectors are excluded. File copies with the "
                "embassy AND the local Ministry simultaneously.",
    ),

    # -----------------------------------------------------------------
    # US -- TVPA T-visa / federal complaint
    # -----------------------------------------------------------------
    ComplaintTemplate(
        slug="us_tvpa_dol_complaint",
        title="US Department of Labor + DOJ TVPA Complaint",
        jurisdiction="US",
        violation_type="forced_labor",
        addressee="US DOL Wage and Hour Division + DOJ Civil Rights / HTPU",
        cites=["us_tvpa", "palermo_protocol_art3", "ilo_c029"],
        body="""
TO:    Wage and Hour Division
       US Department of Labor
       (and copy: Civil Rights Division, Human Trafficking
        Prosecution Unit, US Department of Justice)

FROM:  {complainant_name_or_alias}
       {complainant_contact}
       (Counsel: {counsel_if_any})

DATE:  {today}

RE:    Complaint for Forced Labor and Wage Violations under
       the Trafficking Victims Protection Act (TVPA), 18 U.S.C.
       sec 1589 et seq., and the Fair Labor Standards Act (FLSA),
       against "{respondent_employer}"

1. PARTIES
   Complainant: {complainant_name_or_alias} ({complainant_status})
   Respondent:  {respondent_employer}, located at
                {respondent_address}

2. NATURE OF CONDUCT (TVPA elements)
   Pursuant to 18 U.S.C. sec 1589, forced labor exists where the
   defendant knowingly obtained labor by:
   (a) means of force, threats of force, physical restraint;
   (b) means of serious harm or threats thereof;
   (c) means of the abuse or threatened abuse of law or legal
       process;
   (d) means of any scheme, plan, or pattern intended to cause
       the person to believe that nonperformance would result
       in serious harm.

   The respondent's conduct meets these elements as follows:
{tvpa_elements_narrative}

3. WAGE VIOLATIONS (FLSA)
{flsa_facts}

4. EVIDENCE
{evidence_summary}

5. RELIEF SOUGHT
   (a) Investigation by the WHD and DOJ HTPU;
   (b) Recovery of unpaid wages plus liquidated damages under
       29 U.S.C. sec 216(b);
   (c) Restitution under 18 U.S.C. sec 1593;
   (d) Endorsement of T-visa application for the complainant
       under 8 U.S.C. sec 1101(a)(15)(T) where applicable;
   (e) Injunctive relief preventing the respondent from further
       trafficking.

6. STATUTORY BASIS
   - Trafficking Victims Protection Act (TVPA), 18 U.S.C.
     secs 1589, 1590, 1592, 1595
   - Fair Labor Standards Act (FLSA), 29 U.S.C. sec 201 et seq.
   - Palermo Protocol Article 3 (US is a party)
   - ILO C029 (forced labour indicators)

Respectfully,

{complainant_name_or_alias}
{contact_for_followup}

cc: Polaris Project National Hotline (1-888-373-7888)
""".strip(),
        notes="In the US, victims have access to T-visa protection "
                "for cooperation with law enforcement. Counsel from a "
                "TVPA-experienced legal-aid org (Polaris referral, "
                "ASISTA, NIWAP) is recommended. WHD complaints can be "
                "filed regardless of immigration status.",
    ),

    # -----------------------------------------------------------------
    # EU -- GDPR + Anti-trafficking Directive
    # -----------------------------------------------------------------
    ComplaintTemplate(
        slug="eu_gdpr_dpa_complaint",
        title="EU Data Protection Authority -- GDPR Doxxing Complaint",
        jurisdiction="EU",
        violation_type="doxxing",
        addressee="The competent Data Protection Authority (DPA) of the EU member state",
        cites=["gdpr_art17_erasure", "fb_community_standards_doxxing"],
        body="""
TO:    {dpa_name}
       (Data Protection Authority of {member_state})

FROM:  {complainant_name_or_alias}
       Data subject located in {data_subject_residence}
       Contact: {complainant_contact}

DATE:  {today}

RE:    Complaint under GDPR Articles 17 (Right to Erasure) and
       82 (Compensation) against "{respondent_controller}" for
       unauthorised publication of my personal data

1. THE PROCESSING COMPLAINED OF
   The respondent has published, on the platform "{platform}",
   the following categories of my personal data without lawful
   basis under Article 6 GDPR:
{disclosed_data_categories}

2. UNLAWFULNESS
   The processing is unlawful because:
   (a) No legal basis under Article 6(1) applies (no consent,
       no contract, no legal obligation, no vital interest, no
       public interest, and no legitimate interest that is not
       overridden by my rights and freedoms);
   (b) For special-category data (Article 9), no exception
       applies;
   (c) Article 5(1)(a) (lawfulness, fairness, transparency)
       and Article 5(1)(c) (data minimisation) are violated;
   (d) The publication is conducted with the intent to cause
       material and non-material damage (Article 82(1)).

3. RELIEF SOUGHT
   (a) An order under Article 17 directing the controller to
       erase all references to me on the named platform;
   (b) An order under Article 18 restricting further processing;
   (c) Investigation of cross-border processing under Articles
       60-66 (one-stop-shop), if the controller's main
       establishment is in another member state;
   (d) Administrative fines under Article 83 commensurate with
       the harm caused;
   (e) Compensation under Article 82 for material and non-
       material damage.

4. EVIDENCE
{evidence_summary}

Respectfully,

{complainant_name_or_alias}
{contact_for_followup}

cc: European Data Protection Board (EDPB)
    Anti-Trafficking Coordinator (EU Commission)
""".strip(),
        notes="GDPR applies if ANY data subject is in the EU OR if "
                "the controller is established in the EU. The relevant "
                "DPA is typically that of the data subject's residence. "
                "EU member-state DPAs include CNIL (France), AEPD "
                "(Spain), Garante (Italy), BfDI (Germany), DPC "
                "(Ireland, common for US tech). Filing is free.",
    ),

    # -----------------------------------------------------------------
    # POEA -- Sworn affidavit
    # -----------------------------------------------------------------
    ComplaintTemplate(
        slug="ph_polo_sworn_complaint",
        title="POLO Sworn Complaint Affidavit",
        jurisdiction="PH",
        violation_type="any",
        addressee="Philippine Overseas Labor Office (POLO), {destination_country}",
        cites=["ph_ra10022", "ilo_c181_art7", "palermo_protocol_art3"],
        body="""
REPUBLIC OF THE PHILIPPINES
POLO {destination_country}

POLO FORM NO. 2

I, {complainant_name_or_alias}, of legal age, Filipino citizen,
currently residing at {complainant_address}, after having been
duly sworn in accordance with law, do hereby depose and state:

1. I am an Overseas Filipino Worker (OFW) deployed to
   {destination_country} on or about {deployment_date} for a
   {contract_duration}-year contract as a {position} with
   {employer_name}.

2. I was recruited by the agency "{recruiting_agency}"
   (PH licence: {agency_licence_if_known}).

3. The following violations of my rights as an OFW have occurred:
{violation_narrative}

4. I have evidence of the foregoing in the form of:
{evidence_list}

5. I am submitting this sworn statement requesting the assistance
   of POLO {destination_country} for:
   (a) Recovery of my documents (passport, contract, IDs);
   (b) Repatriation, if my safety is at risk;
   (c) Wage / fee recovery from the agency / employer;
   (d) Referral to the Department of Migrant Workers (DMW) for
       administrative and / or criminal action against the
       responsible parties.

I AFFIRM the foregoing under penalty of perjury under the laws of
the Republic of the Philippines.

___________________________
{complainant_name_or_alias}
Affiant

SUBSCRIBED AND SWORN to before me this {today}, at the
Consulate-General of the Republic of the Philippines in
{destination_country}, the affiant having presented to me her
Philippine passport No. {passport_no_if_known} as competent
proof of identity.

___________________________
Consul / Notarising Officer
""".strip(),
        notes="Submit at the POLO office in person whenever possible. "
                "Bring all original documents AND copies. The Consulate "
                "will notarise free of charge for OFWs. Keep a stamped "
                "copy for your records.",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _placeholders(body: str) -> list[str]:
    """Extract unique {placeholder} names from a template body."""
    return sorted(set(re.findall(r"\{([a-z_0-9]+)\}", body)))


def list_templates(jurisdiction: Optional[str] = None,
                     violation_type: Optional[str] = None) -> list[dict]:
    """Return template summaries for the picker UI."""
    out = []
    for t in TEMPLATES:
        if jurisdiction and t.jurisdiction != jurisdiction \
                and t.jurisdiction != "international":
            continue
        if violation_type and t.violation_type != violation_type \
                and t.violation_type != "any":
            continue
        out.append({
            "slug": t.slug,
            "title": t.title,
            "jurisdiction": t.jurisdiction,
            "violation_type": t.violation_type,
            "addressee": t.addressee,
            "cites": t.cites,
            "placeholders": _placeholders(t.body),
            "notes": t.notes,
        })
    return out


def render_template(slug: str, fields: dict) -> dict:
    """Render a template with operator-supplied fields. Missing
    fields are kept as {placeholder} so the operator can find
    and fill them. Returns {body, missing_fields, used_fields,
    template metadata}."""
    tpl = next((t for t in TEMPLATES if t.slug == slug), None)
    if tpl is None:
        return {"error": f"unknown template slug: {slug!r}",
                "body": "", "missing_fields": [], "used_fields": []}

    placeholders = _placeholders(tpl.body)
    today = datetime.now().strftime("%B %d, %Y")
    fields = {**(fields or {})}
    fields.setdefault("today", today)

    used = []
    missing = []
    body = tpl.body
    for p in placeholders:
        v = fields.get(p)
        if v is None or str(v).strip() == "":
            missing.append(p)
        else:
            used.append(p)
            body = body.replace("{" + p + "}", str(v))

    return {
        "slug": tpl.slug,
        "title": tpl.title,
        "jurisdiction": tpl.jurisdiction,
        "violation_type": tpl.violation_type,
        "addressee": tpl.addressee,
        "cites": tpl.cites,
        "notes": tpl.notes,
        "body": body,
        "missing_fields": missing,
        "used_fields": used,
        "template_chars": len(body),
    }


def suggest_template(verdict_result: dict) -> Optional[dict]:
    """Given a moderation verdict, suggest the most relevant template.
    Returns the template summary or None.

    Used in the BLOCK / REVIEW path so the operator gets a 'next step'
    suggestion: 'this looks like doxxing -> file a PCPD complaint with
    template hk_pcpd_doxxing'."""
    if not verdict_result or verdict_result.get("verdict") not in (
            "block", "review"):
        return None
    sm_harass = verdict_result.get("social_media_harassment") or {}
    if sm_harass.get("pattern_count", 0) >= 1:
        return {"slug": "fb_platform_takedown_doxxing",
                "reason": "Social-media harassment patterns detected -- "
                              "use the platform-takedown template."}
    if (verdict_result.get("predatory_lender") or {}).get("match_count", 0) >= 1:
        return {"slug": "hk_money_lender_demand",
                "reason": "Known predatory-lender match -- use the "
                              "cease-and-desist demand letter."}
    sigs = [s.get("signal", "") for s in
            (verdict_result.get("matched_signals") or [])]
    if any("passport" in s for s in sigs):
        return {"slug": "ph_passport_release_demand",
                "reason": "Passport-retention pattern detected -- "
                              "use the passport-release demand."}
    if any("fee" in s for s in sigs):
        return {"slug": "ph_dmw_illegal_recruitment",
                "reason": "Excessive-fee / recruitment-fraud pattern -- "
                              "use the DMW illegal-recruitment complaint."}
    return None
