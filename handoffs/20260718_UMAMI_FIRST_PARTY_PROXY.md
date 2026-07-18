# Umami first-party proxy (ad-blocker coverage)

You (Rosario) run these steps in **Vercel** and **Google Cloud DNS**. Nothing
here can be done from the container: it touches external accounts. Budget ~15
minutes. The repo side (proxy code + the one-line site flip) is already written;
the last step just uncomments the flip.

## Why

Ad / tracker blockers drop `cloud.umami.is` by hostname, so blocker users are
never counted (the standing gotcha in the analytics-umami memory). Serving the
tracker from a first-party subdomain you control evades that.

## Decision (2026-07-18)

- **Topology:** innocuous subdomain `m.rosarioscalise.com` (change the label if
  you like; keep it non-analytics-sounding). Umami is cookieless and the tracker
  is `defer`, so visitors notice nothing; only your data coverage improves.
- **Host:** **Vercel** (free Hobby), attached with a **single CNAME**. Chosen
  over Cloudflare because free Cloudflare cannot host a subdomain-only zone
  (that is Enterprise), so it would force moving your whole domain's nameservers.
  Vercel needs only one CNAME record, leaving your apex, GitHub Pages,
  nameservers, and the delicate cross-account domain setup completely untouched.
  (Cloudflare-full remains a reference alternative: see the appendix +
  `infra/umami-proxy/cloudflare/`.)

## Current state (verified 2026-07-18)

- DNS: Google Cloud DNS (`ns-cloud-d{1..4}.googledomains.com`).
- Hosting: GitHub Pages, served directly (`rosarioscalise.com` -> `185.199.108.153`).
- No edge/proxy in front today.

## Repo artifacts (already committed)

- `infra/umami-proxy/vercel/middleware.js` : the Edge Middleware reverse proxy
  (forwards the visitor IP via X-Forwarded-For so geo stays correct).
- `infra/umami-proxy/vercel/public/index.html` : placeholder so Vercel has a
  static output dir; all real paths are handled by the middleware.
- `website/site.yaml` : the proxied `umami_src` is staged as a comment, ready to
  uncomment in step 5.

## Steps

### 1. Deploy the proxy on Vercel
Create a free Vercel account if needed (GitHub login works). Then either:

- **Git import (recommended, auto-redeploys):** Vercel > **Add New… > Project** >
  import the `romesco/portfolio` repo. Set **Root Directory** to
  `infra/umami-proxy/vercel`. Framework Preset: **Other**. Deploy. With the root
  directory scoped to that subfolder, Vercel only ever builds the proxy, never
  the main site.
- **CLI (one-off):** `cd infra/umami-proxy/vercel && npx vercel --prod` and
  follow the prompts. (Runnable from the container if you log in with a token.)

You'll get a `*.vercel.app` URL. Sanity check:
`curl -s https://<project>.vercel.app/script.js | head -c 200` should return the
Umami tracker JS.

### 2. Attach the subdomain in Vercel
Project > **Settings > Domains** > **Add Domain** > `m.rosarioscalise.com`.
Vercel shows a **CNAME** to create. The target is **unique to your project**
(e.g. `d1d4fc829fe7bc7c.vercel-dns-017.com`, NOT the old generic
`cname.vercel-dns.com`), so copy the exact value it displays.

### 3. Find where DNS is managed, then add ONE CNAME
The domain is registered at **Squarespace** (ex-Google Domains, per RDAP) and
served by `ns-cloud-*.googledomains.com` nameservers, which BOTH Squarespace's
managed DNS and Google Cloud DNS use, so the name alone does not say where the
records live. Log into **Squarespace** (account.squarespace.com, using the email
that owned the old Google Domains registration) > the domain > **DNS / Name
servers**:
- **If it shows Squarespace/Google name servers with an editable DNS records
  table** -> add the record there: Host `m`, Type `CNAME`, Data = Vercel's target
  (`...vercel-dns-0XX.com`).
- **If it shows custom name servers `ns-cloud-*.googledomains.com`** -> DNS is
  delegated to a **Google Cloud DNS** zone. In console.cloud.google.com find the
  project holding the `rosarioscalise.com` zone (Network Services > Cloud DNS;
  try each of your Google accounts/projects, or `gcloud dns managed-zones list
  --project=<id>`), then **Add Standard** record set: DNS name `m`, type `CNAME`,
  canonical name = Vercel's target **with a trailing dot**
  (e.g. `d1d4fc829fe7bc7c.vercel-dns-017.com.`).

Either way it is the same single record; only the console differs.

Save. This is the ONLY DNS change. Your apex, `www`, MX/email, and the
GitHub-Pages verification records are all untouched. Vercel auto-provisions TLS
for the subdomain within a few minutes.

### 4. Verify the proxy is live
```
curl -s https://m.rosarioscalise.com/script.js | head -c 200      # -> umami tracker JS
curl -s -i -X POST https://m.rosarioscalise.com/api/send \
  -H 'Content-Type: text/plain' -A 'Mozilla/5.0' \
  --data '{"type":"event","payload":{"website":"b3fad5ea-4eb5-42ed-9bfa-95bf0bdfcc76","hostname":"rosarioscalise.com","url":"/proxy-test"}}'
```
The POST should return `200` with a token body, and a `/proxy-test` pageview
should appear in Umami within a minute. If geolocation looks wrong (everything in
one datacenter region), the X-Forwarded-For forwarding isn't reaching Umami :
re-check `middleware.js`.

### 5. Flip the site to the proxy (repo side)
In `website/site.yaml`, under `analytics:`, uncomment the proxied line and delete
the cloud one (`umami_id` stays the same):
```yaml
  # umami_src: "https://m.rosarioscalise.com/script.js"   # <- uncomment
  umami_src: "https://cloud.umami.is/script.js"           # <- delete
```
Commit + push -> Pages redeploys. The tracker now loads from `m.` and auto-posts
events to `m./api/send` (Umami derives the collect host from the script origin).
The CI deploy-event job follows `umami_src`, so it starts using the proxy too.

### 6. Confirm the fix
Load the site with uBlock Origin enabled. Before: no request to `cloud.umami.is`.
After: a request to `m.rosarioscalise.com/script.js` + `/api/send` the blocker
leaves alone, and the visit shows in Umami.

## Rollback
Delete the `m` CNAME and revert step 5. The site itself is never affected.

## Notes
- Vercel Hobby is for non-commercial use; a personal-portfolio analytics proxy is
  fine. Edge Middleware invocation limits are generous for this traffic.
- Update the `analytics-umami` memory once live, since the blocklist gotcha is
  then resolved. This also front-runs part of the self-host plan
  (`20260617_UMAMI_SELFHOST.md`).

## Appendix: Cloudflare alternative (only if you move DNS there)
`infra/umami-proxy/cloudflare/worker.js` does the same job as a Worker. It needs
the zone on Cloudflare, which on the free plan means a **full nameserver move**
(Google -> Cloudflare) with all records replicated (apex A -> GitHub Pages kept
DNS-only/grey-cloud, `www`, MX/SPF, and the `_github-pages-challenge` TXT). More
surface area for no extra blocker benefit; only worth it if you want Cloudflare's
CDN anyway.
