# duecare-llm-cli

Single CLI entrypoint for the Duecare ecosystem.

```bash
# Pipeline
duecare process /path/to/case-files --out ./out --max-images 25
duecare ingest ./out                                          # JSONs -> DB

# Query
duecare query "What is the average illicit fee?"
duecare query "How many complaints does Pacific Coast Manpower have?"

# Demo surfaces
duecare serve --port 8080 --tunnel cloudflared                # public URL for video
duecare moderate "Send your passport copy to recruitment@..."  # Enterprise UC
duecare worker  "Mama-san said I must pay USD 5000 deposit"   # Individual UC

# Research tool
duecare research court-judgments --org "Pacific Coast Manpower" --jurisdiction PH

# DB ops
duecare db init
duecare db dump --out duecare-snapshot.duckdb
```
