#!/usr/bin/env python3
"""Convert a BibTeX entry to a publications.yaml entry.

Usage:
    uv run python scripts/bib2yaml.py < paper.bib              # print to stdout
    pbpaste | uv run python scripts/bib2yaml.py                # macOS clipboard
    xclip -o | uv run python scripts/bib2yaml.py               # X11 clipboard
    uv run python scripts/bib2yaml.py paper.bib                # from file
    uv run python scripts/bib2yaml.py --insert < paper.bib     # prepend into data/publications.yaml

The script does its best to:
  - normalize "Tyler Han" → "T. Han"
  - tag any author whose surname is "Scalise" with `me: true`
  - infer `type` (preprint | journal | conference | workshop) from the BibTeX entry kind + fields
  - extract arxiv/doi links

It will NOT guess at venue abbreviations (e.g. "Conference on Robot Learning" → "CoRL") —
review the printed entry before committing.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB_YAML = ROOT / "data" / "publications.yaml"

# A surname match (case-insensitive) flips `me: true` on that author.
ME_SURNAME = "Scalise"
ME_RENDERED = "R. Scalise"

# Hardcoded venue table. Keys are the canonical short labels (used as `venue:` in YAML).
# `full` is the italicized form rendered in the citation; None means no `venue_full`
# is emitted (e.g. preprints just show "arXiv"). `aliases` are case-insensitive
# strings that map to this entry; include the full name and any common variants.
# To add a venue: append a new entry here.
VENUES: dict[str, dict] = {
    "arXiv": {
        "full": None,
        "aliases": ["arxiv"],
    },
    "IJRR": {
        "full": "The International Journal of Robotics Research (IJRR)",
        "aliases": [
            "the international journal of robotics research",
            "international journal of robotics research",
            "ijrr",
        ],
    },
    "ICRA": {
        "full": "International Conference on Robotics \\& Automation (ICRA)",
        "aliases": [
            "international conference on robotics and automation",
            "international conference on robotics & automation",
            "ieee international conference on robotics and automation",
            "icra",
        ],
    },
    "IROS": {
        "full": "International Conference on Intelligent Robots and Systems (IROS)",
        "aliases": [
            "international conference on intelligent robots and systems",
            "ieee/rsj international conference on intelligent robots and systems",
            "iros",
        ],
    },
    "RSS": {
        "full": "Robotics: Science \\& Systems (RSS)",
        "aliases": [
            "robotics: science and systems",
            "robotics: science & systems",
            "rss",
        ],
    },
    "CoRL": {
        "full": "Conference on Robot Learning (CoRL)",
        "aliases": [
            "conference on robot learning",
            "corl",
        ],
    },
    "HRI": {
        "full": "International Conference on Human-Robot Interaction (HRI)",
        "aliases": [
            "international conference on human-robot interaction",
            "international conference on human robot interaction",
            "conference on human-robot interaction",
            "conference on human robot interaction",
            "acm/ieee international conference on human-robot interaction",
            "hri",
        ],
    },
    "RO-MAN": {
        "full": "Robot and Human Interactive Communication (RO-MAN)",
        "aliases": [
            "robot and human interactive communication",
            "international symposium on robot and human interactive communication",
            "ieee international symposium on robot and human interactive communication",
            "ro-man",
        ],
    },
}


def _normalize_venue_input(s: str) -> str:
    """Normalize a venue string for table lookup: lowercase, strip noise."""
    s = s.strip()
    # Drop trailing parenthetical: "Foo (BAR)" → "Foo"
    s = re.sub(r"\s*\([^)]*\)\s*\Z", "", s)
    # Drop leading "Proceedings of [the] " / "Proc. of "
    s = re.sub(r"\A(proceedings|proc\.?)\s+of\s+(the\s+)?", "", s, flags=re.IGNORECASE)
    # Drop a leading 4-digit year: "2025 IEEE..." → "IEEE..."
    s = re.sub(r"\A\d{4}\s+", "", s)
    # Drop a trailing 4-digit year: "CoRL 2024" → "CoRL"
    s = re.sub(r"\s+\d{4}\Z", "", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s.lower().strip()


def lookup_venue(raw: str) -> tuple[str, str | None]:
    """Look up a venue. Returns (short, full_or_None). On no match, returns (raw, None)."""
    if not raw or not raw.strip():
        return raw, None
    normalized = _normalize_venue_input(raw)
    for short, info in VENUES.items():
        if short.lower() == normalized:
            return short, info["full"]
        if normalized in info["aliases"]:
            return short, info["full"]
    return raw.strip(), None


# --- BibTeX parsing -------------------------------------------------------

def parse_bibtex(text: str) -> dict:
    """Parse a single BibTeX entry. Returns {kind, key, fields: dict}."""
    text = text.strip()
    m = re.match(r"@(\w+)\s*\{\s*([^,\s]+)\s*,\s*(.*)\}\s*\Z", text, re.DOTALL)
    if not m:
        raise SystemExit("Could not parse BibTeX entry. Expected @kind{key, ...}.")
    kind = m.group(1).lower()
    key = m.group(2)
    body = m.group(3).rstrip().rstrip(",").rstrip()

    fields: dict[str, str] = {}
    i = 0
    n = len(body)
    while i < n:
        while i < n and body[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        nm = re.match(r"(\w+)\s*=\s*", body[i:])
        if not nm:
            break
        name = nm.group(1).lower()
        i += nm.end()
        if i >= n:
            break
        if body[i] == "{":
            depth = 1
            i += 1
            start = i
            while i < n and depth > 0:
                if body[i] == "{":
                    depth += 1
                elif body[i] == "}":
                    depth -= 1
                if depth > 0:
                    i += 1
            value = body[start:i]
            i += 1
        elif body[i] == '"':
            i += 1
            start = i
            while i < n and body[i] != '"':
                i += 1
            value = body[start:i]
            i += 1
        else:
            start = i
            while i < n and body[i] not in " \t\r\n,":
                i += 1
            value = body[start:i]
        fields[name] = value
    return {"kind": kind, "key": key, "fields": fields}


# --- Author normalization -------------------------------------------------

def _surname(name: str) -> str:
    name = re.sub(r"\s*\([^)]*\)", "", name).strip()
    if "," in name:
        return name.split(",", 1)[0].strip()
    parts = name.split()
    return parts[-1] if parts else ""


def is_me(name: str) -> bool:
    return _surname(name).lower() == ME_SURNAME.lower()


def normalize_author_name(name: str) -> dict | str:
    """`"Tyler Han"` → `"T. Han"`; `"Rosario Scalise"` → `{name: "R. Scalise", me: true}`."""
    raw = name.strip()
    raw = re.sub(r"\s*\([^)]*\)", "", raw)  # drop "(Ramon)"-style parentheticals

    if "," in raw:
        last, rest = [s.strip() for s in raw.split(",", 1)]
        firsts = rest.split()
    else:
        parts = raw.split()
        if not parts:
            return ""
        if len(parts) == 1:
            last = parts[0]
            firsts = []
        else:
            last = parts[-1]
            firsts = parts[:-1]

    initials: list[str] = []
    for p in firsts:
        if "." in p:
            initials.append(p)             # already initialed (e.g. "S.S.")
        else:
            initials.append(p[0].upper() + ".")

    rendered = (" ".join(initials) + " " + last).strip()
    if is_me(name):
        return {"name": ME_RENDERED, "me": True}
    return rendered


def parse_authors_field(s: str) -> list:
    raw = re.split(r"\s+and\s+", s, flags=re.IGNORECASE)
    return [normalize_author_name(a) for a in raw if a.strip()]


# --- Type / venue / links inference ---------------------------------------

def detect_type_and_venue(entry: dict) -> tuple[str, str, str | None]:
    """Returns (pub_type, venue_short, venue_full_or_None)."""
    f = entry["fields"]
    kind = entry["kind"]

    # Strong arXiv signals → preprint, no venue_full (rendered citation just shows "arXiv")
    archive = f.get("archiveprefix", "").lower()
    if archive == "arxiv":
        return "preprint", "arXiv", None
    if "eprint" in f and "journal" not in f and "booktitle" not in f:
        return "preprint", "arXiv", None

    if kind == "article":
        raw = f.get("journal", "") or f.get("journaltitle", "")
        short, full = lookup_venue(raw)
        return "journal", short, full
    if kind in ("inproceedings", "conference", "incollection"):
        raw = f.get("booktitle", "")
        short, full = lookup_venue(raw)
        return "conference", short, full
    if kind in ("misc", "unpublished"):
        return "preprint", "arXiv", None

    raw = f.get("booktitle", "") or f.get("journal", "")
    short, full = lookup_venue(raw)
    return "conference", short, full


def detect_links(entry: dict) -> dict[str, str]:
    f = entry["fields"]
    links: dict[str, str] = {}
    if "eprint" in f:
        eprint = f["eprint"].strip()
        if eprint.lower().startswith("arxiv:"):
            eprint = eprint[6:].strip()
        links["arxiv"] = eprint
    elif "url" in f and "arxiv.org" in f["url"]:
        m = re.search(r"arxiv\.org/abs/([^/?#\s]+)", f["url"])
        if m:
            links["arxiv"] = m.group(1)
    if "doi" in f and "arxiv" not in links:
        links["doi"] = f["doi"].strip()
    return links


# --- YAML rendering -------------------------------------------------------

# Characters that force YAML double-quoting in this script's output.
_NEEDS_QUOTES = re.compile(r"[:#\[\]{}&*!|>'\"%@`]")


_NUMERIC = re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$")


def yaml_scalar(v) -> str:
    """Render a python value as a YAML scalar with conservative quoting rules.

    Quotes when the value would otherwise be parsed as a non-string YAML scalar
    (number, bool, null) or contains characters with YAML semantic meaning.
    """
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    s = str(v)
    if not s:
        return '""'
    needs_quotes = (
        _NEEDS_QUOTES.search(s) is not None
        or s[0] in "-?,&*!|>'\"%@`#"
        or s.lower() in ("true", "false", "null", "yes", "no", "~")
        or _NUMERIC.match(s) is not None  # bare numbers must stay strings (e.g. arxiv ids)
    )
    if needs_quotes:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def render_yaml_entry(entry: dict, *, venue_override: str | None = None) -> str:
    f = entry["fields"]
    pub_type, venue, venue_full = detect_type_and_venue(entry)
    if venue_override:
        # User-supplied --venue: look up its canonical (short, full) from the table.
        venue, venue_full = lookup_venue(venue_override)
    authors = parse_authors_field(f.get("author", ""))
    title = f.get("title", "").strip()
    title = re.sub(r"[{}]", "", title)  # strip BibTeX brace-protections in titles
    year = f.get("year", "").strip()
    links = detect_links(entry)

    lines: list[str] = []
    year_scalar = year if year else '""'
    lines.append(f"- year: {year_scalar}")
    lines.append(f"  type: {pub_type}")
    lines.append("  authors:")
    for a in authors:
        if isinstance(a, dict):
            inline = ", ".join(f"{k}: {yaml_scalar(v)}" for k, v in a.items())
            lines.append(f"    - {{{inline}}}")
        else:
            lines.append(f"    - {a}")
    lines.append(f"  title: {yaml_scalar(title)}")
    lines.append(f"  venue: {yaml_scalar(venue)}")
    if venue_full:
        lines.append(f"  venue_full: {yaml_scalar(venue_full)}")
    if links:
        link_parts = ", ".join(f"{k}: {yaml_scalar(v)}" for k, v in links.items())
        lines.append(f"  links: {{{link_parts}}}")
    return "\n".join(lines) + "\n"


# --- Insertion into publications.yaml -------------------------------------

def insert_into_publications_yaml(yaml_entry: str) -> None:
    """Prepend the entry just before the first existing `- year:` line."""
    text = PUB_YAML.read_text()
    lines = text.split("\n")
    insert_at = None
    for i, line in enumerate(lines):
        if line.startswith("- year:"):
            insert_at = i
            break
    if insert_at is None:
        # No entries yet — append at end
        if not text.endswith("\n"):
            text += "\n"
        PUB_YAML.write_text(text + yaml_entry)
        return
    new_text = "\n".join(lines[:insert_at]) + "\n" + yaml_entry + "\n".join(lines[insert_at:])
    PUB_YAML.write_text(new_text)


# --- CLI ------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("file", nargs="?", help="BibTeX file (default: stdin)")
    p.add_argument(
        "--insert", action="store_true",
        help="Prepend the entry to data/publications.yaml (before the first `- year:` line)",
    )
    p.add_argument(
        "--venue", metavar="SHORT",
        help=(
            "Override the venue. Pass the short label (e.g. ICRA, CoRL); "
            "the full name is looked up from the built-in table. "
            f"Known: {', '.join(VENUES.keys())}."
        ),
    )
    args = p.parse_args()

    text = Path(args.file).read_text() if args.file else sys.stdin.read()
    entry = parse_bibtex(text)
    yaml_entry = render_yaml_entry(entry, venue_override=args.venue)

    if args.insert:
        insert_into_publications_yaml(yaml_entry)
        sys.stderr.write(f"Inserted into {PUB_YAML.relative_to(ROOT)}:\n\n")
        sys.stderr.write(yaml_entry + "\n")
        sys.stderr.write("Run `make data` to regenerate generated/publications.tex.\n")
    else:
        sys.stdout.write(yaml_entry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
