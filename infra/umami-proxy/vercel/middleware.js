/**
 * First-party reverse proxy for Umami Cloud, on Vercel.
 *
 * Ad / tracker blockers (uBlock Origin + EasyPrivacy, etc.) drop requests to
 * `cloud.umami.is` by hostname, so those visitors are never counted. Serving the
 * tracker and its collect endpoint from a first-party subdomain you control
 * (e.g. https://m.rosarioscalise.com) evades that, since the subdomain is on no
 * blocklist. Attach that subdomain to this Vercel project with a single CNAME,
 * so nothing about your apex / GitHub Pages / nameservers changes.
 *
 * This runs as Vercel Edge Middleware (not a rewrite) for two reasons:
 *   - it sees the ORIGINAL request path, so /script.js and /api/send are routed
 *     correctly;
 *   - it can forward the real visitor IP. Vercel puts the client IP in
 *     x-real-ip / x-forwarded-for; we pass it to Umami as X-Forwarded-For so geo
 *     and session hashing stay correct instead of collapsing onto the edge IP.
 *
 * The upstream host is HARDCODED, so this is NOT an open proxy.
 *
 *   GET  /script.js   the Umami tracker (cached briefly at the edge)
 *   POST /api/send     one pageview / event / identify
 *   POST /api/batch    batched events
 *
 * Cross-origin note: the page is on the apex but posts to this subdomain, a
 * cross-origin request. Umami Cloud already returns a permissive
 * Access-Control-Allow-Origin (that is how the default script-on-your-domain
 * setup works at all); we pass those headers straight through.
 */
const UPSTREAM = 'https://cloud.umami.is';

export const config = { matcher: '/:path*' };

export default async function middleware(request) {
  const url = new URL(request.url);
  const target = UPSTREAM + url.pathname + url.search;

  const headers = new Headers(request.headers);
  headers.delete('host');
  // Preserve the visitor's IP so Umami sees them, not the Vercel edge.
  const ip =
    request.headers.get('x-real-ip') ||
    (request.headers.get('x-forwarded-for') || '').split(',')[0].trim();
  if (ip) {
    headers.set('x-forwarded-for', ip);
    headers.set('x-real-ip', ip);
  }

  const hasBody = request.method !== 'GET' && request.method !== 'HEAD';
  const resp = await fetch(target, {
    method: request.method,
    headers,
    // Buffer the (tiny) body to sidestep streaming/duplex requirements.
    body: hasBody ? await request.arrayBuffer() : undefined,
    redirect: 'manual',
  });

  const out = new Headers(resp.headers);
  if (url.pathname.endsWith('.js')) {
    // The tracker changes rarely; let the edge cache it a little.
    out.set('cache-control', 'public, max-age=3600');
  }
  return new Response(resp.body, { status: resp.status, headers: out });
}
