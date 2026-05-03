# Embedding Duecare in Other Apps

The Duecare safety harness (Gemma 4 + 42 GREP rules + 26 RAG docs +
4 tools + the rubric system) is designed to be embeddable into other
applications via multiple integration paths. Pick the one that
matches your stack.

> **What you get when you embed Duecare:** the same safety harness
> + chat surface that powers the Kaggle notebooks, the HF Space, and
> the Android app. Same prompt assembly, same harness lift (+87.5 /
> +51.2 / +34.1 pp on the legal_citation_quality rubric), same
> privacy posture (no telemetry by default, local-first wherever
> possible).

## Pick your integration path

| Audience | Path | Effort | Privacy |
|---|---|---|---|
| **Python app** | [`pip install duecare-llm-chat`](#1-python-pip) | 5 min | Local |
| **Any web app** | [JS chat widget](#2-web-widget-vanilla-js) drop-in script | 10 min | Server-side proxy required |
| **React app** | [React component](#3-react-component) | 10 min | Server-side proxy required |
| **WordPress / NGO website** | [WordPress plugin](#4-wordpress-plugin) | 15 min | Server-side proxy required |
| **Telegram bot** | [Telegram example](#5-telegram-bot) | 20 min | Bot API |
| **WhatsApp bot** | [WhatsApp via Twilio](#6-whatsapp-bot-via-twilio) | 30 min | Twilio API |
| **Discord / Slack bot** | [Bot SDK example](#7-discord--slack-bots) | 30 min | Bot API |
| **Other Android app** | [Embeddable AAR](#8-android-library-aar) | 1-2 hr | Local |
| **iOS app** | [Swift Package](#9-ios-swift-package) | 2-3 hr | Local |
| **Backend service in any language** | [REST API + OpenAPI codegen](#10-rest-api--openapi-codegen) | 30 min | Server-side |
| **CLI / shell automation** | [`duecare` CLI](#11-cli) | 5 min | Local |
| **Browser extension** | [Extension scaffold](#12-browser-extension) | 1-2 hr | Local + opt-in API |
| **WhatsApp Business / official API** | [API gateway pattern](#13-whatsapp-business-api) | 2-3 hr | Server-side |

## Architecture

Three layers, each independently embeddable:

```
┌──────────────────────────────────────────────────────────────────┐
│                       LAYER 3: SURFACES                           │
│  React widget, Android AAR, iOS Swift, browser ext, bots, ...     │
│  (every app shape that wants chat + safety)                       │
└──────────────────────────┬───────────────────────────────────────┘
                            │ JSON over HTTP / native call
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                       LAYER 2: API                                │
│  /api/chat/send  — chat with optional harness toggles             │
│  /api/grade      — score a response against the rubric system     │
│  /api/classifier/evaluate — structured-output classification      │
│  /api/harness-info / catalog / docs — introspect the bundled      │
│                                       rules / docs / tools        │
│  Served by FastAPI; OpenAPI spec at docs/openapi.yaml             │
└──────────────────────────┬───────────────────────────────────────┘
                            │ Python imports
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                       LAYER 1: HARNESS                            │
│  duecare.chat.harness — 42 GREP rules + 26 RAG docs + 4 tools     │
│                          + 207 5-tier rubrics + 6 required cats   │
│                          + grade_response() + default_harness()   │
│  Shipped on PyPI as duecare-llm-chat                              │
│  Kotlin port at duecare-journey-android (subset for on-device)    │
└──────────────────────────────────────────────────────────────────┘
```

You can embed at any layer:

- **Layer 1 (just the data + logic):** `pip install duecare-llm-chat`,
  use `GREP_RULES`, `RAG_CORPUS`, `_grep_call`, `_rag_call`,
  `grade_response` directly in your Python code. No HTTP needed.
- **Layer 2 (the API):** run `docker run ghcr.io/tayloramareltech/duecare-llm`
  and call the REST endpoints. Codegen typed clients in any language.
- **Layer 3 (a UI widget):** drop in the JS widget or AAR; everything
  below is wrapped.

Pick the lowest layer that works for you — less infrastructure,
fewer security boundaries.

---

## 1. Python (pip)

```bash
pip install duecare-llm-chat
```

```python
from duecare.chat.harness import (
    _grep_call, _rag_call, grade_response, default_harness,
    GREP_RULES, RAG_CORPUS,
)

# Run GREP against arbitrary text
hits = _grep_call("Pay ₱50,000 training fee before deployment")
for h in hits["hits"]:
    print(f"{h['rule']} [{h['severity']}] - {h['citation']}")

# Run RAG retrieval
docs = _rag_call("What is the placement fee cap for PH-HK?", top_k=3)
for d in docs["docs"]:
    print(f"{d['title']}: {d['snippet'][:120]}")

# Score a model response against the cross-cutting rubric
result = grade_response(
    "legal_citation_quality",
    response_text="The fee violates POEA MC 14-2017 §3 and ILO C181 Art. 7.",
    is_category=True,
)
print(f"Score: {result['pct_score']}%")

# Get everything wired for FastAPI
from duecare.chat import create_app
app = create_app(**default_harness(), gemma_call=your_gemma_function)
# now `uvicorn yourmodule:app` serves the full chat surface
```

## 2. Web widget (vanilla JS)

Single `<script>` tag drop-in. Calls a Duecare REST API you've
deployed (Render / Cloud Run / Helm / etc., per `docs/cloud_deployment.md`).

```html
<!-- on any HTML page -->
<div id="duecare-chat"></div>
<script src="https://cdn.jsdelivr.net/gh/TaylorAmarelTech/gemma4_comp@latest/examples/embedding/web-widget/duecare-widget.js"></script>
<script>
  Duecare.mount('#duecare-chat', {
    apiUrl: 'https://your-duecare-deploy.example.com',
    persona: 'migrant_worker_advisor',     // optional
    toggles: { grep: true, rag: true, tools: true },
    theme: 'light',                          // 'light' | 'dark'
  });
</script>
```

Full source at `examples/embedding/web-widget/`.

## 3. React component

```bash
npm install @duecare/chat-widget    # planned: published from this repo's CI
```

```tsx
import { DuecareChat } from '@duecare/chat-widget';

export default function Page() {
  return (
    <DuecareChat
      apiUrl="https://your-duecare.example.com"
      toggles={{ grep: true, rag: true, tools: true }}
      onResponse={(msg) => console.log('Gemma said:', msg)}
    />
  );
}
```

Reference impl at `examples/embedding/react-component/`.

## 4. WordPress plugin

For NGO websites built on WordPress (Polaris, IJM, MfMW HK all run
WordPress as of last check). PHP shortcode that renders the JS widget.

```php
[duecare_chat api_url="https://your-duecare.example.com"]
```

Plugin scaffold at `examples/embedding/wordpress-plugin/`.

## 5. Telegram bot

The most common messaging channel for OFWs in the field.

```bash
cd examples/embedding/telegram-bot
pip install -r requirements.txt
TELEGRAM_TOKEN=... DUECARE_API=https://... python bot.py
```

Each Telegram message → Duecare `/api/chat/send` → reply. Persona +
toggles configurable per chat. Full source at
`examples/embedding/telegram-bot/`.

## 6. WhatsApp bot via Twilio

Twilio's WhatsApp Sandbox is the standard pre-Business-API
integration path. Reach: 2.5B WhatsApp users.

```bash
cd examples/embedding/whatsapp-twilio
pip install -r requirements.txt
TWILIO_ACCOUNT_SID=... TWILIO_AUTH_TOKEN=... DUECARE_API=https://... \
    flask --app bot run --host 0.0.0.0 --port 5000
# Then expose via ngrok: ngrok http 5000
# Configure the public URL as your Twilio WhatsApp webhook
```

Reference: `examples/embedding/whatsapp-twilio/` (planned for v0.2 of
this guide; current scaffold has the architecture sketch).

## 7. Discord / Slack bots

Same pattern as Telegram — wrap the REST API. Reference impls
available on request; the Telegram example is the cleanest reference.

## 8. Android library (AAR)

For other Android apps that want the Duecare safety harness as a
drop-in module — without depending on the full Duecare Journey app.

The current `duecare-journey-android` repo bundles the harness +
chat into the app. To extract for embedding:

1. Move `app/src/main/java/com/duecare/journey/harness/`,
   `inference/`, `journal/`, `advice/` to a new `harness-lib/`
   Gradle module.
2. Add a `harness-lib/build.gradle.kts` declaring it as
   `com.android.library`.
3. Publish to Maven Central via the standard
   `com.vanniktech.maven.publish` plugin or to GitHub Packages.
4. Other Android projects:

   ```kotlin
   // app/build.gradle.kts
   dependencies {
       implementation("com.duecare:harness:0.5.0")
   }
   ```

   ```kotlin
   // anywhere
   import com.duecare.harness.GrepRules
   import com.duecare.harness.RagCorpus

   val grep = GrepRules()
   val hits = grep.match(userText)
   ```

Full extraction PR scaffold at `examples/embedding/android-aar/`
(planned; currently a TODO with the exact file list).

## 9. iOS Swift Package

Kotlin Multiplatform Mobile (KMP) is the cleanest path: share the
harness logic between Android and iOS without rewriting.

```bash
# convert harness/ to KMP
# (build steps documented at examples/embedding/ios-swift-package/)
```

Resulting Swift Package:

```swift
import DuecareHarness

let grep = GrepRules()
let hits = grep.match(text: userText)
```

Currently TODO; rough effort estimate is 2-3 days post-hackathon for
a KMP refactor.

## 10. REST API + OpenAPI codegen

The lingua franca path. Run the Duecare server (`docker run ...`),
codegen a typed client in your language, call it.

OpenAPI spec: `docs/openapi.yaml`.

```bash
# Generate a Python client
openapi-generator-cli generate \
    -i docs/openapi.yaml \
    -g python \
    -o ./generated/python-client

# Or TypeScript
openapi-generator-cli generate \
    -i docs/openapi.yaml \
    -g typescript-fetch \
    -o ./generated/ts-client

# Or Go, Rust, Java, C#, PHP, Ruby, Kotlin, Swift, Dart, ...
# (openapi-generator supports 60+ targets)
```

The generated client wraps every endpoint with typed methods, so
`client.chat.send({...})` returns a typed `ChatResponse` in any
language.

## 11. CLI

For shell scripts, automation, CI integrations, batch processing.

```bash
pip install duecare-llm
duecare grep "Pay ₱50,000 training fee"            # → JSON of GREP hits
duecare rag "PH-HK placement fee cap"              # → JSON of RAG docs
duecare grade legal_citation_quality "<response>"  # → JSON of rubric scores
duecare chat                                        # → interactive REPL
```

## 12. Browser extension

A Chrome / Firefox extension that adds Duecare safety to any chat
window (ChatGPT, Claude.ai, Gemini, etc.) — flags trafficking-
shaped content the user types or receives.

```javascript
// content-script.js
import { DuecareClient } from './duecare-client.js';
const client = new DuecareClient({ apiUrl: 'http://localhost:8080' });

document.addEventListener('input', async (e) => {
    if (e.target.matches('textarea, [contenteditable]')) {
        const hits = await client.grep(e.target.value);
        if (hits.length > 0) showInlineWarning(hits);
    }
});
```

Full scaffold at `examples/embedding/browser-extension/` (planned).

## 13. WhatsApp Business API

Production WhatsApp integration (vs the Twilio sandbox in §6).
Requires Meta WhatsApp Business API approval. Pattern:

```
WhatsApp user -> Meta WBA webhook -> your webhook -> /api/chat/send -> Gemma -> reply
```

Architecture doc at `docs/whatsapp_business_integration.md` (planned).

## Privacy + security posture for embedded surfaces

The default Duecare server has **no auth**. For embedded use:

1. **Always run behind your own auth proxy.** Don't expose the
   Duecare API directly to the public internet without a per-user
   API key, OAuth, or session cookie in front.
2. **Apply per-tenant rate limits.** A widget on a public NGO
   website needs CAPTCHA / rate-limit / abuse protection.
3. **Use the Duecare server's `localStorage` model for per-user
   customizations.** All customizations (GREP rules, RAG docs,
   personas) live client-side and ship per-message — the server
   stays stateless.
4. **For high-trust deployments** (NGO case-management systems),
   run the entire Duecare stack inside the NGO's network. The
   Helm chart + on-prem k3s install path supports air-gapped
   operation.

## Versioning + compatibility

- **Layer 1 (Python harness):** semver-locked at `0.1.x` while
  pre-1.0. Breaking changes to GREP rule schema, RAG doc shape,
  or rubric criteria signatures bump minor.
- **Layer 2 (REST API):** the OpenAPI spec is versioned. Major
  version bumps include breaking changes; minor adds endpoints +
  optional fields.
- **Layer 3 (widgets / AARs):** each surface follows its own
  release cadence + semver.

## Adding a new embedding path

1. Pick a directory under `examples/embedding/<your-platform>/`.
2. Include a runnable example + README.
3. Add a row to the table at the top of this guide.
4. Open a PR.

## Sources / further reading

- [`docs/cloud_deployment.md`](./cloud_deployment.md) — where to host
  the API the embedded clients call
- [`docs/architecture.md`](./architecture.md) §1.1.1 — the
  layered architecture
- [`docs/openapi.yaml`](./openapi.yaml) — the canonical API spec
- [`packages/duecare-llm-chat/`](../packages/duecare-llm-chat/) —
  Python harness source
- [`infra/`](../infra/) — deployment manifests for every cloud
