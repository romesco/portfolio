"""Generate index.html from index.html.j2 + shared portfolio YAML.
Identity lives in data/identity.yaml, and entries in data/publications.yaml
with `featured: true` are rendered, sorted year-desc.

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
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup, escape

ROOT = Path(__file__).parent
DATA_DIR = ROOT.parent / "data"
SITE_YAML = ROOT / "site.yaml"
IDENTITY_YAML = DATA_DIR / "identity.yaml"
PUBS_YAML = DATA_DIR / "publications.yaml"
HEADSHOT_SRC = ROOT.parent / "assets" / "headshot.jpg"
HEADSHOT_DEST = ROOT / "headshot.jpg"

ELLIPSIS_OUT = "…"

VIDEO_EXTS = {".mp4", ".webm", ".mov", ".m4v"}
IMAGE_EXTS = {".gif", ".jpg", ".jpeg", ".png", ".webp", ".avif", ".svg"}


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
    if m["type"] == "youtube" and not m.get("id"):
        m["id"] = _extract_youtube_id(m["src"])
    return m


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
        if a.get("equal"):
            name = f"{name}*"
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
        p["media"] = normalize_media(p.get("media"))

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
    )
    (ROOT / "index.html").write_text(html)
    print(f"wrote index.html ({len(featured)} publications)")

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
