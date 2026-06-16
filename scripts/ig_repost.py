#!/usr/bin/env python3
"""Turn an Instagram post URL into a ready-to-paste repost block for the
microblog at data/twitter.yaml (the hidden /twitter page).

THE TRICK (why this works when scraping normally doesn't): Instagram serves a
JS login wall to ordinary browsers (no OpenGraph, no post JSON), but it still
serves static OpenGraph/Twitter-card meta tags to link-preview crawlers. So we
fetch with a `facebookexternalhit` User-Agent and parse those tags. From them
we recover the author, @handle, caption, and original date. We do NOT get a
reliable aspect ratio (og:image is a square-cropped thumbnail), so `aspect`
defaults to 1 (correct for old square posts); override for portrait/landscape.

The card itself (cropped /embed/ iframe in our own chrome) is rendered by
website/build.py + twitter.html.j2 from the YAML this emits. See the guide at
docs/REPOSTING.md.

Usage:
    python3 scripts/ig_repost.py <instagram-url>            # print the YAML block
    python3 scripts/ig_repost.py <url> --comment "my take"  # add your own line
    python3 scripts/ig_repost.py <url> --aspect 0.8         # portrait (4:5)
    python3 scripts/ig_repost.py <url> --append             # insert into twitter.yaml

Exit non-zero if the post can't be read (deleted/private/age-gated).
"""
from __future__ import annotations

import argparse
import datetime
import html
import re
import sys
import urllib.request
from pathlib import Path

TWITTER_YAML = Path(__file__).resolve().parent.parent / "data" / "twitter.yaml"
# Link-preview crawler UA: Instagram serves static OpenGraph tags to this even
# though normal browsers get a login-walled JS shell.
UA = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"


def fetch_meta(url: str, timeout: int = 10) -> dict:
    """Return a dict of og:/twitter: meta tags from a post page (crawler UA)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
    meta: dict[str, str] = {}
    for m in re.finditer(
            r'<meta\s+(?:property|name)="([^"]+)"\s+content="([^"]*)"', body):
        meta[m.group(1).lower()] = html.unescape(m.group(2))
    return meta


def normalize_url(url: str) -> str:
    """Canonical https://www.instagram.com/p/<shortcode>/ (or /reel/...)."""
    url = url.strip().split("?", 1)[0]
    m = re.search(r"instagram\.com/(?:[^/]+/)?(p|reel|tv)/([A-Za-z0-9_-]+)", url)
    if not m:
        raise ValueError(f"not an Instagram post URL: {url!r}")
    return f"https://www.instagram.com/{m.group(1)}/{m.group(2)}/"


def parse(meta: dict, url: str) -> dict:
    """Pull {author, handle, caption, date} from meta tags, trying the most
    reliable source first for each field."""
    og_url = meta.get("og:url", "")
    tw_title = meta.get("twitter:title", "")
    og_title = meta.get("og:title", "")
    og_desc = meta.get("og:description", "")

    # handle: og:url path (.../<handle>/p/...) is most reliable; else "(@x)".
    handle = ""
    m = re.search(r"instagram\.com/([^/]+)/(?:p|reel|tv)/", og_url)
    if m and m.group(1) not in ("p", "reel", "tv"):
        handle = m.group(1)
    if not handle:
        m = re.search(r"\(@([A-Za-z0-9._]+)\)", tw_title)
        if m:
            handle = m.group(1)

    # author (display name): twitter:title "Name (@handle)"; else og:title prefix.
    author = ""
    m = re.match(r"\s*(.+?)\s*\(@", tw_title)
    if m:
        author = m.group(1).strip()
    if not author:
        m = re.match(r"\s*(.+?)\s+on Instagram", og_title)
        if m:
            author = m.group(1).strip()
    author = author or handle

    # caption: quoted part of og:title, else after the date in og:description.
    caption = ""
    m = re.search(r'on Instagram:\s*[""“](.*)[""”]\s*$', og_title, re.S)
    if m:
        caption = m.group(1).strip()
    if not caption:
        m = re.search(r':\s*[""“](.*)[""”]', og_desc, re.S)
        if m:
            caption = m.group(1).strip()

    # date: "... on June 17, 2015:" in og:description.
    date = None
    m = re.search(r"on ([A-Z][a-z]+ \d{1,2}, \d{4})", og_desc)
    if m:
        try:
            date = datetime.datetime.strptime(m.group(1), "%B %d, %Y").date()
        except ValueError:
            date = None

    return {"author": author, "handle": handle, "caption": caption,
            "date": date, "url": url}


def _yq(s: str) -> str:
    """Double-quote a YAML scalar, escaping embedded quotes/backslashes."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def yaml_block(p: dict, comment: str | None, aspect: str, now: datetime.datetime) -> str:
    lines = [f"  - at: {now:%Y-%m-%d %H:%M:%S}"]
    if comment:
        lines.append(f"    text: {_yq(comment)}")
    lines.append("    repost:")
    lines.append(f"      author: {_yq(p['author'])}")
    if p["handle"]:
        lines.append(f"      handle: {p['handle']}")
    lines.append(f"      url: {p['url']}")
    if p["date"]:
        lines.append(f"      at: {p['date']:%Y-%m-%d} 12:00:00")
    lines.append(f"      aspect: {aspect}   # square; set 0.8 portrait, 1.91 landscape")
    if p["caption"]:
        lines.append(f"      text: {_yq(p['caption'])}")
    return "\n".join(lines) + "\n"


def append_to_yaml(block: str) -> None:
    text = TWITTER_YAML.read_text()
    m = re.search(r"^posts:\s*$", text, re.M)
    if not m:
        raise SystemExit("could not find a `posts:` line in data/twitter.yaml")
    i = m.end()
    TWITTER_YAML.write_text(text[:i] + "\n" + block + text[i:])


def main() -> int:
    ap = argparse.ArgumentParser(description="Instagram post -> twitter.yaml repost block")
    ap.add_argument("url", help="Instagram post URL")
    ap.add_argument("--comment", help="your own line above the repost (optional)")
    ap.add_argument("--aspect", default="1", help="photo width/height (default 1=square)")
    ap.add_argument("--append", action="store_true", help="insert into data/twitter.yaml")
    args = ap.parse_args()

    url = normalize_url(args.url)
    meta = fetch_meta(url)
    if not meta.get("og:title") and not meta.get("twitter:title"):
        print(f"error: no metadata for {url} (deleted, private, or age-gated?)",
              file=sys.stderr)
        return 1
    p = parse(meta, url)
    block = yaml_block(p, args.comment, args.aspect, datetime.datetime.now())

    print(f"# author={p['author']!r} handle={p['handle']!r} "
          f"date={p['date']} caption={(p['caption'] or '')[:48]!r}", file=sys.stderr)
    if args.append:
        append_to_yaml(block)
        print(f"appended to {TWITTER_YAML}", file=sys.stderr)
    else:
        sys.stdout.write(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
