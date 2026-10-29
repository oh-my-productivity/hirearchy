"""Providers of the ``retro`` ports (ARCHITECTURE.md 6.1).

The ledger of the briefs held sits on the kernel's ``LedgerStore``. The brief is built from the ports of the organization it reads: the sources read the cases, the
contracts, the agents, the event log and health through their ports, the committed charters through ``GitCharterHistory`` (``snapshots``, which ``retro`` may not import) and the
retired copies of services through ``FsServiceRetirements``. A brief is recorded under the name of the process that held it: ``mcp``, or ``cli`` for every other process."""

from __future__ import annotations

from ..agents import AgentDirectory, CharterReader, RetiredArchive
from ..blueprint import RoleLibrary
from ..eventlog import EventReader
from ..health import HealthAnalyzer
from ..kernel import Clock, EventSink, LedgerStore, OrgLayout
from ..mail import MailboxReader
from ..reflection import CaseRecords
from ..retro import RetroBriefs, RetroDue, RetroRecords
from ..retro._brief import FileRetroBriefs
from ..retro._due import FileRetroDue
from ..retro._ledger import LedgerRetroRecords
from ..retro._sources import FileBriefSources
from ..runs import RunLogReader
from ..services import ServiceCatalog, ServiceEvidence, ServiceHints, ServiceStore
from ..settings import OrgSettings
from ..snapshots import OrgHistory
from ..telemetry import ProcessLabel
from ._builder import Builder
from ._charter_history import GitCharterHistory
from ._lazy import PortResolver
from ._service_retirements import FsServiceRetirements


def sources(b: PortResolver) -> FileBriefSources:
    """The sources of the brief over the ports ``b`` builds (the brief and the trigger read the same files)."""
    clock = b.get(Clock)
    return FileBriefSources(
        b.get(CaseRecords), b.get(ServiceHints), b.get(ServiceCatalog), b.get(ServiceStore), b.get(ServiceEvidence), b.get(AgentDirectory), b.get(CharterReader),
        b.get(RetiredArchive), b.get(MailboxReader), b.get(EventReader), b.get(HealthAnalyzer), b.get(RoleLibrary), b.get(RunLogReader), b.get(OrgSettings),
        GitCharterHistory(b.get(OrgHistory), clock), FsServiceRetirements(b.get(AgentDirectory), b.get(OrgLayout)), clock,
    )


def briefs(b: PortResolver) -> FileRetroBriefs:
    """The brief over the ports ``b`` builds."""
    by = "mcp" if b.get(ProcessLabel).get() == "mcp" else "cli"
    return FileRetroBriefs(sources(b), b.get(RetroRecords), b.get(OrgSettings), b.get(EventSink), b.get(Clock), by)


def register(b: Builder) -> None:
    b.provide(RetroRecords, lambda b: LedgerRetroRecords(b.get(LedgerStore)))
    b.provide(RetroBriefs, briefs)
    b.provide(RetroDue, lambda b: FileRetroDue(sources(b), b.get(RetroRecords), b.get(OrgSettings)))
