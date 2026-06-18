.PHONY: all cv site serve watch test clean publish-cv

all: cv site

cv:
	uv run python cv/build.py
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -pdf -interaction=nonstopmode -cd cv/main.tex; \
	fi

site:
	uv run python website/build.py

serve: site
	cd website && python3 -m http.server 8000 --bind 127.0.0.1

watch:
	find data/ cv/templates/ -type f | entr make all

test:
	uv run pytest -v

clean:
	rm -f cv/generated/*.tex cv/main.pdf cv/main.aux cv/main.log cv/main.out
	rm -f cv/main.fdb_latexmk cv/main.fls cv/main.synctex.gz
	rm -f website/*.html website/headshot.jpg website/CNAME

# Regenerate the CV LaTeX and refresh the gitignored Overleaf staging mirror
# (.overleaf-cv), FLATTENED so main.tex sits at the repo root -- Overleaf
# compiles from the project root (no `latexmk -cd`), so root-level main.tex +
# generated/ + preamble.tex resolve with zero config. Contents: main.tex,
# preamble.tex, generated/*.tex, data/*.yaml (no website, no python generator).
# Commits locally; you push to 'overleaf' with your token.
PUBLISH_DIR := .overleaf-cv
publish-cv:
	@echo ">> regenerating cv/generated from data/"
	@if command -v uv >/dev/null 2>&1; then \
		uv run python cv/build.py; \
	elif [ -x .venv/bin/python ] && .venv/bin/python -c "import pydantic, jinja2" 2>/dev/null; then \
		.venv/bin/python cv/build.py; \
	else \
		echo "ERROR: need 'uv' on PATH or a populated .venv to regenerate (system python3 lacks pydantic/jinja2) -- run 'make publish-cv' on the host." >&2; \
		exit 1; \
	fi
	@test -d $(PUBLISH_DIR)/.git || { echo "ERROR: $(PUBLISH_DIR)/ staging repo not found -- run the Overleaf sync setup first." >&2; exit 1; }
	@echo ">> refreshing $(PUBLISH_DIR) (flattened: main.tex at root + generated/ + data/)"
	@find $(PUBLISH_DIR) -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
	@printf '%s\n' '*.aux' '*.log' '*.out' '*.fdb_latexmk' '*.fls' '*.synctex.gz' '*.toc' 'main.pdf' > $(PUBLISH_DIR)/.gitignore
	@cp cv/main.tex cv/preamble.tex $(PUBLISH_DIR)/
	@mkdir -p $(PUBLISH_DIR)/generated $(PUBLISH_DIR)/data
	@cp cv/generated/*.tex $(PUBLISH_DIR)/generated/
	@for f in identity education experience publications honors teaching mentoring service; do \
		cp data/$$f.yaml $(PUBLISH_DIR)/data/$$f.yaml; \
	done
	@cd $(PUBLISH_DIR) && git add -A && \
		if git diff --cached --quiet; then echo ">> no CV changes to publish"; else \
			git -c user.name="Rosario Scalise" -c user.email="rosario@cs.uw.edu" \
				commit -q -m "CV: refresh from portfolio $$(date -u +%FT%TZ)" && echo ">> committed CV refresh"; fi
	@echo ">> done. Push to Overleaf:  cd $(PUBLISH_DIR) && git push overleaf main:main   (enter your Overleaf token)"
