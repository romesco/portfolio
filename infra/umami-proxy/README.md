# Umami first-party proxy

Reverse-proxies the Umami tracker + collect endpoint through a first-party
subdomain (`m.rosarioscalise.com`) so ad / tracker blockers that drop
`cloud.umami.is` by hostname don't lose those visitors. Cookieless; the site
just loads its tracker from the subdomain instead of `cloud.umami.is`.

## `vercel/` : the chosen path

Attached to the subdomain with a **single CNAME** in Google Cloud DNS, so your
apex, GitHub Pages, nameservers, and the cross-account custom-domain setup are
all untouched. A Vercel Edge Middleware forwards the real visitor IP so
geolocation stays correct. Setup steps:
**`../../handoffs/20260718_UMAMI_FIRST_PARTY_PROXY.md`**.

## `cloudflare/` : alternative (not default)

A Cloudflare Worker doing the same job. Not the default because the free
Cloudflare plan cannot host a subdomain-only zone (that is Enterprise), so it
requires moving the **whole** domain's nameservers to Cloudflare. Kept for
reference in case DNS ever moves there anyway (you'd also gain a CDN).
