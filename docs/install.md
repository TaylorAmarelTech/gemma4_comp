# Install

Five paths, ranked from "I just want to try it" to "I'm running this
in production." Pick one.

## Path 1: One-line install (fastest, ~60 seconds)

Linux / macOS / WSL:

```bash
curl -fsSL https://raw.githubusercontent.com/TaylorAmarelTech/gemma4_comp/master/scripts/install.sh | bash
```

Windows PowerShell:

```powershell
iex (irm https://raw.githubusercontent.com/TaylorAmarelTech/gemma4_comp/master/scripts/install.ps1)
```

What it does:

1. Detects OS + arch + Python version (needs Python 3.11+ — installs from python.org if missing).
2. Creates a `.venv` in the current dir.
3. `pip install duecare-llm` (the meta package; pulls in the worker-side stack).
4. Runs `python scripts/verify.py` — confirms 37 GREP rules, 26 RAG docs, 4 tools, 394 example prompts, 207 5-tier rubrics, 6 required-rubric categories all import cleanly.
5. Prints next-step commands.

After install, run:

```bash
source .venv/bin/activate          # (or .venv\Scripts\Activate.ps1 on Windows)
python -m duecare.chat.run_server  # opens http://localhost:8080
```

## Path 2: Docker Compose (full stack, no Python on host)

Needs Docker Desktop (Windows / macOS) or Docker Engine + Compose plugin (Linux).

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp
docker compose up
```

What you get:

- chat playground at `http://localhost:8080`
- classifier API at `http://localhost:8081`
- Ollama model server at `http://localhost:11434` (pre-pulls `gemma2:2b` on first run, ~1.5 GB)

To customize ports / model size / log level: copy `.env.example` to `.env` and edit.

```bash
cp .env.example .env
# edit DUECARE_OLLAMA_MODEL=gemma2:9b for the larger model
docker compose up -d                # detached
docker compose logs -f              # tail logs
docker compose down -v              # stop + drop volumes (deletes Ollama cache)
```

## Path 3: Pure pip install (Python 3.11+)

```bash
pip install duecare-llm
duecare verify          # smoke check
duecare chat            # run the chat playground
```

If you only need a subset (e.g., research notebook context):

```bash
pip install duecare-llm-core duecare-llm-models duecare-llm-chat
```

For the Unsloth fine-tuning extras (heavy, ~4 GB transitive deps):

```bash
pip install 'duecare-llm-models[unsloth]'
```

For all heavy extras (transformers + unsloth + llama-cpp + HF Hub):

```bash
pip install 'duecare-llm[all]'
```

## Path 4: Source / contributor (`make install`)

```bash
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp
make install         # uses uv if installed, else pip-editable
make verify          # smoke check
make help            # see all targets
```

Run the test suite + lint:

```bash
make test            # 194 tests
make lint            # ruff + mypy
make adversarial     # adversarial validation + stress test
```

VS Code / Codespaces users: open the repo in a devcontainer for a
fully-configured environment in 90 seconds. `.devcontainer/devcontainer.json`
auto-installs all 17 packages, sets up Python 3.12 + uv + adb +
forwarded ports for chat/classifier/Ollama, and pins the right
extensions.

## Path 5: Kubernetes (production)

Helm chart at `infra/helm/duecare/`. Defaults give chat + classifier
+ Ollama with horizontal autoscaling, 2-min rolling deploys, and a
20 GB persistent model cache.

```bash
# From the repo root:
make helm-install

# Or via helm directly:
helm upgrade --install duecare ./infra/helm/duecare \
    --namespace duecare --create-namespace \
    --values ./infra/helm/duecare/values.yaml
```

Once published to the public Helm repository (auto-fires on a
`chart-v*` tag):

```bash
helm repo add duecare https://tayloramareltech.github.io/gemma4_comp
helm install duecare duecare/duecare \
    --namespace duecare --create-namespace
```

Per-environment overrides via a values file:

```yaml
# my-values.yaml
chat:
  autoscaling:
    minReplicas: 5
    maxReplicas: 20
ollama:
  modelTag: gemma2:9b
  persistence:
    size: 50Gi
ingress:
  enabled: true
  hosts:
    - host: duecare.your-org.example
      paths:
        - { path: /, pathType: Prefix, service: chat }
```

```bash
helm upgrade --install duecare ./infra/helm/duecare -f my-values.yaml \
    --namespace duecare --create-namespace
```

GPU acceleration for the Ollama pod: uncomment the `nodeSelector`
+ `tolerations` block in `values.yaml` to pin Ollama to a GPU node.

## Verify after any install path

```bash
python scripts/verify.py
```

Expected output:

```
  [  OK  ]  GREP rules           37 >=  37   regex rules across 5 categories
  [  OK  ]  RAG corpus           26 >=  26   documents (ILO conventions, statutes, NGO briefs)
  [  OK  ]  Tools                 4 >=   4   lookup functions (corridor / fee / indicator / NGO)
  [  OK  ]  Example prompts     394 >= 394   prompts in the bundled examples library
  [  OK  ]  5-tier rubrics      207 >= 207   prompts with hand-graded worst..best response examples
  [  OK  ]  Required rubrics      6 >=   6   categories of required-element rubrics
  [  OK  ]  Classifier examples  16 >=  16   pre-built classifier examples (6 with SVG document mockups)

OK: all 7 checks passed. Harness is ready.
```

For deeper end-to-end verification (regenerates harness lift report
+ corpus coverage + asserts thresholds — ~5 minutes):

```bash
make reproduce          # or: bash scripts/reproduce.sh
```

## Troubleshooting

**`No module named 'duecare.chat'`** — package not installed. Try `pip install --upgrade --force-reinstall duecare-llm-chat`.

**Counts below thresholds in verify.py** — installed an old wheel. Same fix as above.

**Docker compose: model pull stuck** — Ollama image pre-pulls `gemma2:2b` (~1.5 GB) on first run; it logs to `docker compose logs ollama-init`. Wait 5-10 min on a first run.

**Helm: pods CrashLoopBackOff** — most common cause is the `gemma2:2b` Ollama pull job hasn't finished. `kubectl logs job/duecare-ollama-pull` shows progress. If your cluster has no internet egress, pre-pull the model into a private registry and override `ollama.image.repository`.

**Windows: `chmod` not found** — running install.sh under Git Bash. Use `install.ps1` instead.

**Python 3.13 + 3.14 build errors** — pip's bundled rich vendor module has a known issue on these versions. Use Python 3.11 or 3.12 until upstream fixes ship.
