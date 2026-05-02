# Duecare Embedding Examples

Drop-in integrations of the Duecare safety harness into other apps.
Full guide: [`docs/embedding_guide.md`](../../docs/embedding_guide.md).

## What's here

| Directory | Surface | Status |
|---|---|---|
| [`web-widget/`](./web-widget/) | Single-file vanilla JS — embed in any HTML page | ✓ working |
| [`react-component/`](./react-component/) | React 18+ component | ✓ working |
| [`telegram-bot/`](./telegram-bot/) | Telegram bot wrapping Duecare REST API | ✓ working |
| [`whatsapp-twilio/`](./whatsapp-twilio/) | WhatsApp via Twilio Sandbox | planned |
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
