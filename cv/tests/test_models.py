import pytest
from pydantic import ValidationError

from build import Honor, Education, Teaching, validate


def test_honor_valid():
    h = Honor.model_validate({"name": "NeurIPS Best Demo", "year": "2018"})
    assert h.name == "NeurIPS Best Demo"


def test_honor_missing_field_raises():
    with pytest.raises(ValidationError):
        Honor.model_validate({"name": "missing year"})


def test_validate_empty_list():
    assert validate([], Honor, path=__file__) == []


def test_validate_none_returns_empty():
    assert validate(None, Honor, path=__file__) == []


def test_education_minimal():
    e = Education.model_validate({"degree": "PhD", "institution": "UW"})
    assert e.field is None
    assert e.year is None
    assert e.notes is None


def test_teaching_minimal():
    t = Teaching.model_validate({
        "course": "X", "role": "TA", "institution": "U",
    })
    assert t.term is None
