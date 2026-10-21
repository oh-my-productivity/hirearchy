"""Contract of ``Whoami``: the state summary and the charter."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import OrgError
from hirearchy.prompts import Whoami
from hirearchy.prompts.testing import IMPLEMENTATIONS, PromptsWorld

from ._support import implementations



@pytest.fixture(params=implementations(IMPLEMENTATIONS[Whoami]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> PromptsWorld:
    made = cast(Callable[[Path], PromptsWorld], request.param)(tmp_path)
    assert isinstance(made.whoami, Whoami)
    return made


def test_it_is_the_state_summary_then_the_charter(w: PromptsWorld) -> None:
    w.agent("ceo", {"role": "Chief"}, "# Role: Chief\n\nRun the company.")
    w.budget("ceo", 4)
    assert w.whoami.whoami("ceo") == f"{w.summary.state_summary('ceo')}\n\n## Charter\n# Role: Chief\n\nRun the company."


def test_the_root_has_no_charter(w: PromptsWorld) -> None:
    assert w.whoami.whoami("root") == f"{w.summary.state_summary('root')}\n\n## Charter\n(root has no charter)"


def test_the_contract_of_an_open_task_is_in_it(w: PromptsWorld) -> None:
    w.agent("ceo", {"role": "Chief"}, "Run.")
    w.send("root", "ceo", "task", "Plan", "## Acceptance criteria\nexactly 33 words")
    assert "> exactly 33 words" in w.whoami.whoami("ceo")


def test_an_agent_that_does_not_exist_is_refused(w: PromptsWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: nobody"):
        w.whoami.whoami("nobody")
