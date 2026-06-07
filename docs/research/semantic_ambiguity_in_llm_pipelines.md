# Semantic Ambiguity and Meaning Conflation in LLM Pipelines

> Companion to [`representation_loss_in_llm_pipelines.md`](representation_loss_in_llm_pipelines.md).
> Compiled 2026-06-07. Citations independently web-verified; evidence flagged
> (**✅confirmed · ◐author-list-unverified · ⚠preprint · ⊨inference · ✎blog/trivia**).
> Two numeric corrections carried from verification: SemCor is **226,036** sense
> annotations (not 226,040); OED "run" is **645** meanings (not 606).

---

## A. The thesis, completed: two directions of loss

The first report showed that **rich documents are flattened into simplified text**
(layout, tables, math, provenance lost in conversion). This report adds the second
axis: **rich meanings are flattened into ambiguous tokens, vectors, chunks, labels,
and training examples** — loss that happens *even when every character is preserved
perfectly*. A clean, losslessly-extracted sentence can still be systematically
misunderstood because the word it hangs on has many senses and the disambiguating
context is weak, missing, mixed across domains, or stripped earlier in the pipeline.

> **The strongest form of the thesis:** AI systems lose information in two
> directions — documents are flattened into simplified text, and meanings are
> flattened into ambiguous tokens. **The highest-risk failures occur where both
> losses compound at once:** a scanned recruitment contract (document loss) whose
> decisive word is "bond" or "charge" (meaning loss). DueCare's corpus sits exactly
> there.

This is not a fringe concern. It is the named, central limitation of distributional
semantics. Camacho-Collados & Pilehvar (JAIR 2018, arXiv:1805.04032 ✅) call it the
**meaning conflation deficiency**: a single word type is collapsed into one vector
regardless of how many senses it carries. Contextual models (ELMo, Peters et al.
2018, arXiv:1802.05365 ✅; BERT, Devlin et al. 2019, arXiv:1810.04805 ✅) *reduce*
this by making a token's representation depend on its context — but they **relocate**
disambiguation into the context window rather than eliminating it (⊨ inference;
ELMo explicitly frames its goal as modeling polysemy, not solving WSD). When the
context is thin, noisy, cross-domain, or adversarial, the ambiguity is unresolved
and the model commits to a sense statistically — often the *dominant* one.

---

## B. Why preserved text still loses meaning

Meaning is under-determined by the surface string. Resolution depends on **domain,
syntax, surrounding words, speaker intent, document type, time period, and
metadata** — several of which the pipeline has already discarded by the time the
model sees the text:

- The **domain** that fixes "charge = recruitment fee" is gone if the page was
  ingested into a mixed corpus with no source tag.
- The **document type** that fixes "shall = obligation" is gone if a contract was
  flattened to prose.
- The **time/state** that fixes "the current standard" is gone if the revision
  date and supersession were dropped (the provenance-collapse failure from report 1).
- The **layout** that fixes "positive (test result)" vs "positive (polarity)" is
  gone if a lab table became a line of text.

So semantic ambiguity is partly *primary* (English is polysemous) and partly
*induced* by the representation losses of report 1. They are one problem.

---

## C. The nine ambiguity types

1. **Lexical** — polysemy/homonymy; one word, many senses ("bank" finance vs river;
   "set/run/charge/case/interest/material/positive/normal/field/agent/token/key/
   shell/pipe"). The classic word-sense-disambiguation (WSD) problem.
2. **Domain** — a word with a general sense and a specialized one ("material",
   "significant", "reasonable", "current", "stress", "exposure", "execution",
   "yield", "option", "ground", "fault", "secure"). A general corpus teaches the
   everyday sense; the expert sense is rare.
3. **Syntactic** — multiple parses ("I saw the man with the telescope"); **garden-
   path** sentences force reanalysis (Li et al., CogSci 2024, arXiv:2405.16042 ✅).
4. **Scope** — quantifier/negation/modal interaction ("Every engineer did not
   approve"). Under-studied in modern LLMs (Kamath, Schuster, Vajjala & Reddy,
   TACL 2024, arXiv:2404.04332 ✅ — note: *not* "Kamath & Grand").
5. **Coreference / anaphora** — ambiguous pronouns and referents ("The technician
   told the operator that he should shut down"). Winograd-style reasoning.
6. **Pragmatic** — literal words, context-dependent intent ("That is an interesting
   proposal" = praise / rejection / warning depending on institution).
7. **Temporal** — "current/recent/latest/next/previous/active/retired/effective/
   pending" depend on date and document status.
8. **Figurative** — metaphor, idiom, irony, symbolism, unreliable narration
   ("the market punished the company"; "the immune system remembers").
9. **Technical-term collision** — the same token pulled to different neighborhoods
   by computing/law/medicine/finance/engineering/science ("execute, agent, token,
   key, shell, pipe, prompt, model, field, normal, charge, ground, fault").

---

## D. Taxonomy of semantic failure modes

| # | Failure mode | Mechanism | Stage most affected |
|---|---|---|---|
| 1 | **Meaning conflation** | one vector for all senses | embedding / static |
| 2 | **Dominant-sense bias** | frequent sense wins under weak context | pretraining → all |
| 3 | **Rare-sense suppression** | expert sense underrepresented in corpus | pretraining |
| 4 | **Domain-sense substitution** | wrong domain's sense applied | RAG / agentic |
| 5 | **Obsolete-sense contamination** | archaic/superseded sense retrieved as current | RAG |
| 6 | **Metaphor/literal confusion** | figurative read literally or vice-versa | all |
| 7 | **Negation-scope error** | "not" attaches to wrong operand | reasoning / eval |
| 8 | **Quantifier-scope error** | all/some/only mis-scoped | reasoning |
| 9 | **Modal-obligation error** | may/shall/must confused (permission vs duty) | legal/policy IE |
| 10 | **Pronoun-resolution error** | wrong referent | summarization / multi-turn |
| 11 | **Temporal-reference error** | "current/active" resolved to wrong time | RAG / agentic |
| 12 | **Definition drift** | a term's working definition shifts mid-document/corpus | RAG / long-context |
| 13 | **Cross-domain retrieval collision** | keyword match retrieves wrong-domain doc | **RAG** |
| 14 | **Ambiguity-driven hallucination** | model guesses a sense and fabricates around it | QA / generation |
| 15 | **Adversarial equivocation** | attacker exploits a term's two senses to launder a request | **security** |
| 16 | **Malicious definition injection** | planted/poisoned definition overrides the real sense | **security** |
| 17 | **Ambiguous policy extraction** | a may/shall/scope-ambiguous rule extracted as the wrong rule | legal/compliance |

Modes 13–16 are where semantic ambiguity becomes a **security** surface (see §I) —
and where the published evidence is thinnest.

---

## E. Ambiguity impact matrix (term-level)

Severity = harm if the wrong sense is taken; Confidence = strength of supporting
evidence/centrality (analyst judgment, 1–5). "Trafficking sense" is DueCare's
target sense; the model must resolve to it against the dominant everyday sense.

| Term | Senses (target ↔ distractors) | Domains | Context needed | Likely failure | RAG/security risk | Sev | Conf |
|---|---|---|---|---|---|---|---|
| **bond** | debt-bondage ↔ finance, chemistry, bail | trafficking/finance/chem/legal | debt/repay/wage vs yield/issuer | treat worker-bond as benign deposit | finance pages pollute corpus; equivocation | 5 | 5 |
| **charge** | recruitment fee ↔ electrical, criminal, military | trafficking/physics/law | fee/recruit vs voltage/arrest | miss a banned fee; misread a retaliation threat | wrong-domain retrieval | 5 | 4 |
| **broker** | labour broker ↔ stock/insurance broker | trafficking/finance | recruit/worker vs shares/trade | normalize worker-paid commission | equivocation ("commission is normal") | 4 | 4 |
| **sponsor** | kafala sponsor ↔ event/research sponsor | trafficking/media/science | visa/exit-permit vs brand/grant | treat movement control as benign | equivocation | 5 | 4 |
| **hold** | document withholding ↔ cargo, telecom, finance | trafficking/logistics | passport/withhold vs cargo/call | accept "safekeeping" of passport | euphemism laundering | 5 | 4 |
| **agent** | recruitment agent ↔ software, chemical, spy | trafficking/CS/chem | recruit/manpower vs AI/reagent | normalize wage-deducting agent | cross-domain collision | 4 | 4 |
| **trafficking** | persons ↔ drugs, arms, data/network | trafficking/security/IT | human/forced vs drug/bandwidth | screen the wrong contraband | retrieval collision | 4 | 4 |
| **domestic** | domestic worker ↔ GDP, domestic flight | trafficking/econ/aviation | worker/household vs market/flight | miss domestic servitude | retrieval collision | 4 | 3 |
| **material** | legal materiality ↔ fabric, substance, learning content | law/finance/manufacturing | "material fact/omission" vs cloth | misjudge disclosure significance | wrong-domain extraction | 4 | 4 |
| **positive / negative** | test result ↔ polarity ↔ good/bad ↔ math sign | medicine/physics/math | "tested positive" vs "+terminal" | invert a clinical finding | high-stakes flip | 5 | 4 |
| **normal** | medically normal ↔ Gaussian ↔ perpendicular ↔ ordinary | medicine/stats/geometry | "normal range" vs "normal vector" | misread a lab/result | clinical/eng error | 4 | 3 |
| **execute / execution** | carry out ↔ run code ↔ legal execution ↔ trade execution | law/CS/finance | contract vs code vs order | dangerous action selection in agents | **agentic injection** | 5 | 4 |
| **token / key** | language token ↔ API/crypto token/key ↔ answer key | CS/security/education | auth/crypto vs NLP | leak/confuse credentials | **secret handling** | 4 | 3 |

---

## F. Where each loss bites, by use-stage

The user's pipeline distinction matters: the *same* ambiguity surfaces differently.

| Stage | Dominant ambiguity effect | Note |
|---|---|---|
| **Pretraining** | dominant-sense bias, rare-sense suppression | corpus frequency decides the default sense; minority/expert senses underweighted |
| **Fine-tuning** | domain-sense *re-weighting* | a domain SFT set can teach the target sense — DueCare's `domain_sense_resolution` dimension + `ambiguity_probes` exist for exactly this |
| **Embedding** | meaning conflation (static), residual polysemy (contextual) | retrieval similarity computed in a space where senses partly overlap |
| **RAG retrieval** | cross-domain collision, obsolete/temporal-sense | keyword/embedding match ignores which *domain* the doc means; **the acquisition surface** |
| **Agentic / tool use** | technical-collision → wrong action | "execute"/"charge"/"secure" mapping to the wrong operation is consequential, not just wrong text |
| **Evaluation** | benchmarks under-measure ambiguity | AmbiEnt: GPT-4 disambiguations judged correct only **32%** of the time (Liu et al. 2023, arXiv:2304.14399 ✅) |

---

## G. Datasets and benchmarks (verified)

**Word-sense / context.** SemCor — **226,036** sense annotations across 352
documents, standardized by the unified WSD framework (Raganato, Camacho-Collados &
Navigli, EACL 2017, ACL E17-1010 ✅), which also packages Senseval-2/3 and
SemEval-2007/2013/2015 ✅. **OntoNotes** sense inventory groups fine WordNet senses
to ≥90% inter-annotator agreement (Hovy et al. 2006 ✅). **WiC** (Pilehvar &
Camacho-Collados, NAACL 2019, arXiv:1808.09121 ✅) — does the same word mean the same
thing in two contexts? **XL-WiC** extends it to 12 languages (Raganato et al., EMNLP
2020, arXiv:2010.06478 ✅).

**Coreference / commonsense.** Winograd Schema Challenge (Levesque, Davis &
Morgenstern, KR 2012 ✅); **WinoGrande** ~44k adversarial items (Sakaguchi et al.,
AAAI 2020, arXiv:1907.10641 ✅); **Quoref** coreference-requiring reading
comprehension (Dasigi et al., EMNLP 2019, arXiv:1908.05803 ✅).

**Ambiguous QA.** **AmbigQA / AmbigNQ** — "**over half**" of NQ-open questions are
ambiguous (Min et al., EMNLP 2020, arXiv:2004.10645 ✅; cite "over half", not a
sharper %). **CondAmbigQA** resolves ambiguity with retrieved "conditions"
(Li et al., EMNLP 2025, arXiv:2502.01523 ✅) — and argues apparent hallucination
often stems from query ambiguity.

**Scope / syntax / NLI.** **Scope Ambiguities in LLMs** (Kamath, Schuster, Vajjala &
Reddy, TACL 2024, arXiv:2404.04332 ✅) — ~1,000 scope-ambiguous sentences; explicitly
notes the area is under-studied. **FraCaS** ~346 NLI problems incl. a quantifier-
scope section (FraCaS Consortium 1996 ✅, no canonical DOI). **Garden-path in LLMs**
(Li et al., CogSci 2024, arXiv:2405.16042 ✅).

**Umbrella.** **AmbiEnt** — "We're Afraid Language Models Aren't Modeling Ambiguity"
(Liu et al., EMNLP 2023, arXiv:2304.14399 ✅): the key citation that LLMs are weak at
recognizing and disentangling ambiguity (GPT-4 32%).

---

## H. Industry ambiguous-term inventory (high-stakes)

- **Law / contracts** — material, consideration, party, instrument, execution,
  shall/may/must, "without prejudice", "notwithstanding", scope of exceptions.
- **Medicine / clinical** — positive/negative, normal, acute, stable, discharge,
  presentation, negation ("no evidence of"), tabular dose/route from flattened labels.
- **Pharma** — agent, indication, contraindication, route, boxed warning scope.
- **Finance / accounting** — material(ity), charge, interest, exposure, margin,
  option, position, bond, hedge, derivative.
- **Insurance** — exposure, peril, endorsement, claim, occurrence, "all risks".
- **Cybersecurity** — exploit, payload, shell, pipe, token, key, agent, injection,
  prompt, sandbox.
- **Engineering / manufacturing** — open/closed, live/hot, ground/fault, load/stress,
  current, isolation, normal, tolerance.
- **Oil & gas / utilities / nuclear** — charge, trip, interlock, isolation, hot work,
  live line, "normal operation".
- **Aviation** — domestic, hold, clearance, approach, positive (control), traffic.
- **Logistics / trade compliance** — hold, bond(ed warehouse!), broker, charge,
  manifest, "in bond", origin.
- **Science / research** — field, normal, significant, model, theory, noise, power,
  force, agent.
- **Trafficking (DueCare)** — bond, broker, sponsor, charge, hold, agent, domestic,
  trafficking, exploitation, "safekeeping", "training fee", "commission".

Note the double-collision: in **trade compliance**, "bonded warehouse" and "in bond"
are *legitimate* customs terms — a reminder that the target sense is itself
domain-relative, and a naive trafficking filter on "bond" must disambiguate, which
is exactly what DueCare's `ambiguity.domain_sense` does.

---

## I. Security and exploitation — an honest gap

This is the report's most important **negative** finding. The components exist in
separate literatures; the explicit join of *semantic ambiguity → security* is
largely **unestablished** as of June 2026.

- **Ambiguity → prompt injection (the one on-point result).** ASPI: "Seeking
  Ambiguity Clarification Amplifies Prompt Injection Vulnerability in LLM Agents"
  (arXiv:2605.17324 ⚠ preprint) — when an agent enters an ambiguity-*clarification*
  state, injection success rises sharply (o3: 1.8% → 34.0%). Real and directly
  relevant, but unrefereed and singular.
- **Polysemy → RAG retrieval collision.** ⊨ inference / thin. RAG poisoning and
  retrieval-collision *attack surfaces* are documented (PoisonedRAG arXiv:2402.07867;
  FlippedRAG arXiv:2501.02968 — from report 1), and ambiguity-induced fragility is
  shown (e.g., Chinese textual ambiguity, arXiv:2507.23121 ⚠), but **no peer-reviewed
  work explicitly frames lexical polysemy as a retrieval-collision security vector.**
  It lives in practitioner blogs (✎) and as logical extrapolation.
- **"Definition injection."** ⊨ not an established term — no paper uses it. The
  nearest rigorous anchor is CondAmbigQA's finding that ambiguity drives apparent
  hallucination (a QA-quality framing, not an attack framing).

**Why this matters for DueCare.** Adversarial equivocation is the *practical* threat
our recruiters already use ("it's just a security bond, like a financial
instrument") — see the `ambiguity_probes` set. The lack of a research base means
this is a **contribution opportunity**, not a solved problem: an ambiguity-aware
defense (deterministic domain-sense resolution + a probe suite) is, as far as the
literature shows, novel.

---

## J. The central research question

> *When LLMs learn from large mixed corpora, how often do ambiguous English words
> and phrases produce blended, dominant, or wrong-sense representations — especially
> in niche or high-stakes domains?*

**Answer sketch (evidence-bounded):** Frequently enough to be a first-order problem,
but **unquantified at the corpus level**. We have point evidence — WiC/XL-WiC show
context-sensitivity is imperfect; AmbiEnt shows GPT-4 disambiguates correctly only
~32% of the time; scope ambiguity is under-studied (Kamath et al.); AmbigQA shows
"over half" of natural questions are ambiguous — but **no study measures the rate at
which a deployed pipeline commits to the wrong domain-sense on niche-domain text.**
That measurement, especially for the *compound* document-loss × meaning-loss case,
is the open frontier (and what DueCare's probe set begins to instrument for one
domain).

---

## K. Open research questions (22)

1. What fraction of niche-domain terms are resolved to the *dominant* (wrong) sense
   under realistic RAG context lengths?
2. How much does domain-specific fine-tuning shift sense resolution vs. pretraining
   priors (and does it generalize beyond the SFT terms)?
3. Can a deterministic domain-sense gate measurably reduce wrong-domain ingestion in
   a real acquisition pipeline (DueCare's `ambiguity.domain_sense` is a testbed)?
4. How often does embedding retrieval collide on polysemous keywords across domains,
   and does sense-aware reranking fix it?
5. What is the minimal adversarial-equivocation prompt that flips a safety model to
   the benign sense of "bond/charge/sponsor"?
6. Is "definition injection" (a planted definition overriding the true sense) a real,
   reproducible attack — and what defends it?
7. How do modal verbs (shall/may/must) get mis-extracted from flattened legal/policy
   text, and at what rate?
8. How does negation/quantifier scope error interact with document flattening (e.g.,
   a footnoted exception detached from its rule)?
9. Do temporal terms ("current/active/effective") resolve to the wrong revision when
   provenance was dropped upstream?
10. Which high-stakes flips (clinical positive/negative, electrical vs criminal
    "charge") are most frequent and most harmful?
11. Can sense-disambiguation be evaluated *per domain* with a standard probe suite
    (extend `ambiguity_probes.jsonl` beyond trafficking)?
12. How calibrated is a model's confidence when it has silently chosen a sense?
13. Does multilingual/low-resource text amplify wrong-sense resolution (XL-WiC says
    yes cross-lingually — by how much in deployment)?
14. How does chunking split a term from the context that disambiguates it, and how
    often does that change the resolved sense?
15. Are there systematic dominant-sense biases tied to a corpus's source mix
    (finance-heavy web → "bond=finance")?
16. Can provenance/source-domain tags, carried as metadata, raise correct-sense rate?
17. What is the false-positive rate of keyword-only domain filters (no sense check)
    on adversarially-framed off-domain pages?
18. Do agents take materially different *actions* under technical-term collision
    ("execute/secure/charge"), and can a sense gate prevent it?
19. How do figurative/idiomatic phrases ("the market punished") leak into literal
    factual claims?
20. Does ambiguity-clarification (asking the user) trade accuracy for injection
    exposure, and how to clarify safely (extending ASPI)?
21. Where document-loss and meaning-loss compound (scanned contract + "charge"),
    what is the joint error rate vs. each alone?
22. What human-review interface best surfaces an unresolved/competing-sense decision
    to a curator (the declared-loss principle applied to meaning)?

---

## L. DueCare applied response (built this session)

The analysis is load-bearing, not decorative — it shipped as code:

- **Acquisition gate.** `duecare.research_tools.ambiguity.domain_sense(text)` — a
  deterministic, offline cross-domain word-sense resolver for the 9 trafficking
  collision terms (bond, broker, sponsor, charge, hold, agent, traffick,
  exploitation, domestic). Each ambiguous *bare* term is scored target-sense vs.
  competing-domain anchors; a `collision` flag marks chunks that earn a domain
  keyword only through a competing meaning (a finance "bond" page). Declared-loss
  output: every verdict carries its hit counts.
- **Wired into the curation gate.** `relevance.relevance_with_domain_sense()` adds
  the verdict, a `review_flag`, a score nudge so wrong-sense chunks sort lower, and
  a conservative demotion of borderline off-domain false positives
  (e.g., "freedom of movement of capital … bond market" demoted out). `relevance()`
  itself is unchanged — opt-in.
- **Grading dimension.** `domain_sense_resolution` added to the universal rubric:
  rewards interpreting an ambiguous term in the trafficking/labour sense, penalizes
  equivocation into finance/everyday/technical senses. Applies only when the prompt
  contains a collision term.
- **Prompts / testing.** `configs/duecare/domains/trafficking/ambiguity_probes.jsonl`
  — 10 probes targeting each collision term, including adversarial-equivocation
  recruiter framings and victim-voice phrasings, with worst/best anchors.
- **Tests.** `tests/test_ambiguity.py` (10) covers target/off-domain/unresolved
  resolution and the gate's flag+demote behavior; the rubric addition is validated
  green against the 156-test harness-behavior suite.

This makes DueCare, as far as the §I literature shows, an early concrete
implementation of an **ambiguity-aware safety pipeline**: deterministic domain-sense
resolution at the acquisition boundary, a sense-resolution grading dimension, and an
equivocation probe suite.

---

## M. Annotated bibliography

✅confirmed · ◐author-list-unverified · ⚠preprint · ⊨inference · ✎blog/trivia

**Meaning representation**
- Camacho-Collados & Pilehvar, *From Word to Sense Embeddings: A Survey…*, JAIR 2018.
  arXiv:1805.04032 ✅ — coins/uses "meaning conflation deficiency".
- Peters et al., *Deep contextualized word representations (ELMo)*, NAACL 2018.
  arXiv:1802.05365 ✅ (relocation-not-solution framing ⊨).
- Devlin et al., *BERT*, NAACL 2019. arXiv:1810.04805 ✅.

**WSD / context**
- Raganato, Camacho-Collados & Navigli, *WSD: A Unified Evaluation Framework*,
  EACL 2017, E17-1010 ✅ — SemCor **226,036** annots / 352 docs; Senseval+SemEval sets.
- Hovy et al., *OntoNotes: The 90% Solution*, HLT-NAACL 2006 ✅.
- Pilehvar & Camacho-Collados, *WiC*, NAACL 2019. arXiv:1808.09121 ✅.
- Raganato et al., *XL-WiC*, EMNLP 2020. arXiv:2010.06478 ✅.

**Coreference / commonsense**
- Levesque, Davis & Morgenstern, *The Winograd Schema Challenge*, KR 2012 ✅.
- Sakaguchi et al., *WinoGrande*, AAAI 2020. arXiv:1907.10641 ✅ (~44k).
- Dasigi et al., *Quoref*, EMNLP 2019. arXiv:1908.05803 ✅.

**Ambiguous QA / scope / syntax / umbrella**
- Min et al., *AmbigQA*, EMNLP 2020. arXiv:2004.10645 ✅ ("over half" of NQ-open).
- Li et al., *CondAmbigQA*, EMNLP 2025. arXiv:2502.01523 ✅.
- Kamath, Schuster, Vajjala & Reddy, *Scope Ambiguities in LLMs*, TACL 2024.
  arXiv:2404.04332 ✅ (NOT "Kamath & Grand").
- FraCaS Consortium, *FraCaS test suite*, 1996 ✅ (no canonical DOI).
- Li et al., *Incremental Comprehension of Garden-Path Sentences by LLMs*,
  CogSci 2024. arXiv:2405.16042 ✅.
- Liu et al., *We're Afraid Language Models Aren't Modeling Ambiguity (AmbiEnt)*,
  EMNLP 2023. arXiv:2304.14399 ✅ (GPT-4 32%).

**Security (thin / gap)**
- *ASPI: Seeking Ambiguity Clarification Amplifies Prompt Injection…*,
  arXiv:2605.17324 ⚠ — only directly on-point result (o3 1.8%→34.0%).
- *Fragility via Chinese Textual Ambiguity*, arXiv:2507.23121 ⚠ — ambiguity fragility.
- (Cross-ref report 1: PoisonedRAG 2402.07867, FlippedRAG 2501.02968 — RAG poisoning
  surfaces that polysemy could feed, but the join is ⊨ not established.)

**Lexicographic trivia** (✎, edition-dependent, not peer-reviewed)
- "set" = 430 senses, OED 2nd ed. (Guinness World Records).
- "run" = **645** meanings, OED 3rd-ed. editors (Winchester, NYT, 28 May 2011).

---

### Bottom line

Semantic ambiguity is the **second representation bottleneck**: meaning collapsed
into ambiguous tokens, surviving even perfect text extraction. It is well-named
(meaning conflation deficiency) and demonstrably unsolved (AmbiEnt 32%; scope
under-studied; "over half" of questions ambiguous), but **unquantified at the
deployed-pipeline level** and **barely studied as a security surface** (one preprint).
The compounding case — document-loss × meaning-loss on the same decisive word — is
the frontier and is exactly DueCare's operating regime. We responded in code
(`ambiguity.py`, the sense-aware gate, the `domain_sense_resolution` dimension, the
equivocation probe set), turning a research observation into a working
ambiguity-aware safety pipeline.
