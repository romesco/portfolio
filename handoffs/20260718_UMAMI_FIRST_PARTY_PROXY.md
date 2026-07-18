# Umami first-party proxy (ad-blocker coverage)

You (Rosario) run these steps in your **Cloudflare dashboard** and **Google Cloud
DNS** console. Nothing here can be done from the container: it touches external
accounts. Budget ~15 minutes. The repo side (Worker code + the one-line site
flip) is already written; the last step just uncomments the flip.

## Why

Ad / tracker blockers drop `cloud.umami.is` by hostname, so blocker users are
never counted (the standing gotcha in the analytics-umami memory). Serving the
tracker from a first-party subdomain you control evades that. This does NOT touch
your apex, GitHub Pages, or the delicate cross-account custom-domain / cert
setup: it only adds a new subdomain.

## Current state (verified 2026-07-18)

- DNS: **Google Cloud DNS** (nameservers `ns-cloud-d{1..4}.googledomains.com`).
- Hosting: **GitHub Pages**, served directly (`rosarioscalise.com` -> `185.199.108.153`).
- No edge/proxy in front today. GitHub Pages cannot proxy, hence Cloudflare.

## Decision

- **Topology:** innocuous **subdomain** `m.rosarioscalise.com` (change the label
  if you like; keep it non-analytics-sounding). Chosen over a same-origin apex
  path to keep the apex + GitHub Pages entirely untouched. See the handoff-time
  discussion: near-zero risk, recovers most blocked visitors, no user-facing
  change (Umami is cookieless + the tracker is `defer`).
- **Edge:** Cloudflare Workers (free tier, 100k req/day is plenty).
- **DNS method:** **subdomain delegation** (below) so your apex zone stays on
  Google Cloud DNS exactly as it is. (Alternative: move the whole zone to
  Cloudflare. Don't, unless you want the CDN: it means replicating every apex
  record AND the GitHub-Pages verification TXT, and reconciling the cert. More
  risk for no added blocker benefit.)

## Steps

### 1. Cloudflare: add the subdomain as a zone
1. Create a free Cloudflare account if you don't have one.
2. **Add a site** -> enter `m.rosarioscalise.com` (the subdomain, not the apex).
   Pick the **Free** plan. Cloudflare assigns two nameservers, e.g.
   `xxx.ns.cloudflare.com` / `yyy.ns.cloudflare.com`. Note them.

### 2. Google Cloud DNS: delegate just that subdomain
1. Open the `rosarioscalise.com` zone in Google Cloud DNS.
2. Add an **NS** record set:
   - Name: `m` (i.e. `m.rosarioscalise.com`)
   - Type: `NS`
   - Data: the two Cloudflare nameservers from step 1.
3. Save. This delegates only `m.rosarioscalise.com` to Cloudflare; the apex and
   `www` keep resolving through Google straight to GitHub Pages, unchanged.
   (Delegation can take up to a few hours to propagate; usually minutes.)

### 3. Deploy the Worker
Option A (dashboard, simplest):
1. Cloudflare > **Workers & Pages** > **Create** > **Worker**. Name it
   `umami-proxy`. Replace the starter code with the contents of
   `infra/umami-proxy/worker.js` from this repo. **Deploy**.
2. Worker > **Settings** > **Domains & Routes** > **Add** > **Custom Domain** >
   `m.rosarioscalise.com`. Cloudflare provisions a cert for it automatically.

Option B (CLI): `cd infra/umami-proxy`, then `wrangler deploy` (needs
`CLOUDFLARE_API_TOKEN`). Uncomment the `routes` block in `wrangler.toml` first so
it binds the custom domain. This can be run from the container if you export a
token; the dashboard is fine too.

### 4. Verify the proxy is live
```
curl -s https://m.rosarioscalise.com/script.js | head -c 200      # -> umami tracker JS
curl -s -i -X POST https://m.rosarioscalise.com/api/send \
  -H 'Content-Type: text/plain' -A 'Mozilla/5.0' \
  --data '{"type":"event","payload":{"website":"b3fad5ea-4eb5-42ed-9bfa-95bf0bdfcc76","hostname":"rosarioscalise.com","url":"/proxy-test"}}'
```
The POST should return `200` with a token body, and a `/proxy-test` pageview
should appear in the Umami dashboard within a minute. If geolocation looks wrong
(all one country), re-check the `X-Forwarded-For` line in `worker.js`.

### 5. Flip the site to the proxy (repo side)
In `website/site.yaml`, under `analytics:`, swap the tracker src to the proxy and
remove the now-inaccurate blocklist caveat. The proxied value is already staged
as a comment there:
```yaml
  # umami_src: "https://m.rosarioscalise.com/script.js"   # <- uncomment, use this
  umami_src: "https://cloud.umami.is/script.js"           # <- delete this line
```
Leave `umami_id` unchanged. Commit + push -> Pages redeploys. The tracker now
loads from `m.` and auto-posts events to `m./api/send` (Umami derives the collect
host from the script's own origin).

### 6. Confirm the fix
Load the site with uBlock Origin enabled. Before: no request to `cloud.umami.is`.
After: a request to `m.rosarioscalise.com/script.js` + `/api/send` that the
blocker leaves alone, and the visit shows in Umami.

## Rollback
Revert step 5 (point `umami_src` back at `cloud.umami.is/script.js`). Optionally
delete the Worker, custom domain, and the `m` NS record. The site itself is never
affected by any of this.

## Notes
- Free Worker tier: 100k requests/day. Each engaged visit is a handful of
  requests (script + a few events); comfortably within budget.
- Update the `analytics-umami` memory and the self-host handoff
  (`20260617_UMAMI_SELFHOST.md`) once this is live, since the blocklist gotcha is
  then resolved.
