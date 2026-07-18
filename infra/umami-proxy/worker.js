/**
 * First-party reverse proxy for Umami Cloud.
 *
 * Ad / tracker blockers (uBlock Origin + EasyPrivacy, etc.) drop requests to
 * `cloud.umami.is` by hostname, so those visitors are never counted. Serving the
 * tracker and its collect endpoint from a first-party subdomain you control
 * (e.g. https://m.rosarioscalise.com) evades that, since the subdomain is on no
 * blocklist. Deploy this on Cloudflare Workers and bind it to that subdomain.
 *
 * It forwards every request straight to Umami Cloud. The upstream host is
 * HARDCODED, so this is NOT an open proxy (it can only ever reach cloud.umami.is).
 * The real visitor IP is passed as X-Forwarded-For so Umami's geolocation and
 * session hashing stay correct instead of collapsing onto Cloudflare's edge IP.
 *
 * Paths the tracker uses (all handled by the catch-all below):
 *   GET  /script.js   the Umami tracker  (cached briefly at the edge)
 *   POST /api/send    one pageview / event / identify  (Content-Type: text/plain,
 *                     a CORS "simple request", so no preflight)
 *   POST /api/batch   batched events
 *
 * Cross-origin note: the page is on the apex (rosarioscalise.com) but posts to
 * this subdomain, so the browser does a CORS check. Umami Cloud already returns
 * a permissive `Access-Control-Allow-Origin` (that is how the default
 * script-on-your-domain setup works at all); we pass those headers straight
 * through, so it keeps working here.
 */
const UPSTREAM = 'https://cloud.umami.is';

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = UPSTREAM + url.pathname + url.search;

    const headers = new Headers(request.headers);
    // Preserve the visitor's IP so Umami sees them, not the Cloudflare edge.
    const ip = request.headers.get('CF-Connecting-IP');
    if (ip) {
      headers.set('X-Forwarded-For', ip);
      headers.set('X-Real-IP', ip);
    }

    const method = request.method;
    const hasBody = method !== 'GET' && method !== 'HEAD';
    const init = {
      method,
      headers,
      // Buffer the (tiny) body to sidestep streaming/duplex requirements.
      body: hasBody ? await request.arrayBuffer() : undefined,
      redirect: 'manual',
    };

    const resp = await fetch(target, init);

    const out = new Headers(resp.headers);
    if (url.pathname.endsWith('.js')) {
      // The tracker changes rarely; let the edge cache it a little.
      out.set('Cache-Control', 'public, max-age=3600');
    }
    return new Response(resp.body, { status: resp.status, headers: out });
  },
};
