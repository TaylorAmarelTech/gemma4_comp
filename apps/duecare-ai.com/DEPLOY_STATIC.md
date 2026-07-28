# Deploying duecare-ai.com as a static site

`scripts/export_static.py` renders the FastAPI site to a static bundle that any
static host can serve. It drives the **real app** through Starlette's
`TestClient`, so page content continues to come from maintained templates and
committed assets rather than a second website fork. The exporter makes no
network or model call.

## Build

```powershell
pip install -r requirements.txt httpx httpx2 # Starlette TestClient prefers httpx2
python scripts/export_static.py --out dist --api-base https://gemma4-comp.onrender.com

# Backend-free project-path preview. This neither emits CNAME nor changes DNS.
python scripts/export_static.py --out dist-fallback --fallback `
  --base-path /duecare-ai-site `
  --site-url https://tayloramareltech.github.io/duecare-ai-site `
  --omit-cname
python scripts/validate_static_fallback.py --site dist-fallback `
  --base-path /duecare-ai-site `
  --site-url https://tayloramareltech.github.io/duecare-ai-site
```

Both modes produce 51 pretty-URL pages and the committed `/static` assets.
The live-backend bundle emits `CNAME` and repoints relative API fetches to the
specified origin. The fallback bundle instead:

- renders against an isolated empty hub store;
- bakes exactly five allowlisted public JSON snapshots plus a checksum manifest;
- records the source commit in CI (`working-tree` is the explicit local default);
- installs the API-blocking boundary before any page script executes;
- visibly labels the snapshot and disables state-changing forms, buttons, and
  server-only links;
- supports a GitHub project path as well as a future custom-domain root; and
- includes `.nojekyll`, canonical `robots.txt`/`sitemap.xml`, and a custom
  `404.html`.

The fallback bundle never proxies an API request to Render. Its snapshot
manifest explicitly excludes private submissions, admin state, and raw logs.
Pass `--source-revision <40-character-git-sha>` in other automated builds so
the snapshot manifest remains traceable to its exact source.
`.github/workflows/duecare-site-build.yml` builds, validates, and retains both
modes as separate artifacts on every relevant `master` update.

## GitHub Pages

This repository already publishes MkDocs to GitHub Pages through
`.github/workflows/docs-deploy.yml`, and a repository can have only one Pages
site. Keep that documentation site unchanged.

Use the dedicated `TaylorAmarelTech/duecare-ai-site` repository for the public
website continuity copy. Its workflow checks out an exact public revision of
this monorepo, builds the fallback, validates it, and deploys it with GitHub's
Pages action. The project-path preview intentionally omits `CNAME`, so it does
not claim `duecare-ai.com` or disturb the Render deployment.

At an approved cutover, change the separate repository's build to an empty
`--base-path`, use `--site-url https://duecare-ai.com`, emit
`--cname duecare-ai.com`, validate the root-domain artifact, and only then
change DNS. Never publish the `/duecare-ai-site` project-path build at the
custom-domain root.

## Recommended Render retirement path

GitHub Pages can replace only the static presentation layer. It cannot run
FastAPI, store submissions, authenticate curators, execute automation, or
serve mutable API state.

Treat the routes in three groups:

| Group | Routes and behavior after retirement |
|---|---|
| Durable static pages | Keep the landing, mission, project status, privacy, setup, deployment, benchmark, evaluation, harness, study, case, component, kernel, fine-tuning, data, package, tool, use-case, technical-documentation, and demo pages. Their reviewed HTML and committed static assets remain useful without a backend. |
| Read-only snapshots | Keep hub, stats, research-monitor, server-automation, source-verification, and knowledge-pack views only through dated, checksum-bound public snapshots. |
| Backend-only controls | Disable contribute, newsletter, outreach, local-KB, submission, email-feedback, login, and every mutating control with an explicit unavailable notice. Admin, curator, and sentinel routes stay outside the export. |

Before changing DNS or canceling Render:

1. Keep the fallback exporter, allowlisted snapshots, and validator green.
2. Keep the dedicated Pages project-path preview deployed while Render remains
   the production website. It is a continuity rehearsal, not a DNS cutover.
3. Build the root-domain candidate and crawl every public route and asset on
   desktop and mobile with the Render dependency unavailable.
4. Verify GitHub Pages HTTPS, the custom-domain challenge, `CNAME`, `.nojekyll`,
   `robots.txt`, `sitemap.xml`, canonical URLs, and the custom 404 page.
5. Lower DNS TTL, switch `duecare-ai.com`, verify production, and retain the
   old Render configuration through a documented rollback window.
6. Only then disable Render billing/runtime. Keep the separate MkDocs project
   site at `tayloramareltech.github.io/gemma4_comp/` unchanged.

The retirement gate passes only when the static site remains useful with the
Render service unavailable, every dynamic limitation is visible, no public
control loses user input, and the DNS rollback procedure has been tested.
