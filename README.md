# Portfolio Monorepo

This repo builds Rosario Scalise's portfolio from a shared set of editable YAML files in `data/`.

`data/identity.yaml` is the single source of truth for identity fields. The CV target renders YAML into LaTeX snippets under `cv/generated/`, and the website target renders `website/index.html` from the same publication and identity data.

## Editing Flow

Edit files in `data/`, then run:

```sh
make all
```

Use `make cv` for only the CV snippets and optional PDF build, `make site` for only the website, and `make test` for the CV test suite.

## Publications

Add or edit publications in `data/publications.yaml`. To show a publication on the website, add:

```yaml
featured: true
```

Optional website media can be added with a `media:` block on the publication entry. The CV build ignores these extra website-only fields.

## Deployment

TODO: GitHub Action will run `make site` and publish `website/` to `gh-pages`.
