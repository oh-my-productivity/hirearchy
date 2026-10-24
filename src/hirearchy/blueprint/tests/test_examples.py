# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio
import re
from pathlib import Path

import pytest
import testkit
from testkit.blueprint_world import ex
from testkit.reach.hirearchy.core import ROOT, Org, OrgError
from testkit.blueprint_world import server_of_the_environment

from testkit.blueprint_world import bpm, services_mod

from hirearchy.blueprint._budgeting import BudgetPlanner
from hirearchy.blueprint._example_texts import SERVICE_BUDGETS

ROOT_DIR = testkit.REPO


def codes(found, level=None):
    return {i.code for i in found if level is None or i.level == level}


def fill(text: str, base: Path, *, uncomment: bool = False) -> str:
    """What the assistant does with a template: replace the placeholders it needs with the user's values."""
    for n in ("docs", "data", "proj", "deliverables"):
        (base / n).mkdir(exist_ok=True)
    text = (text.replace("<folder-with-your-files>", "docs").replace("<folder-with-your-data>", "data")
            .replace("<project-folder>", "proj").replace("<name>", "briefs").replace("<service-name>", "my-service")
            .replace("<input-name>", "topic"))
    if uncomment:
        text = "\n".join(re.sub(r"^# (task:|  )", r"\1", line) if line.startswith(("# task:", "#   ")) else line
                         for line in text.split("\n"))
    return text


def filled_service(kind: str, base: Path, **kw) -> dict:
    return bpm.load_text(fill(ex.example(kind, base, service=True), base, **kw))


ALLOWED_WARNINGS = {"path-delivery", "path-parent", "workspace-new", "shell-unconfined"}


@pytest.mark.parametrize("kind", ex.KINDS)
def test_service_templates_validate_once_filled(kind, tmp_path):
    bp = filled_service(kind, tmp_path)
    found = bpm.validate(bp, allowed_roots=[tmp_path])
    assert not bpm.errors(found), [i.render() for i in found]
    assert codes(found) <= ALLOWED_WARNINGS, [i.render() for i in found]
    assert "task" not in bp and len(bp["services"]) == 1 and "deliverable" not in bp["needs"]
    out = bpm.propose_text(bp, allowed_roots=[tmp_path])
    assert bpm.PLAN_HEADING in out and "Nothing runs until you ask for a request" in out and re.search(r"^plan_id: [0-9a-f]{12}$", out, re.M)


@pytest.mark.parametrize("kind", ex.KINDS)
def test_the_service_template_budgets_follow_the_planners_rule(kind, tmp_path):
    """D-E5-2: each template carries the number the planner gives a service without a budget, so the templates cannot drift from the rule."""
    bp = filled_service(kind, tmp_path)
    agents = bpm._resolve(bp, None, [tmp_path], [])
    planner = BudgetPlanner()
    expected = planner.service_budget({}, planner.estimate(agents)["total"], bp["needs"]["budget_runs"], round_runs=planner.client_round(agents))
    assert SERVICE_BUDGETS[kind] == expected
    assert bp["services"][0]["budget"] == expected


@pytest.mark.parametrize("kind", ex.KINDS)
def test_service_templates_with_the_first_request_uncommented_validate(kind, tmp_path):
    bp = filled_service(kind, tmp_path, uncomment=True)
    assert bp["task"] == {"service": "my-service", "inputs": {"topic": "<value>"}, "title": "<Short title of this request>"}
    bp["task"]["inputs"]["topic"] = "ai chips"
    found = bpm.validate(bp, allowed_roots=[tmp_path])
    assert not bpm.errors(found), [i.render() for i in found]
    assert "First request, started on approval: my-service (topic: ai chips)." in bpm.plan_for_user(bp, found, allowed_roots=[tmp_path])


@pytest.mark.parametrize("kind", ex.KINDS)
def test_service_templates_apply_and_are_requestable(kind, tmp_path):
    org = Org.init(tmp_path / "org", "x", {"poll_seconds": 0.05})
    bp = filled_service(kind, tmp_path)
    s = bpm.apply(org, bp, allowed_roots=[tmp_path])
    assert s.services == ["my-service"] and s.task_id == ""
    assert org.request(ROOT, "my-service", {"topic": "x"}).service == "my-service"


@pytest.mark.parametrize("kind", ex.KINDS)
def test_service_templates_comment_every_field_and_keep_the_schema_header(kind, tmp_path):
    text = ex.example(kind, tmp_path, service=True)
    assert text.lstrip().startswith("# Blueprint schema in one paragraph") and "`services`" in text.split("\nmission:")[0]
    lines = text.split("\nservices:")[1].split("\n")
    for field in ("- name:", "owner:", "inputs:", "acceptance:", "budget:", "locked:", "playbook:", "required:"):
        line = next(ln for ln in lines if field in ln)
        assert "#" in line.split(field, 1)[1] or ("#" in line and field == "playbook:"), (kind, line)
    for field in ("description:", "deliverable:"):  # their placeholders and sub-fields explain themselves
        assert any(field in ln for ln in lines)
    assert text.count("<service-name>") >= 2 and "# task:" in text and "\ntask:" not in text
    assert "OPTIONAL first request" in text


def test_the_plain_templates_are_unchanged_by_the_service_option(tmp_path):
    for kind in ex.KINDS:
        plain = ex.example(kind, tmp_path)
        assert plain == ex.example(kind, tmp_path, service=False)
        assert "\ntask:\n" in plain and "services:" not in plain.split("\nmission:")[1]
        svc = ex.example(kind, tmp_path, service=True)
        assert svc != plain and svc.count("\nservices:") == 1


def test_example_rejects_an_unknown_kind_with_service_too(tmp_path):
    with pytest.raises(OrgError, match="unknown kind 'poetry'"):
        ex.example("poetry", tmp_path, service=True)


@pytest.mark.parametrize("kind", ex.KINDS)
def test_the_generated_playbook_fits_the_word_cap_for_every_team_shape(kind, tmp_path):
    for n in ("docs", "data", "proj", "deliverables"):
        (tmp_path / n).mkdir(exist_ok=True)
    bp = filled_service(kind, tmp_path)
    agents = bpm._resolve(bp, None, [tmp_path], [])
    text = bpm.default_playbook(agents[0], agents, bp["services"][0], 25)
    assert 120 < len(text.split()) < 600, len(text.split())
    org = Org.init(tmp_path / "o", "x")
    org.hire(ROOT, "lead", "Lead", "Lead the team.")
    org.define_service(  # the runtime's own check of a playbook: a text over the word cap is refused here
        ROOT, "lead", "my-service", description="d", acceptance=["a"], deliverable={"description": "d"}, budget=1, playbook=text,
    )


# ------------------------------------------------------------------------------------------ the MCP tools
def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


@pytest.fixture
def root_server(tmp_path, monkeypatch):
    for var in ("ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "org"))
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    return server_of_the_environment(), work


def test_blueprint_example_tool_has_a_service_flag(root_server):
    server, work = root_server
    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    assert "service" in tools["blueprint_example"].inputSchema["properties"]
    assert "standing service" in tools["blueprint_example"].description
    for kind in ex.KINDS:
        plain = call(server, "blueprint_example", kind=kind)
        assert plain == call(server, "blueprint_example", kind=kind, service=False) and "\nservices:" not in plain
        svc = call(server, "blueprint_example", kind=kind, service=True)
        assert svc == ex.example(kind, work, service=True) and "\nservices:" in svc
    assert "services" in tools["propose_org"].description and "first request" in tools["propose_org"].description
    assert "services" in tools["apply_org"].description


def test_propose_and_apply_a_services_only_blueprint_through_the_tools(root_server, tmp_path):
    server, work = root_server
    for n in ("docs", "data", "proj", "deliverables"):
        (work / n).mkdir()
    text = fill(call(server, "blueprint_example", kind="research", service=True), work)
    out = call(server, "propose_org", blueprint=text)
    assert bpm.PLAN_HEADING in out and "Nothing runs until you ask for a request" in out
    pid = re.search(r"^plan_id: ([0-9a-f]{12})$", out, re.M).group(1)
    assert pid == bpm.plan_id(bpm.load_text(text))
    call(server, "create_org", mission="services")
    with pytest.raises(Exception, match="plan_id does not match"):
        call(server, "apply_org", blueprint=text.replace("budget: 24", "budget: 23"), approved=True, plan_id=pid)
    reply = call(server, "apply_org", blueprint=text, approved=True, plan_id=pid)
    assert "defined 1 service(s) of lead: my-service" in reply and "Nothing runs yet" in reply
    assert "request(service, inputs)" in reply and "Next step: call start()" not in reply
    services = call(server, "services")
    assert "my-service (offered by lead; contract v1, playbook v1)" in services and "topic*" in services
    sent = call(server, "request", service="my-service", inputs={"topic": "ai"})
    assert "requested service `my-service` from lead" in sent and "Call start()" in sent


def test_apply_with_a_first_request_says_to_start(root_server):
    server, work = root_server
    text = fill(call(server, "blueprint_example", kind="research", service=True), work, uncomment=True)
    text = text.replace("<value>", "ai chips").replace("<Short title of this request>", "Brief on ai chips")
    out = call(server, "propose_org", blueprint=text)
    pid = re.search(r"^plan_id: ([0-9a-f]{12})$", out, re.M).group(1)
    assert "First request, started on approval: my-service (topic: ai chips)." in out
    call(server, "create_org", mission="services")
    reply = call(server, "apply_org", blueprint=text, approved=True, plan_id=pid)
    assert "first request: service my-service, task " in reply and "Next step: call start()" in reply


README = ROOT_DIR / "README.md"
EXAMPLE = ROOT_DIR / "examples" / "blueprint-service.yaml"


def test_the_readme_documents_services_and_reflection():
    text = README.read_text()
    assert text.index("## Create an org from a goal") < text.index("## Services and reflection") < text.index("## Health")
    section = text.split("## Services and reflection")[1].split("\n## Health")[0]
    for needle in (
        "**service**", "**Reflection**", "`SERVICE.md`", "`PLAYBOOK.md`", "history/", "never stored", "`define_service`",
        "`revise_playbook(service, content, reason, evidence)`", "`request(service, inputs, ...)`", "`feedback(task_id, accept", "`report(..., lessons)`",
        "hirearchy services", "define-service OWNER NAME", "retire-service OWNER NAME", "no MCP tool for it",
        "# Your services", "# Playbook: <service>", "# Reflect before you start: <service>", "byte-identical",
        "can never mean \"lowering the bar\"", "`playbook_max_words`", "`locked: true`", "quiet", "`services:`",
        "blueprint_example(kind, service=True)", "examples/blueprint-service.yaml", "cap for ONE request", "nothing runs until you ask for",
        "**Limitations.**", "No schedules", "sibling or\ncross-team requests", "progress window rule",
    ):
        assert needle in section, needle
    assert "`services`, `define-service`, `request`, `feedback`, `retire-service`" in text.split("## Use")[1].split("### Progress")[0]
    # phase 0a documents source, criterion ids, the regression list and the evidence gate (the cap was 90)
    assert len(section.splitlines()) < 98


def test_readme_lists_every_msg_deliver_key_in_pipeline_order():
    shapes = (ROOT_DIR / "tests" / "golden" / "expected" / "events" / "line_shapes.txt").read_text().splitlines()
    block = shapes[shapes.index("msg.deliver:") + 1:]
    keys = []
    for line in block:
        if not line.startswith("  "):
            break
        keys.append(line.split(":")[0].strip())
    pipeline = keys[keys.index("id"):keys.index("trace_rule") + 1]  # after the envelope (v ... trace), up to the last key
    row = next(line for line in README.read_text().splitlines() if line.startswith("| `msg.deliver` |"))
    listed = re.findall(r"`([a-z_]+)`", row.split("(+")[0])
    assert listed == pipeline
    assert "`trace_candidates`" in row.split("(+")[1]


def test_the_shipped_service_example_validates_plans_and_applies(tmp_path):
    """The service example asks for 24 runs per request: the 0a.3 rule (D-E5-2) of one client round on the estimate, as the research template."""
    (tmp_path / "deliverables").mkdir()
    text = EXAMPLE.read_text().replace("~/deliverables/weekly-briefs", str(tmp_path / "deliverables" / "weekly-briefs"))
    bp = bpm.load_text(text)
    found = bpm.validate(bp, allowed_roots=[tmp_path])
    assert not bpm.errors(found), [i.render() for i in found]
    assert codes(found) <= {"path-delivery", "path-parent"}, [i.render() for i in found]
    assert bpm._is_request(bp) and bp["services"][0]["name"] == "weekly-brief" and not bpm._plain(bp)
    block = bpm.plan_for_user(bp, found, allowed_roots=[tmp_path])
    assert len(block.splitlines()) <= 42 and "Services (kept ready" in block
    assert "First request, started on approval: weekly-brief (topic: solid-state batteries)." in block
    org = Org.init(tmp_path / "org", "x", {"poll_seconds": 0.05})
    s = bpm.apply(org, bp, allowed_roots=[tmp_path])
    assert s.services == ["weekly-brief"] and s.budget == 24 and s.service_request == "weekly-brief"
    task = org.find_received("lead", s.task_id)
    assert task.service == "weekly-brief" and task.playbook == 1 and "- topic: solid-state batteries" in task.body
    assert services_mod.read_playbook(org, "lead", "weekly-brief").body.startswith("## Steps")


def test_the_shipped_service_example_as_a_services_only_blueprint(tmp_path):
    (tmp_path / "deliverables").mkdir()
    bp = bpm.load_text(EXAMPLE.read_text().replace("~/deliverables/weekly-briefs", str(tmp_path / "deliverables" / "weekly-briefs")))
    bp.pop("task")
    assert not bpm.errors(bpm.validate(bp, allowed_roots=[tmp_path]))
    assert "Nothing runs until you ask for a request" in bpm.plan_for_user(bp, allowed_roots=[tmp_path])


def test_the_shipped_service_example_header_commands_are_real():
    head = EXAMPLE.read_text().split("mission:")[0]
    for command in ("hirearchy plan examples/blueprint-service.yaml", "hirearchy apply examples/blueprint-service.yaml", "hirearchy request weekly-brief"):
        assert command in head, command
