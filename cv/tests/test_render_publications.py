import pytest

from build import Author, Links, Publication, format_authors, format_links


def test_format_authors_with_me():
    out = format_authors([
        Author(name="A. Smith"),
        Author(name="R. Scalise", me=True),
        Author(name="B. Jones"),
    ])
    assert out == "A. Smith, \\textbf{R. Scalise}, \\& B. Jones."


def test_format_authors_with_equal():
    out = format_authors([
        Author(name="K. Huang", equal=True),
        Author(name="R. Scalise", me=True, equal=True),
    ])
    assert out == "K. Huang*, \\& \\textbf{R. Scalise}*."


def test_format_authors_with_trailing_ellipsis():
    """If list ends with `...`, the terminating period collapses into the ellipsis."""
    out = format_authors([
        "...",
        Author(name="R. Scalise", me=True),
        "...",
    ])
    assert out == "..., \\textbf{R. Scalise}, ..."


def test_format_authors_with_internal_ellipsis():
    """Ellipsis present but not last — still terminates with period."""
    out = format_authors([
        "...",
        Author(name="R. Scalise", me=True),
        Author(name="C. Finn"),
    ])
    assert out == "..., \\textbf{R. Scalise}, C. Finn."


def test_format_authors_single():
    assert format_authors([Author(name="Solo")]) == "Solo."


def test_format_authors_empty():
    assert format_authors([]) == ""


def test_format_links_arxiv_id_expanded():
    assert format_links(Links(arxiv="2507.21533")) == "\\href{https://arxiv.org/abs/2507.21533}{[arxiv]}"


def test_format_links_arxiv_url_passthrough():
    assert format_links(Links(arxiv="https://example.com/x.pdf")) == "\\href{https://example.com/x.pdf}{[arxiv]}"


def test_format_links_multiple_in_order():
    out = format_links(Links(pdf="https://x/y.pdf", arxiv="2507.21533", github="me/repo"))
    assert out.index("[arxiv]") < out.index("[pdf]") < out.index("[github]")


def test_format_links_github_shorthand():
    assert format_links(Links(github="me/repo")) == "\\href{https://github.com/me/repo}{[github]}"


def test_format_links_doi():
    assert format_links(Links(doi="10.48550/arXiv.2510.19495")) == "\\href{https://doi.org/10.48550/arXiv.2510.19495}{[doi]}"


def test_publication_validates_with_string_authors():
    p = Publication.model_validate({
        "year": 2025, "type": "conference",
        "authors": ["T. Han", "R. Scalise", "B. Boots"],
        "title": "Foo", "venue": "ICRA",
    })
    assert isinstance(p.authors[0], Author)
    assert p.authors[0].name == "T. Han"
    assert p.authors[0].me is False


def test_publication_validates_with_dict_author():
    p = Publication.model_validate({
        "year": 2025, "type": "conference",
        "authors": [{"name": "R. Scalise", "me": True, "equal": True}],
        "title": "Foo", "venue": "ICRA",
    })
    a = p.authors[0]
    assert a.me is True
    assert a.equal is True


def test_publication_ellipsis_passes_through():
    p = Publication.model_validate({
        "year": 2024, "type": "conference",
        "authors": ["...", {"name": "R. Scalise", "me": True}, "..."],
        "title": "X", "venue": "ICRA",
    })
    assert p.authors[0] == "..."
    assert p.authors[2] == "..."
