# DueCare in a notebook — a web server with a public URL

`launch_duecare_server.ipynb` runs the DueCare workbench inside a notebook and
exposes it at a public URL, so a non-technical user with only a browser can try
it. It runs unchanged on **Google Colab**, **Kaggle** (turn Internet on), or a
local **Jupyter**.

## What it does, cell by cell

1. **Install** DueCare from source (`pip install` the workspace packages from the
   GitHub checkout). No local environment setup.
2. **Start Ollama** if it is available, and pull `gemma4:e2b` (skipped
   gracefully if Ollama is not present — the server still starts; you load a
   model from the UI).
3. **Launch** the FastAPI server (`duecare.chat.run_server`) in the background.
4. **Tunnel** the port to a public `https://…` URL (via `cloudflared`, falling
   back to `localtunnel`) and print it.
5. Open the printed URL in a new tab — that is the DueCare workbench.

## Notes

- On Kaggle, set the notebook to **Internet: on** so `pip` and the tunnel work.
- The tunnel URL is public while the notebook runs; stop the notebook to take it
  down. Do not paste real worker data into a tunneled demo — use the local or
  Dockerized deployment (`docs/QUICK_LAUNCH.md`) for anything sensitive.
- GPU is optional. On CPU the small `gemma4:e2b` model is the practical choice.
