# Copilot Autonomous Work Session: Gemma 4 Good Hackathon Polish & Deploy

## Mission (2026-05-10; final submission due 2026-05-18)

You are continuing autonomous iterative work on the **DueCare** safety harness for the Gemma 4 Good Hackathon. This is a migrant worker protection system using Gemma 4's native function calling and multimodal capabilities.

**Primary Objective:** Polish ALL components to submission-ready state with focus on **consumer/enterprise installation pathways** and **cross-component consistency**.

## Project Context & Goals

**Hackathon Rubric (100 points total):**
- Impact & Vision (40 pts) â€” Real-world migrant worker protection, inspiring vision
- Video Pitch & Storytelling (30 pts) â€” Exciting 3-minute story with named characters
- Technical Depth & Execution (30 pts) â€” Real Gemma 4 innovation, not faked demo

**Core Innovation:** validated 6-layer safety harness. Keep numeric lift claims
only where they point to reproducible artifacts in the notebooks/reports:
1. Heuristic prescan â†’ 2. GREP rules â†’ 3. RAG retrieval â†’ 4. Tool calls â†’ 5. Gemma 4 verdict â†’ 6. Audit trail

## Current State (Post-Reorganization)

**âœ… COMPLETED / BASELINE AVAILABLE:**
- FastAPI hub (apps/duecare-ai.com/) â€” active website surface with route tests in the repo
- Core notebook (kaggle/02-live-demo/) â€” comprehensive 6-layer demo, auto-detection
- Archive reorganization â€” legacy notebook mirrors and skunkworks moved to `_archive/legacy-research-2026-05-09/`
- Public surface audit â€” clean across 4 checks, 0 findings
- Manual Kaggle publishing workflow documented in CLAUDE.md
- `scripts/setup_consumer.py` â€” safe local install helper with dry-run support
- `docker-compose.enterprise.yml` + deployment configs â€” compose config validates with `.env.enterprise.example`

**ðŸ”„ ACTIVE FOCUS AREAS:**

### 1. Installation & Deployment Pathways

**Consumer Installation (Priority 1):**
- [x] `pip install duecare-llm-cli` â†’ `duecare init` / `duecare demo-stage` workflow smoke-tested from local wheels in an isolated `virtualenv`
- [x] Meta-package `pip install duecare-llm` smoke-tested for `duecare --help`, `duecare domains list`, and end-to-end `duecare run rapid_probe` against a local OpenAI-compatible fake backend; real Gemma/Ollama/API runs still need their configured backends
- [x] Docker Compose stack for local/private deployment validates via `docker compose config`
- [x] Fresh-venv install test for the CLI workflow
- [ ] Desktop/mobile/browser surfaces documented as roadmap unless actually runnable

**Enterprise Installation (Priority 2):**
- [x] Private compose stack config validates locally
- [x] Add a concise deployment README for the compose stack
- [ ] Build/start the stack only if time and local Docker resources permit
- [ ] Keep Kubernetes, SSO/SAML, registry, and 10K+ scale items marked as roadmap unless validated

**Technical Implementation:**
- [x] Create `scripts/setup_consumer.py` â€” safe local install helper with dry-run support
- [x] Harden `docker-compose.enterprise.yml` and its deployment config files
- [ ] Add `scripts/setup_enterprise.py` only if the compose workflow needs a wrapper
- [x] Add installation validation and health checks for current setup/compose paths
- [x] Document hardware requirements (CPU/GPU/RAM) per current/roadmap deployment mode

### 2. Cross-Component Consistency

**Package Distribution:**
- [x] Verify all 17 workspace packages (`duecare-llm-*`) build cleanly in the local venv with `--no-isolation`
- [x] Ensure `scripts/build_all_wheels.py` includes all 17 package directories
- [x] Document version policy: infrastructure packages are `0.1.0`; `duecare-llm-chat` intentionally remains on its independent v0.14.x harness cadence
- [ ] Test optional extras installations ([transformers], [unsloth], [llama-cpp])
- [ ] Validate namespace package imports work correctly

**API Consistency:**
- [ ] Standardize response formats across all 41 FastAPI routes
- [ ] Ensure error handling follows same patterns
- [ ] Validate all routes return proper HTTP status codes
- [ ] Test cross-origin requests for web deployment

**Documentation Consistency:**
- [ ] Align README.md files across all packages
- [ ] Ensure consistent terminology (DueCare vs. duecare vs. Duecare)
- [ ] Validate all internal links work
- [ ] Check that examples use same data formats

### 3. Deployment Mode Deep Dive

**Worker-Side Tool (Mobile/Browser):**
```bash
# Key implementation tasks:
- [ ] LiteRT model conversion and optimization (roadmap unless runnable)
- [ ] Offline capability testing (roadmap unless runnable)
- [ ] Local PII anonymization without server roundtrips
- [ ] WhatsApp bot integration prototype (roadmap unless runnable)
- [ ] Browser extension manifest and permissions (roadmap unless runnable)
```

**Enterprise Integration:**
```bash
# Key implementation tasks:
- [ ] API rate limiting and quotas
- [ ] Multi-tenant data isolation
- [ ] Webhook integrations for job boards
- [ ] Compliance reporting dashboards
- [ ] SSO/SAML authentication (roadmap unless runnable)
```

**Agency/NGO Dashboard:**
```bash
# Key implementation tasks:
- [ ] Batch processing workflows
- [ ] Custom domain pack uploads
- [ ] Model comparison interfaces
- [ ] Export capabilities (PDF reports, CSV data)
- [ ] User role management
```

## Archive & Publishing Rules (Critical)

**âŒ DO NOT TOUCH:**
- `_archive/legacy-research-2026-05-09/` â€” 66 legacy notebooks, ignore unless explicitly needed
- `_archive/legacy_src/` â€” pre-DueCare scaffolding
- `_reference/` â€” private benchmark data, not for public release

**ðŸ“‹ MANUAL KAGGLE PUBLISHING:**
- DO NOT auto-publish to Kaggle via CLI
- Prepare copy/paste ready content only
- User handles manual Kaggle UI steps
- Focus on `kaggle/` kernel.py files and wheel datasets

**ðŸ““ KAGGLE NOTEBOOK POLICY:**
- DO NOT create new `.ipynb` notebooks for the submission by default.
- Treat `kernel.py` plus the folder README as the source of truth; existing
  `notebook.ipynb` files are preview/build artifacts only.
- Regenerate an existing preview notebook only when its source changed and
  Taylor explicitly wants the tracked artifact kept in sync.
- Any included notebook/kernel must bootstrap itself: print required Kaggle
  settings, fail fast on missing GPU/secret/dataset/model source, install
  DueCare from attached wheels first, then pinned PyPI, then immutable GitHub
  release assets or commit-pinned archives only as a fallback.
- Never document or generate notebooks that depend on `_reference/`, local
  `.venv`, root-level legacy mirrors, untracked files, or a moving GitHub
  branch such as `main`.

## Iterative Work Strategy

**Hour 1-3: Installation Infrastructure**
1. Harden setup scripts for consumer/enterprise workflows
2. Build and test Docker compose files from the checked-in deployment configs
3. Document hardware requirements and scaling characteristics
4. Test pip installation flow end-to-end

**Hour 4-6: Deployment Mode Implementation**
1. Label LiteRT/mobile/browser/channel work as roadmap unless runnable
2. Fix stale docs that overclaim deployment readiness
3. Enterprise API authentication and multi-tenancy documentation review
4. Webhook integration templates only if existing examples validate

**Hour 7-9: Integration & Testing**
1. End-to-end testing across all deployment modes
2. Performance benchmarking and optimization
3. Security review of deployment configurations
4. Cross-platform compatibility testing

**Hour 10-12: Polish & Documentation**
1. Installation guide creation with screenshots
2. Troubleshooting guides for common issues
3. Video material preparation (installation demos)
4. Final consistency pass across all components

## Specific Technical Priorities

### Consumer Installation Experience
```python
# Target user experience:
pip install duecare-llm-cli
duecare init
duecare demo-stage
duecare serve --port 8080
# â†’ Opens browser to http://127.0.0.1:8080 with working demo
```

### Enterprise Installation Experience
```yaml
# docker-compose.enterprise.yml
# Copy .env.enterprise.example to .env.enterprise, set strong secrets, then:
# docker compose --env-file .env.enterprise -f docker-compose.enterprise.yml up --build -d
services:
  duecare-api:
    build:
      dockerfile: deployment/docker/api.Dockerfile
  nginx:
    image: nginx:1.27-alpine
```

### Mobile On-Device Experience (roadmap unless linked to a validated artifact)
```python
# Illustrative React Native / Flutter integration target, not a checked-in SDK:
import { DueCareMLKit } from 'duecare-mobile'

const result = await DueCareMLKit.analyze(
  messageText,
  { model: 'gemma-4-e2b-tflite' }
)
```

## Quality Gates

Before each iteration cycle:
- [ ] Relevant tests pass (`make test` on Unix, direct Python/pytest commands on Windows)
- [ ] Public surface audit clean (`scripts/validate_public_surface.py`)
- [ ] No PII in any output files
- [ ] Installation scripts pass dry-run and isolated environment checks before claiming fresh-VM support
- [ ] Local wheel builds pass; clean-environment wheel/install tests pass before claiming PyPI readiness
- [ ] Documentation links resolve correctly

## Success Metrics

**Technical Depth & Execution (30 pts):**
- âœ… Gemma 4 native function calling in 6-layer pipeline
- ðŸ”„ Numeric lift claims backed by reproducible notebook/report artifacts
- ðŸ”„ Multiple deployment modes actually work
- ðŸ”„ Easy installation for both consumers and enterprises

**Impact & Vision (40 pts):**
- ðŸ”„ Clear path from "pip install" to "protecting real workers"
- ðŸ”„ Scalable deployment options (1 worker â†’ 1M workers)
- ðŸ”„ Concrete integration examples

**Video Material:**
- ðŸ”„ Demo of one-command installation
- ðŸ”„ Mobile app showing on-device protection
- ðŸ”„ Enterprise dashboard with real-time worker protection

## Next Actions

Start with **submission-readiness cleanup** â€” this is the foundation that keeps the repo credible. Fix stale claims, align docs with the real CLI/deployment paths, and keep speculative deployment modes labeled as roadmap until runnable.

**Begin with:** package/build consistency, public docs alignment, and validation gates.

## Context Files to Reference

- `CLAUDE.md` â€” Full project context and rules
- `docs/FOR_KAGGLE_JUDGES.md` â€” Submission overview
- `docs/writeup_draft.md` â€” Kaggle writeup (at 1486/1500 words)
- `packages/*/README.md` â€” Package-specific documentation
- `apps/duecare-ai.com/app/main.py` â€” FastAPI implementation reference
- `kaggle/02-live-demo/kernel.py` â€” Core demo notebook

Work autonomously, document decisions, test thoroughly, and focus on making this system genuinely deployable at scale.
