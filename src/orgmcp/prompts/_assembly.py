"""How the roles of ``prompts`` are put together: the one place that knows which small class serves which port of another.

``app/wire_prompts.py`` calls these with the ports of the runtime, and ``testing.py`` with the ones of its worlds, so that the real prompts and the
ones over fakes are made the same way.
"""

from __future__ import annotations

from ..access import AccessScopes, ToolNaming
from ..agents import AgentDirectory, CharterReader
from ..budget import BudgetQuery
from ..eligibility import AgentStates
from ..kernel import OrgLayout
from ..mail import MailboxReader, TaskQuery
from ..reflection import ServicePromptSections
from ..settings import OrgSettings
from ..strays import StrayRegistry
from ._agent_line import StatusAgentLine
from ._batch import BatchRenderer
from ._briefing import CappedMemory, PromptBriefing
from ._files import FilesGuide
from ._notices import RuntimeNotices
from ._ports import ServiceNames
from ._quote import LiteralQuoter
from ._run import TextRunPromptBuilder
from ._state import TextStateSummarizer
from ._tasks import HeldTasks, OutstandingDelegations
from ._upstream import SoleUpstreamTask
from ._whoami import TextWhoami
from .api import RunPromptBuilder, StateSummarizer, Whoami


def state_summarizer(
    agents: AgentDirectory, charters: CharterReader, mail: MailboxReader, tasks: TaskQuery, budgets: BudgetQuery, states: AgentStates,
    scopes: AccessScopes, naming: ToolNaming, layout: OrgLayout,
) -> StateSummarizer:
    quoter = LiteralQuoter(layout)
    return TextStateSummarizer(
        agents, charters, budgets, FilesGuide(scopes, naming, layout), StatusAgentLine(charters, states, budgets, tasks, mail),
        HeldTasks(tasks, quoter), OutstandingDelegations(tasks, agents, states),
    )


def whoami(agents: AgentDirectory, charters: CharterReader, summary: StateSummarizer) -> Whoami:
    return TextWhoami(agents, charters, summary)


def run_prompt_builder(
    agents: AgentDirectory, charters: CharterReader, settings: OrgSettings, mail: MailboxReader, naming: ToolNaming, strays: StrayRegistry,
    services: ServiceNames, sections: ServicePromptSections, layout: OrgLayout, summary: StateSummarizer,
) -> RunPromptBuilder:
    return TextRunPromptBuilder(
        agents, PromptBriefing(settings, charters, CappedMemory(charters, settings)), summary,
        BatchRenderer(mail, LiteralQuoter(layout), SoleUpstreamTask(mail)), naming, RuntimeNotices(strays, services, sections),
    )
