"""``wire_reflection``: the runtime has the four ports of ``reflection``, built from the services, agents, mailboxes, run logs, tasks, settings and layout of
the runtime - so a test that overrides them runs the rules over its own fakes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from hirearchy.agents import AgentDirectory
from hirearchy.app import Org, wire_reflection, wiring
from hirearchy.kernel import OrgError
from hirearchy.mail import MailboxReader
from hirearchy.reflection import CaseHistory, CaseRecords, ReflectionDigest, ServicePromptSections, ServiceReports
from hirearchy.reflection._cases import DerivedCaseHistory
from hirearchy.reflection._digest import DigestBuilder
from hirearchy.reflection._records import DerivedCaseRecords
from hirearchy.reflection._evidence import CaseServiceEvidence
from hirearchy.reflection._allowance import CaseAllowanceOf
from hirearchy.reflection._judged import CaseJudgedVersions
from hirearchy.reflection._reports import TextServiceReports
from hirearchy.reflection._sections import OwnerPromptSections
from hirearchy.reflection.testing import FixedCaseHistory
from hirearchy.services import CaseAllowance, JudgedVersions, ServiceEvidence, ServiceStore
from hirearchy.services.testing import FixedAllowance, FixedJudgedVersions, RefusingServiceEvidence


def test_the_runtime_has_the_reflection_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.case_history, DerivedCaseHistory) and isinstance(runtime.case_history, CaseHistory)
    assert isinstance(runtime.reflection_digest, DigestBuilder) and isinstance(runtime.reflection_digest, ReflectionDigest)
    assert isinstance(runtime.service_reports, TextServiceReports) and isinstance(runtime.service_reports, ServiceReports)
    assert isinstance(runtime.service_prompt_sections, OwnerPromptSections) and isinstance(runtime.service_prompt_sections, ServicePromptSections)
    assert hasattr(wire_reflection, "register")


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.case_history is not None and runtime.reflection_digest is not None and runtime.service_reports is not None
    assert runtime.service_prompt_sections is not None
    assert list(tmp_path.iterdir()) == []


def test_each_port_is_built_once_per_organization(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.case_history is runtime.case_history and runtime.service_reports is runtime.service_reports


def test_the_digest_and_the_sections_read_the_history_of_the_runtime(tmp_path: Path) -> None:
    fixed = FixedCaseHistory()
    runtime = wiring.open_runtime(tmp_path, {CaseHistory: fixed})
    assert runtime.case_history is fixed
    assert runtime.service_reports.services_text("root").startswith("No services yet.")


def test_the_org_asks_the_ports_of_its_runtime(tmp_path: Path) -> None:
    (tmp_path / "ORG.md").write_text("---\nmission: test\n---\nrules\n", encoding="utf-8")
    org = Org(tmp_path)
    assert org.runtime.service_reports.services_text("root").startswith("No services yet.")
    assert isinstance(org.runtime.agents, AgentDirectory)


def test_the_runtime_has_the_port_of_services_that_reflection_implements(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.service_evidence, CaseServiceEvidence) and isinstance(runtime.service_evidence, ServiceEvidence)
    assert runtime.service_evidence is runtime.service_evidence and list(tmp_path.iterdir()) == []


def test_the_runtime_has_the_judged_versions_that_reflection_implements(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.judged_versions, CaseJudgedVersions) and isinstance(runtime.judged_versions, JudgedVersions)
    assert runtime.judged_versions is runtime.judged_versions and runtime.judged_versions.base("ceo", "brief", "no-such-task") is None
    fixed = FixedJudgedVersions()
    assert wiring.open_runtime(tmp_path, {JudgedVersions: fixed}).judged_versions is fixed


def test_the_runtime_has_the_case_allowance_that_reflection_implements(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.case_allowance, CaseAllowanceOf) and isinstance(runtime.case_allowance, CaseAllowance)
    assert runtime.case_allowance is runtime.case_allowance and runtime.case_allowance.left("ceo", "brief", "no-such-task") is None
    fixed = FixedAllowance()
    assert wiring.open_runtime(tmp_path, {CaseAllowance: fixed}).case_allowance is fixed


def test_the_evidence_reads_the_history_of_the_runtime_and_can_be_overridden(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path, {CaseHistory: FixedCaseHistory()})
    with pytest.raises(OrgError, match="^unknown criterion or assertion for `brief`: R1. Its criteria: none; its regression assertions: none yet"):
        runtime.service_evidence.links("ceo", "brief", ["R1"])
    refusing = RefusingServiceEvidence("no")
    assert wiring.open_runtime(tmp_path, {ServiceEvidence: refusing}).service_evidence is refusing


def test_the_case_history_reads_the_charters(tmp_path: Path) -> None:
    """The 7th collaborator of the history is the runtime's charter reader: a task sent before its assignee's charter says it was created reads as such."""
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    org.delegate("root", "ceo", "a task", "do it", "it is done", budget=3)
    (org.root / "ceo" / "AGENT.md").write_text("---\nrole: Chief\ncan_hire: true\ncreated: '2099-01-01T00:00:00+00:00'\n---\nbody\n", encoding="utf-8")
    (case,) = org.runtime.case_history.one_off_cases()
    assert case.runs_unknown == "sent before ceo was hired again: the retired team's run logs are not read"


def test_the_runtime_has_case_records(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.case_records, DerivedCaseRecords) and isinstance(runtime.case_records, CaseRecords)
    assert [r.service for r in runtime.case_records.records()] == [""]  # an empty organization: root's one-off record only
    assert runtime.case_records.deliveries("ceo").deliveries == ()


class RecordingPort:
    """A port that records every call made to it and hands them on to the real one."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def __getattr__(self, name: str) -> Any:
        found = getattr(self._inner, name)

        def call(*args: Any, **kw: Any) -> Any:
            self.calls.append((name, args))
            return found(*args, **kw)

        return call


def test_service_evidence_reads_history_catalog_store_and_mail(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    org.define_service(
        "root", "ceo", "brief", description="A brief.", inputs=[{"name": "topic", "description": "what", "required": True}], acceptance=["Short"],
        deliverable={"description": "one file"}, budget=5, playbook="1. Search.\n2. Write.",
    )
    mail, store, history = RecordingPort(org.runtime.mailbox), RecordingPort(org.runtime.service_store), RecordingPort(FixedCaseHistory())
    runtime = wiring.open_runtime(tmp_path / "org", {MailboxReader: mail, ServiceStore: store, CaseHistory: history})
    found = runtime.service_evidence.watch("ceo", "brief")
    assert [(i.id, i.state) for i in found] == [("P1", "kept"), ("P2", "kept")]  # the catalog's playbook, read as it would migrate
    assert [name for name, _ in history.calls] == ["chains"]  # the cases come from the history port
    assert ("received", ("root",)) in mail.calls and [c for c in mail.calls if c[0] == "received"] == [("received", ("root",))]  # one read of the client's mail
    assert ("versions", ("ceo", "brief", "SERVICE")) in store.calls  # the contract versions come from the store
