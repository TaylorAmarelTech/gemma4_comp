# DueCare — Three Deployment Modes

## 1. Enterprise Integration (Waterfall Detection)

**Target:** Large platforms (Google, Meta, Discord, job boards)

**Architecture:**
```
User posts / chats / searches
         │
    [Quick Filter]  ← keyword + sentiment (cheap, fast, runs on every message)
         │
    Triggers? ──No──→ pass through
         │
        Yes
         │
    [Gemma 4 E4B Analysis]  ← full DueCare rubric evaluation
         │
    Score < threshold?
         │
    ┌────┴────┐
   Yes       No
    │         │
[Action]   pass through
    │
    ├── Warning popup: "This fee may be illegal under ILO C181"
    ├── Link to resources: POEA, labor ministry, hotline
    ├── Flag for human review (content moderation queue)
    └── Block (if score = worst, e.g., explicit recruitment fee instructions)
```

**Quick Filter triggers** (stage 1, runs on everything):
- Keywords: "recruitment fee", "placement fee", "salary deduction",
  "passport held", "training fee", "agency fee", "advance payment",
  "contract substitution", "kafala", "sponsorship transfer"
- Sentiment signals: coercion language, urgency + money,
  employer-to-worker power dynamics
- Context: job postings, DM conversations, group chats about
  overseas employment

**Gemma 4 analysis** (stage 2, only on triggered content):
- Run through the DueCare guardrails scorer with weighted rubric
- Score against all 5 vulnerability categories (BFE, JHE, FCB, PIA, VRV)
- Return structured result: score, grade, applicable ILO indicators,
  jurisdiction-specific law citations

**Actions** (configurable per platform):
- **Warning popup** with localized legal info ("Under Philippines RA 8042,
  recruitment agencies cannot charge domestic workers any fees")
- **Resource links** to POEA, POLO, IOM, local labor ministry
- **Human review queue** for content moderation teams
- **Blocking** for worst-grade content (explicit exploitation instructions)

**API surface:**
```python
# POST /api/v1/analyze
{
    "text": "I need to pay $3000 to the agency before I can start working...",
    "context": "job_posting",  # or "chat", "search", "comment"
    "language": "en",
    "jurisdiction": "PH_HK"   # optional: origin_destination corridor
}

# Response:
{
    "score": 0.12,
    "grade": "worst",
    "action": "block",
    "indicators": ["illegal_recruitment_fee", "debt_bondage_risk"],
    "legal_refs": ["RA 8042 §6", "ILO C181 Art. 7"],
    "warning_text": "This fee may be illegal. Under Philippine law...",
    "resources": [
        {"name": "POEA Hotline", "number": "1343"},
        {"name": "IOM Migration Health", "url": "..."}
    ]
}
```

**Why multimodal matters for this problem:**

Bad actors deliberately use images to evade text-based content filters:
- Screenshots of fee structures (bypass keyword detection)
- Photos of contracts with exploitative clauses (not searchable text)
- QR codes linking to illegal payment portals (opaque to text filters)
- Bank transfer receipts showing illegal deductions
- Fake agency certificates / forged POEA clearances
- WhatsApp screenshots of coercive conversations (image, not text)

Gemma 4's multimodal understanding reads these images. Text-only
filters cannot. This is the load-bearing multimodal use case.

**Similar to existing systems:**
- Facebook's "Are you OK?" popup for suicide-risk content
- Google's "This search is about a crisis" cards
- Discord's age-verification and CSAM detection pipeline
- Job board "report this listing" with automated pre-screening

---

## 2. Worker-Side Tool (Local/Plugin)

**Target:** Prospective migrant workers, their families, community
organizations

**Form factors:**
- **Browser extension** (Chrome/Firefox) that scans job postings and
  chat messages for exploitation indicators
- **WhatsApp/Telegram bot** that workers can forward suspicious messages
  to for analysis
- **Mobile app** (via LiteRT) that runs entirely on-device — no data
  leaves the phone
- **Web app** hosted by an NGO (e.g., Polaris, IJM) where workers paste
  text for analysis

**Architecture:**
```
Worker sees suspicious message / job posting / contract
         │
    [Copy text or screenshot]
         │
    [DueCare Local]  ← runs on phone via LiteRT or via browser extension
         │
    Analysis result:
         │
    ┌────┴────────────────────────────┐
    │  ⚠️  WARNING                    │
    │                                 │
    │  This fee appears to violate    │
    │  Philippine law (RA 8042).      │
    │  Recruitment agencies cannot    │
    │  charge domestic workers any    │
    │  placement fees.                │
    │                                 │
    │  What you can do:               │
    │  • Call POEA at 1343            │
    │  • Contact POLO in [country]    │
    │  • Report to IOM: ...           │
    │                                 │
    │  [Learn More]  [Report This]    │
    └─────────────────────────────────┘
```

**Key design constraint:** Privacy is non-negotiable. The worker's text
never leaves their device. Gemma 4 E2B (via LiteRT or llama.cpp) runs
entirely locally. This is the core value proposition for the hackathon.

**Multilingual support:** Workers from the Philippines, Bangladesh,
Nepal, Indonesia, Ethiopia speak different languages. Gemma 4's
multilingual capabilities handle Tagalog, Bengali, Nepali, Bahasa,
Amharic — not just English.

---

## 3. Agency/NGO Dashboard (Custom-Trained Interface)

**Target:** Recruitment agencies (compliance), NGOs (monitoring),
regulators (enforcement)

**Architecture:**
```
┌──────────────────────────────────────────────────────┐
│  DueCare Dashboard                                    │
│                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │ Batch Eval   │  │ Compliance  │  │ Training     │ │
│  │              │  │ Monitor     │  │ Generator    │ │
│  │ Upload 1000  │  │             │  │              │ │
│  │ job postings │  │ Real-time   │  │ Generate new │ │
│  │ → score all  │  │ feed of     │  │ test cases   │ │
│  │ → export CSV │  │ flagged     │  │ from latest  │ │
│  │              │  │ content     │  │ evasion      │ │
│  │              │  │             │  │ patterns     │ │
│  └─────────────┘  └─────────────┘  └──────────────┘ │
│                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │ Model Comp.  │  │ Domain      │  │ Reports      │ │
│  │              │  │ Explorer    │  │              │ │
│  │ Compare 5    │  │             │  │ PDF/HTML     │ │
│  │ models on    │  │ Browse all  │  │ compliance   │ │
│  │ same prompts │  │ 74K prompts │  │ reports for  │ │
│  │              │  │ + rubrics   │  │ regulators   │ │
│  └─────────────┘  └─────────────┘  └──────────────┘ │
└──────────────────────────────────────────────────────┘
```

**Features:**
- **Batch evaluation:** Upload CSV of job postings / contracts / chat
  logs → score all against rubric → export results
- **Compliance monitoring:** Real-time feed for recruitment agencies
  to self-audit their content
- **Training generator:** Create new test cases from the latest evasion
  patterns discovered by the DueCare agents
- **Model comparison:** Side-by-side evaluation of Gemma 4 vs. GPT vs.
  Claude on the same prompts (useful for agencies choosing a model)
- **Domain explorer:** Browse the 74K prompt corpus with filtering
  by category, difficulty, corridor, grade
- **Compliance reports:** Generate PDF/HTML reports for regulators
  documenting what was tested and how the model performed

**Custom training:** Agencies can fine-tune Gemma 4 on their specific
compliance needs:
- A Philippines recruitment agency focuses on POEA regulations
- A Gulf state labor ministry focuses on kafala reform compliance
- An ILO field office focuses on C181/C189 implementation monitoring

**Deployment:** FastAPI backend (already in DueCare's architecture) +
React/Vue frontend. Can run on-premise or as a hosted service.

---

## How These Map to DueCare Components

| Deployment | Components Used |
|---|---|
| Enterprise (waterfall) | Quick Filter (new) → DueCare scorer → Action Engine (new) |
| Worker tool (local) | LiteRT/llama.cpp model → DueCare scorer → UI (extension/app) |
| Agency dashboard | Full DueCare stack → FastAPI → Web UI |

| Component | Status |
|---|---|
| DueCare scorer (weighted rubric) | ✅ Built |
| 74K prompt corpus | ✅ Extracted |
| 5 evaluation rubrics | ✅ Ported |
| Ollama adapter (local inference) | ✅ Built |
| Pipeline schemas (Pydantic) | ✅ Built |
| Quick Filter (keyword + sentiment) | 🔲 Not built |
| Action Engine (warnings, resources) | 🔲 Not built |
| LiteRT export | 🔲 Not built |
| Browser extension | 🔲 Not built |
| FastAPI dashboard | 🔲 Not built (exists in _reference/) |
| Custom training pipeline | 🔲 Not built |

---

## Video Impact (70 points)

Each deployment mode is a compelling video segment:

1. **Enterprise:** "Imagine if Facebook had flagged this recruitment
   post before Maria clicked Apply" (5 seconds, mock UI)
2. **Worker:** Maria holds her phone, pastes a chat message, sees the
   warning popup in Tagalog (10 seconds, real demo)
3. **Dashboard:** NGO compliance officer runs batch eval, exports
   report for the labor ministry (5 seconds, real UI)

The three modes together tell the story: from platform-level
protection → individual empowerment → institutional accountability.
