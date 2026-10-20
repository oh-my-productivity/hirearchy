# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.legacy.orgmcp.core import ROOT, OrgError

ENG = "ceo/eng"
CHARTER = "---\nrole: Engineer v2\n---\n# New charter\nDo more."


# ------------------------------------------------------------------- QA-1 / QA-2: write guard
@pytest.mark.parametrize(
    "path",
    [
        "ceo/AGENT.md.", "ceo/Agent.MD", "ceo/MEMORY.MD", "ceo/Memory.md", "ceo/INBOX/x.md", "ceo/Sent/x.md",
        "ceo/inflight/x.md", "ceo/Runs/x.log", "ceo/.PAUSED", "ceo/.Retired/x", "ceo/ORG.md.", "ceo/Org.md",
    ],
)
def test_protected_names_are_refused_in_any_spelling(org, path):
    with pytest.raises(OrgError):
        org.write("ceo", path, "x")


@pytest.mark.parametrize("path", ["ceo/ENG/AGENT.md", "ceo/Eng/MEMORY.md", "ceo/ENG/work/x.md", "ceo/eng/agent.md", "ceo/eng/Memory.md"])
def test_case_variants_of_a_direct_report_cannot_dodge_the_charter_only_rule(org, path):
    with pytest.raises(OrgError):
        org.write("ceo", path, CHARTER)
    assert org.charter(ENG)[0]["role"] == "Engineer"
    assert org.memory(ENG) == ""


def test_report_charter_authority_check_cannot_be_dodged_by_case(org):
    greedy = "---\nrole: Engineer\ntools: [shell]\n---\n# x"  # ceo has no tools, so it cannot grant any
    for path in ("ceo/eng/AGENT.md", "ceo/ENG/AGENT.md", "ceo/eng/agent.md"):
        with pytest.raises(OrgError):
            org.write("ceo", path, greedy)
    assert "tools" not in org.charter(ENG)[0] or not org.charter(ENG)[0]["tools"]


def test_memory_cap_cannot_be_dodged_by_case(org):
    big = "word " * (int(org.config["memory_max_words"]) + 10)
    for path in ("ceo/MEMORY.md", "ceo/memory.md", "ceo/Memory.md"):
        with pytest.raises(OrgError):
            org.write("ceo", path, big)
    assert org.memory("ceo") == ""
    org.write("ceo", "ceo/MEMORY.md", "short")  # the exact spelling still works
    assert org.memory("ceo") == "short"


def test_legitimate_writes_still_work(org):
    org.write("ceo", "ceo/work/notes.md", "n")
    org.write("ceo", "ceo/work/AnyCase/Notes.md", "n")  # case is only policed against protected/existing names
    org.write("ceo", "ceo/eng/AGENT.md", CHARTER)  # a parent edits its direct report's charter
    assert org.charter(ENG)[0]["role"] == "Engineer v2"
    org.write(ROOT, "ceo/AGENT.md", CHARTER)  # root edits a direct report's charter
    org.write(ROOT, "ORG.md", org.root.joinpath("ORG.md").read_text(encoding="utf-8"))


def test_writing_a_case_twin_of_an_existing_file_is_refused(org):
    org.write("ceo", "ceo/work/Plan.md", "a")
    with pytest.raises(OrgError, match="letter case"):
        org.write("ceo", "ceo/work/plan.md", "b")
    with pytest.raises(OrgError, match="letter case"):
        org.write("ceo", "ceo/WORK/x.md", "b")
    assert (org.dir("ceo") / "work" / "Plan.md").read_text() == "a"


def test_agent_md_cannot_create_an_agent_anywhere(org):
    charter = "---\nrole: sneaky\ncan_hire: true\nmax_children: 99\n---\n# x"
    for actor, path in (
        ("ceo", "ceo/new/AGENT.md"),
        ("ceo", "ceo/work/AGENT.md"),
        ("ceo", "ceo/new/deeper/AGENT.md"),  # would be addressable as ceo/new/deeper without a parent agent
        ("ceo", "ceo/eng/sub/AGENT.md"),
        ("ceo", "ceo/NEW/AGENT.md"),
        (ROOT, "newagent/AGENT.md"),
        (ROOT, "AGENT.md"),
    ):
        with pytest.raises(OrgError):
            org.write(actor, path, charter)
    assert org.agents() == ["ceo", ENG]
    assert not (org.dir("ceo") / "new").exists() and not (org.root / "newagent").exists()


def test_hire_is_the_way_to_create_agents(org):
    assert org.hire("ceo", "ops", "Ops", "Do ops.") == "ceo/ops"
    org.write("ceo", "ceo/ops/AGENT.md", CHARTER)  # and then the parent may edit the charter
    assert org.charter("ceo/ops")[0]["role"] == "Engineer v2"
