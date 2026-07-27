# Deploying duecare-ai.com as a static site

`scripts/export_static.py` renders the FastAPI site to a static bundle (`dist/`) that any
static host serves. It drives the **real app** through Starlette's `TestClient`, so the output
is byte-identical to production — including the `_nav`/`_footer` includes and the baked
`benchmark_leaderboard.json` — with no template forking.

## Build

```bash
pip install -r requirements.txt httpx httpx2 # Starlette TestClient prefers httpx2
python scripts/export_static.py --out dist --api-base https://gemma4-comp.onrender.com
```

Produces `dist/` with 51 pages (pretty URLs, `mission/index.html`), the `/static` assets,
a `CNAME`, and `.nojekyll`. `--api-base` repoints the dynamic pages' relative `fetch('/api/…')`
calls at the live backend (its CORS already allows the `duecare-ai.com` origin); omit it for a
fully static bundle where those backend calls no-op. The demo page's committed data fetch is
always baked to `/static/demo_priority_examples.json`.

## GitHub Pages

This repo already publishes MkDocs to GitHub Pages via `.github/workflows/docs-deploy.yml`, and
**a repo can have only ONE Pages site.** So the `duecare-site-build` workflow builds the bundle
as a downloadable artifact rather than adding a second `deploy-pages` job (which would fight the
docs deploy). To put the marketing site on Pages, pick one:

1. **Separate repo (recommended).** Push `dist/` to a dedicated `duecare-ai-site` repo with
   Pages enabled and the `duecare-ai.com` custom domain. The emitted `CNAME` + `.nojekyll` make
   it turnkey. This lets the site own the domain root, which the absolute `/static/…` and
   `/route` links require.
2. **Replace docs.** Repoint `docs-deploy.yml` at `dist/` if the marketing site should own the
   existing Pages domain instead of MkDocs.

A `user.github.io/repo/` **project-path** deployment would break every absolute `/static/` and
`/route` reference — deploy at a custom-domain root only.

## Recommended Render Retirement Path

It is worth preserving the public site before Render is retired, but GitHub
Pages can replace only the static presentation layer. It cannot run FastAPI,
store submissions, authenticate curators, execute automation, or serve mutable
API state.

Use a dedicated `duecare-ai-site` repository rather than replacing this
repository's MkDocs deployment. Publish the exported bundle at the
`duecare-ai.com` domain root, which preserves the existing absolute `/static/`
and page links. Build the retirement candidate without `--api-base`; a fallback
must not keep calling the Render origin after Render is disabled.

Treat the routes in three groups:

| Group | Routes and behavior after retirement |
|---|---|
| Durable static pages | Keep the landing, mission, project status, privacy, setup, deployment, benchmark, evaluation, harness, study, case, component, kernel, fine-tuning, data, package, tool, use-case, technical-documentation, and demo pages. Their reviewed HTML and committed static assets remain useful without a backend. |
| Read-only snapshots | Keep hub, stats, research-monitor, server-automation, source-verification, and knowledge-pack views only after their public data is baked into versioned static JSON or HTML. Label the snapshot date and link to the repository source. |
| Backend-only controls | Disable or replace contribute, newsletter, outreach, local-KB, submission, email-feedback, login, and every mutating control with an explicit archived/unavailable notice. Keep admin, curator, and sentinel routes out of `PAGE_ROUTES` and therefore out of the public export. Do not leave buttons that fail silently or imply data was accepted. |

Before changing DNS or canceling Render:

1. Add a fallback export mode that visibly disables backend-only controls and
   contains no executable request to the Render hostname.
2. Bake the safe read-only knowledge-pack and status payloads needed by the
   snapshot pages; never export private submissions, admin state, or raw logs.
3. Deploy the candidate to a temporary custom-domain root, crawl every public
   route and asset, and test on desktop and mobile with Render stopped.
4. Verify GitHub Pages HTTPS, the custom-domain challenge, `CNAME`, `.nojekyll`,
   `robots.txt`, `sitemap.xml`, canonical URLs, and the custom 404 page.
5. Lower DNS TTL, switch `duecare-ai.com`, verify the production route set, and
   retain the old Render configuration through a documented rollback window.
6. Only then disable Render billing/runtime. Keep the separate MkDocs project
   site at `tayloramareltech.github.io/gemma4_comp/` unchanged.

The retirement gate passes only when the static site remains useful with the
Render service unavailable, every dynamic limitation is visible, no public
control loses user input, and the DNS rollback procedure has been tested.
