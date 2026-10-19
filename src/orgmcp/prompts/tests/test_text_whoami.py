"""``TextWhoami``: asks the summary it is given, with no list of shown tasks, and puts the charter of the agent below it."""

from __future__ import annotations

import pytest

from orgmcp.agents.testing import MemoryAgents
from orgmcp.kernel import OrgError
from orgmcp.prompts._whoami import TextWhoami
from orgmcp.prompts.testing import FixedStateSummary

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-prompts")


def made(summary: FixedStateSummary) -> TextWhoami:
    agents = MemoryAgents()
    agents.put("ceo/AGENT.md", "---\nrole: Chief\n---\n# Role: Chief\n\nRun.\n")
    return TextWhoami(agents, agents, summary)


def test_the_charter_follows_the_summary_it_was_given() -> None:
    summary = FixedStateSummary("STATE")
    assert made(summary).whoami("ceo") == "STATE\n\n## Charter\n# Role: Chief\n\nRun."
    assert summary.asked == [("ceo", None)]


def test_the_root_has_a_charter_text_of_its_own() -> None:
    assert made(FixedStateSummary("S")).whoami("root").endswith("\n\n## Charter\n(root has no charter)")


def test_the_summary_is_not_asked_for_an_agent_that_does_not_exist() -> None:
    summary = FixedStateSummary("S")
    with pytest.raises(OrgError):
        made(summary).whoami("nobody")
    assert summary.asked == []


def test_the_address_is_the_one_the_directory_returns() -> None:
    summary = FixedStateSummary("S")
    made(summary).whoami("ceo/")  # a trailing slash names the same agent
    assert summary.asked == [("ceo", None)]
