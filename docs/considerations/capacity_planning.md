# Capacity planning + load testing

> Sizing tables for each topology, the k6 load test that validates
> them, and a procurement-ready cost estimator. Read alongside
> [`docs/deployment_topologies.md`](../deployment_topologies.md) (which
> shape to pick) and [`docs/considerations/SLO.md`](./SLO.md) (what the numbers
> commit to).

## TL;DR sizing

| Workers / day | Recommended topology | Recommended hardware | Monthly $ (cloud, no GPU) |
|---:|---|---|---:|
| 1 | A (single-component local) | A laptop | $0 |
| 2-20 | B (NGO-office edge box) | Mac mini M2 16 GB or Intel NUC | $0 (one-time hardware) |
| 20-200 | C (server, CPU only) | 2× small cloud VM, Render / Cloud Run | $25-100 |
| 200-2,000 | C (server, autoscaled) | k8s + 4-10 replicas, optional T4 GPU | $200-800 |
| 2,000-20,000 | C (server, GPU pool) | k8s + GPU node pool (T4/L4/A10) | $1,500-5,000 |
| 20,000+ | C (server, multi-region) | Multi-region k8s + dedicated inference pool | $10,000+ |

Worker = one human-day of typical use ≈ 10-20 chat turns. Numbers
assume `gemma4:e2b` (default model) and the published harness lift
profile (207-prompt rubric, +56.5 pp mean). Bigger models scale costs
roughly linearly with parameter count.

## Per-RPS sizing (Topology C)

Reference machine: 2 vCPU + 4 GB RAM (e.g., GCP `e2-medium`,
AWS `t3.medium`, Render Standard). All numbers measured with the
`tests/load/k6_chat.js` profile against `gemma4:e2b` via Ollama on
the same host (CPU only). Replace numbers with your own k6 results
in production — these are illustrative.

| Sustained RPS | Replicas needed | Total vCPU | Total RAM | Notes |
|---:|---:|---:|---:|---|
| 0.1 (≈ 8/min) | 1 | 2 | 4 GB | Render free tier handles this |
| 1 | 2 | 4 | 8 GB | $25/mo on Render Standard ×2 |
| 5 | 4 | 8 | 16 GB | $50/mo Render or Cloud Run scale-to-zero |
| 10 | 8 | 16 | 32 GB | $200/mo small k8s; consider GPU |
| 50 | 4 GPU pods + 2 router pods | 8+GPU | 64 GB + 80 GB GPU | T4 / L4 GPU pool; ~$1,500/mo |
| 100 | 8 GPU pods + 4 router pods | 16+GPU | 128 GB + 160 GB GPU | A10 pool; multi-AZ recommended |

**Key insight.** CPU inference for `gemma4:e2b` on a 2 vCPU machine
gives ~0.5 RPS sustained. GPU inference (T4) gives ~5 RPS per pod.
A10 / L4 give ~15 RPS per pod. Above 50 RPS, GPU economics dominate.

For `gemma4:e4b`: divide RPS-per-pod by 2.5. For `gemma3:1b`:
multiply by 4.

## How to load-test

### Local quick check

```bash
# Bring up the stack
docker compose up -d

# Run k6 against it (10 VUs for 60s)
docker run --rm -i --network host grafana/k6 run - <tests/load/k6_chat.js

# Or with native k6
k6 run tests/load/k6_chat.js
```

Expected output: a summary block with RPS, p50/p95/p99 latency,
error rate, and PASS/FAIL against the SLO thresholds.

### Production-shape load test

```bash
# Override target + auth + VU count
k6 run \
  -e DUECARE_URL=https://chat.your-org.com \
  -e DUECARE_TOKEN=$YOUR_BEARER \
  -e VUS=50 \
  -e DURATION=10m \
  -e TENANT_COUNT=20 \
  tests/load/k6_chat.js

# Pipe results to k6 Cloud / Prometheus / InfluxDB:
k6 run --out experimental-prometheus-rw tests/load/k6_chat.js
```

### Extended profiles

Beyond the bundled k6 script, validate:

- **Cold-start budget** — kill all replicas, send 1 request, time it
  to first byte. Should be < 90s per `docs/considerations/SLO.md`.
- **Soak test** — 20 RPS for 2 hours, verify no memory leak (RSS
  stays flat or sawtoothed by GC, not monotonic).
- **Spike test** — 1 RPS for 5 minutes, then 100 RPS for 30 seconds,
  back to 1 RPS. Verify HPA scales up + back down within
  `behavior.scaleDown.stabilizationWindowSeconds`.
- **Failover test** — kill the primary Ollama pod mid-traffic,
  confirm SmartGemmaEngine fallback chain serves canned responses
  without 5xx (Topology D / Android pattern).

## Cost estimator

Use this back-of-envelope formula for monthly USD:

```
total_$/mo  =  baseline_$/mo
            +  vcpu_count   * vcpu_$/mo
            +  ram_gb       * ram_$/mo
            +  gpu_count    * gpu_$/mo
            +  bandwidth_gb * bandwidth_$/gb
            +  cloud_model_tokens / 1000 * model_$/1k
```

Reference unit prices (mid-2026 rough mid-rates):

| Resource | Price (USD) |
|---|---:|
| vCPU (GCP / AWS / Azure) | $20 / vCPU / mo |
| RAM | $3 / GB / mo |
| GPU (T4) | $0.30 / hr ≈ $220 / mo |
| GPU (L4) | $0.60 / hr ≈ $440 / mo |
| GPU (A10) | $0.90 / hr ≈ $660 / mo |
| Bandwidth (cloud egress) | $0.08 / GB |
| Cloud Gemma 2.5 Flash (input) | $0.000075 / 1k tok |
| Cloud Gemma 2.5 Flash (output) | $0.0003 / 1k tok |
| Cloud Claude Sonnet 4 (input) | $0.003 / 1k tok |
| Cloud Claude Sonnet 4 (output) | $0.015 / 1k tok |
| Cloud GPT-4o-mini (input) | $0.00015 / 1k tok |
| Cloud GPT-4o-mini (output) | $0.0006 / 1k tok |
| Local Ollama (any Gemma) | $0 / token (operator hardware) |

The full lookup table is in
[`packages/duecare-llm-server/src/duecare/server/metering.py`](../packages/duecare-llm-server/src/duecare/server/metering.py)
and is queryable via PromQL on the `duecare_model_tokens_*_total`
counters when the observability stack is up.

## Per-tenant chargeback

Once `infra/observability/` is up, the per-tenant cost rollup is one
PromQL query (recording rule) away. From `docs/considerations/multi_tenancy.md`:

```yaml
# Add to infra/observability/prometheus/rules.yml
- record: duecare:tenant_cost_usd_30d
  expr: |
    sum by (tenant) (
      increase(duecare_model_tokens_in_total[30d]) / 1000 * 0.0005
      + increase(duecare_model_tokens_out_total[30d]) / 1000 * 0.0015
    )
```

Replace `0.0005` / `0.0015` with the per-model rates from the
metering lookup. For multi-model deployments, keep one recording
rule per model and sum.

## Validation in CI

The k6 script is designed to be CI-friendly. Add to a GitHub Actions
job:

```yaml
- name: Load test (smoke)
  run: |
    docker compose up -d
    sleep 30
    docker run --rm --network host grafana/k6 run \
      -e VUS=2 -e DURATION=30s \
      <tests/load/k6_chat.js
```

The thresholds in `tests/load/k6_chat.js` (`p95<8000`, `errors<0.005`)
will fail the job if regressed. Adjust per-PR via the `--threshold`
flag for legitimate latency regressions you accept.

## When to revisit this document

- After any scaling-related production incident
- Whenever a new model variant lands (E4B, A4B fine-tunes, etc.)
- Whenever cloud pricing shifts > 20%
- Quarterly along with `docs/considerations/SLO.md`

Next review: **2026-08-01**.
