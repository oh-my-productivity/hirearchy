"""The classes of the package over the ports an ``Org`` has *now*: what the legacy functions and the lenient dashboard need (not a port of the package).

The legacy functions are handed an ``Org`` (duck-typed: a feature may not import the facade). They build the classes over the ports that ``Org`` has at
the moment of the call, not over the ones its runtime was first opened with: the dashboard's lenient ``Org`` replaces the agents and the mailboxes with
cached, tolerant variants, and reads a damaged ORG.md as the defaults.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from ..kernel import JsonObject
from ._cases import DerivedCaseHistory
from ._digest import DigestBuilder
from ._files import OrgServicePaths
from ._ports import ConfigSource
from ._reports import TextServiceReports
from ._runs import LogRunCounter
from ._sections import EvidenceReflectSection, MailRejectedServices, OwnedServicesListing, OwnerPromptSections, QuotedPlaybookSection
from ._timeline import StorePlaybookTimelines


class CallableConfig(ConfigSource):
    """The settings as a function gives them (the dashboard's ``Org`` reads a damaged ORG.md as the defaults, and caches the parse)."""

    def __init__(self, config: Callable[[], JsonObject]) -> None:
        self._config = config

    def config(self) -> JsonObject:
        return self._config()


def history_of(org: Any) -> DerivedCaseHistory:
    rt = org.runtime
    return DerivedCaseHistory(
        rt.service_catalog, rt.agents, rt.mailbox, rt.service_hints, StorePlaybookTimelines(rt.service_store), LogRunCounter(rt.run_log_reader),
    )


def digest_of(org: Any) -> DigestBuilder:
    return DigestBuilder(org.runtime.service_catalog, history_of(org))


def reports_of(org: Any) -> TextServiceReports:
    rt = org.runtime
    return TextServiceReports(rt.agents, rt.service_catalog, history_of(org), OrgServicePaths(rt.paths))


def sections_of(org: Any) -> OwnerPromptSections:
    rt = org.runtime
    paths = OrgServicePaths(rt.paths)
    return OwnerPromptSections(
        rt.service_catalog, OwnedServicesListing(rt.service_catalog, history_of(org), paths), digest_of(org), rt.task_query,
        MailRejectedServices(rt.mailbox), QuotedPlaybookSection(rt.service_catalog, paths),
        EvidenceReflectSection(rt.service_catalog, CallableConfig(lambda: cast(JsonObject, org.config)), paths),
    )
