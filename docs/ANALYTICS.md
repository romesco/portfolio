# Analytics: how to use it

Umami (cookieless) with a first-party proxy. This is the *usage* guide: how to
attribute traffic, stitch a person across devices, and keep your own visits out
of the numbers. Infra + account details live in the gitignored
`notes/analytics-proxy.md`.

## 1. Where traffic comes from: tag the links you share (UTM)

Umami automatically reads `utm_source` / `utm_medium` / `utm_campaign` /
`utm_term` / `utm_content` from the URL and breaks visits down by them (dashboard
> Referrers / UTM). Nothing to deploy: just add the params to links you post.

Convention: `utm_source` = where it's posted, `utm_medium` = the kind of place,
`utm_campaign` = the specific push (a talk, a paper, a thread).

    Twitter bio        https://rosarioscalise.com/?utm_source=twitter&utm_medium=bio
    Twitter post       https://rosarioscalise.com/?utm_source=twitter&utm_medium=post&utm_campaign=compression-essay
    Email signature    https://rosarioscalise.com/?utm_source=email&utm_medium=signature
    Talk slide / QR    https://rosarioscalise.com/?utm_source=talk&utm_medium=slides&utm_campaign=nvidia-srl-2026
    LinkedIn           https://rosarioscalise.com/?utm_source=linkedin&utm_medium=profile

Keep `utm_source`/`campaign` values lowercase-hyphenated and reuse them so they
group. Then you can answer "did the NVIDIA talk drive visits?" or "which tweet
converted?"

## 2. Follow one person across their devices (?v=)

For a link you send to a *specific* person, add `?v=<tag>`. Every visit that used
that link, on any device, is stamped with the same distinct id you can filter by
(the tag is remembered on each device). Anonymous visitors can't be merged
otherwise: there's no shared key.

    https://rosarioscalise.com/?v=acme-recruiter

Combine with UTM freely: `?utm_source=talk&utm_campaign=berkeley-2026&v=berkeley-host`.

## 3. Don't count yourself (?notme)

Visit **https://rosarioscalise.com/?notme** once on each of your own devices/
browsers. It sets `localStorage['umami.disabled']`, which Umami honors, so you
stop inflating your own stats from the next page load on. **/?trackme** undoes it.

## 4. What's tracked (event reference)

Pageviews are automatic. Custom events (Umami > Events):

| Event | Fires when | Key props |
|---|---|---|
| `contact-email` / `contact-scholar` / `contact-github` / `buymeacoffee` | contact row click | — |
| `paper-link` | a paper asset link click | `type` (arxiv/pdf/doi/…), `title` |
| `outbound` | any external link click | destination url |
| `work-expand` | a Selected-work is opened | `title` |
| `section-expand` | News / Mentoring "peek + fade" opened | — |
| `tree-explored` | first pan/zoom/drag on /tree | `via` |
| `engaged-time` | active-time milestone (15s/1m/3m/10m) | `reached`, `path` |
| `scroll-depth` | 50% / 100% of a page scrolled | `pct`, `path` |
| `page-dwell` | tab hidden/closed | `bucket`, `path` |
| `section-view` | a `[data-section]` region held in view ~1s | `name`, `path` |
| `not-found` | a 404 page is hit | `path` |
| `deploy` | CI publishes the site (server-side) | `sha`, `ref`, `trigger` |

`section-view` names: homepage `news` / `selected-works` / `mentoring` /
`elsewhere`; `/reading` `read:<group>`; `/publications` `pub:<group>`; garage
posts `garage-<slug>`.

Note: Umami's built-in "visit duration / bounce" counts pageviews only, so it
reads ~0s for single-page visits. Use `engaged-time` / `page-dwell` /
`scroll-depth` for real engagement instead.

## 5. Dashboard-only wins (no code)

You already emit the events; flip these on in Umami when you want them:
- **Goals** for `contact-*`, `buymeacoffee`, `paper-link`, `not-found`.
- **Funnel**: landed -> `scroll-depth` 50 -> `paper-link` -> `contact-*`.
- **Retention / Journey** for returning visitors.
