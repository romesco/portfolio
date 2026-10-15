"""Half-page "selected works" handout, styled like the website.

Reads the homepage's featured works from data/publications.yaml (same order as
the site: year-desc, YAML order within a year) and identity from
data/identity.yaml, then typesets a half-letter landscape sheet with Typst that
ends by pointing the reader to the website.

Run:  make selected-works   (writes cv/selected-works.pdf)

Font: TeX Gyre Pagella (a Palatino clone, in the site's serif stack). The make
target fetches it from CTAN into ~/.cache/selected-works-fonts, which is the
default --font-path.
"""

import argparse
import json
import sys
from pathlib import Path

import typst
import yaml

ROOT = Path(__file__).resolve().parent.parent
PUBS = ROOT / "data" / "publications.yaml"
IDENTITY = ROOT / "data" / "identity.yaml"
OUT = ROOT / "cv" / "selected-works.pdf"
FONT_CACHE = Path.home() / ".cache" / "selected-works-fonts"

# Colors are the site's light-theme OKLCH tokens (website/styles.css :root).
TEMPLATE = r"""
#let d = json(bytes(sys.inputs.data))
#let bg = oklch(97.5%, 0.012, 80deg)
#let fg = oklch(22.5%, 0.008, 80deg)
#let muted = oklch(50%, 0.012, 80deg)
#let faint = oklch(68.5%, 0.010, 80deg)
#let rule = oklch(86%, 0.012, 80deg)
#let accent = oklch(42%, 0.130, 250deg)

#set page(width: 8.5in, height: 5.5in, fill: bg,
          margin: (x: 0.5in, top: 0.42in, bottom: 0.38in))
#set text(font: "TeX Gyre Pagella", size: 9.4pt, fill: fg,
          features: ("onum",), lang: "en")
#set par(leading: 0.42em, spacing: 0pt)
#show link: set text(fill: accent)

#let label(body) = block(width: 100%, stroke: (top: 0.5pt + rule),
  inset: (top: 5pt), below: 6pt,
  text(size: 7.6pt, weight: "bold", style: "italic", fill: muted, lower(body)))

// Masthead: name, title, affiliation.
#grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
  [
    #block(below: 6pt, text(size: 18pt, weight: "bold", tracking: -0.012em, d.name))
    #text(size: 9.6pt, d.title) #text(size: 9.6pt, fill: muted, [· #d.affiliation])
  ],
  text(size: 9.6pt, link(d.url, d.host)),
)
#v(8pt)

#label[Selected works]

// Left rail (venue over a faint year, award beneath) + title and TL;DR,
// mirroring the homepage's works list.
#let rail(w) = {
  text(size: 7.6pt, weight: "bold", fill: muted, tracking: 0.01em, w.venue)
  if w.kind != none { h(3pt); text(size: 5.4pt, weight: "bold", fill: faint, tracking: 0.09em, upper(w.kind)) }
  linebreak()
  text(size: 7pt, fill: faint, features: ("lnum", "tnum"), str(w.year))
}
#grid(columns: (0.78in, 1fr), column-gutter: 9pt, row-gutter: 6.4pt,
  ..d.works.map(w => (
    rail(w),
    {
      text(weight: "semibold", w.title)
      if w.award != none { text(style: "italic", fill: accent, [ · #w.award]) }
      if w.tldr != none { linebreak(); text(size: 8.3pt, fill: muted, w.tldr) }
    },
  )).flatten()
)

#place(bottom + left, block(width: 100%, stroke: (top: 0.5pt + rule), inset: (top: 6pt),
  grid(columns: (1fr, auto), align: (left, right),
    text(size: 9.4pt, fill: muted)[Full publication list, videos, and writing at #link(d.url, text(weight: "semibold", d.host)).],
    text(size: 7.6pt, fill: faint, d.email),
  )))
"""


def featured_works() -> list[dict]:
    pubs = yaml.safe_load(PUBS.read_text())
    featured = sorted((p for p in pubs if p.get("featured")), key=lambda p: -p["year"])
    works = []
    for p in featured:
        award = None
        if p.get("awards"):
            award = p.get("award_short") or p["awards"][0]
            if p.get("award_at"):
                award += f" @ {p['award_at']}"
        works.append({
            "title": p["title"].replace("\\&", "&"),
            "venue": p.get("venue") or "",
            "kind": "Workshop" if p.get("type") == "workshop" else None,
            "year": p["year"],
            "tldr": p.get("tldr"),
            "award": award,
        })
    return works


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--out", type=Path, default=OUT)
    ap.add_argument("--font-path", action="append", default=[])
    ap.add_argument("--png", type=Path, help="also write a PNG preview here")
    args = ap.parse_args()

    ident = yaml.safe_load(IDENTITY.read_text())
    url = ident["website"].rstrip("/")
    data = {
        "name": ident["name"],
        "title": ident["title"],
        "affiliation": ident["affiliation"],
        "email": ident["email"],
        "url": url,
        "host": url.split("://", 1)[-1],
        "works": featured_works(),
    }
    if not args.font_path:
        args.font_path = [str(FONT_CACHE)]
    src = TEMPLATE.encode()
    inputs = {"data": json.dumps(data)}
    args.out.write_bytes(typst.compile(src, font_paths=args.font_path, sys_inputs=inputs))
    if args.png:
        args.png.write_bytes(typst.compile(src, format="png", ppi=150,
                                           font_paths=args.font_path, sys_inputs=inputs))
    print(f"wrote {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out} "
          f"({len(data['works'])} works)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
