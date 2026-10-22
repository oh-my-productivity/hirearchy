"""Contract of ``RuntimeReadiness``: is kiro-cli ready to run this organization's agents (docs/design/kiro-runtime-v3.md 9)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kiro import RuntimeReadiness
from hirearchy.kiro.testing import IMPLEMENTATIONS, ReadinessHarness

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[RuntimeReadiness], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> ReadinessHarness:
    made = make(request, tmp_path, ReadinessHarness)
    assert isinstance(made.ready, RuntimeReadiness) and isinstance(made.broken, RuntimeReadiness)
    return made


def test_a_ready_world_has_no_problem(h: ReadinessHarness) -> None:
    assert h.ready.state_problem() is None
    assert h.ready.check(h.kiro_bin) is None


def test_a_world_with_a_problem_answers_one_line_from_both_methods(h: ReadinessHarness) -> None:
    for problem in (h.broken.state_problem(), h.broken.check(h.kiro_bin)):
        assert isinstance(problem, str) and problem and "\n" not in problem


def test_neither_method_raises(h: ReadinessHarness) -> None:
    for readiness in (h.ready, h.broken):
        readiness.state_problem()
        readiness.check(h.kiro_bin)
        readiness.check("")
