"""The history and the reports over the ports an ``Org`` has *now*: what ``progress``'s legacy parts still need (not a port of the package).

The legacy ``progress`` functions are handed a runtime (duck-typed: a feature may not import the facade) and build the classes over its ports at the
moment of the call. Goes with the last caller (``app/wire_progress.RuntimeParts``, E3-close).
"""

from __future__ import annotations

from typing import Any

from ._cases import DerivedCaseHistory
from ._files import OrgServicePaths
from ._reports import TextServiceReports
from ._runs import LogRunCounter
from ._timeline import StorePlaybookTimelines


def history_of(org: Any) -> DerivedCaseHistory:
    rt = org.runtime
    return DerivedCaseHistory(
        rt.service_catalog, rt.agents, rt.mailbox, rt.service_hints, StorePlaybookTimelines(rt.service_store), LogRunCounter(rt.run_log_reader),
    )


def reports_of(org: Any) -> TextServiceReports:
    rt = org.runtime
    return TextServiceReports(rt.agents, rt.service_catalog, history_of(org), OrgServicePaths(rt.paths))
