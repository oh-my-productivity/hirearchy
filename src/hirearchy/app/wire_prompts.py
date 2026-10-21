"""Providers of the ``prompts`` ports (ARCHITECTURE.md 6.1).

The texts read the agents, charters, settings, tools and paths, mailboxes, tasks, budgets, states and services of the runtime they are built from; how the
small roles they are made of are put together is the package's (``prompts._assembly``)."""

from __future__ import annotations

from ..access import AccessScopes, ToolNaming
from ..agents import AgentDirectory, CharterReader
from ..budget import BudgetQuery
from ..eligibility import AgentStates
from ..kernel import OrgLayout
from ..mail import MailboxReader, TaskQuery
from ..prompts import AgentLines, ContextRenderer, FilesLines, RunPromptBuilder, StateSummarizer, TaskQuoter, UpstreamTasks, Whoami
from ..prompts import _assembly
from ..reflection import ServicePromptSections
from ..services import ServiceCatalog
from ..settings import OrgSettings
from ..strays import StrayRegistry
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(TaskQuoter, lambda b: _assembly.task_quoter(b.get(OrgLayout)))
    b.provide(
        AgentLines,
        lambda b: _assembly.agent_lines(b.get(CharterReader), b.get(AgentStates), b.get(BudgetQuery), b.get(TaskQuery), b.get(MailboxReader)),
    )
    b.provide(FilesLines, lambda b: _assembly.files_lines(b.get(AccessScopes), b.get(ToolNaming), b.get(OrgLayout)))
    b.provide(UpstreamTasks, lambda b: _assembly.upstream_tasks(b.get(MailboxReader)))
    b.provide(ContextRenderer, lambda b: _assembly.context_renderer(b.get(MailboxReader), b.get(TaskQuoter), b.get(UpstreamTasks)))
    b.provide(
        StateSummarizer,
        lambda b: _assembly.state_summarizer(
            b.get(AgentDirectory), b.get(CharterReader), b.get(MailboxReader), b.get(TaskQuery), b.get(BudgetQuery), b.get(AgentStates),
            b.get(AccessScopes), b.get(ToolNaming), b.get(OrgLayout),
        ),
    )
    b.provide(Whoami, lambda b: _assembly.whoami(b.get(AgentDirectory), b.get(CharterReader), b.get(StateSummarizer)))
    b.provide(
        RunPromptBuilder,
        lambda b: _assembly.run_prompt_builder(
            b.get(AgentDirectory), b.get(CharterReader), b.get(OrgSettings), b.get(MailboxReader), b.get(ToolNaming), b.get(StrayRegistry),
            b.get(ServiceCatalog), b.get(ServicePromptSections), b.get(OrgLayout), b.get(StateSummarizer),
        ),
    )
