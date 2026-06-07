# Acquisition — diverse sources + trend taxonomy

> Research-compiled 2026-06-07. The acquisition pipeline currently harvests ~107
> gov/NGO **sitemaps** (static HTML/PDF). This is the roadmap to *more, more
> diverse, machine-accessible* sources and the **trend-detection** layer that
> turns harvested text into intelligence (not just stored documents).

## 1. Source expansion — beyond sitemaps

Brittle sitemap-HTML is the narrow path. The high-leverage move is **API / RSS /
bulk** sources that slot straight into `fetch → extract → chunk → dedup → scrub →
graph → stage` and refresh on a schedule.

### Integrate-first shortlist (free, machine-accessible)

| # | Source | Endpoint | Method | Intelligence |
|---|---|---|---|---|
| 1 | **GDELT 2.0 DOC API** | `api.gdeltproject.org/api/v2/doc/doc?query=...&format=json` | REST (no key) | Global news, 65 languages, `THEME:TRAFFICKING_*`; the best **emerging-trend** signal (15-min cadence) |
| 2 | **ReliefWeb API** | `api.reliefweb.int/v1/reports?appname=duecare&query[value]=trafficking` | REST (no key) | 4,000+ NGO/UN sources, editor-tagged — best coverage-per-integration |
| 3 | **OpenSanctions bulk** | `opensanctions.org/datasets` | bulk JSON/CSV | Pre-merges OFAC SDN + **UFLPA entity list** + **CBP WROs** with entity resolution |
| 4 | **CourtListener v4** | `courtlistener.com/api/rest/v4/search/?q=trafficking&type=o` | REST (free key) + bulk | US case law full-text + citation graph |
| 5 | **OpenAlex** | `api.openalex.org/works?filter=...` | REST (free key since 2026-02) + S3 snapshot | 250M works, abstracts, citations |
| 6 | **CORE** | `api.core.ac.uk/v3/search/works?q=forced+labour` | REST (free key) | 40M+ **full-text** OA papers |
| 7 | **Wikidata SPARQL** | `query.wikidata.org/sparql` | SPARQL (no key) | Entity grounding (agencies, NGOs, conventions, corridors) |
| 8 | **CTDC + Walk Free GSI** | `ctdatacollaborative.org`, `walkfree.org/.../downloads` | bulk CSV | Victim-level (synthetic, PII-safe) + country prevalence — grounds numeric claims |

**Tier-2:** Semantic Scholar Datasets API · EUR-Lex CELLAR SPARQL · ILOSTAT SDMX ·
DOL ILAB "Sweat & Toil" API · UK Modern-Slavery Statement Registry CSV · Google
News `site:` RSS bundles · HRW / Migrant-Rights / Anti-Slavery RSS · ILO Research
Repository OAI-PMH · DMW/DoFE/BMET/BP2MI origin-country portals (HTML + translate).

### Rules that still apply
- **Two corpora:** trafficking sources → trafficking `RAG_CORPUS`; never commingle
  with the separate `MULTIDOMAIN_CORPUS`.
- **Volatile vs stable (rule 80):** banned-agency lists, fee caps, sanctions, hot
  sectors, compound names → **tool/RAG packs**, never fine-tune targets. Reasoning
  structure (ILO indicators, "any-label fee = violation") is fine-tunable.
- **Ethics (rule 10):** worker-voice / victim-level data → anonymizer, aggregate
  only. **Propose-only** staging stays the rule.

## 2. Trend taxonomy → envelope types

The synthesizer (`research_tools/synthesize.py` + `scripts/synthesize_acquisition.py`)
detects these and emits the matching knowledge envelope. *Trend = velocity*: track
first-seen + frequency deltas, not just presence.

| Trend | Key detectable signals | Envelope | Freshness |
|---|---|---|---|
| **Emerging corridors** | origin↔dest co-occurrence NOT in known set; "bilateral/G2G agreement signed"; "deployment ban lifted/imposed" | `corridor_record` stub + `context_snippet` | volatile (list) / baked (logic) |
| **Fee camouflage** | `<modifier> (bond\|deposit\|deduction\|fee\|charge\|levy)`; "deducted from your first salary"; "refundable after two years" | `grep_rule` + `context_snippet` (→ `FEE_CAMOUFLAGE_LABELS`) | hybrid |
| **Digital coercion** | "wages held in the app"; "biometric scan to withdraw"; "passport stored in app"; "debt-tracker app" | `grep_rule` + `rubric_dimension` | mostly baked |
| **Recruitment-tech abuse** | "job offer via Telegram/TikTok"; "AI-generated job ad / deepfake recruiter"; "verification fee to secure the job"; "pay via gift card/USDT" | `grep_rule` + `rubric_dimension` | hybrid |
| **Scam compounds** | Myawaddy/KK Park/Sihanoukville; "scam compound"; "pig-butchering"; "forced to scam"; "resold to another compound" | `grep_rule` (critical) + `rag_doc` | hybrid |
| **Crisis flows** | "displaced … vulnerable to trafficking"; "(earthquake\|conflict) … exploit"; "stranded workers … wage theft" | `context_snippet` (event→corridor) | volatile |
| **Sector shifts** | "surge in cases in (care\|construction\|fishing\|gig)"; distant-water fishing; rented gig accounts | `context_snippet` counter | volatile |
| **Enforcement** | WRO / UFLPA; "convicted of trafficking … N years"; "licence revoked/suspended"; "TIP Tier downgrade" | `rag_doc` + `corridor_record` | volatile |
| **Financial typologies** | hawala/hundi; "wages routed to recruiter's account"; "USDT … ransom"; mule/structuring/shell | `rag_doc` + `grep_rule` | mostly baked |
| **Vulnerability / counter-innovation** | study/remote-work-visa abuse; "Employer-Pays Principle"; IRIS; "WPS"; survivor-led | `context_snippet` / `rag_doc` + `rubric_dimension` | hybrid |

### Run it

```bash
"$py" scripts/synthesize_acquisition.py
# -> reports/acquisition/trend_report.json + synthesis_envelopes.jsonl
```

First real run (37,052-chunk corpus): **84** scam-compound, **25** financial-
typology, **24** enforcement, **5** crisis-flow signals + novel fee terms →
54 candidate `grep_rule`/`context_snippet` envelopes for curator review.

## 3. Open follow-ups
- Wire the integrate-first sources as connectors (GDELT/ReliefWeb incremental;
  OpenAlex/CourtListener/OpenSanctions bulk refresh).
- LLM reasoning pass (Gemma/Ollama) over the gated set for structured fact
  extraction beyond regex.
- Frontier **prioritization** (drain by domain-novelty, not insertion order — the
  rowid drain hits already-covered domains).
- Velocity tracking (first-seen timestamps + deltas) for true trend detection.
