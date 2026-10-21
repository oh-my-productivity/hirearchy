"""``children_limit``: the one reading of a report's ``max_children`` (A3)."""

from __future__ import annotations

import pytest

from hirearchy.access import CHILDREN_LIMIT_ERROR, children_limit
from hirearchy.kernel import OrgError


def test_the_error_text_is_a3() -> None:
    assert CHILDREN_LIMIT_ERROR == "max_children must be a whole number >= 0"


@pytest.mark.parametrize("value", [True, False, -1, -5, "3", "x", "", 3.0, 2.5, None, [3]])
def test_children_limit_refuses_bool_negative_numeric_string_and_float_a3(value: object) -> None:
    with pytest.raises(OrgError) as caught:
        children_limit(value)
    assert str(caught.value) == "max_children must be a whole number >= 0"


@pytest.mark.parametrize("value", [0, 7, 5, 1000])
def test_children_limit_keeps_0_and_7(value: int) -> None:
    assert children_limit(value) == value
