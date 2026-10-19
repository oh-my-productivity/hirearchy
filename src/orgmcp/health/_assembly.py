"""The analyzer over the ports an ``Org`` has *now*: what the legacy functions and the lenient dashboard need (not a port of the package).

The legacy functions are handed an ``Org`` (duck-typed: a feature may not import the facade). They build the analyzer over the ports that
``Org`` has at the moment of the call, not over the ones its runtime was first opened with: the dashboard's lenient ``Org`` replaces the
mailboxes, the budgets and the pause flags with tolerant variants, reads a damaged ORG.md as the defaults and counts runs in its own cache.
"""

from __future__ import annotations

from typing import Any, cast

from ..kernel import JsonObject
from ._analyzer import FileHealthAnalyzer
from ._hired import CharterHireDates
from ._ports import CallableConfig, CallableRunCount, FsCharterStamp
from ._rework import MailClientRework
from ._thresholds import SettingsHealthThresholds


def thresholds_of(org: Any) -> SettingsHealthThresholds:
    return SettingsHealthThresholds(CallableConfig(lambda: cast(JsonObject, org.config)))


def analyzer_of(org: Any) -> FileHealthAnalyzer:
    rt = org.runtime
    return FileHealthAnalyzer(
        rt.agents, rt.mailbox, rt.run_log_reader, CallableRunCount(lambda addr: cast(int, org.runs_used(addr))), rt.budget_query,
        rt.pause_store, rt.agent_states, thresholds_of(org), MailClientRework(rt.agents, rt.mailbox),
        CharterHireDates(rt.charters, FsCharterStamp(rt.paths)), rt.clock,
    )
