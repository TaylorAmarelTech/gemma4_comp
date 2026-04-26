# Facebook trafficking-facilitation case — research-binder framework

> Sanitized summary of a legal research document (37,553 chars) building
> a litigation binder against Facebook for facilitating migrant-worker
> trafficking and money laundering on its platform. Real names + specific
> victim/agency identifiers redacted; legal framework + research methodology
> preserved.

## I. Potential Offences

### (i) Not taking sufficient action to regulate content
Facebook's failure to remove "WANTED poster" debt-shaming posts, predatory
recruitment ads, and passport-as-collateral lender pages despite repeated
reports under the Coordinating Harm + Bullying community-standards categories.
Evidence corpus: Facebook Posts · News Articles · Previous Cases & Binders.

### (ii) Facilitating human trafficking & money laundering through its platform
Operational thesis: predatory lending pages targeting OFWs use Facebook as
their distribution and harassment channel (recruitment, public shaming, and
remittance coordination), and Facebook's monetisation of these pages amounts
to facilitation. Evidence corpus: Facebook Posts · News Articles · Previous
Cases & Binders.

### (iii) Fraud / Non-disclosure
Failing to inform shareholders of the risks associated with the illicit
activity ongoing on its platform; providing materially false or misleading
information to investors about actions taken to minimise risks that may be
insufficient or ineffective. Evidence corpus: Facebook Posts · News
Articles · Other.

## II. Legal Research

### Personal Data (Privacy) Ordinance (Cap. 486)
Hong Kong's PDPO + the 2021 anti-doxxing amendment criminalise publication
of personal data with intent to cause harm. Maximum penalty: HKD 1M + 5
years' imprisonment. Pages such as "Bank Hongkong" and "Yoursun Caretaker"
publishing OFW passport photos + full names + alleged debt status fall
squarely within the doxxing offence as defined.

### Financial Laws
HK Money Lenders Ordinance Cap. 163 — 48% APR statutory cap on personal
loans. Loans to OFW domestic helpers exceeding this cap are presumptively
extortionate. Cross-references to AMLO (Cap. 615) for cross-border
collection patterns.

## III. Output framework

The case binder consists of four outputs:
- **Binder** — evidence compilation organised by offence category
- **Cover letter** — submission to appropriate authorities (HK Privacy
  Commissioner, Securities and Futures Commission, Department of Justice)
- **Google Slides presentation** — case summary for stakeholder briefings
- **Recorded webinar** — public-facing dissemination

For each project students review available evidence, conduct online
research and online investigations, obtain new evidence through online
searches and interviews (online and offline), and put together the best
legal theories for which laws the suspect company is arguably violating
and why.

## IV. Desired Outcomes

### Immediate
Removal of identified predatory-lender pages from the platform; takedown
of doxxing posts; preservation of evidence for criminal referrals.

### Medium term
Platform-policy changes requiring proof-of-licence for any page offering
financial services targeting migrant workers; mandatory escalation
pathways for posts containing passport photos.

### Long term
Coordinated multi-jurisdiction enforcement (HK + PH + Indonesia + UAE +
Saudi) leveraging the Personal Data Privacy + Money Lenders + AML
regimes already in force. Establish a system for keeping records of
employers and agencies — the cheapest, easiest, and quickest way to
detect and monitor bad actors. Bad employers tend to terminate
employment contracts prematurely; bad agencies tend to recur across
victims.

---

## Why this document matters for Duecare

This research document is the **operator's playbook** that Duecare's
output is designed to feed into. Every BLOCK verdict the system
produces is structured to be a binder-ready evidence record:

- **Verdict + severity** → goes in the executive summary of the binder
- **Matched signals + KB hits** → goes in the offence categorisation
  (matches the Cap. 486 / Cap. 163 / RA 10173 / RA 10175 framework)
- **Tool calls (lookup_statute, check_predatory_lender, etc.)** → goes
  in the legal research section
- **Hotline + embassy** → goes in the Immediate Actions section
- **ILO indicator matches** → cross-references the Palermo Protocol
  Article 3 elements

The trace timeline + JSON record exposed via `/queue` is the audit
trail prosecutors and Privacy Commissioners ask for — every retrieval,
every tool call, every classification step is recorded with timestamps
and inputs, deterministically reproducible from `(git_sha, KB_version,
heuristic_rules_version)`.
