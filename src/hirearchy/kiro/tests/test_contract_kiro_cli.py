"""Contract of ``KiroCli``: a short kiro-cli command with a deadline (docs/design/kiro-runtime-v3.md 9, 13.1)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from hirearchy.kiro import CliResult, KiroCli
from hirearchy.kiro.testing import IMPLEMENTATIONS, CliHarness

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[KiroCli], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> CliHarness:
    made = make(request, tmp_path, CliHarness)
    assert isinstance(made.cli, KiroCli)
    return made


def test_the_exit_code_and_the_output_are_answered(h: CliHarness) -> None:
    result = h.cli.run(h.succeeds, {"PATH": "/usr/bin:/bin"}, 10)
    assert isinstance(result, CliResult) and result.code == 0 and "hello" in result.output


def test_a_failing_command_answers_its_code_and_output(h: CliHarness) -> None:
    result = h.cli.run(h.fails, {"PATH": "/usr/bin:/bin"}, 10)
    assert result is not None and result.code == 3 and "bad" in result.output


def test_a_binary_that_cannot_start_is_none(h: CliHarness) -> None:
    assert h.cli.run(h.missing, {"PATH": "/usr/bin:/bin"}, 10) is None


def test_an_overrun_is_none_within_the_timeout_plus_a_second(h: CliHarness) -> None:
    started = time.monotonic()
    assert h.cli.run(h.hangs, {"PATH": "/usr/bin:/bin"}, 0.5) is None
    assert time.monotonic() - started < 1.5
