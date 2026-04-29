# Duecare — Enterprise deployment (Dockerized API)

This is the **Enterprise Integration** mode from `deployment_modes.md`.
The classifier exposes a structured-output HTTP endpoint that takes
content (text + optional image) and returns a JSON envelope with
classification, risk vectors, and recommended action. Same model,
same harness as the Kaggle classifier notebook — just packaged as a
deployable service.

## What you get

```
POST /api/classifier/evaluate
Content-Type: application/json

{
  "content": "I run an employment agency in Hong Kong...",
  "image": "store://abc123",        // optional (upload first)
  "generation": {"max_new_tokens": 2048, "temperature": 0.3},
  "toggles": {
    "persona": true,
    "grep":    true,
    "rag":     true,
    "tools":   true
  }
}

200 OK
text/event-stream

: stream-open
: keepalive elapsed=4s
data: {
  "parsed": {
    "classification": "predatory_recruitment_debt_bondage",
    "classification_label": "Predatory recruitment with debt bondage",
    "confidence": 0.92,
    "overall_risk": 0.91,
    "risk_vectors": [
      {"dimension": "ilo_forced_labor_indicators",
       "magnitude": 0.95, "direction": "high",
       "evidence": "ILO C029 indicators 4 (debt bondage) + 7 (withheld wages)..."},
      {"dimension": "fee_violation",
       "magnitude": 0.88, "direction": "high",
       "evidence": "68% APR violates HK Money Lenders Ord. Cap. 163 §24..."}
    ],
    "recommended_action": "escalate_to_regulator",
    "rationale": "Multiple ILO indicators + statute violations...",
    "ngo_referrals": ["POEA", "BP2MI", "MfMW HK"]
  },
  "raw": "<full Gemma response>",
  "parse_ok": true,
  "elapsed_ms": 18432,
  "harness_trace": { ... },
  "model_info": { "name": "gemma-4-e4b-it", ... }
}
```

The same harness layers (Persona, GREP, RAG, Tools) run before Gemma
generates. The full pipeline trace is returned in `harness_trace` so
your monitoring layer has byte-level provenance for every decision.

---

## Deploying with Docker

### One-command run (CPU, E2B model — laptop scale)

```bash
docker run -p 8080:8080 \
    -e GEMMA_MODEL_VARIANT=e2b-it \
    -e HF_TOKEN=$HF_TOKEN \
    ghcr.io/tayloramareltech/duecare-classifier:latest
```

Visit `http://localhost:8080` for the same classifier UI judges see on
Kaggle. POST to `http://localhost:8080/api/classifier/evaluate` for the
API. CPU inference is slow (~30-90s per classification on E2B); use
GPU for production.

### GPU (recommended for production)

```bash
docker run --gpus all -p 8080:8080 \
    -e GEMMA_MODEL_VARIANT=e4b-it \
    -e GEMMA_LOAD_IN_4BIT=true \
    -e HF_TOKEN=$HF_TOKEN \
    -v ./model-cache:/root/.cache/huggingface \
    ghcr.io/tayloramareltech/duecare-classifier:latest
```

`--gpus all` requires the NVIDIA Container Toolkit. The model cache
volume persists Gemma 4 weights between container restarts so cold
starts go from minutes to seconds.

### docker-compose.yml (production-ish)

```yaml
services:
  duecare-classifier:
    image: ghcr.io/tayloramareltech/duecare-classifier:latest
    ports:
      - "8080:8080"
    environment:
      GEMMA_MODEL_VARIANT: e4b-it
      GEMMA_LOAD_IN_4BIT: "true"
      HF_TOKEN: ${HF_TOKEN}
      DUECARE_LOG_LEVEL: warning
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - ./model-cache:/root/.cache/huggingface
      - ./customizations:/app/data/customizations
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/healthz"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### Behind nginx / Cloudflare for HTTPS

The classifier app already sets `X-Accel-Buffering: no` and
`Cache-Control: no-cache, no-transform` so SSE streaming works
through nginx:

```nginx
location /api/classifier/ {
  proxy_pass http://duecare-classifier:8080;
  proxy_http_version 1.1;
  proxy_buffering off;       # critical for SSE
  proxy_read_timeout 600s;   # long inferences
  proxy_set_header Connection "";
}
location / {
  proxy_pass http://duecare-classifier:8080;
}
```

---

## Authentication / authorization

The bundled image ships with **no auth** — judges and a dev environment
need to be able to hit `/` directly. For production:

1. **Reverse-proxy auth.** Put the container behind nginx + auth_request
   to your existing OIDC / SAML / mTLS provider. Issue per-team API
   keys.
2. **API key middleware.** Add a single `Authorization: Bearer <key>`
   check in front of `/api/classifier/*` only — leave `/` open for
   the dashboard or lock it down too.
3. **Per-team customizations.** The harness layer supports per-request
   `custom_grep_rules`, `custom_rag_docs`, `custom_corridor_caps`,
   `custom_fee_camouflage`, `custom_ngo_intake`. Mount your team's
   rules JSON, inject in the API gateway.

---

## Customization

### Add organization-specific GREP rules

Each request can include `toggles.custom_grep_rules`:

```json
"toggles": {
  "grep": true,
  "custom_grep_rules": [
    {
      "rule": "internal_compliance_red_flag",
      "patterns": ["\\bcustom_pattern_1\\b", "\\bcustom_pattern_2\\b"],
      "all_required": true,
      "severity": "critical",
      "citation": "<Your-Org> Compliance Manual §3.2",
      "indicator": "Internal red flag for ..."
    }
  ]
}
```

The server merges your rules with the bundled 22 built-ins and runs
all of them. Same shape for `custom_rag_docs`, `custom_corridor_caps`,
`custom_fee_camouflage`, `custom_ngo_intake`. Full schema in
`packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py`.

### Override the persona

```json
"toggles": {
  "persona": true,
  "persona_text": "You are a compliance auditor for <Your-Org>..."
}
```

When `persona_text` is `null`, the bundled `CLASSIFIER_PERSONA` is
used (strict-JSON output instruction).

---

## Monitoring

The response payload includes:

- `harness_trace` — per-layer trace (which rules fired, which docs
  retrieved, which tools called, how long each took)
- `harness_trace._final_user_text` — the exact merged prompt Gemma
  saw (audit trail / "real, not faked" reproducibility)
- `elapsed_ms` — end-to-end Gemma generation time
- `model_info` — `{name, size_b, quantization, device}` so your logs
  record which weights produced the verdict

Recommended log shape:

```json
{
  "ts": 1761234567,
  "request_id": "uuid",
  "user": "team-x/auditor-42",
  "content_hash": "sha256:abc...",
  "image_present": true,
  "classification": "predatory_recruitment_debt_bondage",
  "overall_risk": 0.91,
  "recommended_action": "escalate_to_regulator",
  "rules_fired": ["usury_pattern_high_apr", "debt_bondage_loan_salary_deduction", ...],
  "docs_retrieved": ["ILO_C029_Art_1", "POEA_MC_14_2017"],
  "tools_called": ["lookup_corridor_fee_cap", "lookup_ngo_intake"],
  "elapsed_ms": 18432,
  "git_sha": "70814c7",
  "model_revision": "unsloth/gemma-4-E4B-it@main"
}
```

Sufficient for SIEM ingestion + downstream compliance audit.

---

## Provenance / audit trail

Per the rubric's "real, not faked" invariant, every response carries:

- The exact merged prompt (`harness_trace._final_user_text`)
- The list of fired rules / retrieved docs / called tools
- The model revision (`model_info`)
- The git SHA of the deployed harness (set as a Docker label)

Reproduce any decision after the fact by re-sending the same content
+ toggles to a container running the same git SHA.

---

## What this image bundles

- Gemma 4 weights (downloaded at first run, cached per the volume)
- 22 GREP rules with ILO + national-statute citations
- 18 RAG documents (BM25 over ILO C029/C181/C095/C189 + POEA MCs +
  BP2MI Reg + HK statutes + NGO briefs)
- 4 lookup tools backed by 7 corridor entries, 16 fee labels, 11 ILO
  indicators, 4 corridor hotline groups
- The `CLASSIFIER_PERSONA` (strict JSON output instruction)
- The classifier UI (form + result card + history queue with
  threshold filter + Pipeline modal)
- Same `duecare-llm-chat` wheel as the Kaggle notebooks — single
  source of truth

---

## Building the image yourself

The `Dockerfile.classifier` ships in the repo root once published.
Skeleton:

```dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y python3.11 python3-pip curl \
    && rm -rf /var/lib/apt/lists/*

# Duecare wheels
COPY packages/ /app/packages/
RUN pip install /app/packages/duecare-llm-core/dist/*.whl \
                 /app/packages/duecare-llm-models/dist/*.whl \
                 /app/packages/duecare-llm-chat/dist/*.whl

# Inference deps (Hanchen's pinned Unsloth stack)
RUN pip install \
    "torch>=2.8.0" "triton>=3.4.0" \
    "torchvision" "bitsandbytes" \
    "unsloth" "unsloth_zoo>=2026.4.6" \
    "transformers==5.5.0" "torchcodec" "timm"

# Server entry
COPY scripts/serve_classifier.py /app/serve_classifier.py
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8080/healthz || exit 1
CMD ["python3", "/app/serve_classifier.py"]
```

`serve_classifier.py` would mirror `kaggle/gemma-content-classification-evaluation/kernel.py`
without the cloudflared tunnel — just `uvicorn.run(app, host="0.0.0.0", port=8080)`.

The full Dockerfile + serve script will land in the v0.1.0 release.
