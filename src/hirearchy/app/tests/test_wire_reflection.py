"""``wire_reflection``: the runtime has the four ports of ``reflection``, built from the services, agents, mailboxes, run logs, tasks, settings and layout of
the runtime - so a test that overrides them runs the rules over its own fakes."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.agents import AgentDirectory
from hirearchy.app import Org, wire_reflection, wiring
from hirearchy.kernel import OrgError
from hirearchy.reflection import CaseHistory, ReflectionDigest, ServicePromptSections, ServiceReports
from hirearchy.reflection._cases import DerivedCaseHistory
from hirearchy.reflection._digest import DigestBuilder
from hirearchy.reflection._evidence import CaseServiceEvidence
from hirearchy.reflection._judged import CaseJudgedVersions
from hirearchy.reflection._reports import TextServiceReports
from hirearchy.reflection._sections import OwnerPromptSections
from hirearchy.reflection.testing import FixedCaseHistory
from hirearchy.services import JudgedVersions, ServiceEvidence
from hirearchy.services.testing import FixedJudgedVersions, RefusingServiceEvidence


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


def test_the_evidence_reads_the_history_of_the_runtime_and_can_be_overridden(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path, {CaseHistory: FixedCaseHistory()})
    with pytest.raises(OrgError, match="^unknown criterion or assertion for `brief`: R1. Its criteria: none; its regression assertions: none yet"):
        runtime.service_evidence.links("ceo", "brief", ["R1"])
    refusing = RefusingServiceEvidence("no")
    assert wiring.open_runtime(tmp_path, {ServiceEvidence: refusing}).service_evidence is refusing
