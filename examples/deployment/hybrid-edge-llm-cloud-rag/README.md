# Topology E — hybrid on-device LLM + cloud knowledge

The worker runs Gemma locally on their phone. The harness's deterministic
GREP and on-device journal stay private. **Only knowledge lookups
(RAG queries, web research, ILO statute lookups) cross the network**,
and they carry no worker identity — just the question.

```
┌─────────── worker's phone ───────────┐
│                                      │
│   Gemma 4 (MediaPipe, on-device)     │
│   GREP rules (Kotlin port)           │
│   Encrypted journal (SQLCipher)      │
│   Reports tab (ILO + fee analysis)   │
│                                      │
└──────────────┬───────────────────────┘
               │
               │  POST /knowledge/lookup
               │  body: { question, corridor, indicator }
               │  no chat history, no journal data, no PII
               ▼
┌─────── cloud knowledge endpoint ─────┐
│                                      │
│  Latest GREP rule pack (versioned)   │
│  Latest RAG corpus (BM25)            │
│  duecare-llm-research-tools:         │
│    - Tavily / Brave / Serper         │
│    - Wikipedia                       │
│    - URL fetch + readability         │
│                                      │
└──────────────────────────────────────┘
```

## Why this exists

The Duecare Journey Android app v0.6 ships with the harness embedded
(`intel/DomainKnowledge.kt`: 11 GREP rules, 11 ILO indicators,
6 corridor profiles, NGO directory). That embedded knowledge is
**frozen at APK release time** — every Tuesday a new POEA Memorandum
Circular drops, every month a new corridor cap is announced, and the
APK's view of "what's currently legal" gets older.

Topology E lets the worker keep the privacy guarantees of on-device
inference while pulling fresh knowledge from a server the NGO updates
nightly:

| Stays on the phone | Goes to the cloud |
|---|---|
| Worker's chat history | The question itself |
| Worker's journal entries | The corridor code (e.g. "PH-HK") |
| Worker's identity | (nothing else) |
| Worker's location | |
| Photos of contracts / receipts | |

The cloud endpoint never receives the worker's name, phone, or any
journal data. It receives a generic question + corridor and replies
with current rule citations + statute snippets + NGO contacts — exactly
what would normally come from the on-device static `DomainKnowledge`,
but kept fresh.

## Setup — server side

Deploy the same Duecare image used in [Topology C](../server-and-clients/),
but expose only the knowledge-lookup endpoints:

```bash
docker run -d --restart unless-stopped --name duecare-knowledge \
  -p 80:8000 \
  -e DUECARE_MODE=knowledge_only \
  -e DUECARE_ENABLE_CHAT=false \
  -e TAVILY_API_KEY=$TAVILY_API_KEY \
  ghcr.io/tayloramareltech/duecare-llm:latest
```

`DUECARE_MODE=knowledge_only` disables `/chat` and `/classify` (which
would require an LLM on the server) and exposes only:

- `POST /knowledge/lookup` — returns `{ grep_hits, rag_docs, tool_results }`
  for a given question + corridor
- `POST /research` — internet search, no LLM involved
- `GET /grep/rules` — full GREP rule pack (for offline mirror)
- `GET /grep/version` — current pack version (for staleness check)
- `GET /rag/corpus` — full RAG corpus JSON (for offline mirror)
- `GET /rag/version` — current corpus version

The server has no Gemma. It's just the knowledge layer + research
tools. **Cost: $0/mo idle on Cloud Run, $5/mo always-on on a small
VPS.**

## Setup — client side

The Duecare Journey Android app v0.6.0 doesn't ship with this hybrid
mode wired yet. The contract is documented here so it can be added in
v0.7. Until then, two patterns work today:

### Pattern 1 — manual web research from chat

The worker's on-device Gemma answers from its frozen knowledge, then
the worker types `/research <question>` in the chat to invoke the
cloud-only research tool from the [local-cli](../local-cli/) script
or from a web shortcut.

### Pattern 2 — server's `/research` endpoint as a tool the on-device LLM can call

In v0.7 we'll add a "knowledge lookup" prompt-tool that on-device Gemma
can invoke when it doesn't know an answer:

```kotlin
// android/intel/CloudKnowledgeFallback.kt (planned v0.7)
suspend fun lookupKnowledge(
    question: String, corridor: String?,
): KnowledgeResult? {
    if (knowledgeUrl.isBlank()) return null
    return http.post("$knowledgeUrl/knowledge/lookup",
        body = json { put("question", question); put("corridor", corridor) },
    ).asKnowledgeResult()
}
```

The Settings tab will get a "Cloud knowledge endpoint" field next to
the existing "Cloud model" field. They are independent — a worker can
enable knowledge lookups without enabling cloud model routing.

## Security posture

- **No worker identity transmitted.** The cloud endpoint never sees
  who is asking. There's no auth token on the request — the rate limit
  is per-IP, and the IP belongs to the carrier NAT, not the worker.
- **No chat content transmitted.** The lookup request body is just
  `{ question, corridor }`. The worker can preview exactly what's
  being sent in the Privacy section of the chat UI.
- **Pinned TLS.** The Android client should pin the cloud endpoint's
  certificate fingerprint so a hostile network can't MITM the lookup.
  (Pinning config in `android/app/src/main/res/xml/network_security_config.xml`.)
- **Endpoint can be self-hosted.** The NGO can run the knowledge
  endpoint on its own infrastructure (Topology B, plus a public TLS
  termination via Cloudflare Tunnel). No third party touches even the
  de-identified lookup.

## Updating knowledge over the air

The Duecare Journey app v0.7 will support **signed extension packs**
(see [`docs/extension_pack_format.md`](../../../docs/extension_pack_format.md)).
A pack is a zip with:

- New / updated GREP rules
- New / updated RAG corpus docs
- New / updated tool definitions (corridor caps, NGO directory)

Signed with the NGO's Ed25519 key. The app verifies the signature,
unpacks into the on-device knowledge layer, and the worker's chat
immediately reflects the update — without an APK release.

The pack is *fetched* from this Topology E endpoint, *served* by it,
but *applied* on-device. So the worker can:

- run the v0.7 app fully offline once they've fetched the latest pack
- get deterministic, identical knowledge across an entire NGO's
  worker base by signing one pack and serving it to everyone
- audit which pack version applied to a given chat (the version is
  embedded in the journal entry's metadata)

## When to use Topology E

- **You ship the Android app to many workers** and need to update the
  knowledge layer faster than you can ship APK updates.
- **You want privacy-first defaults** but accept that "what's the
  current POEA fee cap?" is not sensitive enough to keep purely local.
- **You don't want to operate a Gemma-serving backend** — the cloud
  endpoint here doesn't run an LLM, just regex matching + BM25 +
  HTTP fetch. Way cheaper than Topology C.

## When to NOT use Topology E

- **Worker is in a country with cloud-egress restrictions** — pure
  Topology D (on-device only).
- **You don't have any infrastructure** — Topology D works without
  this endpoint. Workers will be 1-3 weeks behind on rule updates,
  but the app still functions.
- **You want a chat experience powered by a bigger model than the
  phone can run** — that's Topology C, not E.

## See also

- [Topology D — on-device only](https://github.com/TaylorAmarelTech/duecare-journey-android) — the pure private mode.
- [Topology C — server + thin clients](../server-and-clients/) — what
  to use if you want to centralize the model too.
- [`docs/extension_pack_format.md`](../../../docs/extension_pack_format.md) — the over-the-air knowledge pack format.
- [`docs/research_server_architecture.md`](../../../docs/research_server_architecture.md) — the continuous-research server design that backs the cloud knowledge endpoint.
