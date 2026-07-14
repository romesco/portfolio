"""Markdown -> LaTeX for garage posts (the arXiv 'position paper' target).

A garage post is ONE Markdown file (website/pages/garage-<slug>.md) that drives
two outputs from a single prose source:

  * the interactive web page  (build.py render_pages, mistune escape=False)
  * an arXiv-ready main.tex    (build.py render_paper -> md_to_latex here)

Dual-target fenced blocks let one source serve both surfaces:

    ```{=web}
    <figure> ...raw HTML / JS / SVG widget... </figure>
    ```
    ```{=paper}
    \begin{figure}\centering ...static LaTeX fallback... \end{figure}
    ```

On the web the `{=web}` block is passed through verbatim and the `{=paper}`
block is dropped; for the paper it is the reverse. Inline `$...$` / display
`$$...$$` math is protected from the Markdown parser and passed through
literally (KaTeX renders it on the web, LaTeX compiles it for the PDF).

This module intentionally covers the Markdown SUBSET a garage post uses
(headings, emphasis, code, links, lists, block quotes, tables, rules, math,
and the dual-target fences). Anything outside that subset should be added here
deliberately rather than silently mis-rendered.
"""
from __future__ import annotations

import re

import mistune

# --- Dual-target fences + math, protected before the Markdown parser runs ---
WEB_FENCE = re.compile(r"^```\{=web\}[^\n]*\n(.*?)\n```[ \t]*$", re.DOTALL | re.MULTILINE)
PAPER_FENCE = re.compile(r"^```\{=paper\}[^\n]*\n(.*?)\n```[ \t]*$", re.DOTALL | re.MULTILINE)
DISPLAY_MATH = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
INLINE_MATH = re.compile(r"(?<![\\$])\$(?!\$)(.+?)(?<![\\$])\$(?!\$)", re.DOTALL)


def latex_escape(s) -> str:
    """Escape plain text for LaTeX. Mirrors cv/build.py's table so the paper's
    author/citation styling matches the CV; kept local to keep website/
    self-contained (no cross-package import that would drag in cv's pydantic)."""
    repl = {
        "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
        "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}", "\\": r"\textbackslash{}",
        ">": r"\textgreater{}", "<": r"\textless{}",
    }
    return "".join(repl.get(ch, ch) for ch in str(s))


# ------------------------------- web preparation ----------------------------
def prepare_web(body: str):
    """Protect a garage post's body for the WEB render. Returns
    (processed_markdown, web_blocks, math_spans). The caller runs mistune
    (escape=False) over processed_markdown, then restores the widget HTML into
    the `<!--WB{i}-->` comment placeholders and the literal math into the
    `zZmathZ{i}Zz` sentinels."""
    body = PAPER_FENCE.sub("", body)  # paper-only: drop from the web page

    webs: list[str] = []

    def _stash_web(m):
        webs.append(m.group(1))
        return f"\n\n<!--WB{len(webs) - 1}-->\n\n"

    body = WEB_FENCE.sub(_stash_web, body)

    maths: list[str] = []

    def _stash_display(m):
        maths.append("$$" + m.group(1).strip() + "$$")
        return f"zZmathZ{len(maths) - 1}Zz"

    def _stash_inline(m):
        maths.append("$" + m.group(1) + "$")
        return f"zZmathZ{len(maths) - 1}Zz"

    body = DISPLAY_MATH.sub(_stash_display, body)
    body = INLINE_MATH.sub(_stash_inline, body)
    return body, webs, maths


# ------------------------------ paper conversion ----------------------------
_HEADINGS = {1: "section", 2: "subsection", 3: "subsubsection",
             4: "paragraph", 5: "subparagraph", 6: "subparagraph"}


def _inline(children) -> str:
    out = []
    for t in children or []:
        typ = t.get("type")
        if typ == "text":
            out.append(latex_escape(t.get("raw", "")))
        elif typ == "strong":
            out.append(r"\textbf{" + _inline(t.get("children")) + "}")
        elif typ == "emphasis":
            out.append(r"\emph{" + _inline(t.get("children")) + "}")
        elif typ in ("del", "strikethrough"):
            out.append(_inline(t.get("children")))  # no strike in the PDF
        elif typ == "codespan":
            out.append(r"\texttt{" + latex_escape(t.get("raw", "")) + "}")
        elif typ == "link":
            url = t.get("attrs", {}).get("url", "")
            label = _inline(t.get("children"))
            url_tex = url.replace("%", r"\%").replace("#", r"\#")
            out.append(r"\href{" + url_tex + "}{" + label + "}")
        elif typ == "image":
            alt = latex_escape(t.get("attrs", {}).get("alt", "") or _inline(t.get("children")))
            out.append(alt)  # inline images degrade to their alt text
        elif typ in ("linebreak",):
            out.append(r"\\" + "\n")
        elif typ == "softbreak":
            out.append(" ")
        elif typ == "inline_html":
            pass  # raw inline HTML has no paper meaning; drop it
        else:
            out.append(latex_escape(t.get("raw", "")))
    return "".join(out)


def _cell_align(cells):
    spec = []
    for c in cells:
        a = (c.get("attrs") or {}).get("align")
        spec.append({"left": "l", "right": "r", "center": "c"}.get(a, "l"))
    return spec


def _block(tok) -> str:
    typ = tok.get("type")
    if typ == "heading":
        lvl = tok.get("attrs", {}).get("level", 1)
        return f"\\{_HEADINGS.get(lvl, 'subparagraph')}{{" + _inline(tok.get("children")) + "}"
    if typ in ("paragraph", "block_text"):
        return _inline(tok.get("children"))
    if typ == "blank_line":
        return ""
    if typ == "thematic_break":
        return r"\vspace{0.5em}\hrule\vspace{0.5em}"
    if typ == "block_code":
        raw = tok.get("raw", "")
        return "\\begin{verbatim}\n" + raw.rstrip("\n") + "\n\\end{verbatim}"
    if typ == "block_quote":
        inner = "\n\n".join(b for b in (_block(c) for c in tok.get("children", [])) if b)
        return "\\begin{quote}\n" + inner + "\n\\end{quote}"
    if typ == "list":
        ordered = tok.get("attrs", {}).get("ordered", False)
        env = "enumerate" if ordered else "itemize"
        items = []
        for it in tok.get("children", []):
            inner = "\n".join(b for b in (_block(c) for c in it.get("children", [])) if b)
            items.append(r"\item " + inner)
        return f"\\begin{{{env}}}\n" + "\n".join(items) + f"\n\\end{{{env}}}"
    if typ == "table":
        head, body_rows, spec = [], [], ["l"]
        for section in tok.get("children", []):
            if section.get("type") == "table_head":
                cells = section.get("children", [])
                spec = _cell_align(cells)
                head = [_inline(c.get("children")) for c in cells]
            elif section.get("type") == "table_body":
                for row in section.get("children", []):
                    body_rows.append([_inline(c.get("children")) for c in row.get("children", [])])
        lines = ["\\begin{tabular}{" + " ".join(spec) + "}", "\\hline"]
        if head:
            lines.append(" & ".join(head) + r" \\")
            lines.append("\\hline")
        for r in body_rows:
            lines.append(" & ".join(r) + r" \\")
        lines.append("\\hline")
        lines.append("\\end{tabular}")
        return "\n".join(lines)
    # Unknown block: fall back to its inline children, else its raw text.
    if tok.get("children"):
        return _inline(tok.get("children"))
    return latex_escape(tok.get("raw", ""))


def md_to_latex(body: str) -> str:
    """Convert a garage post's Markdown body to a LaTeX fragment (no preamble).
    `{=web}` blocks are dropped, `{=paper}` blocks are inserted verbatim, and
    `$...$` / `$$...$$` math passes through literally."""
    body = WEB_FENCE.sub("", body)  # web-only: no place in the PDF

    papers: list[str] = []

    def _stash_paper(m):
        papers.append(m.group(1))
        return f"\n\nzZpaperZ{len(papers) - 1}Zz\n\n"

    body = PAPER_FENCE.sub(_stash_paper, body)

    maths: list[str] = []

    def _stash_display(m):
        maths.append("$$" + m.group(1).strip() + "$$")
        return f"zZmathZ{len(maths) - 1}Zz"

    def _stash_inline(m):
        maths.append("$" + m.group(1) + "$")
        return f"zZmathZ{len(maths) - 1}Zz"

    body = DISPLAY_MATH.sub(_stash_display, body)
    body = INLINE_MATH.sub(_stash_inline, body)

    parse = mistune.create_markdown(renderer=None, plugins=["table", "strikethrough"])
    tokens = parse(body)
    out = "\n\n".join(b for b in (_block(t) for t in tokens) if b.strip())

    for i, m in enumerate(maths):
        out = out.replace(f"zZmathZ{i}Zz", m)
    for i, p in enumerate(papers):
        out = out.replace(f"zZpaperZ{i}Zz", p)
    return out


# ------------------------------- lints --------------------------------------
EMDASH = "—"
AI_DRAFT_RE = re.compile(r"<!--\s*AI-DRAFT\s*-->")
CITE_RE = re.compile(r"\[@([\w:.-]+)\]")
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]*`")


def _strip_code(s: str) -> str:
    """Drop fenced blocks (widgets included) and inline code so lints don't fire
    on example text like a documented `[@key]` or an em-dash inside a snippet."""
    return _INLINE_CODE_RE.sub("", _FENCE_RE.sub("", s))


def lint(body: str, meta: dict) -> list[str]:
    """Return author-facing warnings for a garage post. Non-fatal by design
    (a [WIP] post still builds); flip the caller to raise to harden later."""
    issues: list[str] = []
    prose = _strip_code(body)
    if EMDASH in prose:
        issues.append(f"{prose.count(EMDASH)} em-dash(es): house style is a colon or comma")
    n_ai = len(AI_DRAFT_RE.findall(body))
    if n_ai:
        issues.append(f"{n_ai} unreviewed <!-- AI-DRAFT --> span(s)")
    sources = meta.get("sources") or {}
    for key in CITE_RE.findall(prose):
        s = sources.get(key)
        if not s:
            issues.append(f"citation [@{key}] has no `sources:` entry")
        elif not (isinstance(s, dict) and s.get("checked")):
            issues.append(f"citation [@{key}] not yet `checked: true`")
    return issues
