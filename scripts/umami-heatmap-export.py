#!/usr/bin/env python3
"""Generate website/heatmap-data.json for the ?heatmap attention overlay.

Pulls aggregate event counts from Umami Cloud and writes the JSON the overlay
(website/heatmap.js) consumes. Aggregate counts only: no coordinates, no PII.

Usage:
    UMAMI_API_KEY=... python scripts/umami-heatmap-export.py [days]

  - UMAMI_API_KEY: create in Umami Cloud > Settings > API keys.
  - days: look-back window (default 30).
  - Website ID is read from website/site.yaml (umami_id).

The overlay falls back to website/heatmap-data.sample.json if this file is
absent, so the tool always renders. The real file is gitignored (per-account).

CAVEAT: Umami's API shape varies by version. These endpoints target Umami Cloud
v1 (api.umami.is/v1). If a call 404s/500s, the script prints a warning, writes
whatever it did get, and you can adjust the endpoint or hand-edit the JSON.
Schema:  {"meta": {...},
          "event": {"<name>": <count> | {"<title|url>": <count>}},
          "section": {"<name>": <count>}}
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = os.environ.get("UMAMI_API_HOST", "https://api.umami.is/v1")
KEY = os.environ.get("UMAMI_API_KEY")
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 30

ROOT = Path(__file__).resolve().parent.parent
SITE = (ROOT / "website" / "site.yaml").read_text()
m = re.search(r"umami_id:\s*\"([0-9a-fA-F-]{36})\"", SITE)
if not KEY:
    sys.exit("set UMAMI_API_KEY (Umami Cloud > Settings > API keys)")
if not m:
    sys.exit("could not find umami_id in website/site.yaml")
WID = m.group(1)

END = int(time.time() * 1000)
START = END - DAYS * 86_400 * 1000
BASE = {"startAt": START, "endAt": END}


def _get(path: str, params: dict):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url, headers={"x-umami-api-key": KEY, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def _warn(msg: str):
    print(f"  warn: {msg}", file=sys.stderr)


data = {
    "meta": {"range": f"last {DAYS} days", "generated": time.strftime("%Y-%m-%d")},
    "event": {},
    "section": {},
}

# 1. Event-name totals: /websites/{id}/metrics?type=event -> [{x: name, y: count}]
try:
    for row in _get(f"/websites/{WID}/metrics", dict(BASE, type="event")):
        if row.get("x"):
            data["event"][row["x"]] = row.get("y", 0)
except (urllib.error.HTTPError, urllib.error.URLError, ValueError, KeyError) as e:
    _warn(f"event metrics failed ({e}); event totals will be empty")


def breakdown(event_name: str, prop: str):
    """Per-property counts for a named event, via /event-data/values."""
    try:
        rows = _get(
            f"/websites/{WID}/event-data/values",
            dict(BASE, eventName=event_name, propertyName=prop),
        )
        out = {}
        for r in rows:
            val = r.get("value")
            if val is not None:
                out[val] = r.get("total", r.get("y", 0))
        return out or None
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, KeyError) as e:
        _warn(f"breakdown {event_name}.{prop} failed ({e})")
        return None


# 2. section-view by `name` -> the section map.
sv = breakdown("section-view", "name")
if sv:
    data["section"] = sv

# 3. Replace scalar totals with per-title / per-url breakdowns where available.
for event_name, prop in (("paper-link", "title"), ("work-expand", "title"), ("outbound", "url")):
    bd = breakdown(event_name, prop)
    if bd:
        data["event"][event_name] = bd

out = ROOT / "website" / "heatmap-data.json"
out.write_text(json.dumps(data, indent=2))
print(f"wrote {out}  ({len(data['event'])} events, {len(data['section'])} sections)")
print("view it:  make serve  ->  http://localhost:8000/?heatmap")
