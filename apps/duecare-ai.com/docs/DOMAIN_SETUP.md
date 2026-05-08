# Domain setup for duecare-ai.com

This guide connects duecare-ai.com to the Render web service.

## Target setup

```text
GitHub repo      TaylorAmarelTech/gemma4_comp
Git branch       master
Root directory   apps/duecare-ai.com
Render service   duecare-ai-hub
Render runtime   Docker web service
Health check     /api/health
Disk mount       /app/.duecare
Domains          duecare-ai.com, www.duecare-ai.com
DNS provider     Cloudflare recommended
```

## Step 1 — Deploy the Render service

In Render:

1. Create a new Web Service.
2. Connect the GitHub repo `TaylorAmarelTech/gemma4_comp`.
3. Use branch `master`.
4. Use Docker runtime.
5. Set root directory to `apps/duecare-ai.com`.
6. Set Dockerfile path to `./Dockerfile`.
7. Use region Oregon.
8. Set health check path to `/api/health`.
9. Add a persistent disk:
   - Name: `duecare-ai-data`
   - Mount path: `/app/.duecare`
   - Size: `1 GB`
10. Confirm these environment variables:

```text
DUECARE_ENV=production
DUECARE_PRIVACY_MODE=anonymized_signals_only_no_raw_pii
DUECARE_STORAGE=file
DUECARE_DATA_DIR=/app/.duecare
PORT=10000
```

The monorepo root includes `render.yaml`, so Render may detect most of this automatically.

## Step 2 — Add custom domains in Render

In the Render service settings, add custom domains:

```text
duecare-ai.com
www.duecare-ai.com
```

Render usually creates the corresponding root/www pair automatically when one is added. Keep both visible in the Render Custom Domains panel.

Copy the service's Render hostname. It will look like:

```text
<service-slug>.onrender.com
```

Use the exact hostname Render gives you.

## Step 3 — Put the domain on Cloudflare

If duecare-ai.com is already registered at Cloudflare, skip to Step 4.

If it is registered somewhere else:

1. Open Cloudflare.
2. Add a site for `duecare-ai.com`.
3. Choose the free plan unless you already know you need paid features.
4. Cloudflare will provide two nameservers.
5. Go to the domain registrar where duecare-ai.com was purchased.
6. Replace the registrar nameservers with the two Cloudflare nameservers.
7. Wait for Cloudflare to show the domain as active.

This can take minutes, but sometimes takes several hours.

## Step 4 — Configure Cloudflare DNS records

In Cloudflare, open:

```text
Website → duecare-ai.com → DNS → Records
```

Remove conflicting records first:

- Remove any old `A`, `AAAA`, or `CNAME` records for `@` and `www` that point somewhere else.
- Remove `AAAA` records while configuring Render. Render custom domains currently expect IPv4 routing.
- Do not remove MX records if you have email configured.

Add these records:

| Type | Name | Target | Proxy status | TTL |
|---|---|---|---|---|
| CNAME | @ | `<service-slug>.onrender.com` | DNS only | Auto |
| CNAME | www | `<service-slug>.onrender.com` | DNS only | Auto |

Important: keep Proxy status as **DNS only** until Render verifies the domain and issues certificates.

## Step 5 — Set Cloudflare SSL/TLS mode

In Cloudflare, open:

```text
Website → duecare-ai.com → SSL/TLS → Overview
```

Set encryption mode to:

```text
Full
```

Do not use Flexible. Flexible can cause redirect loops or broken HTTPS when Render is also issuing TLS certificates.

## Step 6 — Verify domains in Render

Return to Render:

1. Open `duecare-ai-hub`.
2. Go to Settings → Custom Domains.
3. Click Verify for `duecare-ai.com` and `www.duecare-ai.com`.
4. Wait for certificate status to become issued/valid.

If verification fails:

- Wait a few minutes and retry.
- Confirm the CNAME target exactly matches the Render hostname.
- Confirm Cloudflare proxy is DNS only.
- Confirm no `AAAA` records remain for the apex or www names.
- Flush public DNS caches if needed.

## Step 7 — Smoke-test the public site

After Render verifies TLS, open:

```text
https://duecare-ai.com/
https://duecare-ai.com/api/health
https://duecare-ai.com/api/hub/status
https://duecare-ai.com/api/hub/knowledge-packs
https://duecare-ai.com/docs
```

Expected health response fields include:

```text
status: ok
storage: file
privacy_mode: anonymized_signals_only_no_raw_pii
```

## Step 8 — Optional Cloudflare proxy

After Render certificates are issued and the site works over HTTPS, you can optionally switch Cloudflare records from DNS only to Proxied.

Recommended for the hackathon deadline:

- Keep DNS only if everything works and time is short.
- Switch to Proxied only if you need Cloudflare caching, WAF, analytics, or DDoS shielding.
- If switching to Proxied, re-test all endpoints and the OpenAPI docs.

## Step 9 — Do not add these before submission

Do not add these just for domain launch:

- Raw worker case intake.
- Auto-email or auto-complaint sending.
- Twilio, WhatsApp, Messenger, or SMS provider credentials.
- GPU inference on Render.
- Login, Stripe, Sentry, PostHog, or analytics keys.
- Cloudflare API tokens in repo files.

The launch goal is a safe public hub: visible, reliable, and privacy-preserving.
