"""Contract of ``Environment``: the process environment and the dictionary-backed one."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import Environment
from hirearchy.kernel.testing import IMPLEMENTATIONS, EnvHarness

VAR = "HIREARCHY_KERNEL_CONTRACT_VAR"


@pytest.fixture(params=IMPLEMENTATIONS[Environment], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[EnvHarness]:
    harness = cast(Callable[[Path], EnvHarness], request.param)(tmp_path)
    assert isinstance(harness.env, Environment)
    try:
        yield harness
    finally:
        harness.close()


def test_an_unset_variable_is_none(h: EnvHarness) -> None:
    assert h.env.get(VAR) is None


def test_a_variable_that_is_set_is_returned_as_text(h: EnvHarness) -> None:
    h.put(VAR, "value é")
    assert h.env.get(VAR) == "value é"


def test_a_variable_set_after_the_environment_was_made_is_seen(h: EnvHarness) -> None:
    assert h.env.get(VAR) is None
    h.put(VAR, "late")
    assert h.env.get(VAR) == "late"
    h.put(VAR, "later")
    assert h.env.get(VAR) == "later"


def test_the_empty_string_is_a_value(h: EnvHarness) -> None:
    h.put(VAR, "")
    assert h.env.get(VAR) == ""


def test_variables_lists_what_is_set(h: EnvHarness) -> None:
    h.put(VAR, "1")
    assert h.env.variables()[VAR] == "1"


def test_variables_is_a_copy(h: EnvHarness) -> None:
    h.put(VAR, "1")
    snapshot = dict(h.env.variables())
    copy = h.env.variables()
    try:
        copy[VAR] = "changed"  # type: ignore[index]
    except TypeError:
        pass  # a read-only mapping is a copy too
    assert h.env.get(VAR) == "1" and dict(h.env.variables()) == snapshot


def test_directories_are_absolute_paths(h: EnvHarness) -> None:
    assert isinstance(h.env.cwd(), Path) and h.env.cwd().is_absolute()
    assert isinstance(h.env.home(), Path) and h.env.home().is_absolute()
