"""The reflection ports over files on disk and over files in memory, a fake case history, and the registry the contract suites iterate over.

``ReflectionWorld`` is what a test gets: the ports of the package built over one organization (the agents, mailboxes, services, settings and clock of
``services``' world, and the run logs of ``runs``' harness), and the means to prepare it. The run logs are stamped by the clock of the messages, so
that a window of a case contains exactly the runs a test made in it. ``FixedCaseHistory`` is the history a test puts in, for the consumers of
``CaseHistory`` (``progress``, ``dashdata``, ``prompts``).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..kernel import STAMP_FORMAT, Message, OrgPaths
from ..runs import RunLogReader
from ..runs.testing import RunsHarness, fs_runs, memory_runs
from ..services import ServiceEvidence
from ..services.testing import ServicesWorld
from ..services.testing import fs_world as services_fs_world
from ..services.testing import memory_world as services_memory_world
from ._cases import DerivedCaseHistory
from ._digest import DigestBuilder
from ._evidence import CaseServiceEvidence
from ._files import OrgServicePaths
from ._ports import RejectedServices, ServicePaths
from ._reports import TextServiceReports
from ._runs import LogRunCounter
from ._sections import EvidenceReflectSection, MailRejectedServices, OwnedServicesListing, OwnerPromptSections, QuotedPlaybookSection, RegressionListSection
from ._steps import TextServiceSteps
from ._timeline import StorePlaybookTimelines
from .api import Case, CaseHistory, ReflectionDigest, ServicePromptSections, ServiceReports, ServiceSteps

# ------------------------------------------------------------------------------ the fake history


class FixedCaseHistory(CaseHistory):
    """The cases a test puts in: ``cases`` answers for the owner and service of each, ``case_of`` finds the case that holds the task."""

    def __init__(self, cases: Sequence[Case] = (), timelines: Mapping[tuple[str, str], Sequence[tuple[int, datetime]]] | None = None) -> None:
        self._cases = list(cases)
        self._timelines = {key: list(value) for key, value in (timelines or {}).items()}

    def cases(self, owner: str, service: str) -> list[Case]:
        return [c for c in self._cases if c.owner == owner and c.service == service]

    def case_of(self, task: Message) -> Case | None:
        return next((c for c in self._cases if task.id in {t.id for t in c.tasks}), None)

    def playbook_timeline(self, owner: str, service: str) -> list[tuple[int, datetime]]:
        return list(self._timelines.get((owner, service), []))


# ------------------------------------------------------------------------------ the worlds


@dataclass(frozen=True)
class ReflectionWorld:
    """The ports over one organization, and the means to prepare it. Addresses of agents: ``ceo``, ``ceo/eng``, ``ceo/qa``, ``ops``; root exists."""

    history: CaseHistory
    digest: ReflectionDigest
    reports: ServiceReports
    sections: ServicePromptSections
    steps: ServiceSteps
    rejections: RejectedServices
    evidence: ServiceEvidence  # the gate over the cases of this world (the real one: ``CaseServiceEvidence``)
    paths: ServicePaths
    s: ServicesWorld  # the organization behind the ports: services, agents, mail, settings, the clock
    runs: RunLogReader  # the run logs the history counts
    use_run: Callable[[str], None]  # the agent makes one run: a log stamped now, by the clock of the messages


def _world(s: ServicesWorld, runs: RunsHarness) -> ReflectionWorld:
    d = s.d
    paths = OrgServicePaths(OrgPaths(d.root))
    history = DerivedCaseHistory(s.catalog, d.agents, d.mail, s.hints, StorePlaybookTimelines(s.store), LogRunCounter(runs.reader))
    digest = DigestBuilder(s.catalog, history)
    rejections = MailRejectedServices(d.mail)
    sections = OwnerPromptSections(
        s.catalog, OwnedServicesListing(s.catalog, history, paths), digest, d.tasks, rejections, QuotedPlaybookSection(s.catalog, paths),
        EvidenceReflectSection(s.catalog, d.settings, paths),
        RegressionListSection(s.catalog, history),
    )

    def use_run(addr: str) -> None:
        runs.add_agent(addr)
        runs.put_log(addr, f"{d.clock.now():{STAMP_FORMAT}}.log", "# run\n")

    return ReflectionWorld(
        history=history, digest=digest, reports=TextServiceReports(d.agents, s.catalog, history, paths), sections=sections,
        steps=TextServiceSteps(d.agents, s.catalog, history, d.mail), rejections=rejections, evidence=CaseServiceEvidence(history, s.catalog), paths=paths, s=s, runs=runs.reader, use_run=use_run,
    )


def fs_world(tmp_path: Path) -> ReflectionWorld:
    return _world(services_fs_world(tmp_path), fs_runs(tmp_path))


def memory_world(tmp_path: Path) -> ReflectionWorld:
    return _world(services_memory_world(tmp_path), memory_runs(tmp_path))


def history_fs(tmp_path: Path) -> CaseHistory:
    return fs_world(tmp_path).history


def history_memory(tmp_path: Path) -> CaseHistory:
    return memory_world(tmp_path).history


def digest_fs(tmp_path: Path) -> ReflectionDigest:
    return fs_world(tmp_path).digest


def digest_memory(tmp_path: Path) -> ReflectionDigest:
    return memory_world(tmp_path).digest


def reports_fs(tmp_path: Path) -> ServiceReports:
    return fs_world(tmp_path).reports


def reports_memory(tmp_path: Path) -> ServiceReports:
    return memory_world(tmp_path).reports


def sections_fs(tmp_path: Path) -> ServicePromptSections:
    return fs_world(tmp_path).sections


def sections_memory(tmp_path: Path) -> ServicePromptSections:
    return memory_world(tmp_path).sections


def steps_fs(tmp_path: Path) -> ServiceSteps:
    return fs_world(tmp_path).steps


def steps_memory(tmp_path: Path) -> ServiceSteps:
    return memory_world(tmp_path).steps


PURE = {"StatsReport"}  # data with derived views (counts that print themselves): one implementation, no fake

IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    CaseHistory: [history_fs, history_memory],
    ReflectionDigest: [digest_fs, digest_memory],
    ServiceReports: [reports_fs, reports_memory],
    ServicePromptSections: [sections_fs, sections_memory],
    ServiceSteps: [steps_fs, steps_memory],
}
