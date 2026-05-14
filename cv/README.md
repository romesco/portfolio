# CV — Data-Driven LaTeX

Single-file LaTeX CV refactored into YAML data + Jinja2 templates. Source-of-truth lives in `data/`; the LaTeX in `generated/` is machine-written, committed, and what Overleaf compiles.

## Editing

**Add a paper:**

1. Open `data/publications.yaml`.
2. Add an entry. The two recurring patterns:

   ```yaml
   # Standard conference / journal entry
   - year: 2025
     type: conference        # preprint | journal | conference | workshop
     authors:
       - F. Author
       - {name: R. Scalise, me: true}
       - L. Author
     title: Title goes here
     venue: ICRA
     venue_full: International Conference on Robotics \& Automation (ICRA)
     links: {arxiv: "2501.12345"}    # optional: arxiv | pdf | doi | ieee | github | project
     awards: []                      # optional list of strings, rendered in red

   # Co-first authorship + abbreviated list
   - year: 2024
     type: conference
     authors:
       - {name: K. Pertsch, equal: true}
       - "..."                         # quoted "..." renders as literal ellipsis
       - {name: R. Scalise, me: true}
       - "..."
       - C. Finn
     title: ...
     venue: RSS
   ```

3. Run `make` (regenerates and recompiles) or `make data` (regenerate only).
4. Commit BOTH `data/publications.yaml` AND `generated/publications.tex`.

**Add an experience / honor / mentee / etc.:** same workflow on the relevant `data/<section>.yaml`.

**Don't hand-edit `generated/*.tex` — they're rebuilt from YAML.** Edit `data/`.

### Add a paper from BibTeX

Paste a BibTeX entry into `scripts/bib2yaml.py` and it spits out a YAML entry ready for `data/publications.yaml`:

```bash
# Print to stdout (review first, then paste into data/publications.yaml)
uv run python scripts/bib2yaml.py < paper.bib
pbpaste | uv run python scripts/bib2yaml.py        # macOS: from clipboard

# Or insert directly at the top of data/publications.yaml
uv run python scripts/bib2yaml.py --insert < paper.bib
make data
```

The script normalizes "Tyler Han" → "T. Han", tags any author whose surname is `Scalise` with `me: true`, and infers `type` (preprint/journal/conference) and `links` (arxiv/doi) from the BibTeX fields. **Always review the output** — the script doesn't know your venue abbreviation conventions (e.g. it won't shorten "Conference on Robot Learning" to "CoRL") and it preserves the title's original case (typically Title Case from arXiv, which you may want to convert to sentence case).

## Build

| Command | What it does |
|---|---|
| `make` | regenerates `generated/` and recompiles `main.pdf` (skips compile if `latexmk` is missing) |
| `make data` | only regenerates `generated/` |
| `make pdf` | explicit local PDF compile (errors if `latexmk` is missing) |
| `make sync` | one-shot round-trip with Overleaf: pull → regenerate → push |
| `make watch` | re-run on YAML/template change (needs `entr`) |
| `make check` | CI guard: fails if `generated/` is out of sync with `data/` |
| `make verify` | side-by-side PDF diff vs. `reference.pdf` (sanity check tool) |
| `make test` | run pytest |
| `make clean` | remove aux + `main.pdf` (NOT generated `.tex`) |

**Typical flow:** edit `data/foo.yaml` → `git add` + `git commit` → `make sync`.

## Layout

- `data/*.yaml` — source of truth.
- `templates/*.tex.j2` — section formatting (Jinja2 with `\VAR{}` and `\BLOCK{}` delimiters).
- `generated/*.tex` — committed, machine-written, never hand-edited.
- `main.tex` — thin shell: `\input{preamble.tex}` + `\input{generated/*.tex}` per section.
- `preamble.tex` — `\usepackage`, margins, custom `\resumeSubheading` macros.
- `build.py` — generator. Validates YAML via pydantic, renders templates.
- `tests/` — pydantic model tests + golden-file render tests for each template.

## Overleaf

The repo compiles directly in Overleaf without running `build.py`, because `generated/*.tex` is committed. Edit YAML locally, regenerate with `make data`, push.

### Edit YAML directly on Overleaf (no local round-trip)

With Overleaf premium's GitHub Sync, you can edit YAML in the Overleaf web UI and have `generated/*.tex` regenerated automatically by GitHub Actions. The flow:

```
   Overleaf web (edit YAML)  ──[Overleaf GitHub Sync]──>  GitHub
                                                            │
                                                            │ Action runs build.py,
                                                            │ commits regenerated/*.tex
                                                            ▼
   Overleaf web (compile PDF)  <──[Overleaf GitHub Sync]──  GitHub
```

**One-time setup:**

1. Create a GitHub repo for this CV and push the local master to it:
   ```bash
   git remote add github git@github.com:<you>/<repo>.git
   git push -u github master
   ```
   (Overleaf stays as `origin`; GitHub is a second remote.)

2. In Overleaf: open the project → menu icon (top-left) → **GitHub** → **Link to GitHub** → pick the repo. Choose **automatic syncing** if your premium tier offers it; otherwise the "Sync to GitHub" / "Sync from GitHub" buttons work manually.

3. The workflow at `.github/workflows/check.yml` will run on every push to `master`. On its first run it'll do nothing (generated/ already matches data/). When you next edit YAML and push (or sync from Overleaf), the Action regenerates and pushes back.

**Editing flow afterward:**

| Where you edit | What happens |
|---|---|
| Overleaf web UI | Sync to GitHub → Action regenerates → Sync from GitHub → compile PDF |
| GitHub web UI / locally with `make sync` | Action regenerates → Overleaf pulls → next compile picks it up |

**Caveats:**

- The bot's auto-commit uses `[skip ci]` to avoid an infinite Action loop. Don't strip that tag manually.
- On PRs (rather than pushes to master), the workflow enforces strict "generated/ must match data/" and will fail if you forget to regenerate. Run `make data` and re-push to fix.
- Branch protection rules with required-reviews can block the bot's push back to master. Either disable branch protection on master or grant the bot bypass permission.

## Adding a new section

1. Define a pydantic model in `build.py` (mirror an existing one — `Honor`, `Education`, etc.).
2. Add an entry to the `SECTIONS` manifest in `build.py`: `(name, Model, "list" | "root")`.
3. Create `templates/<name>.tex.j2`.
4. Create `data/<name>.yaml`.
5. Add a fixture pair under `tests/fixtures/<name>_min.yaml` and `tests/fixtures/<name>_min.expected.tex`. The parametrized test in `tests/test_render_simple.py` will pick it up automatically.
6. Wire `\input{generated/<name>.tex}` into `main.tex`.

## Spec & plan

- Design spec: `docs/superpowers/specs/2026-05-09-cv-redesign-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-09-cv-redesign.md`
