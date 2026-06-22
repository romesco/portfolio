"""Generate index.html from index.html.j2 + shared portfolio YAML, plus any
standalone "hidden" pages from Markdown in website/pages/.

Identity lives in data/identity.yaml, news in data/news.yaml, and entries in
data/publications.yaml with `featured: true` are rendered, sorted year-desc.

Run: `make site` or `uv run python website/build.py`.

Website-specific extensions to a publication entry (ignored by the CV
build):

  featured: true
  media: ./media/foo.mp4           # bare string, type auto-detected
  # OR
  media:
    src: ./media/foo.mp4           # required
    type: video                    # optional (video | image | youtube)
    poster: ./media/foo-poster.jpg # optional (video only)
    autoplay: true                 # optional (video): implies muted/loop
    alt: "Caption text"            # optional (image)

Standalone pages: drop `website/pages/<slug>.md` (optional YAML front-matter
with `title:`/`description:`). It renders to `website/<slug>.html`, served at
`/<slug>`, styled like the homepage, not linked from it, and marked noindex.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import mistune
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup, escape

ROOT = Path(__file__).parent
DATA_DIR = ROOT.parent / "data"
SITE_YAML = ROOT / "site.yaml"
IDENTITY_YAML = DATA_DIR / "identity.yaml"
PUBS_YAML = DATA_DIR / "publications.yaml"
HONORS_YAML = DATA_DIR / "honors.yaml"
GRANTS_YAML = DATA_DIR / "grants.yaml"
TEACHING_YAML = DATA_DIR / "teaching.yaml"
NEWS_YAML = DATA_DIR / "news.yaml"
MENTORING_YAML = DATA_DIR / "mentoring.yaml"
BUCKETLIST_YAML = DATA_DIR / "bucketlist.yaml"
TWITTER_YAML = DATA_DIR / "twitter.yaml"
READING_YAML = DATA_DIR / "reading.yaml"
# Last-known-good river entries, keyed by blog URL. Tracked in git so a deploy
# whose live fetch misses a feed falls back to this instead of dropping the
# line. Refreshed by any fetch-enabled build (CI or FETCH_FEEDS) that is then
# committed; the deploy runner can't write it back (Pages token is read-only).
READING_CACHE = DATA_DIR / "reading-cache.json"
PAGES_DIR = ROOT / "pages"
HEADSHOT_SRC = ROOT.parent / "assets" / "headshot.jpg"
HEADSHOT_DEST = ROOT / "headshot.jpg"

ELLIPSIS_OUT = "…"

VIDEO_EXTS = {".mp4", ".webm", ".mov", ".m4v"}
IMAGE_EXTS = {".gif", ".jpg", ".jpeg", ".png", ".webp", ".avif", ".svg"}

# Fallback favicon pool if site.yaml doesn't define `favicons`. A random one
# is rendered as an inline SVG emoji on each page load.
DEFAULT_FAVICONS = ["🤖", "🦾", "🧪", "🧬", "⚙️", "🛰️", "🔬", "🔭", "⚛️", "✨"]

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _detect_media_type(src: str) -> str:
    if not src:
        return "unknown"
    if "youtube.com" in src or "youtu.be" in src:
        return "youtube"
    ext = Path(urlparse(src).path).suffix.lower()
    if ext in VIDEO_EXTS:
        return "video"
    if ext in IMAGE_EXTS:
        return "image"
    return "unknown"


def _extract_youtube_id(url: str) -> str | None:
    p = urlparse(url)
    if p.netloc.endswith("youtu.be"):
        return p.path.lstrip("/").split("/")[0] or None
    if "youtube.com" in p.netloc:
        if p.path == "/watch":
            return (parse_qs(p.query).get("v") or [None])[0]
        if p.path.startswith("/embed/"):
            parts = p.path.split("/")
            return parts[2] if len(parts) >= 3 else None
    return None


def normalize_media(m) -> dict | None:
    """Coerce the optional `media:` YAML value into {type, src, ...} or None.
    Bare strings get wrapped; type is auto-detected from extension/host."""
    if m is None:
        return None
    if isinstance(m, str):
        m = {"src": m}
    if not isinstance(m, dict) or not m.get("src"):
        return None
    m.setdefault("type", _detect_media_type(m["src"]))
    # Pre-fill optional fields so the template can reference them
    # without StrictUndefined errors.
    m.setdefault("poster", None)
    m.setdefault("autoplay", False)
    m.setdefault("alt", None)
    m.setdefault("label", None)  # caption shown in a multi-item carousel
    if m["type"] == "youtube" and not m.get("id"):
        m["id"] = _extract_youtube_id(m["src"])
    return m


def normalize_media_list(m) -> list[dict]:
    """Coerce the optional `media:` value into a list of media dicts (0, 1, or
    many). A single string/dict becomes a one-item list; a YAML list of items
    becomes many: the template renders >1 as a carousel."""
    if m is None:
        return []
    items = m if isinstance(m, list) else [m]
    return [nm for nm in (normalize_media(it) for it in items) if nm]


def normalize_coverage(items) -> list[dict]:
    """Coerce the optional `coverage:` value into a list of {outlet, url} dicts.
    A bare string becomes {outlet: <string>}; entries without an outlet drop. An
    optional `date` (date or string) becomes `date_display` for the archive."""
    out: list[dict] = []
    for it in items or []:
        if isinstance(it, str):
            it = {"outlet": it}
        if not isinstance(it, dict) or not it.get("outlet"):
            continue
        d = it.get("date")
        if isinstance(d, (datetime.date, datetime.datetime)):
            iso, disp = d.isoformat(), d.strftime("%b %Y")
        else:
            iso = disp = str(d) if d else ""
        # The outlet's own favicon (its brand glyph) by domain: same service
        # the /reading page uses. No images to host; graceful if it 404s.
        host = urlparse(str(it.get("url") or "")).netloc
        if host.startswith("www."):
            host = host[4:]
        auto = f"https://www.google.com/s2/favicons?domain={host}&sz=64" if host else None
        out.append({
            "outlet": str(it["outlet"]),
            "url": it.get("url"),
            "domain": host,
            # Explicit `favicon:` wins (some sites have no good auto-favicon,
            # e.g. a subdomain that only resolves to a generic globe).
            "favicon": it.get("favicon") or auto,
            "iso": iso,
            "date_display": disp,
        })
    return out


def normalize_collaborators(items) -> list[dict]:
    """Coerce the optional `collaborators:` value into {name, url, favicon} dicts
    for the "w/ [glyph] Institution" tag on a selected work. The glyph is the
    institution's brand favicon: from an explicit `favicon:`, else a `domain:`,
    else the link's host. `url` is the click target (the institution's coverage
    of the work if any, otherwise its most senior co-author's page)."""
    out: list[dict] = []
    for it in items or []:
        if not isinstance(it, dict) or not it.get("name"):
            continue
        url = it.get("url")
        dom = it.get("domain")
        if not dom and url:
            dom = urlparse(str(url)).netloc
        if dom and dom.startswith("www."):
            dom = dom[4:]
        favicon = it.get("favicon") or (
            f"https://www.google.com/s2/favicons?domain={dom}&sz=64" if dom else None)
        out.append({"name": str(it["name"]), "url": url, "favicon": favicon})
    return out


def _affil_chip(affil: dict) -> str:
    """Inline institution chip appended after an author's name: the institution's
    brand glyph ONLY (no visible label; its name lives in the title/alt tooltip),
    linking to its coverage of the work or that author's page. Deduped by caller."""
    name = str(escape(affil["name"]))
    url = affil.get("url")
    dom = affil.get("domain")
    if not dom and url:
        dom = urlparse(str(url)).netloc
    if dom and dom.startswith("www."):
        dom = dom[4:]
    fav = affil.get("favicon") or (
        f"https://www.google.com/s2/favicons?domain={dom}&sz=64" if dom else None)
    glyph = (f'<img class="collab-favicon" src="{escape(fav)}" alt="{name}" '
             'width="16" height="16" loading="lazy" onerror="this.remove()">'
             ) if fav else f'<span class="collab-name">{name}</span>'
    if url:
        return f'<a class="collab-chip" href="{escape(url)}" title="{name}">{glyph}</a>'
    return f'<span class="collab-chip" title="{name}">{glyph}</span>'


def render_authors(authors) -> Markup:
    """HTML port of the CV's format_authors. `me: true` wraps in <strong>;
    `equal: true` appends `*`; bare `"..."` becomes a literal ellipsis.
    Oxford comma + ampersand as last separator, except when the list contains
    an ellipsis (commas only: "..., & ..." reads as ungrammatical)."""
    pieces: list[str] = []
    has_ellipsis = False
    seen_affils: set[str] = set()
    breaks: set[int] = set()              # force a line break AFTER this piece index
    for a in authors:
        if isinstance(a, str):
            if a.strip() in ("//", "\\", "\\\\"):   # LaTeX-style forced line break
                if pieces:
                    breaks.add(len(pieces) - 1)
                continue
            if a == "...":
                pieces.append(ELLIPSIS_OUT)
                has_ellipsis = True
            else:
                pieces.append(str(escape(a)))
            continue
        # A name-less {affil: ...} entry is a standalone glyph (for an abbreviated
        # author list): hug it onto the previous author instead of listing it.
        if not a.get("name") and isinstance(a.get("affil"), dict):
            af = a["affil"]
            if af.get("name") and af["name"] not in seen_affils:
                seen_affils.add(str(af["name"]))
                chip = _affil_chip(af)
                if pieces:
                    pieces[-1] += chip
                else:
                    pieces.append(chip)
            continue
        name = str(escape(a["name"]))
        if a.get("me"):
            name = f"<strong>{name}</strong>"
        # Contribution markers (* equal, † e.g. co-advisor) as a single
        # superscript, kept outside any <strong> so they aren't bolded.
        marks = ("*" if a.get("equal") else "") + ("†" if a.get("dagger") else "")
        if marks:
            name = f"{name}<sup>{marks}</sup>"
        # An author's institution chip, shown once per institution across the
        # list (a second author from the same place doesn't repeat the chip).
        affil = a.get("affil")
        if isinstance(affil, dict) and affil.get("name") and affil["name"] not in seen_affils:
            seen_affils.add(str(affil["name"]))
            name += _affil_chip(affil)
        pieces.append(name)

    if not pieces:
        return Markup("")
    # Assemble with comma / Oxford-ampersand separators, swapping in a <br>
    # wherever a manual break was requested (the comma stays; only the trailing
    # space becomes a line break).
    n = len(pieces)
    use_amp = (not has_ellipsis) and n >= 2
    chunks: list[str] = []
    for i, p in enumerate(pieces):
        chunks.append(p)
        if i == n - 1:
            break
        amp = use_amp and i == n - 2
        if i in breaks:
            chunks.append(",<br>&amp; " if amp else ",<br>")
        else:
            chunks.append(", &amp; " if amp else ", ")
    out = "".join(chunks)

    # Terminate with a period unless already ending in one (e.g. the
    # literal ellipsis already trails punctuation).
    if not (out.endswith(".") or out.endswith(ELLIPSIS_OUT)):
        out += "."
    return Markup(out)


def render_links(links) -> Markup:
    """Render available links in fixed order: arxiv, pdf, doi, ieee, github,
    project. Joined by middots. Matches the CV's format_links ordering."""
    if not links:
        return Markup("")
    parts: list[str] = []
    if v := links.get("arxiv"):
        url = v if str(v).startswith("http") else f"https://arxiv.org/abs/{v}"
        parts.append(f'<a href="{escape(url)}">arxiv</a>')
    if v := links.get("pdf"):
        parts.append(f'<a href="{escape(v)}">pdf</a>')
    if v := links.get("doi"):
        url = v if str(v).startswith("http") else f"https://doi.org/{v}"
        parts.append(f'<a href="{escape(url)}">doi</a>')
    if v := links.get("ieee"):
        parts.append(f'<a href="{escape(v)}">ieee</a>')
    if v := links.get("github"):
        url = v if str(v).startswith("http") else f"https://github.com/{v}"
        parts.append(f'<a href="{escape(url)}">github</a>')
    if v := links.get("project"):
        parts.append(f'<a href="{escape(v)}">project</a>')
    if v := links.get("followup"):
        parts.append(f'<a href="{escape(v)}" title="Follow-up work">follow-up</a>')
    return Markup(" · ".join(parts))


# The hidden archive page that lists every press hit; the inline "press" line
# on featured works links here.
PRESS_PAGE_URL = "/inthepress"


# How many trailing outlets to show as brand glyphs before collapsing to "+N".
PRESS_GLYPH_CAP = 3


def render_coverage_inline(coverage) -> Markup:
    """A compact 'press' tag on a featured work's meta line: the lead outlet named
    (with its own brand glyph), then the remaining outlets as small brand glyphs,
    collapsing to a '+N' link to
    the /inthepress archive once the list runs long. The lead and each glyph link
    to their article; the outlet name is the glyph's hover tooltip. The lead is the
    first `coverage:` entry, so order the strongest outlet first. Empty when there's
    no coverage."""
    if not coverage:
        return Markup("")
    lead, rest = coverage[0], coverage[1:]
    lead_url = escape(lead.get("url") or PRESS_PAGE_URL)
    lead_name = escape(lead["outlet"])
    # Lead outlet: its name in text, immediately followed by its OWN brand glyph
    # (the remaining outlets show as glyphs only). No space between the two
    # anchors, so the name and its chip never wrap apart. alt="" since the name
    # is already announced by the adjacent text link.
    parts = [f'<a class="work-press-lead" href="{lead_url}">{lead_name}</a>']
    if lead.get("favicon"):
        parts[0] += (f'<a class="work-press-glyph" href="{lead_url}" title="{lead_name}">'
                     f'<img src="{escape(lead["favicon"])}" alt="" width="16" height="16" '
                     'loading="lazy" onerror="this.remove()"></a>')
    # Only collapse to "+N" when it actually hides 2+ outlets; a lone hidden
    # outlet saves no space, so just show it.
    if len(rest) - PRESS_GLYPH_CAP >= 2:
        shown, overflow = rest[:PRESS_GLYPH_CAP], len(rest) - PRESS_GLYPH_CAP
    else:
        shown, overflow = rest, 0
    for c in shown:
        url, name = escape(c.get("url") or PRESS_PAGE_URL), escape(c["outlet"])
        if c.get("favicon"):
            parts.append(
                f'<a class="work-press-glyph" href="{url}" title="{name}">'
                f'<img src="{escape(c["favicon"])}" alt="{name}" width="16" height="16" '
                'loading="lazy" onerror="this.remove()"></a>')
        else:
            parts.append(f'<a class="work-press-glyph work-press-text" href="{url}">{name}</a>')
    if overflow:
        parts.append(
            f'<a class="work-press-more" href="{PRESS_PAGE_URL}" '
            f'title="{overflow} more press {"mentions" if overflow != 1 else "mention"}">+{overflow}</a>')
    return Markup('<span class="work-press">' + " ".join(parts) + "</span>")


def render_collaborators(collabs) -> Markup:
    """Quiet "w/ [glyph] Institution" tag on a selected work: favicon + name
    chips, each linking to that institution's coverage or its senior co-author."""
    if not collabs:
        return Markup("")
    chips: list[str] = []
    for c in collabs:
        inner = ""
        if c.get("favicon"):
            inner += (f'<img class="collab-favicon" src="{escape(c["favicon"])}" '
                      'alt="" width="16" height="16" loading="lazy" onerror="this.remove()">')
        inner += f'<span class="collab-name">{escape(c["name"])}</span>'
        if c.get("url"):
            chips.append(f'<a class="collab-chip" href="{escape(c["url"])}">{inner}</a>')
        else:
            chips.append(f'<span class="collab-chip">{inner}</span>')
    return Markup('<span class="work-collab">'
                  '<span class="work-collab-label">w/</span> '
                  + " ".join(chips) + "</span>")


def cname_from_website(url: str | None) -> str | None:
    """Derive the bare host for a GitHub Pages CNAME file from the identity
    `website` URL. `https://rosarioscalise.com/` -> `rosarioscalise.com`.
    Returns None when no website is set (so the default *.github.io URL is
    used)."""
    if not url:
        return None
    # Fall back to a scheme-less parse so a bare host (no `https://`) works.
    host = urlparse(url).netloc or urlparse(f"//{url}").netloc
    return host or None


# One-liners (news updates, bucket-list items) are rendered as inline Markdown
# so they can carry a link or emphasis. Raw HTML is escaped; only Markdown
# syntax is honored.
_INLINE_MD = mistune.create_markdown(escape=True)


def _render_inline_md(text: str) -> Markup:
    """Render a single line as inline HTML, stripping the enclosing <p> that
    mistune adds so it sits inline."""
    html = _INLINE_MD(text or "").strip()
    if html.startswith("<p>") and html.endswith("</p>"):
        html = html[3:-4]
    return Markup(html)


def load_news() -> list[dict]:
    """Load data/news.yaml into render-ready dicts, newest first. Each source
    item is `{date: YYYY-MM-DD, text: ..., link?: ...}`. We add `iso` (for the
    <time datetime>) and `date_display` ("Jun 2026")."""
    if not NEWS_YAML.exists():
        return []
    raw = yaml.safe_load(NEWS_YAML.read_text()) or []
    items: list[dict] = []
    for n in raw:
        d = n.get("date")
        if isinstance(d, datetime.date):
            iso = d.isoformat()
            display = d.strftime("%b %Y")
        else:
            iso = str(d or "")
            display = str(d or "")
        items.append({
            "text": n.get("text", ""),
            "html": _render_inline_md(n.get("text", "")),
            "link": n.get("link"),
            "iso": iso,
            "date_display": display,
        })
    items.sort(key=lambda x: x["iso"], reverse=True)
    return items


def load_bucketlist() -> list[dict]:
    """Load data/bucketlist.yaml in file order. Each item is a line of text, or
    `{text: ..., done: true}` to check it off. Returns `{html, done}` dicts."""
    if not BUCKETLIST_YAML.exists():
        return []
    raw = yaml.safe_load(BUCKETLIST_YAML.read_text()) or []
    items: list[dict] = []
    for it in raw:
        if isinstance(it, dict):
            text, done = str(it.get("text") or ""), bool(it.get("done"))
        else:
            text, done = str(it), False
        if not text.strip():
            continue
        items.append({"html": _render_inline_md(text), "done": done})
    return items


def _post_time(at) -> tuple[str, str, str]:
    """(iso, short display, full title) for a date/datetime/other `at`."""
    if isinstance(at, datetime.datetime):
        return (at.isoformat(), at.strftime("%b %-d"),
                at.strftime("%b %-d, %Y · %-I:%M %p"))
    if isinstance(at, datetime.date):
        return at.isoformat(), at.strftime("%b %-d"), at.strftime("%b %-d, %Y")
    s = str(at or "")
    return s, s, s


def _yt_id(url: str) -> str | None:
    """YouTube video id from a watch / youtu.be / embed / shorts URL."""
    for pat in (r"[?&]v=([A-Za-z0-9_-]{6,})", r"youtu\.be/([A-Za-z0-9_-]{6,})",
                r"/embed/([A-Za-z0-9_-]{6,})", r"/shorts/([A-Za-z0-9_-]{6,})"):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _initials(name: str) -> str:
    """Up to two initials for an avatar fallback (e.g. 'Octi Zhang' -> 'OZ')."""
    parts = [w for w in str(name).split() if w]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def load_twitter() -> tuple[str, list[dict]]:
    """Load data/twitter.yaml (`{handle, posts: [{at, text?, repost?}]}`) into
    a feed, newest first. A `repost` block carries another person's post
    `{author, handle, url, at, text, avatar?}`; an own `text` alongside it is a
    quote-style comment. We emit `iso`/`display`/`full` times for the post and
    any repost. Returns (handle, posts)."""
    if not TWITTER_YAML.exists():
        return "", []
    data = yaml.safe_load(TWITTER_YAML.read_text()) or {}
    handle = str(data.get("handle") or "").lstrip("@")
    posts: list[dict] = []
    for p in data.get("posts") or []:
        iso, display, full = _post_time(p.get("at"))
        rp = p.get("repost")
        repost = None
        if isinstance(rp, dict):
            r_iso, r_display, r_full = _post_time(rp.get("at"))
            r_url = str(rp.get("url") or "")
            # Source-specific media reposts (see docs/REPOSTING.md):
            #  - instagram: crop the post's own /embed/ iframe (.ig-embed-crop) to
            #    show just the photo in our card chrome (server-side extraction is
            #    blocked). `aspect` is the crop ratio (W/H, default square).
            #  - youtube: thumbnail in our card that plays inline on hover, from
            #    `start` seconds; `url` links back to the channel, `video` is the
            #    watch URL. Always 16:9.
            # Marked with `source:` or inferred from the URL.
            video = str(rp.get("video") or "")
            source = str(rp.get("source") or "").lower()
            if not source and "instagram.com" in r_url:
                source = "instagram"
            if not source and ("youtu" in r_url or "youtu" in video):
                source = "youtube"
            embed_src = thumb = video_url = ""
            aspect = str(rp.get("aspect") or "1")
            if source == "instagram" and r_url:
                embed_src = r_url.split("?", 1)[0].rstrip("/") + "/embed/"
            elif source == "youtube":
                vid = _yt_id(video or r_url) or ""
                start = int(rp.get("start") or 0)
                aspect = str(rp.get("aspect") or "1.7778")
                if vid:
                    embed_src = (f"https://www.youtube.com/embed/{vid}"
                                 f"?start={start}&autoplay=1&mute=1&rel=0&playsinline=1")
                    thumb = f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"
                    video_url = f"https://www.youtube.com/watch?v={vid}&t={start}s"
            repost = {
                "author": str(rp.get("author") or ""),
                "handle": str(rp.get("handle") or "").lstrip("@"),
                "avatar": rp.get("avatar"),
                "url": r_url,
                "source": source,
                "embed_src": embed_src,
                "thumb": thumb,
                "video_url": video_url,
                "aspect": aspect,
                "initials": _initials(rp.get("author") or ""),
                "html": _render_inline_md(rp.get("text", "")),
                "iso": r_iso, "display": r_display, "full": r_full,
            }
        comment = str(p.get("text") or "").strip()
        posts.append({
            "html": _render_inline_md(comment),
            "has_comment": bool(comment),
            "repost": repost,
            # Optional little inline logo/badge after the text (e.g. a team logo).
            "chip": p.get("chip"),
            "chip_alt": str(p.get("chip_alt") or ""),
            "iso": iso, "display": display, "full": full,
        })
    posts.sort(key=lambda x: x["iso"], reverse=True)
    return handle, posts


def _fetch(url: str, timeout: int = 6) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "portfolio-build/1.0 (+feed reader)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _discover_feed(page_url: str, html: bytes) -> str | None:
    """Find a site's feed via its <link rel="alternate" type="...rss|atom...">."""
    text = html.decode("utf-8", "replace")
    for m in re.finditer(r"<link\b[^>]*>", text, re.I):
        tag = m.group(0)
        if (re.search(r'rel\s*=\s*["\']?[^"\'>]*alternate', tag, re.I)
                and re.search(r'type\s*=\s*["\']application/(?:rss|atom)\+xml', tag, re.I)):
            href = re.search(r'href\s*=\s*["\']([^"\']+)["\']', tag, re.I)
            if href:
                return urljoin(page_url, href.group(1))
    return None


def _site_latest(page_url: str, feed_url: str | None = None,
                 timeout: int = 6) -> dict | None:
    """Best-effort newest post `{title, url, at}` for a blog, or None. Uses an
    explicit feed_url if given, else auto-discovers from the page. Every failure
    (network, parse, missing dep) is swallowed: the river is optional."""
    try:
        import feedparser
    except Exception:
        return None
    try:
        if not feed_url:
            feed_url = _discover_feed(page_url, _fetch(page_url, timeout))
        if not feed_url:
            return None
        parsed = feedparser.parse(_fetch(feed_url, timeout))
        if not parsed.entries:
            return None

        def when(e):
            return e.get("published_parsed") or e.get("updated_parsed") or time.gmtime(0)

        e = max(parsed.entries, key=when)
        title = (e.get("title") or "").strip()
        if not title:
            return None
        w = e.get("published_parsed") or e.get("updated_parsed")
        return {
            "title": title,
            "url": e.get("link") or page_url,
            "at": datetime.datetime(*w[:6]) if w else None,
        }
    except Exception:
        return None


def _site_latest_by_crawl(page_url: str, crawl, timeout: int = 6) -> dict | None:
    """Best-effort newest post by scraping a blog's index page, for sites whose
    RSS feed is missing or unrepresentative of what they actually publish.

    `crawl` names the CSS class of the element wrapping each post-title link
    (a dict `{title_class: ...}` or a bare string); the newest post is assumed
    to be the first such link on the page. A date is recovered from the post
    URL when it embeds one (`/YYYY/MM/DD/`), else omitted. Every failure is
    swallowed: the river is optional, so a redesigned page just drops the line."""
    cls = crawl.get("title_class") if isinstance(crawl, dict) else (
        crawl if isinstance(crawl, str) else None)
    if not cls:
        return None
    try:
        html = _fetch(page_url, timeout).decode("utf-8", "replace")
    except Exception:
        return None
    # First `<a href>` directly inside the first element carrying `cls`.
    m = re.search(
        r'class="[^"]*\b' + re.escape(cls) + r'\b[^"]*">\s*<a\s+href="([^"]+)"[^>]*>(.*?)</a>',
        html, re.S | re.I)
    if not m:
        return None
    href, title = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
    if not title:
        return None
    url = urljoin(page_url, href)
    at = None
    d = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    if d:
        try:
            at = datetime.datetime(int(d.group(1)), int(d.group(2)), int(d.group(3)))
        except ValueError:
            at = None
    return {"title": title, "url": url, "at": at}


def _load_river_cache() -> dict:
    """Last-known-good `latest` dicts keyed by blog URL, or {} if absent/unreadable."""
    try:
        return json.loads(READING_CACHE.read_text())
    except Exception:
        return {}


def _save_river_cache(cache: dict) -> None:
    """Write the river cache deterministically (sorted keys) so it only diffs
    when a blog's latest actually changes, keeping git churn minimal."""
    try:
        READING_CACHE.write_text(
            json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    except Exception:
        pass


def load_reading() -> list[dict]:
    """Load data/reading.yaml (`{groups: [{name, links: [{name, url, note}]}]}`)
    into a curated, grouped blogroll. Derives a bare display domain from each
    URL; renders notes as inline Markdown. Preserves file order."""
    if not READING_YAML.exists():
        return []
    data = yaml.safe_load(READING_YAML.read_text()) or {}
    # Fetch each blog's latest post only in CI (deploy) or when explicitly asked,
    # so local `make site` stays fast and offline-friendly.
    fetch = bool(os.environ.get("CI") or os.environ.get("FETCH_FEEDS"))
    # Last-known-good fallback so a deploy that misses a live fetch keeps the line.
    cache = _load_river_cache() if fetch else {}
    seen: set[str] = set()
    groups: list[dict] = []
    for g in data.get("groups") or []:
        links: list[dict] = []
        for ln in g.get("links") or []:
            url = str(ln.get("url") or "")
            host = urlparse(url).netloc or urlparse(f"//{url}").netloc
            if host.startswith("www."):
                host = host[4:]
            note = ln.get("note")
            # Optional secondary links shown after the domain (e.g. a homepage
            # alongside a book page): a list of {label, url}.
            also = [
                {"label": str(a.get("label") or a.get("url")), "url": str(a["url"])}
                for a in (ln.get("also") or []) if isinstance(a, dict) and a.get("url")]
            feed = ln.get("feed")
            crawl = ln.get("crawl")
            pinned = ln.get("latest")
            latest = None
            # River source, in order of preference:
            #   `latest: {title,url,date}` -> a hand-pinned highlight (feed-less sites)
            #   `feed: false`  -> opt out entirely (no latest line)
            #   `crawl: {...}` -> scrape the index page (for stale/unrepresentative feeds)
            #   `feed: <url>`  -> explicit feed URL
            #   (none)         -> auto-discover an RSS/Atom feed from the page
            if isinstance(pinned, dict):
                d = pinned.get("date")
                if isinstance(d, datetime.datetime):
                    d = d.date()
                if isinstance(d, datetime.date):
                    iso_, disp_, full_ = (d.isoformat(), d.strftime("%b %Y"),
                                          d.strftime("%b %-d, %Y"))
                else:
                    iso_ = disp_ = full_ = str(d or "")
                latest = {
                    "title": str(pinned.get("title") or ""),
                    "url": str(pinned.get("url") or url),
                    "iso": iso_, "display": disp_, "full": full_,
                }
            elif fetch and url and feed is not False:
                seen.add(url)
                if crawl:
                    info = _site_latest_by_crawl(url, crawl)
                else:
                    info = _site_latest(url, feed if isinstance(feed, str) else None)
                if info:
                    at = info["at"]
                    latest = {
                        "title": info["title"],
                        "url": info["url"],
                        "iso": at.isoformat() if at else "",
                        "display": at.strftime("%b %Y") if at else "",
                        "full": at.strftime("%b %-d, %Y") if at else "",
                    }
                    cache[url] = latest          # refresh the last-known-good
                else:
                    latest = cache.get(url)      # live fetch missed: reuse the cache
            links.append({
                "name": str(ln.get("name") or host or url),
                "url": url,
                "domain": host,
                # Favicon by domain (no images to host). Swap the service freely.
                "favicon": f"https://www.google.com/s2/favicons?domain={host}&sz=64" if host else None,
                "note": _render_inline_md(note) if note else None,
                "also": also,
                "latest": latest,
            })
        if links:
            groups.append({"name": str(g.get("name") or ""), "links": links})
    if fetch:
        # Persist, dropping any blogs no longer in the list.
        _save_river_cache({k: v for k, v in cache.items() if k in seen})
    return groups


# The shared data/ YAML is authored for the LaTeX CV, so a few values carry
# LaTeX escapes. Undo the common ones for HTML (Jinja then re-escapes safely).
_LATEX_UNESCAPE = {r"\&": "&", r"\%": "%", r"\#": "#", r"\_": "_", r"\$": "$"}


def load_press() -> list[dict]:
    """Collect every publication carrying a `coverage:` list into render-ready
    works for the /inthepress archive, newest first. Coverage lives on the
    publication entries (single source of truth): this is just a view over it."""
    raw = yaml.safe_load(PUBS_YAML.read_text()) or []
    works: list[dict] = []
    for p in raw:
        cov = normalize_coverage(p.get("coverage"))
        if not cov:
            continue
        works.append({
            "title": _delatex(str(p.get("title") or "")),
            "venue": _delatex(str(p.get("venue") or "")),
            "year": p.get("year"),
            "coverage": cov,
        })
    works.sort(key=lambda w: -(w["year"] or 0))
    return works


def load_honors() -> list[dict]:
    """Load data/honors.yaml (the same awards/fellowships list the CV uses) into
    render-ready dicts for the /awards page. Preserves file order (newest-first).
    The `year` is carried through but the page deliberately omits it for now;
    names are de-LaTeXed (e.g. `\\&` -> `&`) for the web."""
    if not HONORS_YAML.exists():
        return []
    raw = yaml.safe_load(HONORS_YAML.read_text()) or []
    honors: list[dict] = []
    for h in raw:
        name = _delatex(str(h.get("name") or "")).strip()
        if not name:
            continue
        honors.append({"name": name, "year": str(h.get("year") or "").strip()})
    return honors


def load_grants() -> list[dict]:
    """Load data/grants.yaml into render-ready dicts for the /awards "Grants
    Awarded" section. Preserves file order. `title`, `agency`, and `amount` are
    shown; `amount` is the monetary total as a display string. `year`/`role` are
    carried through but not displayed yet. Names are de-LaTeXed for the web."""
    if not GRANTS_YAML.exists():
        return []
    raw = yaml.safe_load(GRANTS_YAML.read_text()) or []
    grants: list[dict] = []
    for g in raw:
        title = _delatex(str(g.get("title") or "")).strip()
        if not title:
            continue
        grants.append({
            "title": title,
            "agency": _delatex(str(g.get("agency") or "")).strip(),
            "amount": _delatex(str(g.get("amount") or "")).strip(),
            "role": _delatex(str(g.get("role") or "")).strip(),
            "year": str(g.get("year") or "").strip(),
        })
    return grants


def load_teaching() -> list[dict]:
    """Load data/teaching.yaml (the same list the CV uses) into render-ready dicts
    for the /teaching page. Preserves file order. `highlight` is an optional note
    (e.g. a TA-rating standing). Text is de-LaTeXed for the web."""
    if not TEACHING_YAML.exists():
        return []
    raw = yaml.safe_load(TEACHING_YAML.read_text()) or []
    courses: list[dict] = []
    for t in raw:
        course = _delatex(str(t.get("course") or "")).strip()
        if not course:
            continue
        courses.append({
            "course": course,
            "role": _delatex(str(t.get("role") or "")).strip(),
            "institution": _delatex(str(t.get("institution") or "")).strip(),
            "term": _delatex(str(t.get("term") or "")).strip(),
            "highlight": _delatex(str(t.get("highlight") or "")).strip(),
            "students": _delatex(str(t.get("students") or "")).strip(),
        })
    return courses


def _delatex(s: str) -> str:
    for k, v in _LATEX_UNESCAPE.items():
        s = s.replace(k, v)
    return s


def _chip_html(c, cls: str) -> Markup:
    """A small institution glyph chip: a favicon img or a literal emoji,
    optionally linked, with the name in the title/alt tooltip. Used for mentee
    destinations and the per-year 'host' marker on the mentoring timeline."""
    if not isinstance(c, dict) or not c.get("name"):
        return Markup("")
    name = str(escape(c["name"]))
    if c.get("favicon"):
        big = " chip-glyph-lg" if c.get("glyph_big") else ""
        inner = (f'<img class="chip-glyph{big}" src="{escape(c["favicon"])}" alt="{name}" '
                 'width="16" height="16" loading="lazy" onerror="this.remove()">')
    elif c.get("emoji"):
        inner = f'<span class="chip-emoji" aria-hidden="true">{escape(c["emoji"])}</span>'
    else:
        inner = f'<span class="chip-name">{name}</span>'
    if c.get("url"):
        return Markup(f'<a class="{cls}" href="{escape(c["url"])}" title="{name}">{inner}</a>')
    return Markup(f'<span class="{cls}" title="{name}">{inner}</span>')


def load_mentoring() -> list[dict]:
    """Load mentees into a year-grouped timeline (newest end-year first). Each
    mentee is one row; the FIRST mentee of each end-year group carries the year
    anchor + a 'host' chip (where Rosario was: a UW prototype). Optional `url`
    links the name to a personal site; optional `now` is a destination chip
    rendered after the span. LaTeX escapes / arrows are cleaned for the web."""
    if not MENTORING_YAML.exists():
        return []
    data = yaml.safe_load(MENTORING_YAML.read_text()) or {}
    # Prototype: where Rosario was while mentoring (UW for now; per-year later).
    HOST = {"name": "University of Washington",
            "favicon": "/img/allen-school.png",
            "url": "https://www.cs.washington.edu/"}

    def end_year(years: str) -> int:
        return max((int(y) for y in re.findall(r"\d{4}", years or "")), default=0)

    raw = list(data.get("mentees") or [])
    # End-year descending; file order preserved within a year (stable).
    order = sorted(range(len(raw)),
                   key=lambda i: (-end_year(str(raw[i].get("years") or "")), i))
    newest = end_year(str(raw[order[0]].get("years") or "")) if order else 0
    mentees: list[dict] = []
    prev = None
    for i in order:
        m = raw[i]
        years = str(m.get("years") or "").strip()
        ey = end_year(years)
        first = ey != prev
        prev = ey
        now = m.get("now") if isinstance(m.get("now"), dict) else None
        chip = _chip_html(now, "mentee-dest")
        role = str(now.get("role")).strip() if now and now.get("role") else ""
        if chip:
            role_html = f'<span class="mentee-role">{escape(role)} @</span>' if role else ""
            now_html = Markup(f' · <span class="mentee-next">Next →</span> {role_html}{chip}')
        else:
            now_html = Markup("")
        mentees.append({
            "name": _delatex(str(m.get("name") or "").strip()),
            "url": m.get("url"),
            "project": _delatex(str(m.get("project") or "").strip()),
            "project_url": m.get("project_url"),
            "span": years.replace("-", "–"),
            "now_html": now_html,
            "year": str(ey) if first else "",
            # The 'host' chip (where Rosario was) shows only on the newest group.
            "host_html": _chip_html(HOST, "mentee-host") if (first and ey == newest) else Markup(""),
        })
    return mentees


def split_front_matter(text: str) -> tuple[dict, str]:
    """Split optional leading `--- ... ---` YAML front-matter from a Markdown
    document. Returns (metadata, body)."""
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    return meta, text[m.end():]


def render_pages(env: Environment, identity: dict, default_description: str,
                 css_version: str, favicons: list[str]) -> list[str]:
    """Render every website/pages/*.md to website/<slug>.html via page.html.j2.
    Returns the slugs written."""
    if not PAGES_DIR.is_dir():
        return []
    md = mistune.create_markdown(escape=False)
    template = env.get_template("page.html.j2")
    written: list[str] = []
    for path in sorted(PAGES_DIR.glob("*.md")):
        slug = path.stem
        meta, body = split_front_matter(path.read_text())
        title = meta.get("title") or slug.replace("-", " ").title()
        description = meta.get("description") or default_description
        html = template.render(
            identity=identity,
            title=title,
            description=description,
            content_html=Markup(md(body)),
            css_version=css_version,
            favicons=favicons,
        )
        (ROOT / f"{slug}.html").write_text(html)
        written.append(slug)
    return written


def main() -> int:
    if not SITE_YAML.exists():
        print(f"error: {SITE_YAML} not found.", file=sys.stderr)
        return 1
    if not IDENTITY_YAML.exists():
        print(f"error: {IDENTITY_YAML} not found.", file=sys.stderr)
        return 1
    if not PUBS_YAML.exists():
        print(f"error: {PUBS_YAML} not found.", file=sys.stderr)
        return 1
    if not HEADSHOT_SRC.exists():
        print(f"error: {HEADSHOT_SRC} not found.", file=sys.stderr)
        return 1

    site = yaml.safe_load(SITE_YAML.read_text()) or {}
    identity = yaml.safe_load(IDENTITY_YAML.read_text()) or {}
    links = dict(identity.get("links") or {})
    links["email"] = identity.get("email")

    raw = yaml.safe_load(PUBS_YAML.read_text()) or []
    # Normalize optional fields on EVERY entry so both the homepage Selected
    # works and the full /publications list render via the shared work macro
    # without StrictUndefined errors. (Per-list year clustering is computed in
    # the macro itself.)
    for p in raw:
        p.setdefault("links", {})
        p.setdefault("awards", [])
        # Award medal (a prize ribbon, see the template) under the year in the
        # rail, shown when a paper carries an award.
        p["medal"] = bool(p["awards"])
        p["award_label"] = _delatex("; ".join(p["awards"])) if p["awards"] else ""
        # Optional shorter inline award label for the website (keeps the meta
        # line uncluttered); the full text stays in `awards` for the CV and in
        # the medal / inline award tooltip.
        p["award_short"] = _delatex(str(p["award_short"])).strip() if p.get("award_short") else ""
        # Optional tiny "@ <where>" tag (e.g. "@ WS") shown in subtle gray next
        # to the prize-ribbon medal, to mark a workshop/secondary-venue award.
        p["award_at"] = _delatex(str(p["award_at"])).strip() if p.get("award_at") else ""
        # Optional one-line TL;DR shown under the title.
        p["tldr"] = _delatex(str(p["tldr"])).strip() if p.get("tldr") else ""
        # Optional shorthand / codename (e.g. "SGS") shown as a quiet muted
        # parenthetical after the title. Auto-suppressed when it already appears
        # in the title, so papers whose acronym is already in the title (DROID,
        # VAMOS, LRN) don't double up.
        short = _delatex(str(p["short"])).strip() if p.get("short") else ""
        p["short"] = short if short and short.lower() not in p["title"].lower() else ""
        # Workshop papers show the host conference as the venue (e.g. CoRL) plus a
        # small "Workshop" kind tag in the rail, so the full workshop name doesn't
        # clutter the venue line (it stays in the venue_full tooltip).
        p["is_workshop"] = p.get("type") == "workshop"
        # Optional: let a long title run one line and spill slightly into the
        # right margin (desktop only) instead of wrapping a trailing word alone.
        p["title_nowrap"] = bool(p.get("title_nowrap"))
        p["venue_full"] = _delatex(str(p["venue_full"])) if p.get("venue_full") else None
        p["media_list"] = normalize_media_list(p.get("media"))
        p["coverage"] = normalize_coverage(p.get("coverage"))
        p["collaborators"] = normalize_collaborators(p.get("collaborators"))

    # Homepage shows featured works; /publications shows the full list. Both
    # sorted year-desc (equal years keep YAML order). `more_count` drives the
    # subtle "+N more" link next to Selected works.
    featured = sorted((p for p in raw if p.get("featured")), key=lambda p: -p["year"])
    if not featured:
        print(f"warning: no `featured: true` entries in {PUBS_YAML}", file=sys.stderr)
    all_pubs = sorted(raw, key=lambda p: -p["year"])
    more_count = len(all_pubs) - len(featured)

    news = load_news()
    mentees = load_mentoring()
    favicons = site.get("favicons") or DEFAULT_FAVICONS
    # Content hash of the stylesheet, appended to its URL so browsers fetch
    # the new CSS immediately instead of serving a stale cached copy.
    css_version = hashlib.sha256((ROOT / "styles.css").read_bytes()).hexdigest()[:8]
    # Build fingerprint: a stable integrity hash stamped onto each page's root
    # element (data-build) for provenance and asset versioning.
    build_fp = "5e4615be69fe6816b3a72e686745aee6d93d01d4d25c53610c8d97ab9a987c92"

    env = Environment(
        loader=FileSystemLoader(ROOT),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
        undefined=StrictUndefined,
    )
    env.filters["authors"] = render_authors
    env.filters["links"] = render_links
    env.filters["coverage"] = render_coverage_inline
    env.filters["collaborators"] = render_collaborators
    env.globals["build_fp"] = build_fp
    env.globals["year"] = datetime.date.today().year
    # Optional analytics config (see site.yaml `analytics:`). Exposed to every
    # template via the shared base layout; the snippet only renders once both
    # the script src and website id are set, so the site stays clean until the
    # self-hosted Umami instance is live.
    env.globals["analytics"] = site.get("analytics") or {}

    shutil.copy2(HEADSHOT_SRC, HEADSHOT_DEST)
    html = env.get_template("index.html.j2").render(
        publications=featured,
        more_count=more_count,
        identity=identity,
        description=site.get("description", ""),
        bio=_render_inline_md(site.get("bio", "")),
        links=links,
        news=news,
        mentees=mentees,
        css_version=css_version,
        favicons=favicons,
    )
    (ROOT / "index.html").write_text(html)
    print(f"wrote index.html ({len(featured)} publications, {len(news)} news)")

    # Full publication list at /publications (every entry, same work format as
    # Selected works), grouped by type like the CV, linked from the "+N more"
    # affordance on the homepage. Each group is sorted year-desc.
    pub_type_order = [
        ("preprint", "Preprints"),
        ("journal", "Journal Articles"),
        ("conference", "Conference Papers"),
        ("workshop", "Workshop Papers"),
    ]
    pub_groups = [
        {"label": label,
         "pubs": sorted((p for p in raw if p.get("type") == key), key=lambda p: -p["year"])}
        for key, label in pub_type_order
    ]
    pub_groups = [g for g in pub_groups if g["pubs"]]
    html = env.get_template("publications.html.j2").render(
        groups=pub_groups,
        identity=identity,
        title="Publications",
        description=f"Full publication list for {identity.get('name', '')}.".strip(),
        css_version=css_version,
        favicons=favicons,
    )
    (ROOT / "publications.html").write_text(html)
    print(f"wrote publications.html ({len(all_pubs)} publications)")

    pages = render_pages(env, identity, site.get("description", ""),
                         css_version, favicons)
    if pages:
        print(f"wrote {len(pages)} page(s): {', '.join(pages)}")

    # Bucket list: a YAML-driven hidden page at /bucketlist.
    if BUCKETLIST_YAML.exists():
        bucket = load_bucketlist()
        html = env.get_template("bucketlist.html.j2").render(
            identity=identity,
            title="Bucket List",
            description=f"{identity.get('name', '')}'s bucket list.".strip(),
            items=bucket,
            css_version=css_version,
            favicons=favicons,
        )
        (ROOT / "bucketlist.html").write_text(html)
        print(f"wrote bucketlist.html ({len(bucket)} items)")

    # Twitter-style microblog feed: a YAML-driven hidden page at /twitter.
    if TWITTER_YAML.exists():
        handle, posts = load_twitter()
        html = env.get_template("twitter.html.j2").render(
            identity=identity,
            title="en mi mente",
            description=f"Short posts from {identity.get('name', '')}.".strip(),
            handle=handle,
            posts=posts,
            css_version=css_version,
            favicons=favicons,
        )
        (ROOT / "twitter.html").write_text(html)
        print(f"wrote twitter.html ({len(posts)} posts)")

    # Reading: a curated blogroll, YAML-driven hidden page at /reading.
    if READING_YAML.exists():
        groups = load_reading()
        html = env.get_template("reading.html.j2").render(
            identity=identity,
            title="Reading",
            description=f"Blogs and feeds {identity.get('name', '')} reads.".strip(),
            groups=groups,
            css_version=css_version,
            favicons=favicons,
        )
        (ROOT / "reading.html").write_text(html)
        print(f"wrote reading.html ({sum(len(g['links']) for g in groups)} links)")

    # In the press: every publication's real media coverage, an exhaustive
    # YAML-driven hidden page at /inthepress (sourced from publications.yaml).
    press_works = load_press()
    if press_works:
        html = env.get_template("inthepress.html.j2").render(
            identity=identity,
            title="In the Press",
            description=f"Press and media coverage of {identity.get('name', '')}'s work.".strip(),
            works=press_works,
            css_version=css_version,
            favicons=favicons,
        )
        (ROOT / "inthepress.html").write_text(html)
        hits = sum(len(w["coverage"]) for w in press_works)
        print(f"wrote inthepress.html ({hits} hits across {len(press_works)} works)")

    # Awards & honors: a standalone page at /awards, sourced from data/honors.yaml
    # (the same list the CV uses). Years are intentionally omitted for now. A
    # "Grants Awarded" section below it is sourced from data/grants.yaml.
    honors = load_honors()
    grants = load_grants()
    if honors or grants:
        html = env.get_template("awards.html.j2").render(
            identity=identity,
            title="Awards & Honors",
            description=f"Awards, fellowships, grants, and honors received by {identity.get('name', '')}.".strip(),
            honors=honors,
            grants=grants,
            css_version=css_version,
            favicons=favicons,
        )
        (ROOT / "awards.html").write_text(html)
        print(f"wrote awards.html ({len(honors)} honors, {len(grants)} grants)")

    # Teaching: a standalone page at /teaching, sourced from data/teaching.yaml
    # (the same list the CV uses). Each course shows role, institution, term, and
    # an optional highlight note.
    teaching = load_teaching()
    if teaching:
        html = env.get_template("teaching.html.j2").render(
            identity=identity,
            title="Teaching",
            description=f"Courses {identity.get('name', '')} has taught and assisted.".strip(),
            courses=teaching,
            css_version=css_version,
            favicons=favicons,
        )
        (ROOT / "teaching.html").write_text(html)
        print(f"wrote teaching.html ({len(teaching)} courses)")

    # Custom-domain CNAME for GitHub Pages, derived from identity.yaml so the
    # domain stays single-sourced. Removed if `website` is cleared.
    cname = cname_from_website(identity.get("website"))
    cname_path = ROOT / "CNAME"
    if cname:
        cname_path.write_text(cname + "\n")
        print(f"wrote CNAME ({cname})")
    elif cname_path.exists():
        cname_path.unlink()

    return 0


if __name__ == "__main__":
    sys.exit(main())
