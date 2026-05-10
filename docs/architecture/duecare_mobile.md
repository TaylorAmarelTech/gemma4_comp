# Duecare Mobile — worker-facing private checker

**Status: Built (sibling repo).** Lives in
[`duecare-journey-android`](https://github.com/TaylorAmarelTech/duecare-journey-android)
v0.9.0.

The worker-facing product. **Global migrant-worker focused, not
OFW-specific** — OFWs are one demo persona among the corridors
covered (Asia + GCC + LATAM + West Africa + Lebanon kafala +
Syria/Ukraine refugee routes).

## Critical framing

The mobile app says, plainly:

> **"This is a private risk check and resource guide. You decide
> what to do next."**

It does not auto-report. It does not tell workers to confront
abusers. It does not store sensitive content by default. It does
not pretend to provide legal advice.

## Modules (target)

| Module | Purpose | Status in v0.9.0 |
|---|---|---|
| Private checker | Paste / screenshot suspicious job offer or message | Built (Journal tab) |
| On-device Gemma | Local inference for privacy | Built (MediaPipe LiteRT, Gemma 4 E2B) |
| Offline packs | Laws, contacts, warning signs by country / corridor | Built (20 corridors hardcoded; Exchange consumption is roadmap) |
| Multimodal scanner | Read job ads, contracts, screenshots | Roadmap (image picker present; on-device multimodal pending) |
| Risk explanation | Plain-language red flags | Built (Advice tab) |
| Trusted help | Official contacts and NGOs | Built (subset of `_contacts.json` baked in; full sync via Exchange is roadmap) |
| Draft report | User-reviewed complaint / referral draft | Built (RefundClaim auto-draft + Reports tab generates intake doc) |
| Safety mode | "Do not confront recruiter / employer" guidance | Built (Settings tab) |
| Localization | Tagalog, Bahasa Indonesia, Nepali, Arabic, Hindi, Bengali, etc. | Partial (en / tl / id / ne / ar shipped; ur / bn / hi / vi / si / ta roadmap) |

## What's already shipped (v0.9.0)

- 4-tab nav: Journal · Advice · Reports · Settings
- MediaPipe Gemma 4 E2B running fully on-device
- Cloud routing (Ollama / OpenAI-compat / HF Inference) as fallback
- SQLCipher encrypted journal
- 11 ILO Forced Labour indicators
- 20 migration corridors (Asia + GCC + LATAM + West Africa)
- Lebanon kafala framework
- Syria / Ukraine refugee corridor coverage
- Add-Fee dialog auto-drafts LegalAssessment + RefundClaim
- Reports tab generates NGO intake markdown
- Image picker (multimodal recipe pending)
- 42 GREP rules (subset of the 161 in the chat package)
- 42-dim rubric (subset of the 46 in the chat package)

APK: [v0.9.0-twenty-corridors-new-rules](https://github.com/TaylorAmarelTech/duecare-journey-android/releases/download/v0.9.0-twenty-corridors-new-rules/duecare-journey-v0.9.0-twenty-corridors-new-rules.apk)

## How Mobile relates to the chat package

The chat package is the **canonical source** of GREP rules, RAG
docs, rubrics, contacts, and personas. The Mobile app is a
**codegen-mirrored** subset — the v0.9.0 app shipped with 42 of the
161 GREP rules and 42 of the 46 rubric dimensions because that was
the point in time when the Android codegen was run. Future versions
either:

1. Pull updated subsets via the Exchange protocol (vetted packs
   delivered as APK in-app updates), or
2. Continue receiving codegen-mirrored snapshots when the Android
   wheel is rebuilt.

Either path keeps Mobile honest: when the chat package gains a
rule, Mobile picks it up at the next sync — never at runtime via
the model.

## Critical boundaries

- Do not auto-report.
- Do not tell workers to confront abusers.
- Do not expose raw messages.
- Do not store sensitive content by default.
- Do not hallucinate contact info.
- Do not pretend to provide legal advice.

These match the chat package's safety boundaries — the model
generates and reasons; trusted data comes from the deterministic
contact directory and signed RAG packs.
