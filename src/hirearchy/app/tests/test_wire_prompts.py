"""``wire_prompts``: the runtime has the three texts, built from the ports of the runtime."""

from __future__ import annotations

import pytest

from pathlib import Path

from hirearchy.access import AccessScopes, ToolNaming
from hirearchy.access.testing import StaticAccess
from hirearchy.agents import AgentDirectory, CharterReader
from hirearchy.app import wiring
from hirearchy.budget import BudgetQuery
from hirearchy.budget.testing import FixedBudget
from hirearchy.eligibility import AgentStates
from hirearchy.kernel import Message, OrgLayout, OrgPaths
from hirearchy.mail import MailboxReader, TaskQuery
from hirearchy.mail.testing import MemoryMailbox, memory_mailbox
from hirearchy.prompts import AgentLines, ContextRenderer, FilesLines, RunPromptBuilder, StateSummarizer, TaskQuoter, UpstreamTasks, Whoami
from hirearchy.prompts._agent_line import StatusAgentLine
from hirearchy.prompts._batch import BatchRenderer
from hirearchy.prompts._files import FilesGuide
from hirearchy.prompts._quote import LiteralQuoter
from hirearchy.prompts._upstream import SoleUpstreamTask
from hirearchy.prompts._run import TextRunPromptBuilder
from hirearchy.prompts._state import TextStateSummarizer
from hirearchy.prompts._whoami import TextWhoami
from hirearchy.prompts.testing import FixedRunPrompt, FixedSections, FixedStates, FixedStateSummary, FixedWhoami, NamedServices, ToldOnce
from hirearchy.reflection import ServicePromptSections
from hirearchy.services import ServiceCatalog
from hirearchy.settings import OrgSettings
from hirearchy.strays import StrayRegistry



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


def test_whoami_is_built_over_the_summary_of_the_runtime(tmp_path: Path) -> None:
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", "---\nrole: Chief\n---\nRun.\n")
    runtime = wiring.open_runtime(tmp_path, {AgentDirectory: box.agents, CharterReader: box.agents, StateSummarizer: FixedStateSummary("S")})
    assert runtime.agent_whoami.whoami("ceo") == "S\n\n## Charter\nRun."


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
    assert text.startswith("# hirearchy run: you are `ceo`\n\n# Organization\n") and "\nNOTICE\n\n# SECTIONS\n\n# New messages for this run (0)" in text
    assert "- Budget: 7 run(s) left" in runtime.state_summarizer.state_summary("ceo")
    assert "\n\n## Charter\n" in runtime.agent_whoami.whoami("ceo")
    assert list(tmp_path.iterdir()) == []


def test_the_runtime_hands_out_the_parts_the_texts_are_made_of(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.agent_lines, StatusAgentLine) and isinstance(runtime.agent_lines, AgentLines)
    assert isinstance(runtime.task_quoter, LiteralQuoter) and isinstance(runtime.task_quoter, TaskQuoter)
    assert isinstance(runtime.files_lines, FilesGuide) and isinstance(runtime.files_lines, FilesLines)
    assert isinstance(runtime.upstream_tasks, SoleUpstreamTask) and isinstance(runtime.upstream_tasks, UpstreamTasks)
    assert isinstance(runtime.context_renderer, BatchRenderer) and isinstance(runtime.context_renderer, ContextRenderer)


def test_the_context_renderer_is_made_of_the_quoter_and_the_upstream_of_the_runtime(tmp_path: Path) -> None:
    class Quote(TaskQuoter):
        def quote(self, m: Message) -> str:
            return "QUOTED"

    class Nothing(UpstreamTasks):
        def upstream(self, addr: str, delegated: Message) -> None:
            return None

    box = MemoryMailbox()
    task = Message(sender="ceo", to="ceo/eng", type="task", body="b", title="T", id="20260101T000000000001-ceo-aaaa")
    result = Message(sender="ceo/eng", to="ceo", type="result", body="r", status="done", reply_to=task.id, id="20260101T000000000002-ceo.eng-bbbb")
    box.store(task)
    runtime = wiring.open_runtime(tmp_path, {TaskQuoter: Quote(), UpstreamTasks: Nothing(), MailboxReader: box})
    shown = runtime.context_renderer.render("ceo", result)
    assert "verbatim:]\nQUOTED\n" in shown and "probably serves" not in shown
