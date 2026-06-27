<!-- Provenance: indicator-frameworks workflow (wf_4aca8f61-abb), multi-agent draft->verify->synthesize. 4 frameworks verified (ILO Delphi adults+children, US TVPA FFC, GLAA/FLEX); OSCE/UNODC agent content-filter-blocked, omitted. -->

# Unified Weighted Trafficking-Indicator Reference — Migrant-Worker Forced Labour

A single de-duplicated indicator set synthesized from four verified frameworks, organized by dimension and anchored to the project's base taxonomy: the **ILO 11 Indicators of Forced Labour** (SAP-FL 2012; revised Nov 2025) and the **UN Palermo Protocol Art. 3** Act–Means–Purpose triad. Each indicator shows its weight per profile, which frameworks include it, and its ILO-11 / Palermo mapping. Duplicate concepts across frameworks are folded into one canonical row; the same indicator appearing at *recruitment* vs *destination* is kept as two rows because the weight legitimately escalates (a deliberate feature, not duplication).

## Source frameworks (all verified, no fabrication)

| Tag | Framework | Profile / contribution |
|---|---|---|
| **D·A** | ILO–EC "Delphi" Operational Indicators (2009) | Adults, labour exploitation — 67 weighted indicators, 6 dimensions |
| **D·C** | ILO–EC "Delphi" Operational Indicators (2009) | Children (<18), labour exploitation — 65 weighted indicators (no "weak" tier) |
| **TVPA** | US TVPA force/fraud/coercion + Action-Means-Purpose | Act verbs + statutory Means categories + exploitation Purpose |
| **GLAA** | UK GLAA "Spot the Signs" | Observational victim-side detection signs (~1:1 with ILO-11) |
| **FLEX** | Focus on Labour Exploitation | Upstream structural drivers + systemic enabling environment |

## How to read this reference

- **Weight legend:** `S` strong · `M` medium · `W` weak · `—` not in that profile/list · `n/a` structural/legal element or context (not a graded signal).
- **Two weight columns** carry the profile-specific ratings: `A·L` = adults-labour (Delphi), `C·L` = children-labour (Delphi). **Weights are profile-specific** — the same indicator can be weak for adults-labour and strong for children-labour or sexual exploitation. Use the column that matches the case.
- **TVPA / GLAA / FLEX weights are analytic overlays.** The TVPA/AMP model and the 2012 ILO-11 list are *not* officially weighted; the strong/medium/weak methodology originates with the 2009 ILO/EC Delphi survey and is applied here for consistency.
- **Palermo element + phase** is stated once in each dimension heading (it is constant within a Delphi dimension — that is the whole point of the Delphi decomposition). The per-row **ILO-11 #** is what varies.
- These are **screening / detection indicators, not legal determinations.** A single indicator flags risk; the offence requires the combination rule below.

## Case-strength scoring (the headline use: strong + strong ⇒ strong case)

**Step 1 — Score each dimension (ILO/EC combination rule, WCMS_105023 p.3).** A dimension is **POSITIVE** if it contains at least:
- (a) **2 strong**; OR
- (b) **1 strong + 1 medium-or-weak**; OR
- (c) **3 medium**; OR
- (d) **2 medium + 1 weak**.

**Step 2 — Combine the dimensions (Palermo / Moldova LFS classification).**

| Result | Means present | Exploitation | Destination coercion | Classification |
|---|---|---|---|---|
| Successful migrant | no | no | no | not a victim |
| Exploited migrant | no | **yes** | no | labour-rights case |
| Deception + exploitation | deceptive recruitment | **yes** | no | victim of deception + exploitation |
| **Trafficking for forced labour** | **deceptive OR coercive recruitment** | **yes** | **yes** | **VICTIM** |

*Abuse of vulnerability (recruitment or destination) substitutes for or reinforces the "means" element.* For **adults**, trafficking = Act + Means + Purpose. For **children (<18), the Means element is not required** (Palermo Art. 3(c); TVPA mirrors this for sex trafficking of a minor) — Act + a positive Exploitation dimension suffices; the means dimensions add evidentiary weight. **Consent is irrelevant** once any means is used (Palermo Art. 3(b); US courts: initial/voluntary entry is no defence once force/fraud/coercion compels the service).

So two strong indicators in one dimension make that dimension strongly positive; multiple positive means + purpose dimensions = a strong case.

---

## Dimension 0 — The Act (conduct element)

Palermo **ACT** / TVPA **Action**. Weight `n/a` (a required structural verb, not a graded signal). **ILO-11: none** (the ILO-11 are exploitation signs, not act verbs).

| Indicator | Palermo Act | Also flagged by |
|---|---|---|
| Recruitment | recruitment | TVPA §7102; implied by all recruitment-phase dimensions |
| Transportation / transfer | transport / transfer | TVPA §7102; GLAA "controlled travel" is a proxy sign (Dim 9) |
| Harbouring | harbouring | TVPA §7102 |
| Receipt | receipt | TVPA "Provision" / "Obtaining" (supply-side analogs of receipt) |
| Patronizing / soliciting / advertising / maintaining | no direct Palermo analog (US demand-side extension) | TVPA §1591 — "maintains" added by TVPRA 2008; "patronizes/solicits" added by JVTA 2015 |

---

## Dimension 1 — Deceptive recruitment

Palermo **MEANS = fraud / deception**, recruitment phase → maps to **ILO #2 Deception**. *(Note: education-deception is a child-rights / worst-forms marker — ILO C182, UN CRC — and jumps from W to S for children.)*

| Indicator | ILO-11 | A·L | C·L | Also flagged by |
|---|---|---|---|---|
| Deceived about the nature of the job, location or employer | #2 | **S** | **S** | TVPA Fraud "false promises re: work" (S); GLAA "deception re: job" (S) |
| Deceived about wages / earnings | #2 (+#8) | M | M | TVPA "deception re: wages/pay" (S, →#8); GLAA (S) |
| Deceived about conditions of work | #2 | M | M | TVPA "deception re: conditions/destination" (M); GLAA (S) |
| Deceived about content or legality of work contract | #2 | M | M | TVPA "contract substitution" (M, **§1351** fraud in foreign labor contracting) |
| Deceived about housing and living conditions | #2 (re #10) | M | M | TVPA "deception re: living conditions" (M) |
| Deceived about legal documentation / obtaining legal migration status | #2 (→#1) | M | M | — |
| Deceived about travel and recruitment conditions | #2 (→#9) | M | M | FLEX recruitment-fee deception (M) |
| Deceived about family reunification | #2 | M | M | — |
| Deceived through promises of marriage or adoption | #2 | M | M | child-specific harm (sale / forced marriage / illegal adoption) |
| Deceived about access to education opportunities | #2 (C182/CRC) | **W** | **S** | — |

---

## Dimension 2 — Coercive recruitment

Palermo **MEANS = threat / use of force, coercion, abduction**, recruitment phase. `→S at dest` = escalates at destination (Dim 5).

| Indicator | ILO-11 | A·L | C·L | Also flagged by |
|---|---|---|---|---|
| Violence on victims | #5 | **S** | **S** | TVPA Force "physical/sexual violence" (S); GLAA (S) |
| Threats of violence against victim | #6 | M | **S** | TVPA "threats of serious physical harm/restraint" (S, **§7102(3)(A)**); GLAA (S) |
| Abduction, forced marriage, forced adoption or selling of victim | underpins involuntariness; →#5/#6 (child) | M | **S** | Palermo MEANS = abduction + payments/benefits to control (selling) |
| Debt bondage | #9 | M | **S** | TVPA peonage (S, **§1581**); GLAA (S); FLEX visa/flight loan (S) `→S at dest` |
| Confiscation of documents | #7 | M | M | TVPA document servitude (S, **§1592**); GLAA "document retention" (S) `→S at dest` |
| Isolation, confinement or surveillance | #3 + #4 | M | M | TVPA "physical restraint/confinement" (S, →#3); GLAA "restricted movement" (S) `→S at dest` |
| Threat of denunciation to authorities | #6 | M | M | TVPA "abuse of legal process / deportation threat" (S, **§1589(a)(3)**) |
| Threats to inform family, community or public | #6 | M | M | TVPA §1589(c)(2) "serious harm" incl. reputational (S) |
| Violence on family (threats or effective) | #5 / #6 | M | M | — |
| Withholding of money | #8 | M | M | — |

---

## Dimension 3 — Recruitment by abuse of vulnerability

Palermo **MEANS = abuse of a position of vulnerability / abuse of power**, recruitment phase → all map to **ILO #1** (some + #2). *(No "strong" tier exists for adults-labour here.)*

| Indicator | ILO-11 | A·L | C·L | Also flagged by |
|---|---|---|---|---|
| Abuse of difficult family situation | #1 | M | M | — |
| Abuse of illegal status | #1 | M | M | FLEX "insecure immigration status / tied visa" (M) |
| Abuse of lack of education (language) | #1 | M | M | FLEX "isolation — language barrier" (M) |
| Abuse of lack of information | #1 (+#2) | M | M | — |
| Control of exploiters | #1 | M | M | — |
| Economic reasons | #1 | M | M | — |
| False information about successful migration | #1 (+#2) | M | M | — |
| False information about law, attitude of authorities | #1 (+#2) | M | **—** | *(omitted from the child-labour list)* |
| Family situation | #1 | M | M | — |
| Personal situation | #1 | M | M | — |
| Psychological and emotional dependency ("lover-boy" / befriending) | #1 | M | M | — |
| Relationship with authorities / legal status | #1 | M | M | FLEX "tied visa / NRPF" (M/W) |
| Difficulties in the past (prior trafficking / failed migration) | #1 | M | M | — |
| Difficulty to organise the travel | #1 | M | M | — |
| Abuse of cultural / religious beliefs | #1 | **W** | **M** | — |
| General context (post-conflict / environmental / political climate) | #1 | **W** | **M** | — |

---

## Dimension 4 — Exploitative conditions of work (the PURPOSE)

Palermo **PURPOSE = exploitation / forced labour**. The legally decisive dimension for a child case (with the Act).

| Indicator | ILO-11 | A·L | C·L | Also flagged by |
|---|---|---|---|---|
| Excessive working days or hours | #11 (+#10) | **S** | **S** | GLAA "excessive hours / dangerous / no contract or PPE" (M, #11+#10) |
| Low or no salary (below minimum, in-kind) | #8 | M | M | GLAA "withheld / deducted wages" (S); FLEX "bogus self-employment / underpayment" (M) |
| Wage manipulation (fines, excessive deductions, payment to middleman) | #8 / #9 | M | M | GLAA "unlawful deductions" (S) |
| Bad living conditions | #10 | M | M | GLAA "poor / employer-tied accommodation" (M) |
| Very bad working conditions | #10 | M | M | — |
| Hazardous work | #10 | M | M | *(child-sexual profile: S)* |
| No respect of labour laws or contract signed | #10 (+#2) | M | M | FLEX "bogus self-employment / no written contract" (M) |
| No social protection (contract, social insurance, etc.) | #10 | M | **—** | *(omitted from the child-labour list)* |
| No access to education | #10 (C182/CRC) | **W** | **M** | — |

---

## Dimension 5 — Coercion at destination

Palermo **MEANS sustained into the exploitation phase** (what makes the labour involuntary under menace of penalty). This is where recruitment-phase coercion indicators escalate to strong for adults.

| Indicator | ILO-11 | A·L | C·L | Also flagged by |
|---|---|---|---|---|
| Confiscation of documents | #7 | **S** | **S** | TVPA §1592 (S); GLAA (S) — *escalated from M at recruitment* |
| Debt bondage | #9 | **S** | **S** | TVPA §1581 (S); GLAA (S); FLEX (S) — *escalated* |
| Isolation, confinement or surveillance | #3 + #4 | **S** | **S** | TVPA restraint (S); GLAA restricted movement (S) — *escalated* |
| Violence on victims | #5 | **S** | **S** | TVPA Force (S); GLAA (S) |
| Threats of violence against victim | #6 | M | **S** | TVPA §7102(3)(A) (S); GLAA (S) |
| Forced into illicit / criminal activities | forced-labour outcome | M | **S** | Palermo PURPOSE via MEANS = coercion |
| Forced tasks or clients (duties not agreed / quotas) | forced-labour outcome | M | **S** | *(adult-sexual & child-sexual: S)* |
| Under strong influence (dependency; forced to stay with same employer) | #1 + #6 | M | **S** | TVPA "scheme/plan/pattern to instill fear" (S, **§7102(3)(B)**) |
| Forced to act against peers | #6 | M | M | — |
| Forced to lie to authorities, family, etc. | #6 + #4 | M | M | identity change / fraudulent accounts |
| Threat of denunciation to authorities | #6 | M | M | TVPA abuse of legal process (S, §1589(a)(3)) |
| Threat to impose even worse working conditions | #6 | M | M | TVPA §1589(c)(2) "serious harm" incl. financial (S) |
| Violence on family (threats or effective) | #5 / #6 | M | M | — |
| Withholding of wages (retained to compel continued work) | #8 | M | M | TVPA "withholding to compel labor" (M); GLAA (S) |
| Threats to inform family, community or public | #6 | **W** | **M** | TVPA §1589(c)(2) reputational harm |

> **TVPA serious-harm note:** 18 U.S.C. §1589(c)(2) defines "serious harm" to include **psychological, financial, and reputational** harm, so non-physical threats and §7102(3)(B) psychological coercion ("scheme/plan/pattern") are squarely covered — TVPA coercion is broader than the physical reading of Palermo on this axis.

---

## Dimension 6 — Abuse of vulnerability at destination

Palermo **MEANS = abuse of vulnerability sustaining the exploitation** → all map to **ILO #1**.

| Indicator | ILO-11 | A·L | C·L | Also flagged by |
|---|---|---|---|---|
| Dependency on exploiters (daily life / movement / contacts) | #1 | M | M | FLEX "tied visa / break fees" (M) |
| Difficulty to live in an unknown area (language / unfamiliarity) | #1 | M | M | GLAA "isolation — no support network" (M) |
| Economic reasons (poverty / debt / dependants at destination) | #1 | M | M | — |
| Family situation | #1 | M | M | — |
| Relationship with authorities / legal status (irregular status, fear) | #1 | M | M | FLEX "insecure status / NRPF" (M/W) |
| Difficulties in the past | #1 | **W** | **M** | — |
| Personal characteristics (discriminated / marginalised group) | #1 | **W** | **M** | — |

---

## Dimension 7 — Structural drivers (FLEX)

Upstream risk drivers that operationalise **ILO #1 / Palermo "abuse of a position of vulnerability."** Strong *risk multipliers* but medium/weak as standalone *victim* indicators. Use in screening and to explain how the victim-level indicators became possible.

| Indicator | ILO-11 / Palermo | Weight | Note |
|---|---|---|---|
| Insecure immigration status / visa tied to a single sponsor-employer | #1 / abuse of vulnerability | **M** | strong risk multiplier; removes the ability to change employer |
| Worker-paid recruitment fees | precursor to #9 + #1 / recruitment + debt | **M** | contrary to the Employer-Pays Principle / IRIS |
| "Break fees" / penalties / barriers to changing employer | #3 (economic) + #8/#9 / coercion | **M** | care- and seasonal-worker visa schemes |
| Bogus self-employment / no written contract / under-payment | #8 + #10 | **M** | obscures employer liability & minimum-wage protection (FLEX + GLAA) |
| No recourse to public funds (NRPF) | #1 / abuse of vulnerability | **W** | raises captivity / exit risk |
| Lack of worker voice / barriers to remedy & justice | #1 + #3 / abuse of vulnerability | **W** | sustains exploitation by removing exit |
| Subcontracting / outsourcing chains obscuring responsibility | enables #1 + #8 | **W** | diffuses accountability up the supply chain |

---

## Dimension 8 — Systemic enabling environment (FLEX)

Environment-level multipliers with **no victim-level diagnostic value** (weight `n/a`). Belongs in screening / prioritisation, **never** in a per-case forced-labour determination.

| Indicator | Effect | Weight |
|---|---|---|
| Labour-market enforcement gap (inspector:worker below the ILO 1:10,000 benchmark; culture of impunity) | amplifies every ILO indicator by removing deterrence | n/a |
| High-risk sector exposure (agriculture, care, cleaning, construction, hospitality, gig economy) | used to prioritise screening | n/a |

---

## Dimension 9 — Victim-presentation corroborating signs (GLAA)

Raise suspicion and corroborate; **not standalone** ILO-11 indicators or Palermo elements. Weight `W` by design.

| Indicator | Corroborates | Weight |
|---|---|---|
| Unusual / controlled travel — collected and dropped off, transport controlled by a third party | proxy for #3; Palermo Act = transport/harbouring | W |
| Few or no personal possessions / wearing the same clothing | indirect proxy for #8 / #1 | W |
| Physical appearance — malnourished, unkempt, withdrawn, untreated injuries, signs of abuse | #5 / #10 | W |
| Fearful behaviour / mistrust of authorities / lets others speak / scripted answers | #6 (psychological coercion) | W |

---

## Exploitation Purpose taxonomy (statutory anchors)

The exploitative **PURPOSE** (corroborated by ILO #8 wage withholding, #10 abusive conditions, #11 excessive overtime). Weight `n/a` — a required exploitation type, not a graded signal.

| Purpose | Palermo | ILO-11 | US statute |
|---|---|---|---|
| Forced labour / services | forced labour | overall pattern (#8/#10/#11) | 18 U.S.C. §1589 |
| Involuntary servitude | servitude | overall | §1584 |
| Peonage / debt servitude | practices similar to slavery | #9 | §1581 |
| Debt bondage (as purpose) | practices similar to slavery | #9 | §1581 |
| Slavery / practices similar to slavery | slavery | overall | §1590 (trafficking into servitude) |
| Commercial sexual exploitation | sexual exploitation | #5 applied to commercial-sex setting | §1591 |
| Minor (<18) in a commercial sex act | **means not required** (Art. 3(c)) | — | §7102 / §1591 (means waived) |
| Organ removal | organ removal | — | *(Palermo purpose; not in the TVPA labour set)* |

---

## ILO-11 reverse index (which unified indicators feed each base indicator)

Use this to drive detection from the base taxonomy outward.

| ILO-11 indicator | Fed by |
|---|---|
| **#1 Abuse of vulnerability** | all of Dim 3 + all of Dim 6 + "Under strong influence", "Control of exploiters", "Psychological/emotional dependency"; all FLEX structural drivers (Dim 7) |
| **#2 Deception** | all of Dim 1 + "False information about successful migration / about law" + "No respect of contract signed" |
| **#3 Restriction of movement** | "Isolation/confinement/surveillance" (both phases); GLAA "restricted freedom of movement"; TVPA "physical restraint"; FLEX "break fees / barriers to change employer" |
| **#4 Isolation** | "Isolation/confinement/surveillance"; GLAA "isolation"; "Difficulty to live in an unknown area"; "Forced to lie to authorities" |
| **#5 Physical & sexual violence** | "Violence on victims" (both); "Violence on family"; TVPA Force; "Abduction/forced marriage/selling"; "Forced into illicit"/"Forced tasks or clients" (child) |
| **#6 Intimidation & threats** | every "Threat(s)…" row; "Forced to act against peers"; "Forced to lie to authorities"; "Threat to impose worse conditions"; TVPA §1589(c)(2) serious-harm threats; GLAA fearful behaviour (corroborating) |
| **#7 Retention of identity documents** | "Confiscation of documents" (both); TVPA §1592; GLAA "document retention" |
| **#8 Withholding of wages** | "Withholding of money/wages"; "Low or no salary"; "Wage manipulation"; "Deceived about wages"; GLAA withheld wages; FLEX bogus self-employment |
| **#9 Debt bondage** | "Debt bondage" (both); "Wage manipulation"; TVPA §1581; FLEX worker-paid recruitment fees |
| **#10 Abusive working & living conditions** | "Bad/Very bad conditions"; "Hazardous work"; "No social protection"; "Bad living conditions"; "No access to education"; GLAA accommodation |
| **#11 Excessive overtime** | "Excessive working days or hours"; GLAA "excessive hours" |

---

## Phase-escalation table (recruitment → destination)

A real, deliberate weighting feature — coercive force is judged heavier once exploitation is under way.

| Indicator | A·L recruitment → destination | C·L recruitment → destination |
|---|---|---|
| Confiscation of documents | M → **S** | M → **S** |
| Debt bondage | M → **S** | S → S |
| Isolation, confinement or surveillance | M → **S** | M → **S** |
| Threats of violence against victim | M → M | S → S |
| Violence on victims | S → S | S → S |
| Forced into illicit / Forced tasks or clients / Under strong influence | (destination only) M | (destination only) **S** |

> **Transparency footnote:** the enumerated Delphi data (and the verified correction) make **"Violence on victims" strong at *both* phases for adults-labour** — the sole strong coercive-recruitment indicator in that profile. The ILO brochure's summary prose loosely groups it among four "medium→strong" escalators; the three genuine M→S escalators for adults-labour are document confiscation, debt bondage, and isolation/confinement/surveillance.

## Profile caveat, child rule, consent

- **Weights are not universal.** "Forced tasks or clients" is M for adults-labour but S for sexual exploitation; the Exploitation dimension has a strong indicator here (excessive hours) but none for sexual exploitation; education indicators are W for adults-labour but promoted for children. **The child-labour set contains zero "weak" ratings** — several adult-weak items become medium/strong for children. Pick the column for the actual case.
- **Child rule (Palermo Art. 3(c); TVPA §7102 for minor sex trafficking):** Means is **not required** for anyone under 18 — Act + a positive Exploitation dimension establishes trafficking; the five means-bearing dimensions add evidentiary weight only.
- **Consent (Palermo Art. 3(b)):** irrelevant once any Means is used; a worker's initial or voluntary entry is no defence once force, fraud, or coercion compels the service.
- **TVPA Means is narrower than Palermo** (force / fraud / coercion only): Palermo's "abuse of a position of vulnerability," "abduction," and "payments-to-control" are not standalone US means — in TVPA practice they surface inside "coercion" or as the vulnerability backdrop.

## Sources (verified)

- **ILO/EC**, *Operational Indicators of Trafficking in Human Beings — Results from a Delphi survey* (first pub. March 2009, rev. September 2009): weighted lists — `WCMS_105023`; indicator definitions — *Details of indicators for labour exploitation*, `WCMS_105035`.
  https://www.ilo.org/sites/default/files/wcmsp5/groups/public/@ed_norm/@declaration/documents/publication/wcms_105023.pdf · https://www.ilo.org/sites/default/files/wcmsp5/groups/public/@ed_norm/@declaration/documents/publication/wcms_105035.pdf
- **ILO**, *Indicators of Forced Labour* (2012, `WCMS_203832`; first major revision published Nov 2025 — the 11 core indicators are unchanged, with tightened explanations and a new state-imposed forced-labour section).
- **UN**, Protocol to Prevent, Suppress and Punish Trafficking in Persons (Palermo Protocol), **Art. 3** (2000).
- **US TVPA / AMP:** 22 U.S.C. §7102 (definitions; coercion at §7102(3)(A)/(B)/(C)); 18 U.S.C. §1581 (peonage), §1584 (involuntary servitude), §1589 (forced labor; "serious harm" §1589(c)(2)), §1590 (trafficking into servitude), §1591 (sex trafficking; "maintains" added by **TVPRA 2008**, "patronizes/solicits" by **JVTA 2015**), §1592 (document servitude), §1351 (fraud in foreign labor contracting).
- **GLAA** "Spot the Signs" (gla.gov.uk; GLAA absorbed into the UK **Fair Work Agency**, April 2026 — indicator categories reproduced verbatim across official/partner sources).
- **FLEX** (Focus on Labour Exploitation), structural risk-driver analysis (e.g., *Risky Business*, 2017).
