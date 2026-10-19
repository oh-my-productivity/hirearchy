"""``wire_prompts``: the runtime has the three texts, built from the ports of the runtime."""

from __future__ import annotations

import pytest

from pathlib import Path

from orgmcp.access import AccessScopes, ToolNaming
from orgmcp.access.testing import StaticAccess
from orgmcp.agents import AgentDirectory, CharterReader
from orgmcp.app import wiring
from orgmcp.budget import BudgetQuery
from orgmcp.budget.testing import FixedBudget
from orgmcp.eligibility import AgentStates
from orgmcp.kernel import OrgLayout, OrgPaths
from orgmcp.mail import MailboxReader, TaskQuery
from orgmcp.mail.testing import MemoryMailbox, memory_mailbox
from orgmcp.prompts import RunPromptBuilder, StateSummarizer, Whoami
from orgmcp.prompts._run import TextRunPromptBuilder
from orgmcp.prompts._state import TextStateSummarizer
from orgmcp.prompts._whoami import TextWhoami
from orgmcp.prompts.testing import FixedRunPrompt, FixedSections, FixedStates, FixedStateSummary, FixedWhoami, NamedServices, ToldOnce
from orgmcp.reflection import ServicePromptSections
from orgmcp.services import ServiceCatalog
from orgmcp.settings import OrgSettings
from orgmcp.strays import StrayRegistry

RED = pytest.mark.xfail(strict=True, reason="red: C-prompts")


def test_the_runtime_has_the_three_texts(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.state_summarizer, TextStateSummarizer) and isinstance(runtime.state_summarizer, StateSummarizer)
    assert isinstance(runtime.agent_whoami, TextWhoami) and isinstance(runtime.agent_whoami, Whoami)
    assert isinstance(runtime.run_prompt_builder, TextRunPromptBuilder) and isinstance(runtime.run_prompt_builder, RunPromptBuilder)


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.state_summarizer is not None and runtime.agent_whoami is not None and runtime.run_prompt_builder is not None
    assert list(tmp_path.iterdir()) == []


def test_an_override_replaces_the_port(tmp_path: Path) -> None:
    summary, who, prompt = FixedStateSummary("s"), FixedWhoami("w"), FixedRunPrompt("p")
    runtime = wiring.open_runtime(tmp_path, {StateSummarizer: summary, Whoami: who, RunPromptBuilder: prompt})
    assert runtime.state_summarizer is summary and runtime.agent_whoami is who and runtime.run_prompt_builder is prompt


@RED
def test_whoami_is_built_over_the_summary_of_the_runtime(tmp_path: Path) -> None:
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", "---\nrole: Chief\n---\nRun.\n")
    runtime = wiring.open_runtime(tmp_path, {AgentDirectory: box.agents, CharterReader: box.agents, StateSummarizer: FixedStateSummary("S")})
    assert runtime.agent_whoami.whoami("ceo") == "S\n\n## Charter\nRun."


@RED
def test_every_collaborator_of_the_prompts_comes_from_the_runtime(tmp_path: Path) -> None:
    """The whole run prompt over fakes: nothing of the organization directory is read or written."""
    mail = memory_mailbox(tmp_path)
    box = mail.reader
    assert isinstance(box, MemoryMailbox)
    access = StaticAccess(agents=box.agents)
    access.put_agent("ceo", {"role": "Chief"})
    states, budgets, services = FixedStates(), FixedBudget(mail.tasks, box.agents, box.agents), NamedServices()
    states.words["ceo"] = "running"
    budgets.held["ceo"] = 7
    services.offered["ceo"] = ["weekly-brief"]
    sections, strays = FixedSections(), ToldOnce()
    sections.text["ceo"] = "\n# SECTIONS\n"
    strays.notices["ceo"] = "NOTICE"
    runtime = wiring.open_runtime(tmp_path, {
        AgentDirectory: box.agents, CharterReader: box.agents, MailboxReader: box, TaskQuery: mail.tasks, BudgetQuery: budgets, AgentStates: states,
        AccessScopes: access, ToolNaming: access, OrgSettings: access.settings, OrgLayout: OrgPaths(box.agents.root), StrayRegistry: strays,
        ServiceCatalog: services, ServicePromptSections: sections,
    })
    text = runtime.run_prompt_builder.run_prompt("ceo", [])
    assert text.startswith("# orgmcp run: you are `ceo`\n\n# Organization\n") and "\nNOTICE\n\n# SECTIONS\n\n# New messages for this run (0)" in text
    assert "- Budget: 7 run(s) left" in runtime.state_summarizer.state_summary("ceo")
    assert "\n\n## Charter\n" in runtime.agent_whoami.whoami("ceo")
    assert list(tmp_path.iterdir()) == []
