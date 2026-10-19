"""The prompts slice of the ``Org`` facade goes through the ports of the runtime (``state_summarizer``, ``agent_whoami``, ``run_prompt_builder``)."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from orgmcp.app import Org
from orgmcp.app.tests import _prompt_scenarios as scenarios
from orgmcp.kernel import Message
from orgmcp.prompts import RunPromptBuilder, StateSummarizer, Whoami
from orgmcp.prompts.testing import FixedRunPrompt, FixedStateSummary, FixedWhoami

RED = pytest.mark.xfail(strict=True, reason="red: C-prompts")


def use(org: Org, **ports: Any) -> None:
    org.runtime = dataclasses.replace(org.runtime, **ports)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    return scenarios.make(tmp_path)



def test_the_real_ports_are_the_ones_the_architecture_names(org: Org) -> None:
    assert isinstance(org.runtime.state_summarizer, StateSummarizer)
    assert isinstance(org.runtime.agent_whoami, Whoami)
    assert isinstance(org.runtime.run_prompt_builder, RunPromptBuilder)


@RED
def test_the_state_summary_is_the_text_of_the_port_and_the_shown_ids_travel_with_it(org: Org) -> None:
    fixed = FixedStateSummary("state")
    use(org, state_summarizer=fixed)
    assert org.state_summary("ceo") == "state" and org.state_summary("ceo", {"x"}) == "state"
    assert fixed.asked == [("ceo", None), ("ceo", {"x"})]


@RED
def test_whoami_is_the_text_of_the_port(org: Org) -> None:
    fixed = FixedWhoami("who")
    use(org, agent_whoami=fixed)
    assert org.whoami("ceo") == "who" and fixed.asked == ["ceo"]


@RED
def test_the_run_prompt_is_the_text_of_the_port_and_the_batch_travels_with_it(org: Org) -> None:
    fixed = FixedRunPrompt("prompt")
    use(org, run_prompt_builder=fixed)
    batch: list[Message] = []
    assert org.run_prompt("ceo", batch) == "prompt" and fixed.asked == [("ceo", batch)]
