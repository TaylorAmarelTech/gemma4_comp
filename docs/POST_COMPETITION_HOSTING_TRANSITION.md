# Post-Competition Hosting Transition

**Decision:** keep the current Render production service and `duecare-ai.com`
available through Gemma 4 Good grading. After the owner confirms grading is
complete, retire centralized Fly/Render-style hosting and make GitHub Pages the
durable public presentation. Preserve the runtime and hub as software that
organizations can deploy as independently governed nodes.

This is an event-triggered runbook. It does not authorize an early shutdown,
DNS change, data deletion, or credential revocation while grading continues.

Its companion is
[`REPOSITORY_IDENTITY_MIGRATION.md`](REPOSITORY_IDENTITY_MIGRATION.md), which
covers renaming or replacing the source repository itself. Both are gated on
the same owner confirmation, and both change public URLs, so sequence them
deliberately rather than running them in parallel.

## Before and after

| Capability | During grading | After the transition |
|---|---|---|
| `duecare-ai.com` presentation | Render-hosted FastAPI pages | Static GitHub Pages export, optionally under the custom domain after DNS verification |
| MkDocs documentation | `tayloramareltech.github.io/gemma4_comp` | Unchanged and independently deployed |
| Continuity website | `tayloramareltech.github.io/duecare-ai-site` project-path preview | Durable static website and cutover candidate |
| Mutable public hub APIs | Available on the Render service within current safety boundaries | Not provided by GitHub Pages |
| Accounts/admin/submissions/outreach automation | Server-backed controls where implemented | Disabled with a visible static-site notice |
| Worker-facing or partner runtime | Local, Kaggle, edge, mobile, or self-hosted | Same; not removed by central-host retirement |
| Network exchange | Central demo intake plus manual/curator boundaries | Reviewed pack/artifact exchange or a partner-owned self-hosted hub |

The static site is not a serverless replacement for FastAPI. It cannot accept
submissions, persist signals, authenticate curators, execute automation, or
serve mutable API state. Those routes and controls must remain visibly disabled.

## Target public surfaces

- Documentation: <https://tayloramareltech.github.io/gemma4_comp/>
- Backend-free website: <https://tayloramareltech.github.io/duecare-ai-site/>
- Source: <https://github.com/TaylorAmarelTech/gemma4_comp>
- Kaggle workbench: <https://www.kaggle.com/code/taylorsamarel/duecare-app>
- Kaggle live demo: <https://www.kaggle.com/code/taylorsamarel/duecare-live-demo>
- Kaggle proof path: <https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation>

The custom-domain choice is operational, not architectural. If
`duecare-ai.com` is retained, point it to the validated root-domain Pages build
only after GitHub's domain verification and HTTPS are green. Otherwise leave
the project-path Pages URL as the durable website and retire the custom domain
separately.

## Node-first operating model

After central-host retirement, the repository remains the distribution point
for deployable nodes:

```text
organization-owned input
  -> local/tenant DueCare runtime and versioned packs
  -> deterministic GREP, RAG, tools, privacy checks
  -> optional locally chosen model
  -> local trace and human review
  -> explicitly reviewed sanitized export
  -> GitHub release/PR, offline transfer, or partner-owned hub
```

Each node owns its raw data, access controls, reviewer identities, retention,
provider credentials, budgets, and jurisdictional obligations. Public GitHub
Pages hosts documentation and reviewed static artifacts only. It does not
become a raw case-data warehouse.

Organizations needing live coordination may deploy the FastAPI hub from
`apps/duecare-ai.com`, use the repository's Docker/local deployment paths, and
operate their own storage and secrets. Agents such as Hermes or server
automation remain proposers/routers; a named human or organization-owned policy
must approve promotion.

## Cutover sequence

1. Record owner confirmation that competition grading is complete.
2. Freeze the exact source revision and run the model-free release, site,
   package-collection, Kaggle-source, privacy, and link gates.
3. Export and validate both the project-path fallback and the root-domain
   candidate from the real FastAPI templates.
4. Crawl all 51 public routes and assets at desktop and mobile widths with the
   Render dependency unavailable. Confirm all five snapshots and their
   checksums.
5. Export a private, access-controlled copy of any Render disk data that the
   owner is authorized and required to retain. Publish none of it by default.
6. Verify `.nojekyll`, canonical URLs, sitemap, robots policy, custom 404,
   GitHub Pages HTTPS, domain challenge, and rollback target.
7. If retaining `duecare-ai.com`, lower DNS TTL, publish the root-domain Pages
   build with `CNAME`, change DNS, and verify root plus `www` over HTTPS. If not,
   publish the project-path build as the final canonical website and update
   public links.
8. Observe the static production surface through the rollback window. Confirm
   no page silently tries to reach Render and every former mutable control
   explains the limitation.
9. Remove public traffic from Render/Fly, then disable the centralized service,
   scheduler hooks, persistent disk, and provider secrets according to the
   retention decision. Do not delete the private archive until its retention
   owner approves.
10. Publish the final Kaggle/community notice and update the handoff receipt
    with the actual cutover revision, date, DNS result, archive disposition, and
    rollback evidence.

The detailed exporter commands and DNS variants remain in
[`apps/duecare-ai.com/DEPLOY_STATIC.md`](../apps/duecare-ai.com/DEPLOY_STATIC.md).

## Acceptance gate

The centralized host may be retired only when all of these are true:

- [ ] competition grading completion is owner-confirmed;
- [ ] the 51-route fallback and five-snapshot validator passes at the frozen revision;
- [ ] desktop and mobile route/asset crawls pass without Render;
- [ ] mutable controls are disabled and clearly explained;
- [ ] the selected Pages URL and HTTPS work from an external network;
- [ ] DNS and a tested rollback target are recorded if the custom domain moves;
- [ ] private Render data has an explicit archive/delete/retention decision;
- [ ] no provider or platform secret remains on a retired service;
- [ ] public docs describe the loss of centralized APIs and the node deployment path; and
- [ ] the final transition receipt names the revision, date, owner, and evidence.

Until this gate passes, Render remains the current production service and the
GitHub Pages website remains a read-only continuity preview.
