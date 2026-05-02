# HF Spaces — Deployment runbook

For when GPU is back. Step-by-step to get
`huggingface.co/spaces/taylorscottamarel/duecare-live-demo` LIVE.

## Pre-flight (5 min)

```bash
# 1. Make sure the chat wheel is current (394 prompts + rubrics)
ls -la kaggle/live-demo/wheels/duecare_llm_chat-0.1.0-py3-none-any.whl
#       expected: 549,257 bytes (chat wheel with rubrics)

# 2. Make sure HF_TOKEN env var is set
echo $HF_TOKEN | head -c 6  # should print 'hf_xxxx'
```

## Step 1: Create the Space (one-time)

Via web UI (https://huggingface.co/new-space):
- Owner: `taylorscottamarel`
- Space name: `duecare-live-demo`
- License: MIT
- SDK: Docker
- Hardware: T4 small (free tier — bump to a10g-large for 31B later)
- Visibility: Public

Or via CLI:

```bash
huggingface-cli login
# (paste your write-scope HF token)

curl -X POST "https://huggingface.co/api/repos/create" \
  -H "Authorization: Bearer $HF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":      "duecare-live-demo",
    "type":      "space",
    "private":   false,
    "sdk":       "docker"
  }'
```

## Step 2: Stage the deploy

```bash
# From repo root
cd hf-space

# Copy in the kernel + wheels
cp ../kaggle/live-demo/kernel.py .
mkdir -p wheels
cp ../kaggle/live-demo/wheels/*.whl wheels/

# (Total wheels size will be ~7 MB; HF Spaces handles up to ~50 GB)
```

## Step 3: Push

```bash
# Initialize as separate git repo for the HF remote
git init
git add .
git commit -m "Initial deploy: Duecare Live Demo (Gemma 4 E4B)"
git branch -M main
git remote add origin \
  https://huggingface.co/spaces/taylorscottamarel/duecare-live-demo
git push -u origin main
```

## Step 4: Set the HF_TOKEN secret

In the Space settings (`https://huggingface.co/spaces/taylorscottamarel/duecare-live-demo/settings`):

- Click **New secret**
- Name: `HF_TOKEN`
- Value: your write-scope HF token

Without this, Gemma 4 download fails (model is gated).

## Step 5: Wait for build

The Space will:
1. Pull the nvidia/cuda Docker image
2. Install Hanchen's Unsloth stack (~5 min)
3. Install Duecare wheels (~30 sec)
4. Pre-cache Gemma 4 E4B weights (~2 min)
5. Start the FastAPI server

Total cold start: ~10 minutes for the FIRST build. Subsequent
deploys (only `kernel.py` or wheels changed) take ~2 minutes.

## Step 6: Verify

Visit `https://huggingface.co/spaces/taylorscottamarel/duecare-live-demo`.

Expected:
- The full Duecare home page (4 tile cards: Use cases / pages)
- Click `▸ Examples` → modal with 394 prompts
- Submit any prompt → response in 5-15 sec
- Click `▸ View pipeline` on any response → 7-card modal showing
  byte-for-byte transformation

## Step 7: Pin the URL in submission docs

Update these files with the live URL:

```bash
sed -i.bak 's|HF_SPACES_URL_TBD|https://huggingface.co/spaces/taylorscottamarel/duecare-live-demo|g' \
  docs/writeup_draft.md docs/FOR_JUDGES.md docs/notebook_index.md README.md
```

## Troubleshooting

**Build fails on Chromium install** — ok to skip; agentic-research is
appendix A4 only, not required for live-demo. The `|| true` in the
Dockerfile already swallows this.

**Build fails on Gemma 4 download** — verify `HF_TOKEN` secret is set
in Space settings. If still failing, accept the gating terms at
https://huggingface.co/google/gemma-4-e4b-it then re-deploy.

**OOM on T4** — switch to E2B variant by editing `kernel.py` line ~50:
`GEMMA_MODEL_VARIANT = "e2b-it"`. E2B fits comfortably on a T4 small.

**Free tier daily quota exhausted** — bump the Space hardware to
t4-medium ($0.60/hr) or a10g-large ($3.15/hr) in Settings → Hardware.

## Estimated cost

| Tier | Hardware | $/hr | Hackathon period (7 days × 8 hrs) |
|---|---|---|---|
| Free | t4-small | $0 (within quota) | $0 |
| Mid | t4-medium | $0.60 | ~$34 |
| Premium | a10g-large | $3.15 | ~$176 |

Recommendation: **t4-small + E4B** for the hackathon window. Bump only
if judges report timeouts.

## After hackathon

The Space stays live indefinitely. Pause via Settings → Pause Space
to stop billing if you want to take it offline.
