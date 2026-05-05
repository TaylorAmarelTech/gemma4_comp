# Duecare Journey — Android App Architecture (v1)

> Stretch deliverable for the Gemma 4 Good Hackathon. The Android
> companion to the Duecare safety harness: an in-pocket migration
> assistant that runs entirely on-device using **Gemma 4 E2B via
> LiteRT**, helps a migrant worker document each step of their
> journey, gives advice grounded in the bundled GREP/RAG/Tools
> harness, and — when the worker decides to file a complaint —
> generates a ready-to-send complaint packet from the captured
> evidence.
>
> **Status (2026-04-30):** architecture + APK skeleton published.
> v1 MVP build planned for the week of 2026-05-19 (immediately
> post-hackathon). This doc is the design judges can verify.
>
> **The buildable APK skeleton lives in a sibling repo** at
> [`../duecare-journey-android/`](../../duecare-journey-android/) —
> separated from this Python research repo because Android build
> tooling (Gradle, Kotlin, Android SDK) and the Python / FastAPI /
> Kaggle workflow have nothing in common, and forcing them into one
> CI pipeline costs both. See the cross-repo relationship doc in the
> sibling repo for source-of-truth boundaries (e.g., GREP rules
> remain authored here in Python and codegen-mirrored to Kotlin).
>
> Sibling repo also contains a GitHub Actions workflow that builds
> a debug APK on every push, so reviewers / contributors can produce
> a sideloadable APK without installing Android Studio locally.
>
> **Special Technology Track eligibility:** LiteRT.

---

## Vision

A migrant worker's journey is a sequence of decisions, each one
exploitable. *Should I sign this contract? Why does my recruiter want
₱50,000 for "training"? Is this loan's APR legal? Why is my passport
being held? Who do I call if my employer refuses to let me leave?*

Today the worker has two options: ask a frontier-API LLM (which
sends every detail to a third party — frequently violating their
home-country labour-recruiter NDAs and regional data-residency law)
or a mobile-responsive web UI that requires connectivity their
employer often controls.

Duecare Journey is the third option: **a pocket-sized,
zero-connectivity, evidence-keeping legal companion that uses Gemma 4
E2B running entirely on the worker's phone.**

When something goes wrong — and statistically it will, for ~28% of
PH→HK and ~31% of NP→Gulf domestic-worker placements per IJM 2023 —
the journal isn't a memory aid; it's an evidence packet. One tap
generates a structured PDF the worker can hand to POEA, BMET, MfMW
HK, IJM, or their embassy attaché.

---

## The four layers

```
┌──────────────────────────────────────────────────────────────────┐
│                     Duecare Journey (Android)                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  [4] EXPORT LAYER                                          │ │
│  │      One-tap "Generate complaint packet" -> PDF            │ │
│  │      with timeline + evidence photos + auto-drafted        │ │
│  │      narrative + recommended NGO + share intent            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ▲                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  [3] ADVICE LAYER                                          │ │
│  │      Chat UI that pulls journal context into the prompt    │ │
│  │      so each answer is journey-aware                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ▲                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  [2] JOURNAL LAYER                                         │ │
│  │      Room (SQLCipher-encrypted) timeline of events,        │ │
│  │      photos, recruiter messages, contracts                 │ │
│  │      + DataStore for preferences                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ▲                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  [1] INFERENCE LAYER                                       │ │
│  │      LiteRT Gemma 4 E2B (INT8) + bundled harness:          │ │
│  │      49 GREP rules, 33 RAG docs, 5 tools                   │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘

       NO NETWORK CALLS      |       NO CLOUD STORAGE
       NO TELEMETRY          |       NO ACCOUNT REQUIRED
```

### Layer 1 — Inference (LiteRT)

| Concern | Choice |
|---|---|
| Base model | `google/gemma-4-e2b-it` (~2.5B params) |
| Quantization | INT8 (LiteRT default for E2B) |
| On-device size | ~1.5 GB |
| Distribution | Download on first launch (over Wi-Fi only by default), cached to internal storage |
| Throughput target (Pixel 8 / Snapdragon 8 Gen 3) | 10-20 tokens/sec |
| Throughput target (mid-range, Snapdragon 7-class) | 4-8 tokens/sec |
| Conversion path | PyTorch → AI Edge Torch → `.task` LiteRT bundle |
| Hardware acceleration | NNAPI on Android 13+; Vulkan compute fallback; CPU INT8 floor |
| Bundled with | the same 49 GREP rules + 33 RAG docs + 5 tools that the Kaggle notebooks ship with — packed into the APK assets |

**Why E2B not E4B:** E2B fits comfortably on every device with 4GB+
RAM. E4B requires 6GB+ and excludes a meaningful fraction of the
target audience (entry-level Android devices common in PH/ID/NP/BD).
The harness does the heavy lifting on legal-citation quality (see
`docs/harness_lift_report.md`); the model just needs to be coherent.

**Why LiteRT not llama.cpp:** llama.cpp on Android requires NDK
builds, a JNI bridge, and per-architecture binaries. LiteRT is
first-class on Android with NNAPI delegation and AI Edge Torch
conversion, and is what the Special Technology Track rewards. We
keep llama.cpp for desktop deployment (already published in
`kaggle/bench-and-tune/`).

### Layer 2 — Journal (Room + SQLCipher)

The journal is the structured timeline of the worker's migration.
Every event the worker records becomes a row in the journal DB and
can be referenced later — by the chat (Layer 3) for context-aware
advice, and by the complaint packet (Layer 4) as evidence.

```kotlin
@Entity(tableName = "journal_entries")
data class JournalEntry(
    @PrimaryKey val id: String,           // UUID
    val timestamp: Long,                   // epoch millis
    val stage: JourneyStage,               // PRE_DEPARTURE | IN_TRANSIT | ARRIVED | EMPLOYED | EXIT
    val kind: EntryKind,                   // PHOTO | MESSAGE | DOCUMENT | NOTE | EXPENSE | INCIDENT
    val title: String,
    val body: String,                      // user note / extracted text
    val attachmentPath: String?,           // local file path, encrypted
    val locationLatLng: String?,           // optional, opt-in
    val parties: List<String>,             // who was involved (recruiter, employer, agent)
    val tagged_concerns: List<String>,     // e.g. ["fee", "passport_retention"]
    val gemma_analysis: String?,           // optional: Gemma's read on this entry
    val grep_hits: List<String>,           // GREP rules that fired on `body`
)

enum class JourneyStage {
    PRE_DEPARTURE,    // recruitment, contract, fees, training
    IN_TRANSIT,       // departure, layovers, broker handoffs
    ARRIVED,          // onboarding, document handling
    EMPLOYED,         // ongoing work, wages, conditions
    EXIT,             // contract end, complaints, repatriation
}

enum class EntryKind {
    PHOTO,            // contract scan, receipt, ID card
    MESSAGE,          // recruiter WhatsApp, employer note
    DOCUMENT,         // PDF or text doc
    NOTE,             // free-text observation
    EXPENSE,          // money paid + to whom + for what
    INCIDENT,         // something the worker flagged as concerning
}
```

**Encryption.** The DB uses SQLCipher with a key stored in Android
Keystore (hardware-backed where available, software-backed otherwise).
Attachment files (photos, contract scans) are encrypted with a
worker-derived key using Tink's StreamingAead. **No data ever leaves
the device unless the worker explicitly invokes the export layer.**

**Design reference.** The journal + share-to-NGO + panic-wipe pattern
mirrors [Tella by Horizontal](https://tella-app.org/) — open-source
human-rights documentation app used in the field by activists,
journalists, and at-risk populations. We're not forking Tella (different
audience and prompt-injection-bearing chat surface), but their
SQLCipher / EncryptedSharedPreferences / share-intent architecture is
proven at scale and the v1 MVP studies their patterns directly. Code
reference: `github.com/Horizontal-org/Tella-Android`.

**Schema migrations.** Standard Room migration framework. v1 schema
documented above; v2 will add `evidentiary_status` (untouched /
notarized / submitted) and `linked_entry_ids` (for entries that
reference each other, e.g. a payment note referencing a receipt
photo).

### Layer 3 — Advice (Compose chat with journal context)

The chat surface looks like the existing Duecare chat playground but
with one crucial difference: every chat request includes a *journal
context window* in the prompt. The user's recent journal entries are
summarized and prepended to their question, so when they ask "is
this fee normal?" Gemma already knows what corridor they're on, what
they've paid so far, and what their recruiter has been asking.

Pseudocode for prompt assembly (see `AdviceViewModel.kt`):

```kotlin
suspend fun answer(question: String): Flow<String> {
    val recentEntries = journalRepository.recentEntries(maxEntries = 10)
    val journeyStage = journalRepository.currentStage()
    val corridor = journalRepository.detectedCorridor()  // e.g. "PH-HK"

    val systemPrompt = buildJourneyAwarePersona(journeyStage, corridor)
    val journalSummary = summarizeForPrompt(recentEntries)
    val grepHits = harness.runGrep(question + journalSummary)
    val ragDocs = harness.runRag(question + journalSummary, topK = 3)
    val toolResults = harness.runTools(question, corridor)

    val finalPrompt = buildString {
        append(systemPrompt); append("\n\n")
        append("## Worker journey so far\n"); append(journalSummary); append("\n")
        append("## Detected indicators\n"); append(grepHits.format()); append("\n")
        append("## Reference law\n"); append(ragDocs.format()); append("\n")
        append("## Corridor lookups\n"); append(toolResults.format()); append("\n")
        append("## User's question\n"); append(question)
    }
    return inference.streamGenerate(finalPrompt)
}
```

The chat persists in the same SQLCipher DB (separate `chat_messages`
table). The "View pipeline" modal from the desktop chat ports to a
bottom-sheet on mobile — same byte-for-byte transparency, just sized
for a phone.

### Layer 4 — Export (one-tap complaint packet)

When the worker decides to file a complaint, they tap **"Generate
complaint packet."** The exporter:

1. Pulls all journal entries flagged with `tagged_concerns` matching
   trafficking indicators (fee, passport_retention, debt_bondage,
   wage_withholding, etc.).
2. Sorts them chronologically into a timeline.
3. Asks Gemma to draft a narrative cover letter ("On 2026-03-04, the
   worker was charged ₱50,000 by Pacific Coast Manpower for 'training
   fees' she did not know were illegal...").
4. Identifies the appropriate NGO/regulator from the corridor:
   - PH-HK → POEA Anti-Illegal Recruitment Branch + MfMW HK
   - PH-SA → POEA + PH Embassy Riyadh
   - ID-HK → BP2MI + IMWU HK
   - NP-Gulf → DoFE + Pravasi Nepali Coordination Committee
   - BD-Gulf → BMET + WARBE
5. Generates a single PDF with: cover narrative + chronological
   timeline + evidence photo thumbnails + recommended recipient +
   draft text the worker can copy into an email/WhatsApp message to
   the recipient.
6. Opens an Android share intent so the worker can send via any
   installed app (WhatsApp, Gmail, Signal, etc.) or save locally
   and present in person.

**Critical privacy choice:** the complaint packet is NEVER auto-sent.
The worker reviews it, decides if and where to send it, and chooses
their own delivery channel. The app is the evidence-keeper, not the
filing agent.

---

## Tech stack

| Concern | Choice | Why |
|---|---|---|
| Language | Kotlin 1.9+ | Android-native; modern, null-safe, coroutines for streaming inference |
| UI | Jetpack Compose | Declarative; faster iteration than XML; well-suited to chat surfaces |
| Min SDK | API 26 (Android 8.0) | Covers ~98% of in-use devices including budget phones common in PH/ID/NP/BD |
| Target SDK | API 34 (Android 14) | Latest stable |
| Inference | LiteRT (`com.google.ai.edge.litert`) + AI Edge Torch | Special Tech Track; first-class Gemma 4 support |
| Database | Room + SQLCipher | Encrypted-at-rest; standard Android persistence |
| At-rest crypto | Tink (StreamingAead) for files; SQLCipher for DB | Hardware-backed via Keystore where available |
| Preferences | DataStore (Proto) | Type-safe; coroutine-friendly |
| DI | Hilt | Standard Android DI |
| Background work | WorkManager | For optional NGO sync (v2 only); fully opt-in |
| PDF generation | Android `PdfDocument` API | No external dependency |
| Image handling | Coil + Tink crypto wrapper | Compose-native image loading |
| Networking | NONE in v1 | First-launch model download is the only net call; opt-in NGO sync in v2 |

---

## Privacy posture

This app exists for users in environments where their phone may be
inspected by a hostile party (employer, recruiter, sponsor, broker).
The privacy posture is therefore stricter than typical consumer apps:

1. **No telemetry.** Zero analytics SDKs. Zero crash reporting that
   leaves the device. (Local crash logs are written to encrypted
   storage and surface in a debug menu; the worker can choose to
   share them when reporting an app bug.)
2. **No account.** No sign-in, no email, no phone-number entry. The
   app is fully usable by an unauthenticated worker.
3. **No cloud sync.** Zero by default. Optional in v2 as opt-in
   "share my evidence with my chosen NGO" — and even then, the
   worker chooses one specific NGO (POEA, BP2MI, IJM, etc.) and the
   data is end-to-end encrypted to that NGO's published key.
4. **Stealth mode.** A long-press on the app icon launches a decoy
   calculator. The real app opens via a 4-digit PIN entered into the
   calculator. (Standard pattern in domestic-worker safety apps.)
5. **Panic wipe.** A 3-tap-and-hold on the app's title bar opens the
   destructive-action confirm: "Permanently erase all journal
   entries? This cannot be undone." Triggers a SQLCipher key
   destruction + file overwrite + uninstall recommendation.
6. **App lock.** Biometric / PIN required to open after any background
   suspension > 30 seconds. Configurable to "always require."
7. **No background.** The app does no background work in v1. It
   doesn't appear in recent-tasks unless explicitly opened.
8. **Localization.** UI strings translatable. Initial v1 ships with
   English + Tagalog + Indonesian + Nepali + Bengali (the corridor
   languages) — community translations welcome.

---

## What the app does NOT do

- Does NOT auto-detect or auto-classify any photo without explicit
  user action. The worker chooses what to journal.
- Does NOT report to any third party automatically.
- Does NOT use the camera or microphone unless the worker explicitly
  taps the camera / record button.
- Does NOT request location permission unless the worker enables
  per-entry geo-tagging (off by default).
- Does NOT include any "social" features. No sharing with other
  workers, no public posts, no comments.
- Does NOT depend on Play Services. Sideloadable APK.

---

## Roadmap

### v1 — MVP (target: week of 2026-05-19, post-hackathon)

- [ ] LiteRT Gemma 4 E2B inference (single-prompt, no streaming)
- [ ] Encrypted journal with PHOTO / MESSAGE / NOTE / INCIDENT entries
- [ ] Chat UI with journal context injection
- [ ] One-tap complaint-packet PDF generation
- [ ] English-only
- [ ] Sideloadable APK; no Play Store listing

### v2 — Hardened (target: 2026-Q3)

- [ ] Streaming inference
- [ ] Multi-language UI (Tagalog, Indonesian, Nepali, Bengali)
- [ ] Stealth mode + panic wipe
- [ ] Opt-in NGO sync (end-to-end encrypted to a chosen NGO's key)
- [ ] Voice journaling (on-device speech-to-text)
- [ ] Encrypted backup to user-controlled location (Google Drive,
      iCloud, Bitwarden Send, etc.)

### v3 — Ecosystem (target: 2027)

- [ ] Worker-to-NGO secure inbox (NGOs receive E2EE complaint
      packets directly)
- [ ] Pre-departure mode: recruiter-vetting flow before signing
      anything
- [ ] Inter-corridor evidence search ("show me other workers who had
      Pacific Coast Manpower as their agent" — local-only, no
      network)
- [ ] iOS port (Kotlin Multiplatform Mobile)

---

## Why this stretch goal earns its place

| Rubric dimension | How the Android app contributes |
|---|---|
| Impact & Vision (40 pts) | "In your pocket" reaches a meaningfully larger audience than "on your laptop." Workers in domestic-help corridors typically own a phone but not a personal laptop. The journal/evidence packet meets them where the harm actually happens. |
| Video Pitch (30 pts) | Mobile-on-physical-phone footage is dramatically more compelling than a desktop chat. The "tap, type, see ILO citation, generate PDF" flow is filmable in 30 seconds. |
| Technical Depth (30 pts) | LiteRT integration is one of the named Special Technology Tracks. AI Edge Torch + INT8 quant + NNAPI delegation + on-device encryption + journal-context injection in the chat is real engineering, not vaporware. |
| Privacy posture | The "Privacy is non-negotiable" claim from the writeup lands hardest in a context where even the harness can't be subpoena'd. |

---

## How a reviewer can verify this design

The Android app is not built by hackathon submission day, but the
following are ALREADY publishable:

1. This document.
2. The APK skeleton at [`duecare-journey-android/`](../../duecare-journey-android/)
   — separate repo, buildable Gradle project with stub modules for
   inference / journal / advice / export.
3. The included GitHub Actions workflow at
   `duecare-journey-android/.github/workflows/build-apk.yml` —
   produces a sideloadable debug APK on every push to that repo,
   so reviewers can verify the build path without installing
   Android Studio.
4. The mobile-responsive view of the existing chat UI (the same
   harness, same RAG/GREP/Tools, same Pipeline modal) — open the
   HF Space URL on a phone and the full surface adapts to the
   small viewport. This is what the v1 inference layer will look
   like in the Android shell.
5. The layer-2 schema (Room entities) is real; the encryption choices
   (SQLCipher + Tink + Keystore) are real and standard; the v1
   roadmap is realistic.

---

> **Built with Google's Gemma 4** (target on-device variant:
> [google/gemma-4-e2b-it](https://huggingface.co/google/gemma-4-e2b-it)).
> Used in accordance with the
> [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
