# duecare-llm-server

FastAPI server exposing the Duecare engine + evidence DB through a
card-style homepage with four surfaces:

| Card | Surface | Path |
|---|---|---|
| Enterprise compliance | content moderation queue + classifier | `/enterprise` |
| Individual chatbot | worker / family education chatbot | `/individual` |
| Knowledge insights | NGO graph + NL Q&A over evidence DB | `/knowledge` |
| Settings | DB + engine + tunnel config | `/settings` |

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
