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

Produces `dist/` with 50 pages (pretty URLs, `mission/index.html`), the `/static` assets,
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
