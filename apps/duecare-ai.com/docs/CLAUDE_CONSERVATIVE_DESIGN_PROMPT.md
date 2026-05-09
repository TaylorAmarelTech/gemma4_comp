# Claude conservative website redesign prompt for duecare-ai.com

Copy/paste this prompt into Claude Designer or another design/code agent when the current site starts becoming too visually ambitious, overlapping, brittle, or unclear.

---

You are working on the public website for **Duecare AI** at `duecare-ai.com`.

Your task is to produce a **simple, conservative, robust, responsive website design** that is much less likely to break than a high-concept hi-fi prototype. Do not try to impress with complex visual tricks. The priority is clarity, trust, responsiveness, and no overlapping content.

## Absolute design goal

Build a website that a judge, NGO director, regulator, platform safety lead, or academic researcher can understand quickly on a laptop or phone.

The site should feel like:

- a serious public-interest technology project;
- a clear documentation/product website;
- privacy-first civic infrastructure;
- credible enough for regulators and NGOs;
- simple enough to work in a 3-minute video.

The site should **not** feel like:

- a startup dashboard with too many widgets;
- an emergency hotline;
- a law firm;
- a government reporting portal;
- a complex SaaS control panel;
- a dark cyberpunk security product;
- an experimental art direction.

If a design choice increases the risk of overlap, clipping, bad mobile behavior, or hard-to-maintain formatting, choose the simpler option.

## Current implementation facts

- Repo: `TaylorAmarelTech/gemma4_comp`
- Branch: `master`
- Website folder: `apps/duecare-ai.com`
- Render root directory: `apps/duecare-ai.com`
- Runtime: FastAPI Docker web service on Render
- No frontend framework, no build step, no bundler
- Public page content currently lives mostly in `app/site_content.py`
- Dashboard HTML currently lives in `app/main.py` and is served at `/dashboard`
- Tests live in `tests/test_app.py`

Routes that should remain valid:

- `/`
- `/setup`
- `/packages`
- `/tools`
- `/intelligence`
- `/components`
- `/grep-rules`
- `/client-connect`
- `/contribute`
- `/sentinel`
- `/volunteer`
- `/partners`
- `/submissions`
- `/dashboard`
- `/use-cases`
- `/privacy`
- `/contact`
- `/login`
- `/demo`
- `/docs`
- `/api/health`

Do not remove existing API endpoints.

## Canonical use cases

Use exactly these four use cases, in this exact order, everywhere:

1. **Platform Safety**
2. **NGO / Regulators**
3. **Migrant Worker Chat**
4. **Academic Research**

Do not reorder them. Do not replace them with older labels such as "worker-side", "enterprise", "social platforms", or "researchers" in top-level navigation, homepage cards, diagrams, demo chapters, or summaries.

### Platform Safety

Trust and safety teams at social media companies, job platforms, marketplaces, and recruitment boards. They screen risky recruitment posts, ads, messages, recruiter profiles, and scam patterns.

### NGO / Regulators

NGOs, caseworkers, legal-aid groups, consulates, labor ministries, labor inspectors, regulators, and authorized enforcement partners. They triage messages/documents, route people to trusted help, draft complaints, and update corridor-specific knowledge.

### Migrant Worker Chat

Migrant workers and prospective migrant workers using a trusted chat, mobile, web, or local tool. OFWs are one demo persona, not the whole category. They privately check suspicious job offers, contracts, recruiter messages, fee demands, document retention, and threats.

### Academic Research

Academic researchers, public-interest researchers, evaluators, auditors, Kaggle judges, and model-safety teams. They reproduce prompts, evaluate model behavior, compare interventions, and verify claims from source artifacts.

## Plain-language technical components

Use these public component names. Avoid unclear labels like Runtime, Harness, Eval, Exchange, Sentinel, or Channels on public pages unless they are explicitly described as internal nicknames.

1. **Gemma 4 Model Layer** — calls Gemma 4 for classification, explanation, summarization, multimodal reading, and draft generation.
2. **Safety Guidance Layer** — wraps Gemma 4 with persona, GREP rules, RAG, tools, online search, and imports so outputs are grounded and traceable.
3. **Knowledge Packs** — versioned bundles of GREP data, RAG documents, contacts, tools, corridor fees, regulations, examples, and policies.
4. **Quality Testing Framework** — tests model and guidance behavior with text prompts, image prompts, rule-based scoring, LLM-based judging, and regression checks.
5. **Local Anonymization Module** — runs locally or inside a trusted tenant to convert sensitive content into anonymized information objects.
6. **Information Submission Module** — sends only anonymized objects, public-source updates, aggregate counts, or signed pack proposals to the central server.
7. **Central Knowledge Server** — powers duecare-ai.com, review queues, pack metadata, public pages, and API docs.
8. **Public Information Research Monitor** — uses public-source tools such as OpenClaw to find updated laws, advisories, trends, negative news, and policy changes.
9. **Knowledge Formatter** — converts scraped public content or stakeholder submissions into validated knowledge objects and pack updates.
10. **Stakeholder Engagement Module** — asks subscribers to rank responses, provide observations, suggest useful tools, and submit new public information.
11. **Stakeholder Response Formatter** — converts survey answers and feedback into structured information objects or reviewable proposals.
12. **Newsletter and Alert Module** — shares reviewed summaries of anonymized trends and public facts with subscribed partners.
13. **Fine-Tuning Module** — adapts Gemma 4 using approved, anonymized, provenance-tracked examples and stakeholder rankings.
14. **Channel and Deployment Package** — packages models, guidance layer, knowledge packs, config UI, API endpoint, and webhook service for real deployments.

## Required safety and privacy language

Use these exact phrases in the hero, privacy section, and tools/submission areas:

> Centralized knowledge. Decentralized privacy.

> Privacy is non-negotiable.

> Duecare drafts; the user or trusted caseworker decides.

> No raw case intake.

The anonymizer must be explained as a **bidirectional privacy gate**:

1. **Outbound gate:** anything sent from a local/tenant deployment to the central server must be anonymized first.
2. **Inbound gate:** anything received by the server through direct submission or scraping must be checked, structured, and anonymized before it can become a displayed object, newsletter item, knowledge-pack proposal, or training candidate.

The public hub accepts anonymized patterns and public-source facts. It does not accept raw worker chats, phone numbers, passports, home addresses, emails, or private case narratives.

## Conservative visual system

Use a stable, restrained visual system:

- Background: warm off-white `#FAFAF7` or white.
- Text: dark ink `#0E1116`.
- Muted text: slate/gray.
- Primary accent: teal, used sparingly.
- Warning/privacy accent: ember/amber, used only for privacy and caution callouts.
- Red: only for true risk/error states.
- Typography: system sans-serif is acceptable and preferred for reliability. If using Inter Tight or JetBrains Mono, ensure fallbacks are present and layout does not depend on the font loading.
- Layout: max-width content containers, clear sections, simple cards, tables, step lists, and diagrams.
- Visual density: moderate. Prefer fewer elements per section.

Do not create a design that depends on decorative gradients, absolute-positioned blobs, floating badges, overlays, parallax, animated hero text, or complex glassmorphism.

## CSS/layout hard rules to avoid overlap

Follow these rules strictly:

1. No `position: absolute` for normal content layout.
2. No negative margins.
3. No fixed-height cards for text-heavy sections.
4. No badges placed on top of headings or card corners.
5. No overlapping number labels and status pills.
6. No CSS transforms for layout positioning.
7. No text over images or gradients unless the contrast is guaranteed.
8. No multi-column layout below `860px`; stack into one column.
9. Use `minmax(0, 1fr)` in grid columns to prevent overflow.
10. Use `overflow-wrap: anywhere` for URLs, code, package names, and long labels.
11. Use `line-height` of at least `1.45` for headings and `1.6` for body text.
12. Let cards grow naturally with content.
13. Use consistent card internals: eyebrow/status line, heading, paragraph, actions.
14. Keep nav simple. If it wraps, it must wrap cleanly without overlapping the logo.
15. Avoid complex nested grids. Two levels maximum.
16. Test at widths: `360px`, `414px`, `768px`, `1024px`, `1440px`.
17. Nothing should horizontally scroll except code blocks and intentionally scrollable tables.
18. Never hide important content in hover-only states.
19. Do not use JavaScript to fix layout problems.
20. When in doubt, use a single-column section.

## Conservative page structure

Use the same page grammar everywhere:

1. **Page header**
   - Eyebrow
   - H1
   - One-paragraph summary
   - 1-2 clear CTAs max

2. **Primary content**
   - Cards, simple tables, or step lists
   - No more than 3-4 cards per row on desktop
   - One column on mobile

3. **Privacy boundary callout**
   - Always clear about no raw case intake
   - Always explicit about draft-only handoff

4. **Next-step links**
   - One row/list of simple links
   - No complex footer CTA cluster

## Top navigation

Keep the nav short and stable:

- Demo
- Setup
- Packages
- Tools
- Intelligence
- Contribute
- Live hub
- Sign in

If more links are needed, put them in the footer or page body. Do not overload the top nav.

## Homepage requirements

The homepage must explain the whole project, not just a worker chat example.

Recommended order:

1. **Hero**
   - H1: `Centralized knowledge. Decentralized privacy.`
   - One plain-language sentence: Duecare uses Gemma 4, safety guidance, knowledge packs, and testing to help Platform Safety, NGO / Regulators, Migrant Worker Chat, and Academic Research without centralizing raw case data.
   - CTAs: `Watch demo`, `Explore setup`, `View live hub`.
   - Trust line: `No raw case intake · Draft-only handoff · Anonymized/public-source updates only`.

2. **Problem statement**
   - Risky recruitment signals appear across posts, messages, documents, and changing laws.
   - Sensitive worker data cannot be centralized.
   - Models need grounding, testing, and update mechanisms.

3. **Solution overview**
   - Local/tenant deployments use Gemma 4 + Safety Guidance Layer.
   - Knowledge Packs provide rules, RAG, tools, and contacts.
   - Local Anonymization protects anything shared.
   - Central Knowledge Server coordinates reviewed updates.
   - Quality Testing and Fine-Tuning improve behavior safely.

4. **Four use cases**
   - Platform Safety
   - NGO / Regulators
   - Migrant Worker Chat
   - Academic Research

5. **Component overview**
   - Use simple cards or a table, not a complex overlapping diagram.
   - Group components by function: private experience, knowledge/data, privacy/submission, central server, testing/training.

6. **Privacy boundary**
   - Explain bidirectional anonymization.
   - Explain what never goes to the central server.

7. **What judges can verify**
   - Kaggle demo
   - Live hub
   - GitHub repo
   - API docs
   - Knowledge-pack examples
   - Evaluation results

## Demo page requirements

The demo page must cover the full story from problem statement to solution. It must not be worker-chat-only.

Create a conservative demo page with a video embed area and chapter list. The video can be a placeholder until the file exists, but the page content must reflect the full narrative.

Required demo chapters:

1. **Problem statement** — risky recruitment content, private worker data, changing rules, and why normal chatbots are not enough.
2. **Platform Safety** — screen a recruitment post/ad/message, show risk trace and reviewer support.
3. **NGO / Regulators** — show grounded draft guidance, contact routing, and complaint-channel context.
4. **Migrant Worker Chat** — show private local/chat guidance for a suspicious message or document, with no raw hub submission.
5. **Academic Research** — show reproducible prompts, scoring, model comparison, and provenance.
6. **Central Knowledge Server** — show anonymized submission, public-source update proposal, pack metadata, and live hub health.
7. **Privacy boundary** — show outbound anonymization and inbound anonymization for submissions/scraping.
8. **Solution close** — one shared core, four use cases, no raw case intake, draft-only handoff.

Demo page layout:

- H1: `Duecare AI demo: from problem to privacy-preserving solution.`
- One short summary paragraph.
- 16:9 video frame with safe placeholder.
- Chapter list in a normal stacked card list; no overlapping timeline.
- "What to watch for" bullets.
- Transcript accordion or simple section.
- CTAs: `Reproduce on Kaggle`, `Inspect architecture`, `Open live hub`.

Do not make the demo page look like a media startup landing page. Make it look like a reliable documentation/demo page.

## Page-by-page priorities

### `/components`

Use simple grouped sections:

1. Private decision-support experience
2. Knowledge and data formats
3. Privacy and submission
4. Central server and shared intelligence
5. Testing and model improvement

Each component card should show:

- name;
- status;
- what it does;
- what it displays;
- what it communicates with.

No overlay badges. Put the status below the heading or in a normal inline row.

### `/use-cases`

Use exactly four large cards in the canonical order. Each card answers:

- who uses it;
- what they provide;
- where data stays;
- what Duecare returns;
- which components are involved.

### `/privacy`

Make this plain and conservative. Include:

- no raw case intake;
- outbound anonymization;
- inbound anonymization;
- hashes not plaintext;
- draft-only handoff;
- what data can be stored;
- what data must stay local.

### `/tools`

Keep tools grounded and safe:

- fee-cap checker;
- complaint draft builder;
- contact router;
- citation verifier;
- anonymization gate;
- pack diff reviewer.

Every form must have an explicit no-raw-case consent checkbox.

### `/contribute`

Do not invite raw stories. Ask for:

- public-source URLs;
- anonymized observations;
- tool suggestions;
- response rankings;
- contact updates;
- corridor rule updates.

### `/intelligence` or `/sentinel`

Use the term **Public Information Research Monitor**. Explain that OpenClaw-style tools search public sources, propose updates, and require curator review. Do not imply the crawler scrapes private chats or social accounts without permission.

## Copy tone

Use conservative, precise language:

- "reviewable draft" instead of "automated complaint";
- "risk signal" instead of "proof";
- "public-source update proposal" instead of "verified fact" until reviewed;
- "authorized partner" instead of broad "law enforcement";
- "Migrant Worker Chat" instead of "worker-side";
- "Platform Safety" instead of "enterprise";
- "Quality Testing Framework" instead of "Eval";
- "Safety Guidance Layer" instead of "Harness" on public pages.

Avoid claims that sound too broad:

- Do not say Duecare prevents trafficking.
- Do not say it gives legal advice.
- Do not say it reports abuse automatically.
- Do not say it replaces caseworkers.
- Do not say it is an emergency service.

## Implementation expectations

If you output code, prefer:

- one stable `styles.css` or one stable style block;
- semantic HTML;
- simple CSS classes;
- no dependency on external assets;
- no fragile positioning;
- accessible labels and focus states;
- regression tests that check key routes and key phrases.

Before claiming completion, run or describe checks for:

- no overlap at mobile/tablet/desktop widths;
- nav wraps cleanly;
- long text and URLs wrap;
- forms have no-raw-case consent checkboxes;
- use cases appear in canonical order;
- required privacy phrases appear;
- demo page covers all four use cases and the central server, not only a worker question.

## Output requested

Produce a practical redesign plan and implementation guidance, not a flashy concept deck.

Include:

1. A diagnosis of why the current prototype risks overlap and confusion.
2. A conservative information architecture.
3. A minimal design system: colors, type, spacing, cards, forms, tables, callouts.
4. A page-by-page layout plan.
5. A demo page structure that covers the full problem-to-solution arc.
6. A CSS/layout checklist that prevents overlapping.
7. If code is included, keep it no-build FastAPI compatible.

Remember: boring, clear, and reliable beats flashy, fragile, and confusing.
