# Compatibility matrix

## Python

| Version | Supported | Notes |
|---|---|---|
| 3.11 | ✓ Tested | Floor for the project |
| 3.12 | ✓ Tested | Recommended |
| 3.13 | ⚠ Mostly works | Some pip vendoring quirks; install via uv recommended |
| 3.14 | ⚠ Source-build only | Pip build toolchain has known issues; use editable install |
| 3.10 and below | ✗ | Pydantic v2 + match statements require 3.11 |

## Operating systems

| OS | Chat playground | Classifier | Docker | Helm |
|---|---|---|---|---|
| Linux (any modern distro, glibc 2.31+) | ✓ | ✓ | ✓ | ✓ |
| macOS (Intel) | ✓ | ✓ | ✓ | ✓ |
| macOS (Apple Silicon, M1+) | ✓ | ✓ | ✓ | ✓ |
| Windows 10 / 11 | ✓ | ✓ | ✓ (via Docker Desktop) | ✓ (via WSL2) |
| WSL2 | ✓ | ✓ | ✓ | ✓ |
| ChromeOS (Crostini) | ✓ | ✓ | partial | n/a |
| Android | n/a | n/a | n/a | n/a — see `duecare-journey-android` for the on-device app |
| iOS | n/a | n/a | n/a | n/a — Kotlin Multiplatform port roadmap'd post-hackathon |

## Hardware architectures

| Architecture | Native install | Docker | Notes |
|---|---|---|---|
| x86_64 / amd64 | ✓ | ✓ | Most common; CI builds amd64 first |
| arm64 / aarch64 | ✓ | ✓ | Apple Silicon, AWS Graviton, Raspberry Pi 4+, Ampere |
| armv7 (Raspberry Pi 3 and older) | ⚠ | ⚠ | Works for chat playground; Ollama models too big for 1 GB RAM |
| RISC-V | untested | ✗ | No prebuilt wheels for transitive deps yet |

## Gemma model variants

The chat playground + classifier work with any Ollama-served model
that supports the chat-template format. Recommended:

| Model | Size | RAM (host) | Throughput (CPU) | Throughput (GPU) | Use case |
|---|---|---|---|---|---|
| `gemma2:2b` | 1.5 GB | 4 GB+ | ~3 sec/token | ~30 tok/sec | Default; works on most laptops |
| `gemma2:9b` | 5.4 GB | 8 GB+ | ~10 sec/token | ~50 tok/sec | Better quality; needs 8GB+ RAM |
| `gemma2:27b` | 16 GB | 32 GB+ | impractical | ~80 tok/sec | Production server with GPU |
| `gemma4:e2b` | ~1.5 GB | 4 GB+ | TBD | TBD | When Ollama lands Gemma 4 stable |
| `gemma4:e4b` | ~4 GB | 8 GB+ | TBD | TBD | Recommended Gemma 4 variant for desktop |
| `gemma4:31b` | ~16 GB | 32 GB+ | impractical | ~70 tok/sec | Production-quality Gemma 4 |

For the Kaggle notebooks, the model is loaded directly via the
Hanchen-pinned Unsloth + transformers stack (not Ollama). See
`packages/duecare-llm-models/` for the model adapter implementations.

For the Android on-device app (`duecare-journey-android` sibling
repo), the LiteRT-converted variant is `gemma-4-e2b-it.task` (~1.5 GB
INT8). Conversion path: `google/gemma-4-e2b-it` → AI Edge Torch →
`.task` bundle. Conversion happens once per model release in the
`kaggle/bench-and-tune/` notebook; the result is published to HF Hub.

## Container runtimes

| Runtime | Supported | Notes |
|---|---|---|
| Docker (Compose plugin v2+) | ✓ | Default; `docker compose up` works |
| Docker (legacy `docker-compose` python tool) | ⚠ | Works but unmaintained; switch to plugin |
| Podman + podman-compose | ✓ | Drop-in replacement |
| containerd / nerdctl | ✓ | The image itself is OCI-compliant |
| Kubernetes | ✓ | See Helm chart at `infra/helm/duecare/` |
| K3s / k3d / kind | ✓ | Local Kubernetes for testing the Helm chart |
| OpenShift | untested | Helm chart should work; the `securityContext` is permissive enough |

## GPU / accelerator support

| Accelerator | Direct install | Docker | Kubernetes |
|---|---|---|---|
| NVIDIA (CUDA) | via `pip install duecare-llm-models[transformers]` + `torch` | docker-compose: uncomment GPU block; needs nvidia-container-toolkit | Helm: set `ollama.nodeSelector` to GPU node + tolerations for `nvidia.com/gpu` |
| AMD (ROCm) | works for transformers; not yet wired into Unsloth path | image works; ROCm container deps not bundled | works with rocm device plugin |
| Apple Silicon (MPS) | `torch` auto-detects MPS | n/a (Docker uses Linux runtime) | n/a |
| Intel (Arc / oneAPI) | untested | untested | untested |
| TPU | works for the transformers path on Kaggle | n/a | n/a |

## Browser compatibility (chat UI)

| Browser | Min version | Notes |
|---|---|---|
| Chrome / Chromium | 100+ | Reference target |
| Firefox | 100+ | Tested |
| Safari (macOS / iOS) | 15+ | Tested; mobile-responsive layout activates ≤ 480 px |
| Edge | 100+ | Same engine as Chrome |
| Opera | 90+ | Same engine as Chrome |
| Samsung Internet | 18+ | Tested for the Android web-companion fallback |

## Network egress requirements

| Path | Egress required |
|---|---|
| Local install (chat playground only) | None at runtime — all GREP / RAG / Tools are local code |
| Local install + Ollama | None at runtime — model is local once pulled |
| Docker Compose first run | Pulls Ollama base image + the Gemma model (~1.5-5 GB total) |
| Kubernetes first run | Same — Helm hook job pulls the model |
| Android on-device app | None at runtime; one-time first-launch model download (~1.5 GB) from HF Hub |
| Agentic-research notebook (A4) | Per-search egress to Tavily / Brave / Serper / DuckDuckGo / Wikipedia (BYOK; PII-filtered + audit-logged) |

## Disk + memory footprint

| Component | Disk | RAM (idle) | RAM (under load) |
|---|---|---|---|
| Chat playground (Python install) | ~150 MB | ~120 MB | ~250 MB |
| Classifier (Python install) | ~150 MB | ~120 MB | ~280 MB |
| Docker image (multi-arch) | ~480 MB compressed, ~1.4 GB on disk | (same as Python install when running) | (same) |
| Ollama + `gemma2:2b` | ~1.5 GB | ~2 GB | ~3.5 GB |
| Ollama + `gemma2:9b` | ~5.4 GB | ~6 GB | ~9 GB |
| Android APK (v0.1.0 skeleton) | 55 MB | minimal | (real RAM use lands with v1 MVP + LiteRT) |

## Dependency floors

The chat package's runtime deps:

| Package | Min version | Why |
|---|---|---|
| `pydantic` | 2.0 | v2 model API |
| `fastapi` | 0.115 | required for SSE streaming on `/api/chat` |
| `uvicorn` | 0.30 | matches FastAPI version |
| `structlog` | 24.0 | observability filter that strips PII |
| `huggingface_hub` | 0.20 | optional; only needed for HF model downloads |

For the full pinned set, see each package's `pyproject.toml`.
