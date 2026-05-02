# Deployment topology examples

Concrete runnable examples for each of the five deployment topologies
documented in [`docs/deployment_topologies.md`](../../docs/deployment_topologies.md).

## Quick selector

| You are... | Try... |
|---|---|
| A solo developer evaluating Duecare on a laptop | [`local-all-in-one/`](./local-all-in-one/) (Docker Compose) or [`local-cli/`](./local-cli/) (Python) |
| An NGO with one office, 1-20 caseworkers | [`ngo-office-edge/`](./ngo-office-edge/) (Mac mini / NUC) |
| A platform deploying Duecare as a hosted service | [`server-and-clients/`](./server-and-clients/) (Render / Cloud Run / EKS + 8 client examples) |
| A privacy-first NGO shipping an Android app | [Topology D — on-device only](https://github.com/TaylorAmarelTech/duecare-journey-android) (no cloud at all) |
| A privacy-first NGO that also wants fresh knowledge | [`hybrid-edge-llm-cloud-rag/`](./hybrid-edge-llm-cloud-rag/) (on-device LLM + cloud knowledge) |

For the full decision tree + comparison matrix + hardware sizing, see
[`docs/deployment_topologies.md`](../../docs/deployment_topologies.md).

## What's bundled in each example

| Topology | Gemma 4 | GREP / RAG / Tools | Internet search | Suitable for |
|---|---|---|---|---|
| [`local-all-in-one/`](./local-all-in-one/) | Local Ollama | Local | Local (DuckDuckGo + optional API) | Solo, dev |
| [`local-cli/`](./local-cli/) | Local Ollama | Local Python | Local | Solo, terminal-friendly |
| [`ngo-office-edge/`](./ngo-office-edge/) | Edge box Ollama | Same box | Same box | Office LAN, 1-20 users |
| [`server-and-clients/`](./server-and-clients/) | Cloud server | Cloud server | Cloud (Tavily/Brave/Serper) | Hosted SaaS, multi-NGO |
| [`hybrid-edge-llm-cloud-rag/`](./hybrid-edge-llm-cloud-rag/) | On-device | Mixed (GREP local, RAG cloud) | Cloud | Privacy + freshness |

## Cost / privacy / internet matrix

| Topology | Cost | Privacy | Needs internet at runtime? |
|---|---|---|---|
| local-all-in-one | $0 | ★★★★★ | No (after model pull) |
| local-cli | $0 | ★★★★★ | No |
| ngo-office-edge | $400-800 hardware, $0/mo | ★★★★★ | No |
| server-and-clients | $0-25/mo small, $75+/mo enterprise | ★★★ | Yes |
| hybrid-edge-llm-cloud-rag | $5/mo VPS or $0 cloud-run | ★★★★ | Knowledge lookups only |

## Composability

You can combine topologies:

- **A + C**: developers run Topology A locally; users hit Topology C in
  production. Same image either way.
- **B + C**: NGO HQ runs Topology B for the office; field workers on
  the road use Topology C against the same backend.
- **C + D + E**: hosted Topology C server; some workers use pure
  Topology D for max privacy; others use Topology E to get current
  knowledge from the same Topology C server.

## Related

- Cloud cookbook (13 platforms): [`docs/cloud_deployment.md`](../../docs/cloud_deployment.md)
- Embedding patterns (8 client examples): [`docs/embedding_guide.md`](../../docs/embedding_guide.md)
- Application-level deployment patterns: [`docs/deployment_modes.md`](../../docs/deployment_modes.md)
- Enterprise concerns (SSO, audit, RBAC): [`docs/deployment_enterprise.md`](../../docs/deployment_enterprise.md)
