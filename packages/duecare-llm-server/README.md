# duecare-llm-server

FastAPI server package for the focused DueCare live-demo surface. The
active Kaggle recording path is owned by `kaggle/02-live-demo`, which
boots this package, opens a Cloudflare URL, and serves the product demo
around the same Gemma 4 ecosystem contracts used by the workbench.

| Surface | Path | Purpose |
|---|---|---|
| Demo start | `/start` | choose the short demo path or setup lanes |
| Live slides | `/slides` | recording-friendly narrative and interaction flow |
| Setup lanes | `/slides/setup` | six public setup lanes and deployment notes |
| Slide APIs | `/api/slides/*` | scripted state, examples, and demo telemetry |

The companion workbench package (`duecare-llm-chat`) owns the broader
local-node flows: Bulk File Review, Knowledge Extraction, Search,
Templates, Anonymization & Sharing, portability contracts, and sample
artifacts.

## Launch (local)

```bash
duecare serve --port 8080
# open http://localhost:8080
```

## Launch with public URL (for Kaggle demo)

```bash
duecare serve --port 8080 --tunnel cloudflared
# prints https://<random>.trycloudflare.com
```

Cloudflared quick-tunnels need no account or token. Add `--tunnel ngrok`
if you have an ngrok account (`NGROK_AUTHTOKEN` env var).
