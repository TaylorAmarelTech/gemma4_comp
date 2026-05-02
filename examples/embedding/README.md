# Duecare Embedding Examples

Drop-in integrations of the Duecare safety harness into other apps.
Full guide: [`docs/embedding_guide.md`](../../docs/embedding_guide.md).

## What's here

| Directory | Surface | Status |
|---|---|---|
| [`web-widget/`](./web-widget/) | Single-file vanilla JS — embed in any HTML page | ✓ working |
| [`react-component/`](./react-component/) | React 18+ component | ✓ working |
| [`telegram-bot/`](./telegram-bot/) | Telegram bot wrapping Duecare REST API | ✓ working |
| [`messenger-bot/`](./messenger-bot/) | Facebook Messenger bot for an NGO Page | ✓ working |
| [`whatsapp-cloud-api/`](./whatsapp-cloud-api/) | WhatsApp via Meta's official Cloud API (production) | ✓ working |
| [`whatsapp-twilio/`](./whatsapp-twilio/) | WhatsApp via Twilio Sandbox (5-min prototype) | planned |
| [`wordpress-plugin/`](./wordpress-plugin/) | WordPress shortcode plugin | planned |
| [`browser-extension/`](./browser-extension/) | Chrome/Firefox extension flagging trafficking-shaped content | planned |
| [`android-aar/`](./android-aar/) | Notes on extracting an embeddable Android library from `duecare-journey-android` | planned |
| [`ios-swift-package/`](./ios-swift-package/) | Notes on KMP-based iOS port | planned |
| [`sample_pack/`](../sample_pack/) | Sample extension pack format demo (separate from embeddings) | ✓ working |

## Common pattern

Every embedding talks to a deployed Duecare REST API. Deploy first
(see [`docs/cloud_deployment.md`](../../docs/cloud_deployment.md)),
then point your embedding's `apiUrl` at it.

For **Python** apps that want to skip the REST hop, just
`pip install duecare-llm-chat` and import directly — no embedding
needed.

## Where does the server live?

The embeddings here are **clients**. Where to put the *server* depends
on the deployment topology you've picked:

| Topology | Where the server lives | These embeddings work? |
|---|---|---|
| [A — local all-in-one](../deployment/local-all-in-one/) | Your laptop | yes — `apiUrl=http://localhost` |
| [B — NGO-office edge](../deployment/ngo-office-edge/) | Office Mac mini / NUC | yes — `apiUrl=http://duecare.local` |
| [C — server + thin clients](../deployment/server-and-clients/) | Cloud server | yes — `apiUrl=https://...` |
| [D — on-device only](https://github.com/TaylorAmarelTech/duecare-journey-android) | Worker's phone | no — Android app *is* the client |
| [E — hybrid edge LLM + cloud knowledge](../deployment/hybrid-edge-llm-cloud-rag/) | Server has knowledge only | partial — `/research` works, `/chat` doesn't |

For the topology decision tree, see
[`docs/deployment_topologies.md`](../../docs/deployment_topologies.md).

## Each example includes

- A working code sample
- A README with usage instructions
- A note on which deployment paths it pairs well with
- Production-readiness checklist (auth proxy, rate limiting, etc.)

## Adding a new embedding

1. Create `<your-platform>/` here.
2. Include a runnable example + README.
3. Add a row to the table above + to the matching section in
   `docs/embedding_guide.md`.
4. Open a PR.

## License

Each example inherits MIT from the parent repo.
