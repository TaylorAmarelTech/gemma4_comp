# Representation Loss in LLM Data Pipelines

> Senior-analyst research report. Compiled 2026-06-07. Citations were
> independently web-verified; evidence quality is flagged throughout
> (**confirmed** / **inference** / **preprint** / **writeup** / **author-list
> unverified**). The thesis is treated as a *general representation bottleneck* —
> Markdown is one instance, not the problem.

---

## A. Executive summary

Every step that turns a rich source artifact into model-ready text is a **lossy
encoder**. The thesis — that LLM systems train, fine-tune, embed, and retrieve
from *simplified shadows* of the original artifact, creating blind spots and
security surfaces — is **well-supported by primary evidence**, but the support is
uneven: strongest for document-AI/math/charts and for the security surface,
weaker (under-quantified) for end-to-end attribution of *which* pipeline stage
causes *which* downstream failure, and for provenance/state collapse.

- **Strongest evidence.** Nougat states plainly that "the PDF format leads to a
  loss of semantic information, particularly for mathematical expressions"
  (arXiv:2308.13418, confirmed). ChartQAPro shows a strong model dropping **90.5%
  → 55.81%** when charts/questions become realistic (arXiv:2504.05506, confirmed).
  PoisonedRAG corrupts answers with **5 malicious texts among millions, ~90%
  success** (arXiv:2402.07867, confirmed). Trojan Source (CVE-2021-42574) makes
  rendered text diverge from the token stream (arXiv:2111.00169, confirmed).
- **Weakest / least-studied.** The *quantitative* link from a specific parser
  choice (e.g., footnote detachment, table linearization, chunk boundary) to a
  specific downstream error; provenance/draft-final/jurisdiction collapse; and a
  standard methodology for **declaring** representation loss rather than measuring
  it after the fact.
- **Most-at-risk domains.** Those whose canonical artifact **is not prose**:
  spreadsheets, financial filings/XBRL, legal/regulatory, scientific & math
  papers, engineering/industrial diagrams, medical labels (SPL), charts/dashboards,
  forms/claims, patents, and low-resource scanned archives. These sit at the top
  of every loss axis simultaneously.
- **Markdown is one layer.** The deeper bottlenecks are **acquisition** (Common
  Crawl: a sample, no JS, no cookies/login), **selection/filtering** (C4 blocklist
  bias), **tokenization** (numbers, scripts), and **artifacts that were never
  recorded** (tacit knowledge). The format choice sits between selection and
  tokenization.

---

## B. Core thesis

1. **The pipeline is a stack of lossy encoders.** Acquisition → parsing/OCR →
   extraction → cleaning/filtering → dedup → quality scoring → intermediate
   representation (Markdown/JSON/…) → chunking → tokenization → use
   (pretraining / fine-tuning / embedding / RAG / agentic / eval). Each stage can
   destroy, distort, reorder, or over-emphasize information.
2. **Harm ∝ decision-relevant distinctions destroyed**, not bytes dropped. A
   cosmetic loss (font) is harmless; collapsing a *distinction* (draft/final,
   measured/estimated, zero/blank, active/superseded, header↔cell binding) is the
   failure. This reframes the goal as **declared, auditable loss — not lossless.**
3. **The format is task-relative and self-contradictory across the stack.** The
   Llama 3 report describes *removing* Markdown markers because, for a web-trained
   model, they were distribution pollution (arXiv:2407.21783) — even as RAG/doc-AI
   pipelines *add* Markdown to preserve structure. There is no single correct
   representation.
4. **The same simplification that loses information conflates the *data* channel
   with the *control* channel.** That conflation — not "special characters" — is
   the root of the security surface: untrusted content read as instruction
   (injection) or surviving invisibly past human + classifier (evasion).

---

## C. How LLM document pipelines simplify knowledge

The pipeline differs by lab and by *use* (pretraining vs fine-tuning vs embedding
vs RAG vs eval). Do not assume one pipeline.

| Stage | What it does | What it loses / distorts | Primary evidence |
|---|---|---|---|
| **Collection / crawl** | Sample the web | Dynamic/JS, logged-in, personalized, portal, SCADA, proprietary systems structurally absent | Common Crawl FAQ: "a sample of the web", honors robots.txt, HTTP GET, "JavaScript is not executed and Cookies are not used" (confirmed). Private-system under-representation is **inference** from that design. |
| **Parsing / OCR / extraction** | HTML/PDF/Office/image → text | Layout, reading order, tables, math, figures, OCR substitution errors | Nougat (PDF→loses math semantics, confirmed); Donut (built to avoid **OCR error propagation**, confirmed); van Strien et al. ICAART 2020 (downstream NLP degrades sharply below ~70-80% OCR quality; workshop paper, no arXiv) |
| **Cleaning / filtering** | Heuristic + model quality filters, blocklists | Disproportionate removal of minority-associated and dialect text | Dodge et al., C4 case study, EMNLP 2021, arXiv:2104.08758 (confirmed) |
| **Deduplication** | URL/document/line near-dup removal | Wastes capacity + inflates eval via train-test overlap; can drop legitimate repeats | Lee et al., ACL 2022, arXiv:2107.06499 (confirmed); Llama 3 multi-level dedup (confirmed) |
| **Quality scoring** | Rank/keep "high-quality" docs | Privileges prose-like web text; structured/tabular/scientific underweighted | Dolma, arXiv:2402.00159 (documented mixture, confirmed) |
| **Intermediate representation** | → Markdown/JSON/DocTags/… | Depends on format (see §D format table); Markdown loses merged cells, math, layout | Docling exports Markdown/HTML/lossless JSON/**DocTags** (formats per repo/report body, not the abstract — flagged) |
| **Chunking** | Split into retrievable windows | Detaches disclaimers/footnotes/captions from claims; boundary artifacts | "Problem Solved?" arXiv:2502.18179 (representation/chunking choices materially affect IE, confirmed) |
| **Tokenization** | Text → tokens (BPE) | Number grouping harms arithmetic; byte-fallback degrades rare scripts | Llama 3 tokenizes digits individually as a deliberate lever (confirmed); general BPE-number issue is well-established |
| **Use** | pretrain / fine-tune / embed / RAG / agent / eval | Each consumes a *different* simplification; eval benchmarks inherit the same losses | — |

**Use-stage distinctions (load-bearing):**
- *Pretraining* — bulk web text; markdown markers may be **stripped** (Llama 3).
  Loss here is broad and statistical.
- *Fine-tuning* — chat-template format (itself markdown-ish + special tokens);
  document content embedded within inherits format loss.
- *Embedding / RAG* — Markdown/plain-text chunks dominate; **retrieval ranking**
  becomes an attack surface (PoisonedRAG, FlippedRAG).
- *Agentic* — the model acts on retrieved/tool content → indirect prompt injection
  becomes *consequential*, not just wrong text (Greshake et al.).
- *Evaluation* — benchmarks are built from the same lossy conversions, so they can
  **understate** the problem (ChartQAPro shows prior chart benchmarks were
  saturated/overstated).

---

## D. Taxonomy of representation-loss failure modes

Grouped by mechanism; each with a one-line description and an anchor citation
where one exists.

**Parser / extraction**
- *Parser omission* — content silently dropped (hidden layers, footnotes, alt
  text).
- *Parser hallucination* — extractor emits text not in the source (esp. VLM
  parsers; CDM eval shows GPT-4o hallucinating formulas, arXiv:2409.03643).
- *Wrong reading order* — multi-column/sidebar linearized out of order.
- *OCR substitution errors* — character/word corruption; threshold ~70-80%
  (van Strien et al. 2020); script-dependent (low-resource OCR, arXiv:2412.16119).

**Structural**
- *Table flattening* — merged cells, multi-level headers, header↔cell binding
  lost (PubTables-1M's "oversegmentation" fix, arXiv:2110.00061; FinTabNet/GTE,
  arXiv:2005.00589).
- *Formula loss* — math/chemical notation corrupted (Nougat; CDM eval).
- *Semantic hierarchy loss* — statute Part›Chapter›Section›clause flattened.
- *Footnote / caption detachment* — qualifier separated from claim (chunking).
- *Hidden spreadsheet logic loss* — formulas, hidden sheets/rows, named ranges,
  cross-sheet deps (SpreadsheetBench, arXiv:2406.14991).

**Visual / multimodal**
- *Chart-to-text distortion* — axes, scale, legend, trend lost (ChartQA/ChartQAPro).
- *Image / diagram blindness* — P&IDs, drawings, stamps, signatures → nothing.
- *Visual cue loss* — color-as-semantics, callout/warning boxes, typography.
- *Unit & scale corruption* — thousands separators, units, scale factors.

**Metadata / provenance** (the most under-studied cluster)
- *Metadata loss* — author, timestamp, source reliability.
- *Provenance collapse* — draft/final, active/superseded, proposed/withdrawn,
  jurisdiction, version (XBRL contextual tags exist *because* this matters; SEC's
  own flattened datasets carry an extraction-error caveat).
- *Negative-space loss* — blank field vs unchecked box vs N/A (forms; FUNSD).

**Security / adversarial**
- *Hidden-text leakage / omission* — white-on-white, HTML comments, `opacity:0`
  ("Publish to Perish", arXiv:2508.20863; arXiv:2509.05831).
- *Invisible-char & bidi manipulation* — zero-width, Trojan Source bidi
  (CVE-2021-42574, arXiv:2111.00169).
- *Misleading Markdown/HTML/CSV/XML/YAML syntax* — structure spoofing, fake
  headings, malformed tables, code-fence/delimiter collision.
- *Chunk-boundary distortion* — disclaimer separated from claim; poison elevated.
- *Retrieval poisoning* — PoisonedRAG (arXiv:2402.07867), FlippedRAG (arXiv:2501.02968).
- *Indirect prompt injection* — Greshake et al. (arXiv:2302.12173).
- *Citation laundering / obsolete-document contamination* — stale or
  unverifiable sources retrieved as authoritative.

### D.2 Representation format comparison

| Format | Preserves well | Loses | Enables (errors / attacks) |
|---|---|---|---|
| **Plain text** | Universal, simple, model-native | Everything structural/visual/relational | Hidden-text laundering; no structure to audit |
| **Markdown** | Headings, lists, links, fenced code, simple tables | Merged cells, math, layout, color, provenance | Structure spoofing, image-exfil beacons, fence/delimiter collision |
| **HTML** | Rich structure, some layout, links | Rendered layout, JS-built content; verbose | Comments/`opacity:0` hidden text; script/style injection |
| **XML (generic)** | Arbitrary structure + metadata | Visual layout unless schema encodes it | Entity/parser attacks; schema mismatch |
| **JSON** | Arbitrary typed structure, machine-clean | Layout unless explicitly modeled | Over-trust of "clean" data; injection in string fields |
| **CSV** | Flat tables, ubiquitous | Multi-table, formulas, types, merged cells, hidden sheets | Formula/CSV injection; delimiter ambiguity |
| **OCR text** | Text from images at scale | Layout, accuracy (substitution), order | Error propagation; script-dependent degradation |
| **ALTO XML** | *Physical* layout from OCR (position/size/style) | Logical semantics; verbose | Standard, low attack surface; pairs with METS |
| **TEI** | *Logical* structure + rich semantic annotation | Physical geometry (pairs with ALTO) | Standard; effort-heavy |
| **DocTags / layout-aware JSON** | Tables, forms, code, equations, captions, footnotes + positions | Native modality (raw image) | Best structured fidelity; richer = larger attack surface to validate |
| **Multimodal (page image)** | Layout, figures, stamps, handwriting — *as seen* | Visual-encoder limits (resolution, hallucination) | Relocates the bottleneck to the vision tokenizer; not free |
| **Original-file preservation** | Everything (lossless) | Not model-ready; needs a parser anyway | The safe baseline for audit/provenance |

**Principle:** richer fidelity reduces *information* loss but increases *attack
surface* and cost, and models often under-use the extra structure (ChartQAPro
result). The engineering target is *declared, decision-relevant* fidelity, not
maximal fidelity.

---

## E. Industry impact matrix

Columns: primary docs · what conversion loses · likely model failure · security
risk · existing research/datasets · mitigation · **Severity (1-5)** ·
**Confidence (1-5)**. Scores are analyst judgments (severity = potential harm if
loss occurs; confidence = strength of supporting evidence).

| Industry / domain | Primary doc types | Conversion loses | Likely model failure | Security risk | Research / datasets | Mitigation | Sev | Conf |
|---|---|---|---|---|---|---|---|---|
| **Finance / SEC / XBRL** | Filings, statements, footnotes, XBRL | Dimensional tags, period, unit scale, footnote scope, reported-vs-derived | Misstate figures; ignore restatement/non-GAAP | Poisoned filings in RAG; number spoofing | SEC Inline XBRL; FinTabNet (2005.00589) | Keep XBRL tags as data; tables-as-data; provenance | 5 | 5 |
| **Spreadsheets / FP&A** | Workbooks (formulas, hidden sheets, charts) | Formulas, deps, hidden rows, merged headers, conditional formatting | Wrong totals; miss assumptions; bad edits | Formula/CSV injection | SpreadsheetBench (2406.14991); SheetCopilot (2305.19308) | Operate the workbook, not its text; preserve formulas | 5 | 4 |
| **Insurance / claims** | Forms, scans, photos, adjuster notes | Checkbox state, signatures, blanks, endorsements | Miss exclusion; treat blank as filled | Forged/poisoned forms | FUNSD (1905.13538); RVL-CDIP | Forms-as-structured; negative-space capture | 4 | 4 |
| **Legal / regulatory / contracts** | Statutes, contracts, exhibits, redlines | Hierarchy, exceptions, exhibits, supersession, jurisdiction | Cite superseded/draft clause; detach exception | Injected clauses; obsolete-doc contamination | DocLayNet (2206.01062); "Problem Solved?" (2502.18179) | Provenance/state as data; graph cross-refs | 5 | 4 |
| **Healthcare / pharma (SPL)** | Drug labels, clinical forms, lab tables | Route, boxed warning, pediatric/adult, contraindication scope | Blur dose/warning scope | Tampered labels | FDA SPL (HL7); FUNSD | Keep SPL coded sections; multimodal forms | 5 | 4 |
| **Scientific / math** | PDFs, equations, figures, refs | Formulae, notation, figure refs, proof structure | Corrupt math; detach figure refs | Hidden text in PDFs (peer-review injection) | Nougat (2308.13418); CDM (2409.03643); "Publish to Perish" (2508.20863) | Math-aware markup; vision; defang PDFs | 5 | 5 |
| **Chemistry / patents** | Claims, drawings, reference numerals, formulae | Claim deps, numeral↔drawing links, embodiments | Confuse embodiment/claim | — | DocLayNet (patents) | Structured claim graph | 4 | 3 |
| **Engineering / AEC / BIM** | Drawings, P&IDs, plans, dimensions | Topology, flow direction, symbols, dimensions, level refs | Lose component identity/safety relations | — | (symbol-centric drawing understanding emerging) | Symbol/graph extraction; vision | 5 | 3 |
| **Industrial / oil-gas / nuclear** | P&IDs, procedures, SCADA, logs | Process topology, valve state, interlocks, hazard context | Miss safety interlock relationships | Private-system absence; tampered manuals | (P&ID understanding emerging) | Domain schemas; keep diagrams; human review | 5 | 3 |
| **Logistics / customs / trade** | BoL, HS codes, manifests, tariff tables | Units, Incoterms, line-item relations, license rules | Misclassify goods; miss license | Portal-only data absent (Common Crawl) | Common Crawl FAQ (coverage) | Connect private portals; tables-as-data | 4 | 3 |
| **Charts / BI / dashboards** | Charts, infographics, dashboards | Axes, scale, legend, color map, trend, outliers | Misread values/trends | Misleading-chart injection | ChartQA (2203.10244); ChartQAPro (2504.05506) | Chart-data extraction; vision; verify numerics | 4 | 5 |
| **Government / local ordinance** | Scanned PDFs, agendas, maps, amendments | Map overlays, parcel exceptions, amendment context | Miss local rule/amendment | Uneven digitization; portal gaps | DocLayNet (laws); Common Crawl coverage | Multimodal OCR; provenance; local ingest | 4 | 3 |
| **Low-resource / archives** | Scanned, multilingual, non-Latin | Dialects, scripts, code-switching | Script-dependent OCR collapse | Filtering erases minority text | Low-resource OCR (2412.16119); C4 (2104.08758); HAI gap (white paper) | Script-aware OCR; revisit filters | 4 | 4 |
| **Enterprise RAG / agents** | Mixed corpora, web, tickets | Chunk-boundary context; trust/provenance | Retrieve poison; obey injected instruction | Indirect injection; RAG poisoning; exfil | Greshake (2302.12173); PoisonedRAG (2402.07867); FlippedRAG (2501.02968); OWASP LLM Top 10 | Data/control separation; defang; trust scoring; provenance display | 5 | 5 |

---

## F. Research literature review (verified)

**Corpus curation & coverage bias.** Common Crawl is *a sample*, honors robots,
fetches via HTTP GET, runs no JS and no cookies (FAQ, confirmed) — so dynamic and
login-gated systems are structurally under-represented (**inference**). C4
documentation (Dodge et al., EMNLP 2021, arXiv:2104.08758) found blocklist
filtering disproportionately removes minority-associated text and surfaces
unexpected sources (patents). Dolma (arXiv:2402.00159) is a documented multi-source
mixture, not a neutral mirror. Lee et al. (ACL 2022, arXiv:2107.06499) show dedup
both saves capacity and fixes train-test overlap (eval validity). Llama 3
(arXiv:2407.21783) details a custom HTML parser, math/alt-text handling, multi-level
dedup, heuristic+model filtering, and *removal* of Markdown markers.

**Document AI & layout.** LayoutLM/v2/v3 (arXiv:1912.13318 / 2012.14740 /
2204.08387) show that jointly modeling text + 2D layout (+ image) recovers
information text-only pipelines drop (FUNSD F1 70.72→79.27 for v1). DocLayNet
(arXiv:2206.01062) and PubLayNet (arXiv:1908.07836) are layout datasets;
DocLayNet's six categories include law/finance/patents — the layout-sensitive
corpora. FUNSD (arXiv:1905.13538) treats forms as spatial/semantic artifacts.
RVL-CDIP's critique (arXiv:2306.12550) documents ~8.1% label noise, ambiguity,
train/test overlap, and PII — evidence that *benchmarks themselves* encode
representational risk.

**OCR error propagation.** van Strien et al. (ICAART 2020, ARTIDIGH; workshop, no
arXiv) quantify a ~70-80% OCR-quality threshold below which downstream NLP
degrades sharply, unevenly across tasks. Donut (arXiv:2111.15664) is explicitly
motivated by avoiding OCR error propagation. Low-resource OCR (arXiv:2412.16119,
**preprint, authors unverified**) shows Urdu accuracy collapsing with length while
Latin scripts stay resilient — loss is script-dependent.

**Tables.** PubTables-1M (arXiv:2110.00061) fixes "oversegmentation" ground-truth
inconsistency and annotates blank cells; GTE/FinTabNet (arXiv:2005.00589) targets
hard real-world financial tables; TabFact (arXiv:1909.02164) probes reasoning over
semi-structured tabular evidence — all bearing on what linearization loses.

**Charts.** ChartQA (arXiv:2203.10244) requires recovering data not present as
text; ChartQAPro (arXiv:2504.05506) shows Claude Sonnet 3.5 dropping **90.5% →
55.81%** on realistic charts and concludes prior benchmarks "may have overstated
progress" (confirmed).

**Spreadsheets.** SpreadsheetBench (arXiv:2406.14991) is built from 912 real Excel
forum tasks with multi-table/non-standard/non-textual layouts; SheetCopilot
(arXiv:2305.19308) frames spreadsheets as an agentic control problem (44.3%
single-generation success — hard even with the workbook in hand).

**Formulas / parsing benchmarks.** Nougat (arXiv:2308.13418) is the cleanest "PDF
loses math semantics" citation. CDM (arXiv:2409.03643) measures formula-recognition
errors: GPT-4o hallucination, Mathpix formatting failures, Nougat LaTeX-syntax
errors. OmniDocBench (arXiv:2412.07626) benchmarks diverse PDF parsing across 9
sources. Docling (arXiv:2408.09869) demonstrates the multi-representation point —
one `DoclingDocument` exporting Markdown/HTML/lossless-JSON/DocTags (formats per
repo/report body, **not the abstract**).

**Structured standards.** SEC Inline XBRL embeds machine-readable contextual tags
(period, dimension, definitions); SEC's *own* flattened datasets warn they "are not
a substitute for filings" and may contain extraction errors (confirmed). FDA SPL is
an HL7/FDA XML standard carrying coded sections, routes, and warnings that
free-text scraping flattens.

**Design space.** "Problem Solved?" (arXiv:2502.18179) frames layout-aware IE
around data *structuring* (the representation/chunking choice), model engagement,
and output refinement — directly the thesis.

---

## G. Security and exploitation vectors

The unifying mechanism is **conflation of the data channel and the control
channel**; format syntax is one carrier. Two threat directions:

- **Injection (runtime).** Untrusted retrieved/web/email/document content carries
  instructions the model obeys. Greshake et al. (AISec '23, arXiv:2302.12173)
  established indirect prompt injection on real LLM apps. Hidden carriers are
  documented: white-on-white / `opacity:0` / HTML comments / alt text / metadata
  ("Publish to Perish", arXiv:2508.20863; arXiv:2509.05831; Unit 42 in-the-wild
  writeup). OWASP ranks **LLM01 Prompt Injection** #1 (2025), spanning direct +
  indirect (+ multimodal/hidden per the full entry — **flag:** qualifier from the
  chapter, not the landing snippet).
- **Poisoning (corpus / train-time).** Carlini et al. (S&P 2024, arXiv:2302.10149)
  show **web-scale poisoning is practical** (split-view / frontrunning; ~$60 to
  poison 0.01% of LAION-400M). In RAG, PoisonedRAG (arXiv:2402.07867) reaches ~90%
  success with **5 docs among millions**; FlippedRAG (CCS 2025, arXiv:2501.02968)
  manipulates *ranking* to elevate poison (~50% opinion-polarity shift). OWASP
  **LLM04 Data and Model Poisoning** + **LLM08 Vector/Embedding Weaknesses** cover
  this. Liu et al. (USENIX Sec '24, arXiv:2310.12815) give the formal
  attack/defense benchmark.

**Injection ≠ poisoning.** Injection is a *runtime* exploit via content in the
context window (no training access). Poisoning is a *corpus-time* exploit that
alters what the model learned or what the retriever ranks. A safety system must
defend both, and a third — **evasion** (Trojan Source bidi, zero-width,
homoglyphs; CVE-2021-42574) — where harmful content survives invisibly past both
the human reviewer and the classifier.

**Format-specific manipulability (confirmed classes):** Markdown image-exfil
beacons (Rehberger, Embrace-the-Red 2023; arXiv:2406.00199); fake
headings/structure spoofing; malformed tables/pipes; code-fence and special-token
delimiter collision; CSV/formula injection; HTML hidden text; XML entity attacks;
Unicode bidi/homoglyph. Retrievers can over-rank keyword-stuffed/formatted content
(PoisonedRAG ranks poison via keyword stuffing). Chunking can separate a disclaimer
from the claim it qualifies (a structural attack, under-quantified).

**Mitigations (security):** content/instruction separation (never execute
retrieved text as instructions); **canonicalization / defang** (NFKC, strip
zero-width + bidi, neutralize template delimiters, declaw exfil links); source
**trust scoring**; retrieval filtering + provenance display (show the *raw*, not the
rendered, to reviewers); parser sandboxing; adversarial testing; human review at
the trust boundary. (Map to DueCare's `defang.py` + `_safe_text.py` chokepoint.)

---

## H. Case studies

1. **Math erased by PDF.** Nougat frames scientific-PDF extraction as semantic loss
   "particularly for mathematical expressions"; CDM then shows even GPT-4o/Mathpix/
   Nougat leave large formula-error rates. *Pretraining + RAG + eval* all affected.
2. **Charts overstated.** ChartQAPro's 90.5→55.81 drop shows prior benchmarks
   (chart QA) were saturated — the *evaluation* layer masked the loss. *Eval + RAG.*
3. **Five documents flip RAG.** PoisonedRAG: 5 crafted texts in a million-doc store
   → ~90% wrong answers. *RAG only* (a runtime/corpus exploit, not pretraining).
4. **Text that lies to the eye.** Trojan Source (CVE-2021-42574): bidi overrides
   reorder rendered text vs. the token/byte stream — the representation-vs-tokenization
   gap as a weapon. *All stages where a human reviews rendered text.*
5. **Filtering as a politics.** C4's blocklist disproportionately removed
   minority-associated text — a *selection-layer* loss invisible at the format layer.
   *Pretraining.*
6. **The regulator's own caveat.** SEC publishes flattened financial datasets *and*
   warns they "are not a substitute for filings" and may contain extraction errors —
   an institution declaring its own representation loss. The model to emulate.
7. **DueCare (live).** This project's acquisition pipeline scrapes arbitrary public
   pages → extract → RAG/judge, and its canonical artifacts (recruitment contracts,
   IDs, chat screenshots, fee/wage tables, Arabic kafala docs) sit at the *top* of
   every loss axis. In response we shipped: typed multi-envelope synthesis (not flat
   blobs), a citation/co-mention graph, relevance + meaningfulness gates, a hybrid
   keyword/semantic/lift validation harness, and — directly from this analysis — a
   **defang** primitive (`defang.py`) that strips bidi/zero-width, neutralizes
   chat-template delimiters, declaws markdown image exfil, NFKC-normalizes, and
   *flags* suspicious docs (declared loss). Still open for us: tables-as-data and a
   distinction-preservation eval.

---

## I. Underexplored research gaps

1. **Parser-induced ontology loss** — measuring how often a parser erases a
   *distinction* (draft/final, measured/estimated, zero/blank, active/superseded).
   Almost no benchmark targets this directly.
2. **Chunk-boundary attacks** — quantifying how often chunking separates a
   disclaimer/footnote from the claim it qualifies, and whether an adversary can
   force it. Named widely, measured rarely.
3. **Spreadsheet→text failure modes** — controlled loss measurement across CSV /
   Markdown / HTML / JSON / screenshot for formulas, hidden sheets, merged cells.
4. **Provenance / state collapse** — can models distinguish active / proposed /
   withdrawn / guidance / superseded / local / vendor-summary after normalization?
5. **Multimodal-to-text laundering** — how images/charts/stamps/signatures become
   *overconfident* plain text; calibration of the resulting claims.
6. **Low-resource OCR × filtering compounding** — joint effect of script-dependent
   OCR error and "quality"/language-ID/dedup/blocklist filtering on minority data.
7. **Declared-loss methodology** — a standard for *emitting* a loss manifest per
   conversion (what was linearized/dropped/normalized) and scoring pipelines on it.

---

## J. Mitigations and best practices

**By pipeline layer:**
- *Acquisition* — capture dynamic/login-gated artifacts where authorized; do not
  treat Common Crawl as "all knowledge."
- *Representation* — prefer **typed, structured** output over flat text: tables as
  data (XBRL-/PubTables-like), DocTags / lossless JSON, relationships as graph
  edges; **multimodal-first** for visually-encoded artifacts (charts, drawings,
  scans) — while remembering vision has its own bottleneck.
- *Tokenization* — digit-level number handling; script-aware tokenizers for
  low-resource languages.
- *Chunking* — keep qualifier↔claim together; carry section/provenance into the
  chunk; overlap to avoid boundary loss.
- *Security* — **data/control separation**; canonicalization/defang; source trust
  scoring; retrieval filtering; **provenance display (raw, not rendered)** to
  reviewers; parser sandboxing; adversarial testing; human review at the boundary.
- *Cross-cutting* — **declared loss, not silent**: emit a per-document report of
  what was normalized/dropped; quarantine on adversarial signals; keep the original
  file as the audit baseline.

**DueCare mapping (what's done / open):** done — multi-envelope typed synthesis,
graph edges, relevance+meaningfulness gates, keyword/semantic/lift validation,
`defang.py` (canonicalization + injection/evasion detection), propose-only review.
Open — tables-as-structured-data, a distinction-preservation eval, multimodal
extraction on the visual artifacts.

---

## K. Open research questions (24)

1. How often do PDF→Markdown pipelines detach footnotes from the claims they qualify?
2. How much financial meaning is lost when XBRL filings are reduced to plain text?
3. How do hidden spreadsheet formulas affect LLM understanding of business documents?
4. Can malicious Markdown headings increase retrieval ranking in enterprise RAG?
5. Do OCR errors disproportionately damage low-resource and non-Latin scripts?
6. How often do chart→text conversions lose scale, axis, or legend information?
7. Can prompt injection hide in alt text, metadata, comments, or table cells at scale?
8. Which industries rely most on private, uncrawlable knowledge artifacts?
9. How should systems preserve provenance, status, revision history, and jurisdiction?
10. What is the best *canonical* representation for rich documents in AI pipelines?
11. Can a "declared-loss" manifest be standardized and scored across parsers?
12. How reliably can chunk-boundary placement be adversarially forced?
13. What fraction of table linearizations break header↔cell binding, and where?
14. Does multimodal extraction *reduce* or merely *relocate* representation loss?
15. How calibrated are model claims derived from charts/diagrams vs. from text?
16. Do retrievers systematically over-rank formatted/keyword-stuffed content?
17. What is the minimal poison-document count to flip domain-specific RAG (vs the
    general ~5 in PoisonedRAG)?
18. How effective is NFKC/defang canonicalization against real-world evasion corpora?
19. Can provenance/state distinctions be recovered post-hoc, or must they be captured
    at ingest?
20. How much does dedup remove *legitimate* high-value repetition (statutes, labels)?
21. What is the downstream cost of detaching warnings/callout boxes from drug labels?
22. Can engineering-diagram topology (P&ID flow/interlocks) survive any text format?
23. How does filtering bias interact with low-resource OCR error (compounding harm)?
24. What human-review interface best exposes hidden/encoded content to curators?

---

## L. Annotated bibliography

**Evidence key:** ✅ confirmed (title+ID+venue) · ◐ author-list unverified ·
⚠ preprint/unrefereed · ✎ researcher writeup · § standard/primary doc ·
⊨ inference (not a verbatim source claim).

**Corpus & curation**
- Common Crawl FAQ. § — "sample of the web", robots.txt, HTTP GET, no JS/cookies.
  https://commoncrawl.org/faq · private-system under-representation is ⊨.
- Dodge et al., *Documenting Large Webtext Corpora (C4)*. EMNLP 2021.
  arXiv:2104.08758 ✅ — blocklist removes minority text; unexpected sources.
- Soldaini et al., *Dolma*. ACL 2024. arXiv:2402.00159 ✅ — documented 3T mixture.
- Lee et al., *Deduplicating Training Data Makes LMs Better*. ACL 2022.
  arXiv:2107.06499 ✅ — dedup cuts memorization ~10×, fixes eval overlap.
- Llama Team, *The Llama 3 Herd of Models*. 2024. arXiv:2407.21783 ✅ — custom HTML
  parser, math/alt-text, multi-level dedup, markdown-marker removal.
- Pava et al., *Mind the (Language) Gap*. Stanford HAI white paper. ⚠ (year
  unconfirmed). https://hai.stanford.edu/assets/files/hai-taf-pretoria-white-paper-mind-the-language-gap.pdf
- *Deciphering the Underserved (low-resource OCR)*. arXiv:2412.16119 ⚠◐.

**Document AI / layout / OCR**
- Jaume et al., *FUNSD*. ICDAR-OST 2019. arXiv:1905.13538 ✅.
- Larson et al., *On the Evaluation of Document Classification with RVL-CDIP*.
  EACL 2023. arXiv:2306.12550 ✅◐ — ~8.1% label noise, PII, train/test overlap.
- Pfitzmann et al., *DocLayNet*. KDD 2022. arXiv:2206.01062 ✅◐.
- Zhong et al., *PubLayNet*. ICDAR 2019. arXiv:1908.07836 ✅ — auto-labeled (noise).
- Xu et al., *LayoutLM* (1912.13318) / *v2* (2012.14740) / *v3* (2204.08387). ✅.
- Kim et al., *Donut*. ECCV 2022. arXiv:2111.15664 ✅ — avoids OCR error propagation.
- van Strien et al., *Assessing the Impact of OCR Quality on Downstream NLP*.
  ICAART/ARTIDIGH 2020 (workshop, no arXiv) ✅ — ~70-80% threshold.
- Colakoglu et al., *Problem Solved? IE Design Space for Layout-Rich Docs*.
  EMNLP 2025 Findings. arXiv:2502.18179 ✅.

**Tables / charts / spreadsheets / formulas**
- Smock et al., *PubTables-1M*. CVPR 2022. arXiv:2110.00061 ✅ — oversegmentation fix.
- Zheng et al., *GTE / FinTabNet*. WACV 2021. arXiv:2005.00589 ✅.
- Chen et al., *TabFact*. ICLR 2020. arXiv:1909.02164 ✅.
- Masry et al., *ChartQA*. ACL Findings 2022. arXiv:2203.10244 ✅.
- Masry et al., *ChartQAPro*. ACL Findings 2025. arXiv:2504.05506 ✅ — 90.5→55.81.
- Ma et al., *SpreadsheetBench*. NeurIPS 2024. arXiv:2406.14991 ✅.
- Li et al., *SheetCopilot*. NeurIPS 2023. arXiv:2305.19308 ✅.
- Blecher et al., *Nougat*. 2023 (ICLR 2024). arXiv:2308.13418 ✅ — PDF loses math.
- Wang et al., *CDM (Image Over Text)*. 2024. arXiv:2409.03643 ✅◐ — formula errors.
- Ouyang et al., *OmniDocBench*. CVPR 2025. arXiv:2412.07626 ✅◐.
- Auer et al., *Docling Technical Report*. 2024. arXiv:2408.09869 ✅ (formats per
  repo/report body, not abstract).

**Standards**
- SEC Inline XBRL + Financial Statement Data Sets. § —
  https://www.sec.gov/data-research/structured-data/inline-xbrl ; "not a substitute
  for filings" caveat confirmed.
- FDA Structured Product Labeling (HL7 V3). § —
  https://www.fda.gov/industry/fda-data-standards-advisory-board/structured-product-labeling-resources
- ALTO XML (Library of Congress) §; TEI Consortium §.

**Security**
- Greshake et al., *Not What You've Signed Up For (indirect prompt injection)*.
  AISec '23. arXiv:2302.12173 ✅.
- Zou et al., *PoisonedRAG*. USENIX Sec 2025. arXiv:2402.07867 ✅ — 5 docs → ~90%.
- Liu et al., *Formalizing & Benchmarking Prompt Injection*. USENIX Sec 2024.
  arXiv:2310.12815 ✅ (distinct from Yi Liu et al.).
- Boucher & Anderson, *Trojan Source*. 2021. arXiv:2111.00169 · CVE-2021-42574 /
  -42694 ✅.
- Carlini et al., *Poisoning Web-Scale Training Datasets is Practical*. S&P 2024.
  arXiv:2302.10149 ✅ — ~$60 to poison 0.01% of LAION-400M.
- Chen et al., *FlippedRAG*. CCS 2025. arXiv:2501.02968 ✅ — ranking manipulation.
- Collu et al., *Publish to Perish (hidden-text injection in peer review)*. 2025.
  arXiv:2508.20863 ✅; HTML hidden injection arXiv:2509.05831.
- Rehberger, *Bing Chat data-exfiltration*. Embrace-the-Red 2023 ✎; academic
  corroboration arXiv:2406.00199.
- OWASP Top 10 for LLM Applications (2025). § — https://genai.owasp.org/llm-top-10/
  (LLM01 Prompt Injection; LLM04 Data/Model Poisoning; LLM08 Vector/Embedding).

---

### Bottom line

- **Most at risk:** spreadsheets, financial/XBRL, legal/regulatory, scientific &
  math, engineering/industrial diagrams, medical labels, charts, forms/claims,
  low-resource archives, enterprise RAG/agents.
- **Most important works:** Nougat, ChartQAPro, PubTables-1M, LayoutLMv3, Docling,
  Greshake (indirect injection), PoisonedRAG, Carlini (web poisoning), Trojan
  Source, Dodge/C4.
- **Strongest evidence for the thesis:** explicit semantic-loss framings (Nougat),
  measured capability drops on realistic artifacts (ChartQAPro), and the security
  surface (PoisonedRAG, Greshake, Trojan Source) — all confirmed primary sources.
- **Weakest / least-studied:** stage-attributed quantification of loss→failure;
  provenance/state collapse; chunk-boundary attacks; declared-loss methodology.
- **Recommendations:** *labs* — declared-loss manifests, structured/multimodal
  representations, dedup/filter audits; *enterprise RAG* — data/control separation,
  defang/canonicalization, trust scoring, provenance display, adversarial tests;
  *regulators* — require provenance/state fidelity and machine-readable structure
  (XBRL/SPL as precedent); *researchers* — build the under-studied benchmarks in §I.
- **Prioritized agenda:** (1) declared-loss eval + distinction-preservation
  benchmark; (2) chunk-boundary attack quantification; (3) provenance/state
  recovery; (4) low-resource OCR × filtering compounding; (5) multimodal
  loss-relocation calibration.

*Markdown is not the problem. The problem is that AI systems train and retrieve
from a simplified shadow of the original artifact — and domains whose knowledge
lives in structure, layout, provenance, or private systems are systematically
misunderstood unless those dimensions are preserved, declared, and defended.*
