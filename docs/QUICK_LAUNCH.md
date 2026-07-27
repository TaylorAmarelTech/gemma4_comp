# Quick launch — one command per audience

DueCare runs as a web server you can start several ways. Pick the row that
matches who you are. Every path is a plain command; `launch.py` just picks the
right one for you and checks prerequisites first.

```bash
python launch.py            # list the profiles
python launch.py <profile>  # start it   (add --dry-run to preview)
```

| You are… | Profile | What you get | Prerequisites |
|---|---|---|---|
| **NGO / regulator / non-technical operator** | `ngo` | One-command Dockerized stack (Ollama + DueCare + reverse proxy), built from source, at `http://localhost`. | Docker Desktop. |
| **Developer / reviewer** | `workbench` | The full FastAPI chat + harness workbench at `http://localhost:8080`. | `uv sync --all-packages`, then `ollama pull gemma4:e2b`. |
| **Quick look / screen recording** | `demo` | The standalone FastAPI demo app at `http://localhost:8080`. | Packages installed. |
| **Researcher / analyst** | `benchmark` | Regenerates the harness-lift read from the graded panel — offline, no model, no server. | — |
| **Colab / Kaggle user** | `notebook` | DueCare running in a notebook with a public URL. | A notebook host (see below). |

## NGO / operator — Docker, no Python setup

The single-box path. It needs only Docker; the first run downloads the Gemma 4
model automatically.

```bash
cd examples/deployment/local-all-in-one
# Build DueCare from this checkout (no need for a published image):
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build
# then open http://localhost
```

For an office edge box that caseworkers reach at `http://duecare.local` from
their phones, use `examples/deployment/ngo-office-edge/` instead (adds mDNS).

## Developer — local FastAPI workbench

```bash
uv sync --all-packages        # install all 18 workspace packages
ollama pull gemma4:e2b        # ~1.5 GB; or gemma4:e4b for higher quality
python -m duecare.chat.run_server --host 0.0.0.0 --port 8080
# open http://localhost:8080  (load a model from the UI, then chat / compare arms)
```

## Notebook — a web server inside Colab or Kaggle

`examples/deployment/notebook/launch_duecare_server.ipynb` pip-installs DueCare
from source, starts the FastAPI server, and prints a public tunnel URL you can
open in a browser. It runs unchanged on Colab, Kaggle (Internet on), or a local
Jupyter. See `examples/deployment/notebook/README.md`.

## Just the data — no install

The graded benchmark and the RuleCard supervision fabric are public on Kaggle,
with runnable example notebooks attached:

- `taylorsamarel/duecare-harness-benchmark-grades`
- `taylorsamarel/duecare-rulecard-supervision-fabric`

## Deeper deployment topologies

`docs/deployment_local.md`, `docs/deployment_enterprise.md`, and
`docs/deployment_topologies.md` cover the enterprise waterfall-detection path,
the auth-enabled stack (`docker-compose.auth.yml`), and multi-box topologies.
