#!/usr/bin/env python3
"""Turn a YouTube URL into a ready-to-paste repost block for data/twitter.yaml.

Unlike Instagram, YouTube is friendly: its official oEmbed endpoint (no auth)
returns the title, channel name, and channel URL, and thumbnails are directly
hotlinkable. The card links back to the channel and plays the video inline on
hover, starting at --start (default 0). See docs/REPOSTING.md.

Usage:
    python3 scripts/yt_repost.py <youtube-url>                  # print the block
    python3 scripts/yt_repost.py <url> --start 4:20            # hover starts at 4:20
    python3 scripts/yt_repost.py <url> --comment "my take"
    python3 scripts/yt_repost.py <url> --start 4:20 --append   # insert into yaml
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

TWITTER_YAML = Path(__file__).resolve().parent.parent / "data" / "twitter.yaml"
UA = "Mozilla/5.0 (portfolio-build yt-repost)"


def video_id(url: str) -> str | None:
    for pat in (r"[?&]v=([A-Za-z0-9_-]{6,})", r"youtu\.be/([A-Za-z0-9_-]{6,})",
                r"/embed/([A-Za-z0-9_-]{6,})", r"/shorts/([A-Za-z0-9_-]{6,})"):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def parse_start(s: str) -> int:
    """Seconds from '260' or 'M:SS' / 'H:MM:SS'."""
    s = str(s or "0").strip()
    if ":" not in s:
        return int(s or 0)
    sec = 0
    for part in s.split(":"):
        sec = sec * 60 + int(part)
    return sec


def oembed(watch_url: str, timeout: int = 10) -> dict:
    api = ("https://www.youtube.com/oembed?url="
           + urllib.parse.quote(watch_url, safe="") + "&format=json")
    req = urllib.request.Request(api, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def _yq(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def yaml_block(vid: str, info: dict, start: int, comment: str | None,
               now: datetime.datetime) -> str:
    lines = [f"  - at: {now:%Y-%m-%d %H:%M:%S}"]
    if comment:
        lines.append(f"    text: {_yq(comment)}")
    lines.append("    repost:")
    lines.append("      source: youtube")
    lines.append(f"      author: {_yq(info.get('author_name', ''))}")
    if info.get("author_url"):
        lines.append(f"      url: {info['author_url']}   # link back to the channel")
    lines.append(f"      video: https://www.youtube.com/watch?v={vid}")
    if start:
        lines.append(f"      start: {start}   # hover preview starts here ({start // 60}:{start % 60:02d})")
    if info.get("title"):
        lines.append(f"      text: {_yq(info['title'])}")
    return "\n".join(lines) + "\n"


def append_to_yaml(block: str) -> None:
    text = TWITTER_YAML.read_text()
    m = re.search(r"^posts:\s*$", text, re.M)
    if not m:
        raise SystemExit("could not find a `posts:` line in data/twitter.yaml")
    i = m.end()
    TWITTER_YAML.write_text(text[:i] + "\n" + block + text[i:])


def main() -> int:
    ap = argparse.ArgumentParser(description="YouTube video -> twitter.yaml repost block")
    ap.add_argument("url", help="YouTube video URL")
    ap.add_argument("--start", default="0", help="hover-preview start, seconds or M:SS (default 0)")
    ap.add_argument("--comment", help="your own line above the repost (optional)")
    ap.add_argument("--append", action="store_true", help="insert into data/twitter.yaml")
    args = ap.parse_args()

    vid = video_id(args.url)
    if not vid:
        print(f"error: no video id in {args.url!r}", file=sys.stderr)
        return 1
    start = parse_start(args.start)
    try:
        info = oembed(f"https://www.youtube.com/watch?v={vid}")
    except Exception as e:
        print(f"error: oEmbed failed for {vid} ({e}); video private/deleted?",
              file=sys.stderr)
        return 1

    block = yaml_block(vid, info, start, args.comment, datetime.datetime.now())
    print(f"# channel={info.get('author_name')!r} url={info.get('author_url')} "
          f"start={start}s title={(info.get('title') or '')[:48]!r}", file=sys.stderr)
    if args.append:
        append_to_yaml(block)
        print(f"appended to {TWITTER_YAML}", file=sys.stderr)
    else:
        sys.stdout.write(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
