# Chat harness

| Method | Path | Status |
|---|---|---|
| POST | `/api/chat/upload-image` | live |
| GET | `/api/chat/image/{sid}` | live |
| POST | `/api/chat/send` | live (Phase 5b) |

## Files

- `handler.py` -- image endpoints (`register_routes`)
- `send.py` -- chat-send orchestrator (`serve_chat_send`)

The orchestrator takes its three helpers (`resolve_messages`,
`call_gemma`, `run_harness`) as keyword arguments because they close
over local state in `create_app` (persona_default, layer callables,
etc.). `create_app` wires them in at route-registration time.
