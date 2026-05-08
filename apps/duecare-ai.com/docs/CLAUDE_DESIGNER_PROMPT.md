# Claude Designer prompt for duecare-ai.com

Copy/paste this prompt into Claude Designer.

---

You are Claude Designer. Design a polished, high-converting public website for Duecare AI at `duecare-ai.com`.

## Project context

Duecare AI is a Gemma 4 Good Hackathon project for migrant-worker safety. It combines:

1. A Kaggle Gemma 4 harness that demonstrates grounded safety behavior.
2. A public website/hub at `duecare-ai.com` that explains the project and coordinates anonymized updates.
3. Future Platform Safety, NGO / Regulators, Migrant Worker Chat, and Academic Research deployments that share one consistent privacy boundary.

Core message:

> Centralized knowledge. Decentralized privacy.

Required phrase:

> Privacy is non-negotiable.

Operational boundary:

> Duecare drafts; the user or trusted caseworker decides.

The public hub is **not** a raw case-management platform. It must not look like an emergency hotline, official government portal, law firm, or reporting endpoint. It is a technical/impact hub showing architecture, use cases, privacy-preserving signal exchange, public-source update proposals, and the Gemma 4 harness story.

## Current implementation facts

The site is a small FastAPI app inside the main Duecare/Gemma 4 monorepo:

- Repo: `TaylorAmarelTech/gemma4_comp`
- Branch: `master`
- Website folder: `apps/duecare-ai.com`
- Render root directory: `apps/duecare-ai.com`
- Render URL: `https://duecare-ai-com.onrender.com/`
- Runtime: Docker web service on Render
- No frontend framework, no build step, no bundler
- Server-rendered HTML strings currently live in `app/site_content.py`
- Existing dashboard HTML lives in `app/main.py` as `_index_html()` and is now served at `/dashboard`
- Tests are in `tests/test_app.py`

Existing pages/routes:

- `/` — public homepage
- `/components` — architecture component map
- `/use-cases` — use-case stories
- `/grep-rules` — rule-category explainer
- `/tools` — draft-only tool catalog
- `/context` — context by corridor/jurisdiction
- `/dashboard` — live operational dashboard and API demo forms
- `/docs` — FastAPI OpenAPI docs
- `/api/health` — health check
- `/api/hub/status` — counters/privacy mode
- `/api/hub/knowledge-packs` — knowledge-pack metadata
- `/api/hub/trends` — aggregate trends

## Design goal

Replace the current plain dashboard-looking design with a premium, memorable hackathon finalist website that looks credible to judges, NGOs, regulators, and open-source reviewers.

The site should feel like:

- Public-interest AI infrastructure
- Privacy-first civic technology
- Modern research/NGO tooling
- Serious enough for regulators, clear enough for a 3-minute demo video

Reference vibes, not literal copies:

- Linear / Stripe polish for clarity and spacing
- Anthropic / OpenAI research-page restraint
- Human Rights Watch / ILO seriousness
- Modern maps/knowledge-graph dashboards for technical depth

Avoid:

- Generic SaaS dashboard look
- Toy hackathon styling
- Emergency-services styling
- Overly dark cyberpunk visuals
- Cluttered tables on the homepage
- Stock-photo NGO imagery

## Visual identity

Recommended direction:

- Background: warm off-white or very dark navy with subtle gradient sections. Choose one coherent direction.
- Accent colors: blue/teal/emerald for trust and privacy; amber for caution; red only for risk indicators.
- Typography: strong editorial headline, readable body. Use system fonts unless you can propose a safe no-build alternative.
- Shapes: soft cards, thin borders, gentle glows, timeline/flow diagrams.
- Diagrams should be visible on screen in the video without requiring scrolling.

## Homepage content requirements

Design the homepage as a narrative landing page, not a dashboard.

Suggested sections:

1. **Hero**
   - Headline: `Centralized knowledge. Decentralized privacy.`
   - Subheadline explaining Gemma 4 + Duecare in one sentence.
   - CTA buttons: `Explore architecture`, `Open live demo`, `View API`
   - Trust/safety badge: `No raw case intake · Anonymized signals only · Gemma 4 harness`

2. **Human impact story**
   - Use a composite worker example, clearly labeled composite.
   - Example: “Maria is offered a job abroad, but the message asks for placement fees and passport handoff.”
   - Show how Duecare helps without sending her private message to the public hub.

3. **System diagram**
   A beautiful four-part visual:
   - Platform Safety; NGO / Regulators; Migrant Worker Chat; Academic Research
   - Local Gemma 4 + Safety Guidance Layer
   - Duecare AI public hub
   - Curated knowledge packs back to local deployments

   Must communicate: raw details stay local; anonymized patterns and public-source updates go to the hub.

4. **Eight-component map**
   Show components with honest status labels:
   - Runtime — Live
   - Harness — Live
   - Eval — Live
   - Exchange — Prototype
   - Sentinel — Prototype
   - Trainer — Prototype
   - Channels — Roadmap
   - Mobile — Sibling project

   Make this look like a product architecture diagram, not a bullet list.

5. **What judges can verify**
   Cards linking to:
   - Kaggle notebooks / harness demo
   - Public GitHub repo
   - API docs
   - Live dashboard
   - Model/evaluation writeup

6. **Privacy boundary**
   Strong callout:
   - `Privacy is non-negotiable.`
   - Public hub accepts anonymized patterns only.
   - Complaint flows are draft-only; users/caseworkers send.

7. **Use cases**
   Four cards:
   - Platform Safety
   - NGO / Regulators
   - Migrant Worker Chat
   - Academic Research

8. **Footer**
   Links to components, use cases, GREP rules, tools, context, dashboard, API.

## Dedicated page requirements

### `/components`

Make this the architecture proof page.

Include:

- Large component diagram
- Eight component cards with status labels
- One sentence each on what is live vs prototype vs roadmap
- A privacy/data-flow diagram showing what crosses the hub boundary

### `/grep-rules`

Make deterministic safety visible.

Include:

- Explain GREP as the millisecond safety layer before generation
- Category cards: recruitment fees, document retention, threats, jailbreak resistance, complaint routing, grounding gaps
- A mini “paste → rules fire → context injected → answer grounded” diagram
- Link/CTA to `/dashboard`

### `/tools`

Make tools clear but safe.

Include:

- Tool cards: fee-cap checker, complaint draft builder, contact router, citation verifier, anonymization gate, pack diff reviewer
- Strong draft-only warning: no auto-submission, no auto-email
- “Duecare drafts; humans decide” visual callout

### `/context`

Make RAG/context concrete.

Include:

- Corridor cards: Philippines → Hong Kong, Indonesia → Gulf, Nepal → Malaysia, Bangladesh → Singapore, Global maritime, online ads
- Diagram: public source → Sentinel proposal → curator review → signed pack → local deployment
- Make context feel like a curated knowledge graph, not a text list

### `/use-cases`

Make this accessible to non-technical judges.

Include:

- Scenario cards in the canonical order: Platform Safety, NGO / Regulators, Migrant Worker Chat, Academic Research
- Each card should answer: who uses it, what they paste/provide, where data stays, what Duecare returns

### `/dashboard`

Keep as operational demo, but make it visually subordinate to the main narrative.

Improve:

- Top explainer: “This is the live hub, not the model chat UI.”
- Make API forms feel like demo widgets, not the homepage.
- Keep the existing forms and IDs working unless you update tests.

## Technical constraints

Do not introduce a frontend framework unless absolutely necessary. Prefer:

- Plain HTML/CSS generated from Python strings
- Minimal vanilla JavaScript only where needed
- No external CDN dependencies unless strongly justified
- No images required; use CSS diagrams, SVG-like layout, cards, and semantic HTML

If you propose implementation, target these files:

- `app/site_content.py` for public pages
- `app/main.py` only for route wiring or dashboard changes
- `tests/test_app.py` for route/content tests
- `README.md` for route documentation

Keep FastAPI endpoints unchanged. Do not remove:

- `/api/health`
- `/api/hub/status`
- `/api/hub/knowledge-packs`
- `/api/hub/trends`
- `/api/hub/signals`
- `/api/hub/opencrawl/updates`

## Safety and content constraints

- Do not include real personal names, phone numbers, emails, passport numbers, addresses, or case details.
- Composite names are allowed only if labeled composite.
- Real NGO/institution names are allowed if public organizations.
- Do not imply Duecare is an official hotline, legal counsel, or emergency response service.
- Do not imply the hub receives raw worker cases.
- Do not add auto-email/auto-reporting UX.
- Do not ask for API keys or credentials.

## Output requested

Provide:

1. A concise design diagnosis of the current site.
2. A proposed information architecture.
3. A polished visual direction with color/type/spacing guidance.
4. Section-by-section copy and layout for the homepage.
5. Wireframe-level layouts for `/components`, `/grep-rules`, `/tools`, `/context`, `/use-cases`, and `/dashboard`.
6. If possible, provide implementation-ready HTML/CSS patterns compatible with the current no-build FastAPI setup.
7. Prioritize changes that can ship before the 2026-05-18 hackathon deadline.

Remember: this website exists to support the video and public judging. It must make the project feel real, humane, technically deep, and privacy-preserving within the first 10 seconds.
