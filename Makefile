.PHONY: all cv site serve watch test clean

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
	rm -f website/index.html website/headshot.jpg
