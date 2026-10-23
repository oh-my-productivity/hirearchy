"""``wire_hierarchy``: the runtime has the two hierarchy ports, built from the agents, access, settings, templates, mailboxes, budget, delivery,
clock and event sink of the runtime - so a test that overrides them runs the rules over its own fakes."""

from __future__ import annotations

from pathlib import Path

from hirearchy.access.testing import StaticAccess
from hirearchy.access import AccessScopes, AuthorityPolicy, ModelResolver
from hirearchy.agents import AgentDirectory, AgentRegistry, CharterReader
from hirearchy.agents.testing import MemoryAgents
from hirearchy.app import wiring
from hirearchy.budget import BudgetQuery
from hirearchy.budget.testing import FixedBudget, MovingDelivery
from hirearchy.delivery import MessageDelivery
from hirearchy.delivery.testing import RecordingDelivery
from hirearchy.hierarchy import Hiring, Retired, Retirement
from hirearchy.hierarchy._hiring import RuleHiring
from hirearchy.hierarchy._retirement import RuleRetirement
from hirearchy.kernel import RUNTIME, Clock, EventSink, join_frontmatter
from hirearchy.kernel.testing import FakeClock, ListEventSink, SequenceIdGenerator
from hirearchy.mail import TaskQuery
from hirearchy.mail._tasks import DerivedTaskQuery
from hirearchy.mail.testing import MemoryMailbox
from hirearchy.settings import OrgSettings
from hirearchy.templates import DocumentTemplates, Notices
from hirearchy.templates.testing import RecordingNotices


def test_the_runtime_has_the_two_hierarchy_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.hiring, RuleHiring) and isinstance(runtime.hiring, Hiring)
    assert isinstance(runtime.retirement, RuleRetirement) and isinstance(runtime.retirement, Retirement)


def test_building_the_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.hiring is not None and runtime.retirement is not None
    assert list(tmp_path.iterdir()) == []


def test_every_runtime_has_its_own_ports(tmp_path: Path) -> None:
    assert wiring.open_runtime(tmp_path).hiring is not wiring.open_runtime(tmp_path).hiring


def test_an_override_replaces_a_port(tmp_path: Path) -> None:
    class Nobody(Hiring):
        def hire(self, actor: str, name: str, role: str, charter: str, **kw: object) -> str:
            return "from-the-fake"

    fake = Nobody()
    runtime = wiring.open_runtime(tmp_path, {Hiring: fake})
    assert runtime.hiring is fake and isinstance(runtime.retirement, RuleRetirement)


def test_every_collaborator_comes_from_the_runtime(tmp_path: Path) -> None:
    files = MemoryAgents()
    files.put("ceo/AGENT.md", join_frontmatter({"role": "Chief", "can_hire": True, "tools": []}, "# Role\n"))
    box = MemoryMailbox(files)
    tasks = DerivedTaskQuery(box)
    clock = FakeClock()
    events = ListEventSink()
    inner = RecordingDelivery(clock, SequenceIdGenerator(clock))
    budget = FixedBudget(tasks, files, files)
    delivery = MovingDelivery(inner, budget)
    access = StaticAccess(agents=files, org_md="---\ndefault_model: claude-opus-5.5\n---\nrules\n")
    notices = RecordingNotices()
    overrides: dict[type, object] = {
        AgentDirectory: files, CharterReader: files, AgentRegistry: files, OrgSettings: access.settings, AccessScopes: access,
        AuthorityPolicy: access, ModelResolver: access, TaskQuery: tasks, BudgetQuery: budget, MessageDelivery: delivery,
        Notices: notices, Clock: clock, EventSink: events,
    }
    runtime = wiring.open_runtime(tmp_path, overrides)

    assert runtime.hiring.hire("ceo", "eng", "Engineer", "Build.") == "ceo/eng"
    assert files.exists("ceo/eng") and files.read("ceo/eng/AGENT.md") is not None
    assert "created: '2026-10-18T10:00:00+00:00'" in (files.read("ceo/eng/AGENT.md") or "")  # the clock of the runtime
    (hired,) = events.events
    assert hired.kind == "agent.hire" and hired.fields["model"] == "claude-opus-5.5"  # the model resolver and the sink of the runtime

    budget.held["ceo/eng"] = 5
    assert runtime.retirement.retire_team("ceo", "eng", "done") == Retired("ceo/eng", 5, "ceo")
    (note,) = inner.messages
    assert note.sender == RUNTIME and note.to == "ceo" and note.body.startswith("budget_returned: ceo/eng | 5 | ceo | done")  # the notices of the runtime
    assert not files.exists("ceo/eng") and events.events[-1].kind == "agent.retire"
    assert list(tmp_path.iterdir()) == []  # nothing on disk: the agents, the delivery and the sink were the fakes
    assert isinstance(runtime.document_templates, DocumentTemplates)
