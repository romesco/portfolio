# Reposting guide (for future agents)

How to quickly add a repost to the hidden microblog at `/twitter` without
re-deriving the mechanics. When Rosario says *"repost this Instagram thing
&lt;url&gt;"* (or similar), this is the path.

## TL;DR recipe

```bash
# 1. Extract metadata and insert a repost block at the top of the feed:
python3 scripts/ig_repost.py "https://www.instagram.com/p/<code>/" --append \
    --comment "optional line in Rosario's voice"

# 2. If the photo isn't square, set the aspect (the one thing not auto-detected):
#    edit the new block in data/twitter.yaml -> aspect: 0.8 (portrait) / 1.91 (landscape)

# 3. Build, verify, commit, push (auto-deploys via GitHub Pages):
/workspace/.venv/bin/python website/build.py
git add data/twitter.yaml && git commit -m "Twitter: repost <handle>'s post" && git push
```

Then verify live (`curl -s https://rosarioscalise.com/twitter | grep ...`) the
way every other change in this repo is verified.

## The one non-obvious trick

Instagram shows a **JS login wall** to normal browsers and to `curl` with a
desktop UA: no OpenGraph, no post JSON, nothing extractable. But it **still
serves static OpenGraph / Twitter-card meta tags to link-preview crawlers**.
So `scripts/ig_repost.py` fetches with a `facebookexternalhit` User-Agent and
parses the tags. From them it recovers, reliably:

- **author / display name** : `twitter:title` = `Name (@handle) • Instagram photo`
- **@handle**               : the username in `og:url` path (`/<handle>/p/<code>/`)
- **caption**               : the quoted part of `og:title`
- **original date**         : `og:description` (`... on June 17, 2015: "..."`)

What it canNOT get: the **true aspect ratio**. `og:image` is a square-cropped
thumbnail, so its dimensions lie. `aspect` defaults to `1` (right for old square
posts); set it by eye for portrait/landscape. This is the only manual field.

oEmbed (token-gated), the `/embed/` endpoint (JS shell), `?__a=1` (auth-gated),
and the Wayback Machine were all checked and do not work from the container.
There is no headless browser here. The crawler-UA OG path is the working route.

## How the card renders

`data/twitter.yaml` posts can carry a `repost:` block. When `repost.url` is an
instagram.com link (or `source: instagram` is set), `website/build.py`
(`load_twitter`) marks it Instagram and computes `embed_src` = the post's
`/embed/` URL. `website/twitter.html.j2` then renders our own card chrome (IG
glyph, author, @handle, `instagram.com ↗` source link) wrapping a **cropped**
`/embed/` iframe: `.ig-embed-crop` (in `website/styles.css`) is an `overflow`
window that reveals only the photo, hiding Instagram's header/caption/footer.

Tuning knobs live on `.repost-instagram` in `styles.css` (inherited by the crop):

- `--ig-max-h` (default `300px`) : caps the photo height.
- `--ig-aspect` (set inline per post from `aspect:`) : photo width/height; the
  card width is `max-h * aspect + padding`, so the card hugs the photo.
- `--ig-header` (default `58px`) : how much of Instagram's title bar to crop.
  Bump it if Instagram restyles the embed and a header sliver peeks through.

The photo is a live cross-origin iframe, so it only renders in a browser, you
can't pixel-check the crop from the shell. Confirm the markup is deployed, then
ask Rosario to eyeball.

## Adding non-Instagram reposts

A plain `repost:` block (no instagram URL) renders the original avatar/initials
card. See the header comment in `data/twitter.yaml` for the field shape
(`author`, `handle`, `url`, `at`, `text`, optional `avatar`).

## Extending to other platforms

The same crawler-UA OG trick generalizes: most platforms serve OpenGraph to
`facebookexternalhit`. To add (say) a TikTok or Bluesky source, generalize
`fetch_meta`/`parse` in `scripts/ig_repost.py` and add a `source` branch in the
template with whatever crop/embed treatment fits. Keep the card on-brand rather
than dropping in a third-party widget (we tried Instagram's official widget and
rejected it: it forces a light-themed box that clashes with the site).
