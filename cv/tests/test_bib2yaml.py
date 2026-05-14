import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import bib2yaml  # noqa: E402


# --- Author normalization -------------------------------------------------

@pytest.mark.parametrize("inp,expected", [
    ("Tyler Han", "T. Han"),
    ("Yanda Bao", "Y. Bao"),
    ("Bhaumik Mehta", "B. Mehta"),
    ("S.S. Srinivasa", "S.S. Srinivasa"),
    ("M. G. Castro", "M. G. Castro"),
    ("Yiren (Ramon) Qu", "Y. Qu"),
    ("Han, Tyler", "T. Han"),                    # bibtex Lastname, Firstname form
    ("van Berg, Pieter", "P. van Berg"),         # surname-first, multi-word last
    ("Madonna", "Madonna"),                      # single name
])
def test_normalize_author_name_non_me(inp, expected):
    assert bib2yaml.normalize_author_name(inp) == expected


def test_normalize_author_name_me_returns_dict():
    out = bib2yaml.normalize_author_name("Rosario Scalise")
    assert out == {"name": "R. Scalise", "me": True}


def test_normalize_author_name_me_already_initialed():
    out = bib2yaml.normalize_author_name("R. Scalise")
    assert out == {"name": "R. Scalise", "me": True}


def test_parse_authors_field_splits_on_and():
    out = bib2yaml.parse_authors_field("Tyler Han and Yanda Bao and Rosario Scalise")
    assert out == ["T. Han", "Y. Bao", {"name": "R. Scalise", "me": True}]


# --- Type / venue / link inference ---------------------------------------

def test_detect_type_misc_with_arxiv_archiveprefix():
    entry = {"kind": "misc", "fields": {"archiveprefix": "arXiv", "eprint": "2507.21533"}}
    assert bib2yaml.detect_type_and_venue(entry) == ("preprint", "arXiv", None)


def test_detect_type_article():
    entry = {"kind": "article", "fields": {"journal": "IJRR"}}
    assert bib2yaml.detect_type_and_venue(entry) == (
        "journal", "IJRR", "The International Journal of Robotics Research (IJRR)",
    )


def test_detect_type_inproceedings_with_full_name_lookup():
    entry = {"kind": "inproceedings", "fields": {"booktitle": "Conference on Robot Learning"}}
    assert bib2yaml.detect_type_and_venue(entry) == (
        "conference", "CoRL", "Conference on Robot Learning (CoRL)",
    )


def test_detect_type_inproceedings_unknown_venue_no_full():
    entry = {"kind": "inproceedings", "fields": {"booktitle": "Some Random Workshop"}}
    assert bib2yaml.detect_type_and_venue(entry) == (
        "conference", "Some Random Workshop", None,
    )


def test_detect_links_from_eprint():
    assert bib2yaml.detect_links({"fields": {"eprint": "2507.21533"}}) == {"arxiv": "2507.21533"}


def test_detect_links_strips_arxiv_prefix():
    assert bib2yaml.detect_links({"fields": {"eprint": "arXiv:2507.21533"}}) == {"arxiv": "2507.21533"}


def test_detect_links_from_url():
    out = bib2yaml.detect_links({"fields": {"url": "https://arxiv.org/abs/2507.21533"}})
    assert out == {"arxiv": "2507.21533"}


def test_detect_links_doi_when_no_arxiv():
    assert bib2yaml.detect_links({"fields": {"doi": "10.48550/arXiv.x"}}) == {"doi": "10.48550/arXiv.x"}


# --- BibTeX parsing ------------------------------------------------------

def test_parse_bibtex_basic():
    text = """@article{key, title = {Foo}, year = {2024} }"""
    out = bib2yaml.parse_bibtex(text)
    assert out["kind"] == "article"
    assert out["key"] == "key"
    assert out["fields"]["title"] == "Foo"
    assert out["fields"]["year"] == "2024"


def test_parse_bibtex_handles_nested_braces():
    text = """@misc{k, title = {{VAMOS}: A model}, year = {2025} }"""
    out = bib2yaml.parse_bibtex(text)
    assert out["fields"]["title"] == "{VAMOS}: A model"


def test_parse_bibtex_unparseable():
    with pytest.raises(SystemExit):
        bib2yaml.parse_bibtex("not bibtex at all")


# --- Venue lookup --------------------------------------------------------

@pytest.mark.parametrize("inp,expected_short,expected_full", [
    # Short label as input
    ("ICRA", "ICRA", "International Conference on Robotics \\& Automation (ICRA)"),
    ("CoRL", "CoRL", "Conference on Robot Learning (CoRL)"),
    ("corl", "CoRL", "Conference on Robot Learning (CoRL)"),  # case-insensitive
    # Full name as input
    ("Conference on Robot Learning", "CoRL", "Conference on Robot Learning (CoRL)"),
    ("International Conference on Robotics and Automation", "ICRA",
     "International Conference on Robotics \\& Automation (ICRA)"),
    ("International Conference on Robotics & Automation", "ICRA",
     "International Conference on Robotics \\& Automation (ICRA)"),
    # Year prefix stripped
    ("2025 IEEE International Conference on Robotics and Automation", "ICRA",
     "International Conference on Robotics \\& Automation (ICRA)"),
    # Trailing parenthetical stripped
    ("Conference on Robot Learning (CoRL)", "CoRL", "Conference on Robot Learning (CoRL)"),
    # "Proceedings of" stripped
    ("Proceedings of the Conference on Robot Learning", "CoRL", "Conference on Robot Learning (CoRL)"),
    # Trailing year stripped
    ("CoRL 2024", "CoRL", "Conference on Robot Learning (CoRL)"),
    # HRI variants — both with and without hyphen
    ("Conference on Human-Robot Interaction", "HRI",
     "International Conference on Human-Robot Interaction (HRI)"),
    ("Conference on Human Robot Interaction", "HRI",
     "International Conference on Human-Robot Interaction (HRI)"),
    # IJRR
    ("The International Journal of Robotics Research", "IJRR",
     "The International Journal of Robotics Research (IJRR)"),
    # arXiv (no full)
    ("arXiv", "arXiv", None),
])
def test_lookup_venue_known(inp, expected_short, expected_full):
    short, full = bib2yaml.lookup_venue(inp)
    assert short == expected_short
    assert full == expected_full


@pytest.mark.parametrize("inp", [
    "Some Random Workshop on Foo",
    "Workshop on Model Learning at RSS",  # workshop venues are paper-specific
    "",
])
def test_lookup_venue_unknown(inp):
    short, full = bib2yaml.lookup_venue(inp)
    assert short == inp.strip()
    assert full is None


# --- End-to-end: user's example ------------------------------------------

USER_EXAMPLE = """@misc{han2026modelpredictiveadversarialimitation,
      title={Model Predictive Adversarial Imitation Learning for Planning from Observation},
      author={Tyler Han and Yanda Bao and Bhaumik Mehta and Gabriel Guo and Anubhav Vishwakarma and Emily Kang and Sanghun Jung and Rosario Scalise and Jason Zhou and Bryan Xu and Byron Boots},
      year={2026},
      eprint={2507.21533},
      archivePrefix={arXiv},
      primaryClass={cs.RO},
      url={https://arxiv.org/abs/2507.21533},
}"""


def test_end_to_end_user_example_yaml_loadable():
    """The user's example bibtex must yield valid YAML matching the expected shape."""
    entry = bib2yaml.parse_bibtex(USER_EXAMPLE)
    yaml_text = bib2yaml.render_yaml_entry(entry)
    parsed = yaml.safe_load(yaml_text)
    # YAML loads to a list with one entry (since we wrote `- year: ...`)
    assert isinstance(parsed, list) and len(parsed) == 1
    e = parsed[0]
    assert e["year"] == 2026
    assert e["type"] == "preprint"
    assert e["title"] == "Model Predictive Adversarial Imitation Learning for Planning from Observation"
    assert e["venue"] == "arXiv"
    assert e["links"] == {"arxiv": "2507.21533"}

    # Authors: 11 entries, R. Scalise marked me
    assert len(e["authors"]) == 11
    assert e["authors"][0] == "T. Han"
    assert e["authors"][1] == "Y. Bao"
    assert e["authors"][2] == "B. Mehta"
    assert e["authors"][3] == "G. Guo"
    assert e["authors"][4] == "A. Vishwakarma"
    assert e["authors"][5] == "E. Kang"
    assert e["authors"][6] == "S. Jung"
    assert e["authors"][7] == {"name": "R. Scalise", "me": True}
    assert e["authors"][8] == "J. Zhou"
    assert e["authors"][9] == "B. Xu"
    assert e["authors"][10] == "B. Boots"


def test_end_to_end_validates_against_publication_model():
    """The script's output must round-trip through build.py's Publication model."""
    sys.path.insert(0, str(ROOT))
    from build import Publication

    entry = bib2yaml.parse_bibtex(USER_EXAMPLE)
    yaml_text = bib2yaml.render_yaml_entry(entry)
    pub_dict = yaml.safe_load(yaml_text)[0]
    pub = Publication.model_validate(pub_dict)
    assert pub.year == 2026
    assert pub.type == "preprint"
    assert pub.authors[7].me is True


CORL_EXAMPLE = """@inproceedings{schmittle2025lrn,
    title = {Long Range Navigator (LRN): Extending robot planning horizons beyond metric maps},
    author = {Matthew Schmittle and Rohan Baijal and Nathan Hatch and Rosario Scalise and Mateo Guaman Castro and Sidharth Talia and Khimya Khetarpal and Byron Boots and Siddhartha Srinivasa},
    booktitle = {Conference on Robot Learning},
    year = {2025},
}"""


def test_end_to_end_corl_emits_venue_full():
    """A CoRL paper should produce both venue: CoRL and venue_full: full name."""
    entry = bib2yaml.parse_bibtex(CORL_EXAMPLE)
    yaml_text = bib2yaml.render_yaml_entry(entry)
    pub_dict = yaml.safe_load(yaml_text)[0]
    assert pub_dict["venue"] == "CoRL"
    assert pub_dict["venue_full"] == "Conference on Robot Learning (CoRL)"
    assert pub_dict["type"] == "conference"


def test_venue_override_looks_up_full_name():
    """--venue CoRL should look up the canonical full name from the table."""
    entry = bib2yaml.parse_bibtex(CORL_EXAMPLE)
    # Override with a different known venue — full name should switch to match.
    yaml_text = bib2yaml.render_yaml_entry(entry, venue_override="ICRA")
    pub_dict = yaml.safe_load(yaml_text)[0]
    assert pub_dict["venue"] == "ICRA"
    assert pub_dict["venue_full"] == "International Conference on Robotics \\& Automation (ICRA)"


def test_venue_override_unknown_no_full():
    """--venue with a label not in the table just sets venue, drops venue_full."""
    entry = bib2yaml.parse_bibtex(CORL_EXAMPLE)
    yaml_text = bib2yaml.render_yaml_entry(entry, venue_override="MySymposium")
    pub_dict = yaml.safe_load(yaml_text)[0]
    assert pub_dict["venue"] == "MySymposium"
    assert "venue_full" not in pub_dict


# --- YAML scalar quoting -------------------------------------------------

@pytest.mark.parametrize("inp,expected", [
    ("simple", "simple"),
    ("", '""'),
    ("with: colon", '"with: colon"'),
    ("- starts with dash", '"- starts with dash"'),  # leading - flips YAML to a sequence
    ("yes", '"yes"'),
    ("123abc", "123abc"),
    ("2507.21533", '"2507.21533"'),                  # bare numbers must stay strings (arxiv id)
    ("42", '"42"'),                                   # likewise for integer-looking strings
    (True, "true"),
    (False, "false"),
    (42, "42"),
])
def test_yaml_scalar(inp, expected):
    assert bib2yaml.yaml_scalar(inp) == expected
