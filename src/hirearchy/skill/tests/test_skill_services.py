# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio

import testkit
from testkit.reach.hirearchy.core import ROOT, Org
from testkit.skill_world import build_server

ROOT_DIR = testkit.REPO
SKILL = ROOT_DIR / "skills" / "hirearchy" / "SKILL.md"


def test_the_skill_teaches_the_service_workflow_within_its_line_limit():
    text = SKILL.read_text()
    assert len(text.splitlines()) <= 125
    needles = (
        'Once, or repeatedly?', '"every week", "whenever I...", "for each new ..."', "is a **service**",  # elicit
        "which\ninputs change per request and what stays fixed (criteria, format, place)", "`blueprint_example(kind, service=True)`",
        "Before building anything, call `services()`", "never build a new org or team",  # an org that exists
        "`request(service, inputs)`", "the inputs and the per-request budget in one line",
        "their asking for it within the approved per-request budget is the approval", "then `start()`",
        "Nothing runs until you ask for a request",  # plan with no first task
        'ask ONE short question ("Keep it, or what should change?")', "`feedback(task_id, accept|reject, note)`",  # finish
        "reject needs the user's reason in their words", '("always", "never", "from now on")',
        "propose adding it to the contract as a checkable criterion", "`define_service(owner, name, add_acceptance=[<the new criterion>])`", "the resulting criteria",
        "Never edit SERVICE.md or PLAYBOOK.md yourself",
    )
    for needle in needles:
        assert needle in text, needle
    # the order of the workflow: look for a service before eliciting; feedback after the delivery reply
    assert text.index("## 0b.") < text.index("## 1. Elicit") and text.index("Reply briefly") < text.index("record\n   `feedback(")


def test_the_tools_the_skill_names_exist_for_root(tmp_path):
    tools = {t.name: t for t in asyncio.run(build_server(Org.init(tmp_path / "o", "m"), ROOT).list_tools())}
    for name in ("services", "request", "feedback", "define_service", "blueprint_example"):
        assert name in tools and f"`{name}" in SKILL.read_text(), name
    assert "service" in tools["blueprint_example"].inputSchema["properties"]
    instructions = build_server(Org.init(tmp_path / "o2", "m"), ROOT).instructions
    assert "`service=True` for recurring work" in instructions and "check it before building a new org" in instructions
    assert len(instructions) < 2700  # sent on every connection; the limit is 2800: keep 100 characters of headroom for a long path


def test_the_skill_ships_in_the_wheel_and_the_installed_copy_is_this_one(tmp_path):
    from testkit.skill_world import install_skill, skill_source
    pyproject = (ROOT_DIR / "pyproject.toml").read_text()
    assert '"skills/hirearchy/SKILL.md" = "hirearchy/_skill/SKILL.md"' in pyproject  # the wheel copy is this very file
    assert skill_source().read_text() == SKILL.read_text()
    install_skill(tmp_path / "skills")
    assert (tmp_path / "skills" / "hirearchy" / "SKILL.md").read_text() == SKILL.read_text()
