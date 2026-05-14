from pathlib import Path

import pytest
import yaml

from build import (
    BANNER,
    Education,
    Experience,
    Honor,
    MentoringSection,
    ServiceSection,
    Teaching,
    make_env,
    validate,
    validate_root,
)

FIXTURES = Path(__file__).parent / "fixtures"


def render_list_fixture(section: str, model):
    raw = yaml.safe_load((FIXTURES / f"{section}_min.yaml").read_text())
    entries = validate(raw, model, FIXTURES / f"{section}_min.yaml")
    body = make_env().get_template(f"{section}.tex.j2").render(entries=entries)
    return BANNER.format(section=f"{section}_min") + body


def render_root_fixture(section: str, model):
    raw = yaml.safe_load((FIXTURES / f"{section}_min.yaml").read_text())
    data = validate_root(raw, model, FIXTURES / f"{section}_min.yaml")
    body = make_env().get_template(f"{section}.tex.j2").render(data=data)
    return BANNER.format(section=f"{section}_min") + body


def _expected(section: str) -> str:
    return (FIXTURES / f"{section}_min.expected.tex").read_text()


def _have_fixture(section: str) -> bool:
    return (FIXTURES / f"{section}_min.yaml").exists() and (FIXTURES / f"{section}_min.expected.tex").exists()


# A list of (section, shape, model). Only rows whose fixtures exist will run —
# this lets us add fixtures incrementally per task without breaking the suite.
SIMPLE_SECTIONS = [
    ("honors", "list", Honor),
    ("education", "list", Education),
    ("teaching", "list", Teaching),
    ("mentoring", "root", MentoringSection),
    ("service", "root", ServiceSection),
    ("experience", "list", Experience),
]


@pytest.mark.parametrize("section,shape,model", SIMPLE_SECTIONS)
def test_section_renders(section, shape, model):
    if not _have_fixture(section):
        pytest.skip(f"no fixture for {section} yet")
    if shape == "list":
        actual = render_list_fixture(section, model)
    else:
        actual = render_root_fixture(section, model)
    assert actual.strip() == _expected(section).strip()
