# Duecare — Local setup

Three local-deployment paths, fastest to most-controlled:

1. **Ollama** — easiest, CPU works, no Python env required
2. **Kaggle notebook (run locally on your GPU)** — same kernel.py
   that runs on Kaggle's free T4×2 also runs on your local box
3. **`pip install duecare-llm` + run the FastAPI app yourself** —
   most controlled, integrates into your existing Python stack

---

## Path 1 — Ollama (5 minutes, no Python needed)

Best for "I just want to chat with Gemma 4 on my laptop and try the
harness." Skips the FastAPI server / harness entirely; you talk to
Gemma 4 directly via Ollama's REST API.

```bash
# 1. Install Ollama (Mac / Linux / Windows)
#    https://ollama.com/download

# 2. Pull Gemma 4 (~4 GB for Q4 quantized E4B)
ollama pull gemma4:e4b

# 3. Chat
ollama run gemma4:e4b
```

For the **harness** behavior (Persona / GREP / RAG / Tools), you need
one of the other two paths — Ollama doesn't run our FastAPI app.

---

## Path 2 — Kaggle kernel.py on your local GPU (recommended for full demo)

Best for "I want the same chat playground / classifier that judges see,
with all four toggle layers, the Pipeline modal, the history queue —
running on my own GPU."

### Prerequisites

- An NVIDIA GPU with ≥16 GB VRAM (single 4090, A100, H100, etc. for
  E4B at 4-bit; 31B needs ≥48 GB total = single A100 80GB or 2× T4)
- Python 3.11+
- ~30 GB free disk for the model cache
- A Hugging Face account + token (Gemma 4 is gated)

### Setup

```bash
# 1. Clone
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp

# 2. Build the wheels (uv recommended)
uv build packages/duecare-llm-core
uv build packages/duecare-llm-models
uv build packages/duecare-llm-chat

# 3. Install Hanchen's pinned Unsloth stack
uv pip install --system \
    "torch>=2.8.0" "triton>=3.4.0" \
    "torchvision" "bitsandbytes" \
    "unsloth" "unsloth_zoo>=2026.4.6" \
    "transformers==5.5.0" "torchcodec" "timm"

# 4. Install the Duecare wheels you just built
uv pip install --system \
    packages/duecare-llm-core/dist/*.whl \
    packages/duecare-llm-models/dist/*.whl \
    packages/duecare-llm-chat/dist/*.whl

# 5. Set HF token
export HF_TOKEN=hf_yourtokenhere

# 6. Run the chat playground locally (the same kernel.py from the
#    chat-playground-with-grep-rag-tools Kaggle notebook)
python kaggle/chat-playground-with-grep-rag-tools/kernel.py
```

The kernel will:

1. Detect that you're not in a Kaggle environment and skip the wheel
   install + cloudflared tunnel
2. Load Gemma 4 31B-it via Unsloth FastModel (or whichever variant
   you set in `GEMMA_MODEL_VARIANT`)
3. Launch the FastAPI app on `http://localhost:8080`
4. Print the URL

Open `http://localhost:8080` in your browser. You get the same UI
judges see on Kaggle: 4 toggle tiles, Examples modal with 204 prompts,
View pipeline modal, Persona library, custom rule additions.

### To run the **classifier** instead

```bash
python kaggle/gemma-content-classification-evaluation/kernel.py
```

Same setup; serves the form-based classifier UI on port 8080.

### Choose a smaller model

Edit `GEMMA_MODEL_VARIANT` in the kernel.py:

| Variant | VRAM (4-bit) | Time per response |
|---|---|---|
| `e2b-it` | ~2 GB | very fast (CPU possible) |
| `e4b-it` | ~5.5 GB | fast on a single 4090 |
| `26b-a4b-it` | ~14 GB | needs 2× T4 / 1× A100 |
| `31b-it` | ~18 GB | needs 2× T4 / 1× A100 |

For development, `e4b-it` is the sweet spot.

---

## Path 3 — `pip install duecare-llm` + run the app yourself

For integration into your existing Python service, skip the kernel.py
and import the app directly.

### Install

```bash
pip install duecare-llm  # the meta package pulls all 16 siblings
# OR install only what you need:
pip install duecare-llm-core duecare-llm-models duecare-llm-chat
```

### Minimal chat-playground server (Python)

```python
# serve_chat.py
from unsloth import FastModel
from duecare.chat import create_app
from duecare.chat.harness import default_harness
import uvicorn

# Load Gemma 4 (your variant + your device)
model, tokenizer = FastModel.from_pretrained(
    model_name="unsloth/gemma-4-E4B-it",
    max_seq_length=8192,
    load_in_4bit=True,
)

def gemma_call(messages, max_new_tokens=2048, temperature=1.0,
               top_p=0.95, top_k=64):
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt").to("cuda")
    out = model.generate(
        **inputs, max_new_tokens=max_new_tokens, use_cache=True,
        temperature=temperature, top_p=top_p, top_k=top_k)
    return tokenizer.batch_decode(out)[0]

app = create_app(
    gemma_call=gemma_call,
    model_info={"loaded": True, "name": "gemma-4-e4b-it",
                  "display": "Gemma 4 E4B (local)"},
    **default_harness(),  # all 4 layers wired
)

uvicorn.run(app, host="0.0.0.0", port=8080)
```

Run it:

```bash
python serve_chat.py
```

Open `http://localhost:8080`.

### Minimal classifier server (Python)

Same shape, just import the classifier instead:

```python
from duecare.chat import create_classifier_app
from duecare.chat.harness import default_harness, CLASSIFIER_EXAMPLES

_h = default_harness()
_h["example_prompts"] = list(CLASSIFIER_EXAMPLES)

app = create_classifier_app(
    gemma_call=gemma_call,
    model_info={...},
    **_h,
)
```

Same FastAPI conventions, same routes, same UI.

### Programmatic API (no UI)

You don't need to run the FastAPI server at all if you just want the
harness logic from your own service:

```python
from duecare.chat.harness import (
    _grep_call, _rag_call, _tools_call,
    GREP_RULES, RAG_CORPUS, EXAMPLE_PROMPTS,
)

# Run the GREP layer directly
hits = _grep_call("I run an agency in HK at 68% APR...")
print(hits["hits"])  # list of {rule, severity, citation, indicator, match_excerpt}

# Run the RAG layer directly
docs = _rag_call("trafficking debt bondage", top_k=5)
print(docs["docs"])  # list of {id, title, source, snippet, score}

# Run the Tools layer directly
result = _tools_call([{"role": "user", "content": [{"type": "text", "text": "Philippines to Hong Kong domestic worker fees"}]}])
print(result["tool_calls"])  # list of {name, args, result}
```

Each function accepts an `extra_*` kwarg to merge custom rules /
docs / data tables per call. Full extension docs in the `▸ View`
modal of any layer in the chat UI, or in
`packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`
(the `LAYER_DOCS` constant).

---

## Verify your install

```bash
python -c "
from duecare.chat.harness import GREP_RULES, RAG_CORPUS, _TOOL_DISPATCH, EXAMPLE_PROMPTS, CLASSIFIER_EXAMPLES
print(f'GREP rules: {len(GREP_RULES)}')
print(f'RAG docs:   {len(RAG_CORPUS)}')
print(f'Tools:      {len(_TOOL_DISPATCH)}')
print(f'Example prompts:    {len(EXAMPLE_PROMPTS)}')
print(f'Classifier examples: {len(CLASSIFIER_EXAMPLES)}')
"
```

Expected:

```
GREP rules: 22
RAG docs:   18
Tools:      4
Example prompts:    204
Classifier examples: 16
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'unsloth'`**
Install the Hanchen pin: see Path 2 step 3 above.

**`OutOfMemoryError` on 31B**
Drop max_new_tokens in the UI from 8192 to 2048. Or switch to E4B.

**Cloudflare 524 timeout**
Only relevant for Kaggle's cloudflared tunnel — not local. The local
FastAPI server has no proxy timeout; the SSE keepalive runs anyway.

**Gemma 4 download is gated**
Accept the gating terms at `https://huggingface.co/google/gemma-4-e4b-it`
then `huggingface-cli login` with your HF token.

**Multiple GPUs but only one is being used**
For 31B / 26B-A4B, set `GEMMA_DEVICE_MAP="balanced"` in the kernel.py
(or pass `device_map="balanced"` to `FastModel.from_pretrained`).
