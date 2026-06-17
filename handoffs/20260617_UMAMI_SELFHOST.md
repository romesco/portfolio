# Self-hosting Umami analytics for rosarioscalise.com

A runbook for standing up a cookieless, self-hosted [Umami](https://umami.is)
instance and connecting it to the portfolio site. The site-side wiring is
**already done and merged** (see "What's already in the repo" below); this doc
covers the part that runs on your own server, plus the one final step to flip
analytics on.

You run the server steps from a shell with SSH access to a VPS. The final
"flip it on" step (editing `site.yaml` + push) can be done from any session,
including a Claude container session.

---

## What you'll end up with

- A small VPS running Umami + Postgres + Caddy (auto-HTTPS) in Docker.
- Umami reachable at `https://analytics.rosarioscalise.com` (a subdomain you
  control: first-party, which also dodges most ad-blockers).
- The portfolio site reporting **pageviews + referrers (incoming)** and
  **outbound link clicks** (the outbound shim is already in the layout).
- Cookieless, no consent banner needed.

Total footprint is small: Umami app ~200MB RAM, with Postgres the whole stack
stays under ~500MB. A 1GB box is comfortable.

---

## What's already in the repo (no action needed)

These shipped with the commit that introduced this runbook:

- `website/site.yaml` has an `analytics:` block with `umami_src` and `umami_id`
  (both empty). The tracking snippet renders **only** when both are set, so the
  live site is untouched until you fill them in.
- `website/_layout.html.j2` injects, when configured:
  - the Umami tracker `<script defer src=... data-website-id=...>` in `<head>`,
  - a small JS shim before `</body>` that tags every external link with
    `data-umami-event="outbound"` so clicks fire an `outbound` event carrying
    the destination URL.
- `website/build.py` exposes `analytics` to every template via `env.globals`.

So once Umami is live, flipping analytics on is a two-field edit + push.

---

## Prerequisites

- A VPS. Anything with **1GB+ RAM** works (Hetzner CAX11 / CX22, DigitalOcean
  1GB, Fly.io, etc.). Ubuntu 22.04/24.04 assumed below.
- DNS control for `rosarioscalise.com`.
- A subdomain pointed at the VPS:
  - Create an **A record**: `analytics.rosarioscalise.com -> <VPS_IP>`.
  - Note: the apex `rosarioscalise.com` stays on GitHub Pages. This is a
    separate subdomain, so it does not touch the existing Pages setup.

---

## Step 1: Provision and harden the box

SSH in as root (or a sudo user), then:

```bash
# Basic updates + firewall
apt update && apt upgrade -y
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

## Step 2: Install Docker + Compose plugin

```bash
curl -fsSL https://get.docker.com | sh
docker compose version   # sanity check; should print v2.x
```

## Step 3: Lay down the stack

```bash
mkdir -p /opt/umami && cd /opt/umami
```

Create `/opt/umami/.env` with strong secrets (the commands below generate them):

```bash
cat > .env <<EOF
POSTGRES_PASSWORD=$(openssl rand -hex 24)
APP_SECRET=$(openssl rand -hex 32)
EOF
cat .env   # keep these safe; APP_SECRET rotating logs everyone out
```

Create `/opt/umami/docker-compose.yml`:

```yaml
services:
  umami:
    image: ghcr.io/umami-software/umami:postgresql-latest
    environment:
      DATABASE_URL: postgresql://umami:${POSTGRES_PASSWORD}@db:5432/umami
      DATABASE_TYPE: postgresql
      APP_SECRET: ${APP_SECRET}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: umami
      POSTGRES_USER: umami
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - umami-db:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U umami -d umami"]
      interval: 5s
      timeout: 5s
      retries: 10

  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    depends_on:
      - umami
    restart: unless-stopped

volumes:
  umami-db:
  caddy-data:
  caddy-config:
```

Create `/opt/umami/Caddyfile` (Caddy fetches a Let's Encrypt cert automatically):

```
analytics.rosarioscalise.com {
    reverse_proxy umami:3000
}
```

## Step 4: Bring it up

```bash
cd /opt/umami
docker compose up -d
docker compose logs -f umami   # wait for "Listening on ... 3000", Ctrl-C to exit
```

Give Caddy ~30s to obtain the TLS cert, then visit
`https://analytics.rosarioscalise.com`.

## Step 5: First-run setup in the Umami UI

1. Log in with the default credentials: **`admin` / `umami`**.
2. **Immediately** change the admin password (Settings -> Profile).
3. Settings -> Websites -> **Add website**:
   - Name: `rosarioscalise.com`
   - Domain: `rosarioscalise.com`
4. Open the new website -> **Edit** (or the code/`</>` icon). Copy:
   - the **Website ID** (a UUID),
   - the tracking script URL, which is `https://analytics.rosarioscalise.com/script.js`.

## Step 6: Flip analytics on in the site (can be done from a Claude session)

Edit `website/site.yaml`:

```yaml
analytics:
  umami_src: "https://analytics.rosarioscalise.com/script.js"
  umami_id: "<the-website-UUID-from-step-5>"
```

Then rebuild + push (auto-deploys via GitHub Pages):

```bash
.venv/bin/python website/build.py
git add -A && git commit -m "Analytics: enable self-hosted Umami" && git push origin main
```

## Step 7: Verify

- Load `https://rosarioscalise.com` in a normal (non-blocking) browser.
- In Umami, the Realtime view should show your visit within a few seconds.
- Click an external link (e.g. an arXiv/GitHub link). Under the website's
  **Events** tab you should see an `outbound` event; its `url` property holds
  the destination.
- View-source on the live page: you should see the `script.js` tag in `<head>`
  and the outbound shim before `</body>`. With analytics unset, neither
  appears.

---

## Ad-blocker note (optional hardening)

Hosting on your own subdomain (first-party) already avoids most blocking. If
you find some clients still block the default `/script.js` name or the
`/api/send` collection endpoint, Umami supports renaming the tracker script and
customizing the collect endpoint via environment variables. Check the current
[Umami environment-variables docs](https://umami.is/docs/environment-variables)
for the exact var names (they have shifted across versions), set them on the
`umami` service, and update `umami_src` in `site.yaml` to match the new script
path. Treat this as a later tweak, not required for launch.

## Do Not Track / privacy posture

Umami is cookieless and stores no personal data by default, so no consent
banner is required. If you want to honor browser Do-Not-Track, there's a global
toggle in the Umami settings. This pairs well with the site's existing
`noai`/privacy stance.

---

## Maintenance

- **Update Umami:** `cd /opt/umami && docker compose pull && docker compose up -d`
  (Postgres data persists in the `umami-db` volume).
- **Back up the data:**
  ```bash
  docker compose exec db pg_dump -U umami umami | gzip > umami-$(date +%F).sql.gz
  ```
  Copy the dump off-box (or just accept that analytics history is non-critical).
- **Logs:** `docker compose logs -f umami` / `... caddy`.
- **Disk:** Umami's data is tiny at portfolio traffic; you're unlikely to need
  retention pruning, but it's configurable in-app if it ever grows.

---

## If you ever want to undo it

Set both `analytics` fields back to `""` in `site.yaml`, rebuild, push: the
snippet stops rendering immediately. Then `docker compose down` on the VPS
(add `-v` to also delete the database volume).
