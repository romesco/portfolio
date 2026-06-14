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
    autoplay: true                 # optional (video) — implies muted/loop
    alt: "Caption text"            # optional (image)

Standalone pages: drop `website/pages/<slug>.md` (optional YAML front-matter
with `title:`/`description:`). It renders to `website/<slug>.html`, served at
`/<slug>`, styled like the homepage, not linked from it, and marked noindex.
"""
from __future__ import annotations

import datetime
import hashlib
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import mistune
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup, escape

ROOT = Path(__file__).parent
DATA_DIR = ROOT.parent / "data"
SITE_YAML = ROOT / "site.yaml"
IDENTITY_YAML = DATA_DIR / "identity.yaml"
PUBS_YAML = DATA_DIR / "publications.yaml"
NEWS_YAML = DATA_DIR / "news.yaml"
MENTORING_YAML = DATA_DIR / "mentoring.yaml"
BUCKETLIST_YAML = DATA_DIR / "bucketlist.yaml"
TWITTER_YAML = DATA_DIR / "twitter.yaml"
READING_YAML = DATA_DIR / "reading.yaml"
PAGES_DIR = ROOT / "pages"
HEADSHOT_SRC = ROOT.parent / "assets" / "headshot.jpg"
HEADSHOT_DEST = ROOT / "headshot.jpg"

ELLIPSIS_OUT = "…"

VIDEO_EXTS = {".mp4", ".webm", ".mov", ".m4v"}
IMAGE_EXTS = {".gif", ".jpg", ".jpeg", ".png", ".webp", ".avif", ".svg"}

# Fallback favicon pool if site.yaml doesn't define `favicons`. A random one
# is rendered as an inline SVG emoji on each page load.
DEFAULT_FAVICONS = ["🤖", "🦾", "🧠", "🧬", "⚙️", "🛰️", "🔬", "🔭", "⚛️", "✨"]

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
    becomes many — the template renders >1 as a carousel."""
    if m is None:
        return []
    items = m if isinstance(m, list) else [m]
    return [nm for nm in (normalize_media(it) for it in items) if nm]


def render_authors(authors) -> Markup:
    """HTML port of the CV's format_authors. `me: true` wraps in <strong>;
    `equal: true` appends `*`; bare `"..."` becomes a literal ellipsis.
    Oxford comma + ampersand as last separator, except when the list contains
    an ellipsis (commas only — "..., & ..." reads as ungrammatical)."""
    pieces: list[str] = []
    has_ellipsis = False
    for a in authors:
        if isinstance(a, str):
            if a == "...":
                pieces.append(ELLIPSIS_OUT)
                has_ellipsis = True
            else:
                pieces.append(str(escape(a)))
            continue
        name = str(escape(a["name"]))
        if a.get("me"):
            name = f"<strong>{name}</strong>"
        # Contribution markers (* equal, † e.g. co-advisor) as a single
        # superscript, kept outside any <strong> so they aren't bolded.
        marks = ("*" if a.get("equal") else "") + ("†" if a.get("dagger") else "")
        if marks:
            name = f"{name}<sup>{marks}</sup>"
        pieces.append(name)

    if not pieces:
        return Markup("")
    if len(pieces) == 1:
        out = pieces[0]
    elif has_ellipsis:
        out = ", ".join(pieces)
    else:
        out = ", ".join(pieces[:-1]) + ", &amp; " + pieces[-1]

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
    return Markup(" · ".join(parts))


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


def _initials(name: str) -> str:
    """Up to two initials for an avatar fallback (e.g. 'Octi Zhang' -> 'OZ')."""
    parts = [w for w in str(name).split() if w]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def load_twitter() -> tuple[str, list[dict]]:
    """Load data/twitter.yaml — `{handle, posts: [{at, text?, repost?}]}` — into
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
            repost = {
                "author": str(rp.get("author") or ""),
                "handle": str(rp.get("handle") or "").lstrip("@"),
                "avatar": rp.get("avatar"),
                "url": rp.get("url"),
                "initials": _initials(rp.get("author") or ""),
                "html": _render_inline_md(rp.get("text", "")),
                "iso": r_iso, "display": r_display, "full": r_full,
            }
        comment = str(p.get("text") or "").strip()
        posts.append({
            "html": _render_inline_md(comment),
            "has_comment": bool(comment),
            "repost": repost,
            "iso": iso, "display": display, "full": full,
        })
    posts.sort(key=lambda x: x["iso"], reverse=True)
    return handle, posts


def load_reading() -> list[dict]:
    """Load data/reading.yaml — `{groups: [{name, links: [{name, url, note}]}]}`
    — into a curated, grouped blogroll. Derives a bare display domain from each
    URL; renders notes as inline Markdown. Preserves file order."""
    if not READING_YAML.exists():
        return []
    data = yaml.safe_load(READING_YAML.read_text()) or {}
    groups: list[dict] = []
    for g in data.get("groups") or []:
        links: list[dict] = []
        for ln in g.get("links") or []:
            url = str(ln.get("url") or "")
            host = urlparse(url).netloc or urlparse(f"//{url}").netloc
            if host.startswith("www."):
                host = host[4:]
            note = ln.get("note")
            links.append({
                "name": str(ln.get("name") or host or url),
                "url": url,
                "domain": host,
                # Favicon by domain (no images to host). Swap the service freely.
                "favicon": f"https://www.google.com/s2/favicons?domain={host}&sz=64" if host else None,
                "note": _render_inline_md(note) if note else None,
            })
        if links:
            groups.append({"name": str(g.get("name") or ""), "links": links})
    return groups


# The shared data/ YAML is authored for the LaTeX CV, so a few values carry
# LaTeX escapes. Undo the common ones for HTML (Jinja then re-escapes safely).
_LATEX_UNESCAPE = {r"\&": "&", r"\%": "%", r"\#": "#", r"\_": "_", r"\$": "$"}


def _delatex(s: str) -> str:
    for k, v in _LATEX_UNESCAPE.items():
        s = s.replace(k, v)
    return s


def load_mentoring() -> list[dict]:
    """Load mentees from data/mentoring.yaml (file order preserved). Cleans
    LaTeX escapes and stray whitespace, and renders `->` / year ranges with
    proper arrows/en dashes for the web."""
    if not MENTORING_YAML.exists():
        return []
    data = yaml.safe_load(MENTORING_YAML.read_text()) or {}
    mentees: list[dict] = []
    for m in data.get("mentees") or []:
        current = _delatex(str(m.get("current") or "").strip()).replace("->", "→")
        years = str(m.get("years") or "").strip().replace("-", "–")
        mentees.append({
            "name": _delatex(str(m.get("name") or "").strip()),
            "project": _delatex(str(m.get("project") or "").strip()),
            "current": current,
            "years": years,
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
    featured = [p for p in raw if p.get("featured")]
    if not featured:
        print(
            f"warning: no `featured: true` entries in {PUBS_YAML}",
            file=sys.stderr,
        )
    featured.sort(key=lambda p: -p["year"])

    # Normalize optional fields so the template can iterate without
    # StrictUndefined errors on entries missing `links`, `awards`, or `media`.
    for p in featured:
        p.setdefault("links", {})
        p.setdefault("awards", [])
        p["media_list"] = normalize_media_list(p.get("media"))

    news = load_news()
    mentees = load_mentoring()
    favicons = site.get("favicons") or DEFAULT_FAVICONS
    # Content hash of the stylesheet, appended to its URL so browsers fetch
    # the new CSS immediately instead of serving a stale cached copy.
    css_version = hashlib.sha256((ROOT / "styles.css").read_bytes()).hexdigest()[:8]

    env = Environment(
        loader=FileSystemLoader(ROOT),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
        undefined=StrictUndefined,
    )
    env.filters["authors"] = render_authors
    env.filters["links"] = render_links

    shutil.copy2(HEADSHOT_SRC, HEADSHOT_DEST)
    html = env.get_template("index.html.j2").render(
        publications=featured,
        identity=identity,
        description=site.get("description", ""),
        bio=site.get("bio", ""),
        links=links,
        news=news,
        mentees=mentees,
        css_version=css_version,
        favicons=favicons,
    )
    (ROOT / "index.html").write_text(html)
    print(f"wrote index.html ({len(featured)} publications, {len(news)} news)")

    pages = render_pages(env, identity, site.get("description", ""),
                         css_version, favicons)
    if pages:
        print(f"wrote {len(pages)} page(s): {', '.join(pages)}")

    # Bucket list — a YAML-driven hidden page at /bucketlist.
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

    # Twitter-style microblog feed — a YAML-driven hidden page at /twitter.
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

    # Reading — a curated blogroll, YAML-driven hidden page at /reading.
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
