# IT director — operational ownership of a Duecare deployment

> **Persona.** You're the Director of IT (or "the IT person") at a
> 50-500 person organization: a regional NGO, a labor-ministry
> office, a mid-size legal aid clinic, a healthcare network, a
> credit union. A program lead asked you to "evaluate this Duecare
> thing and tell us what it'll take to run it."
>
> **What you actually need to know.** Total cost of ownership.
> What can break. Vendor lock-in. Backup + DR. Patching cadence.
> Helpdesk impact when it goes down. Whether you can support it
> with the team you have today.
>
> **What this doc gives you.** Honest answers to those questions
> in the order an IT director asks them. Skip ahead to whichever
> section bites first.

## TL;DR

| Question | Answer |
|---|---|
| One-line description? | Self-hosted privacy-first chat / classifier wrapping Gemma 4. Open source, MIT. |
| Vendor lock-in? | None. Source on GitHub, image on GHCR, all deps pinned, you can fork. |
| Cost? | $0 in license fees. ~$25-100/mo cloud OR $250-800 one-time hardware for on-prem. |
| Cost surprises? | Optional cloud LLM fallback (Tavily/Brave/Serper for web search) — capped by API key. |
| RTO / RPO? | Operator-defined. The shipped backup script does nightly snapshots; restore is one command. |
| Patching cadence? | `git pull && make demo` weekly. Image is multi-arch, signed, in GHCR. |
| Helpdesk impact? | Low — diagnostic CLI (`make doctor`) prints a one-screen health report when a user complains. |
| Required skills on staff? | One person comfortable with Docker Compose. Anyone can run `make demo`. |
| Compliance posture? | SOC 2 / GDPR / HIPAA / FedRAMP control map shipped at `docs/considerations/COMPLIANCE.md` for inheritance. |
| Telemetry to vendor? | Zero. The maintainers don't operate any service your data passes through. |

## What it actually is

Duecare is **three runnable services** wrapped in a Docker Compose:

1. **Ollama** — runs Gemma 4 locally. Same Ollama you'd run for any
   other local LLM use case.
2. **Duecare server** — a FastAPI Python app (open source) that puts
   a safety harness around Ollama: regex pattern detection + RAG
   over a legal corpus + corridor-specific lookups + structured
   classification. Speaks an OpenAPI 3 schema.
3. **Caddy reverse proxy** — TLS termination, healthcheck endpoint.

Plus optional sidecars:
- **oauth2-proxy** — when you want SSO (Google Workspace / Microsoft
  Entra / Okta / etc.) in front
- **Prometheus + Grafana + Loki + OpenTelemetry Collector** — when
  you want monitoring

That's the entire surface. There's no SaaS dependency, no phone-home
telemetry, no API key required from the maintainer.

## What you'll evaluate

### Compute footprint

The default model (`gemma4:e2b`) needs:

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 8 GB | 16 GB |
| Disk | 10 GB free | 50 GB |
| GPU | none | T4 / L4 if > 5 RPS |

For larger models or higher RPS, [`docs/considerations/capacity_planning.md`](../considerations/capacity_planning.md)
has the per-RPS sizing tables and a load-test script.

### Network footprint

- **Inbound**: 8080 (chat) and optionally 8081 (classifier),
  3000 (Grafana), 4180 (oauth2-proxy)
- **Outbound at startup**: pull `ollama/ollama:latest` + `caddy:2-alpine`
  + `ghcr.io/tayloramareltech/duecare-llm:latest`. After first pull,
  no outbound traffic except optional model updates.
- **Outbound at runtime**: zero by default. If you enable web search
  for caseworkers (Tavily / Brave / Serper), those go to the chosen
  provider's API.

### Security footprint

- Container runs as **non-root user** (uid 1000)
- All deps **pinned**, image **multi-arch** (amd64 + arm64), **cosign-signed**
- **NetworkPolicy default-deny** template in the Helm chart
- Per-tenant **rate limit** + **token budget** in the server middleware
- **No raw PII** in logs (the harness's audit log records hashes, not plaintext)
- Threat model + compliance crosswalk at [`docs/considerations/`](../considerations/)

### Vendor profile

| Aspect | Verdict |
|---|---|
| Maintainer | Single individual (Taylor Amarel) — see `SECURITY.md` |
| License | MIT (commercial use OK; no attribution required for non-derivative use) |
| Source code | Public on GitHub: `TaylorAmarelTech/gemma4_comp` |
| Image registry | Public on GHCR: `ghcr.io/tayloramareltech/duecare-llm` |
| Dep on Big Tech APIs at runtime | None by default. Optional: Cloud Gemma routing (Ollama-compatible / OpenAI / HF Inference) |
| Going-out-of-business risk | Low — you can fork the repo + run the image you already pulled |

For procurement: handed to your security team, the
[`docs/considerations/vendor_questionnaire.md`](../considerations/vendor_questionnaire.md)
file pre-fills CAIQ-Lite / SIG-Lite answers.

## What it'll cost you in staff time

| Activity | Frequency | Time | Skill required |
|---|---|---|---|
| First-time setup | once | 90 min | Docker basics |
| Update + restart | weekly | 5 min | none |
| Backup verification | weekly | 5 min | bash basics |
| Restore drill | quarterly | 30 min | Docker basics |
| User onboarding | per user | 15 min | nothing technical |
| Incident response | when something breaks | 30 min | depends on incident |
| Compliance review | annually | 4 hours | your existing process |

Total: ~30 min/week of an IT-comfortable colleague + a quarterly
half-day for the restore drill. For a 50-person org running it for
internal use, this is well within "the IT person can support it
alongside everything else."

## What it'll cost you in money

| Cost | Local-only (Topology B) | Cloud (Topology C, small) | Cloud (Topology C, large) |
|---|---|---|---|
| License | $0 | $0 | $0 |
| Hardware | $250-800 one-time (Mac mini / NUC) | — | — |
| Cloud compute | — | $25-100/mo | $200-1500/mo |
| GPU (if needed) | optional, +$200-600 one-time | — | $200-660/mo (T4/L4) |
| Bandwidth | $0 | included up to free tier | $50-200/mo |
| Optional 3rd-party search (Tavily/Brave/Serper) | $0-25/mo | $0-25/mo | $25-100/mo |
| Backup storage (USB drive vs S3) | $30 one-time | $5/mo S3 / GCS | $20/mo |
| **Total month 1** | **$300-900 one-time** | **$30-130/mo** | **$300-1900/mo** |
| **Total month 12+** | **$0-25/mo** | **$30-130/mo** | **$300-1900/mo** |

### Cost surprises to watch

- **Optional cloud-LLM fallback** — if you enable cloud Gemma
  routing (`docker-compose.auth.yml`-style), you pay the chosen
  provider's per-token rate. The bundled cost meter (PromQL recording
  rule template in `docs/considerations/multi_tenancy.md`) shows
  per-tenant spend so you can chargeback or alert on runaway use.
- **Optional internet search** — Tavily / Brave / Serper free tiers
  give 1k-2.5k queries/month. Cap with their dashboard or rate limits.
- **GPU instance left running** — typical $0.30-0.60/hr. If you don't
  need < 1s latency, default to CPU and save $200-600/mo.

## Day-1 setup

Identical to the [NGO director walkthrough](./ngo-office-deployment.md)
because the underlying topology is the same. Differences for an
IT director:

- You'll probably want **docker-compose.dev.yml** in your dev
  environment for hot reload during evaluation, then switch to
  the production compose for the pilot.
- You'll want **HTTPS from day 1** — Caddy in the bundled compose
  fetches a Let's Encrypt cert if you point it at a real hostname.
  Edit `Caddyfile` accordingly.
- You'll want **OAuth from day 1** for any real user testing
  (`docker-compose.auth.yml` overlay; configure your OIDC provider
  per `docs/considerations/multi_tenancy.md`).

## What can break (in order of likelihood)

| What | How often | Severity | Fix |
|---|---|---|---|
| Worker says chat is slow | Weekly during cold-starts | Low | First request after pod start takes ~30s; subsequent requests ~5s. Set HPA `minReplicas: 2` to keep one warm. |
| Disk fills up | Monthly without cleanup | Medium | Backups + log rotation cron. Audit log default 90-day retention. |
| Ollama OOM-killed | When you under-sized RAM | Medium | Use `gemma4:e2b` or `gemma3:1b` instead of `gemma4:e4b`; bump RAM. |
| Image pull fails | When GHCR has an outage | Low | Pin to a SHA digest in your Helm values; the image you already pulled keeps working. |
| Network policy blocks Ollama | After a Helm upgrade | Low | `kubectl describe networkpolicy` will show what's blocked; the chart's network policy is documented in `infra/helm/duecare/templates/networkpolicy.yaml`. |
| Worker can't login | After OIDC config drift | Medium | oauth2-proxy logs; check OIDC provider's app config. Same as any OIDC-protected app you run today. |
| Power outage corrupts journal | Rare | High | Restore from last night's backup: `bash scripts/restore.sh`. |
| Worker accuses chat of being wrong | Daily | Low | Always verify cited statute against the source; the harness reduces lookup time, not lawyer judgment. |

[`docs/considerations/runbook.md`](../considerations/runbook.md) has
the per-Prometheus-alert response.

## Vendor management

You're not contracting with anyone — Duecare is open-source. But
you're effectively a "vendor" to the program lead who asked you
to evaluate it. Things they'll ask:

| Q from program lead | A you can give them |
|---|---|
| "Who do we sue if it leaks data?" | Nobody, because nothing leaves the box you control. |
| "What's the SLA?" | Whatever uptime your IT team commits to. The community SLO target is in `docs/considerations/SLO.md`. |
| "Can we get a SOC 2 letter?" | Not for the project, but the deployment can support a SOC 2 / ISO 27001 audit run by your auditor. Control map at `docs/considerations/COMPLIANCE.md`. |
| "What if Taylor disappears?" | The image you pulled keeps working forever. The repo is forkable. Worst case, your team owns it. |
| "Is there a paid support tier?" | No. Community support via GitHub issues + `SECURITY.md` for vulns. |

## Migration path if you outgrow the deployment

| Today | Next step | When |
|---|---|---|
| Single Mac mini | Add a 2nd as hot standby | After 1 power outage |
| 2 Mac minis on LAN | Move to a small k8s cluster | When > 50 caseworkers or > 1000 RPM |
| Small k8s | Multi-region | When you have field offices in different cities |
| Single tenant | Multi-tenant per-caseworker | When chargeback / audit isolation matters |
| CPU-only Ollama | GPU pool | When p95 latency > 8s sustained |

Each step is documented in [`docs/deployment_topologies.md`](../deployment_topologies.md).
The image is the same across all of them; only the compose / Helm
shape changes.

## What this looks like 12 months in

If the deployment sticks:

- One Mac mini in the office, ~5-15 caseworkers using it daily
- Nightly backups to USB, never restored from in anger
- 30 min/month of your time tweaking config
- One vendor question / quarter for compliance audit prep
- Maybe a custom domain pack added for your jurisdiction

If it doesn't stick:

- `docker compose down -v` + the box is repurposed
- No subscription to cancel
- No data scattered across someone else's cloud to chase down

The downside risk is bounded.

## See also

- [`docs/scenarios/ngo-office-deployment.md`](./ngo-office-deployment.md) — the underlying setup walkthrough
- [`docs/scenarios/caseworker_workflow.md`](./caseworker_workflow.md) — what your users will do day-to-day
- [`docs/considerations/`](../considerations/) — full enterprise governance set
- [`docs/cloud_deployment.md`](../cloud_deployment.md) — when you outgrow on-prem
