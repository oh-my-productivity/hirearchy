"""The write guard, case by case: the names an agent may not write, in every spelling a filesystem would treat as the same name.

macOS and Windows ignore letter case (and Unicode form), Windows also trailing dots and blanks; the guard compares names through one folded
key, so it behaves the same on every filesystem and never asks which kind it is. The texts of the refusals are the ones agents are shown.
Everything here runs over both implementations; the filesystem's own aliasing is in ``test_filesystem_guards.py``."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.orgfiles import OrgFileWriter
from orgmcp.orgfiles.testing import IMPLEMENTATIONS, OrgFilesHarness

from ._support import make, refusal, team, written


SERVICES = (
    "services/ is managed by the runtime: the contract (SERVICE.md) is written by your parent with define_service, "
    "and you change your playbook (PLAYBOOK.md) with revise_playbook"
)
CHARTER_ONLY = "inside a direct report's directory you may only edit its charter (AGENT.md)"
CREATE_BY_HIRE = "AGENT.md can only be written for an existing direct report; create agents with hire (it enforces hiring rights, limits and authority)"
OWN_CHARTER = "your charter is owned by your parent"
ORG_MD = "ORG.md is owned by root"
CHARTER = "---\nrole: Engineer v2\n---\n# New charter\nDo more."


def runtime(name: str) -> str:
    return f"{name} is managed by the runtime; use send/delegate/report to communicate"


def reserved(exact: str) -> str:
    return f"that name is reserved: it must be spelled exactly `{exact}`"


def twin(part: str, existing: str) -> str:
    return f"`{part}` differs only by letter case from the existing `{existing}`; use the exact name `{existing}`"


@pytest.fixture(params=IMPLEMENTATIONS[OrgFileWriter], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> OrgFilesHarness:
    made = make(request, tmp_path)
    assert isinstance(made.writer, OrgFileWriter)
    return team(made)


def refused(h: OrgFilesHarness, actor: str, path: str) -> str:
    """The refusal of ``resolve_write``, which ``write`` repeats; the path must not be written."""
    said = refusal(lambda: h.writer.resolve_write(actor, path))
    assert refusal(lambda: h.writer.write(actor, path, "x")) == said
    return said


# ------------------------------------------------------------------------------ names the runtime owns


@pytest.mark.parametrize(
    "name",
    [
        "inbox", "INBOX", "Inbox", "inflight", "read", "Sent", "sent", "runs", "Runs", ".paused", ".PAUSED", ".Retired",
        ".retired", ".kiro", ".runtime", ".git", ".gitignore", ".anything-hidden",
    ],
)
def test_runtime_names_and_dot_names_are_refused_in_any_case(h: OrgFilesHarness, name: str) -> None:
    assert refused(h, "ceo", f"ceo/{name}/x.md") == runtime(name)
    assert refused(h, "ceo", f"ceo/{name}") == runtime(name)


@pytest.mark.parametrize("spelling", ["inbox.", "inbox ", "inbox. .", "INBOX..", ".paused.", "Runs ", "ｉｎｂｏｘ", "ＩＮＢＯＸ", "ｓｅｎｔ", "read."])
def test_the_name_is_compared_the_way_windows_and_unicode_would(h: OrgFilesHarness, spelling: str) -> None:
    assert refused(h, "ceo", f"ceo/{spelling}/x.md") == runtime(spelling)


def test_the_runtime_names_are_policed_only_at_the_top_of_the_own_directory(h: OrgFilesHarness) -> None:
    for path in ("ceo/work/inbox/x.md", "ceo/work/.paused", "ceo/work/runs/a.log", "ceo/notes/sent/x.md"):
        h.writer.write("ceo", path, "x")
    assert written(h, "ceo", "work", "inbox", "x.md") == "x"


@pytest.mark.parametrize("name", ["services", "Services", "SERVICES", "services.", "services ", "ｓｅｒｖｉｃｅｓ"])
def test_the_services_directory_belongs_to_the_runtime(h: OrgFilesHarness, name: str) -> None:
    assert refused(h, "ceo", f"ceo/{name}/x.md") == SERVICES
    assert refused(h, "ceo", f"ceo/{name}/ops/SERVICE.md") == SERVICES
    assert refused(h, "ceo", f"ceo/{name}") == SERVICES


def test_the_services_text_comes_before_the_runtime_name_text(h: OrgFilesHarness) -> None:
    assert refused(h, "ceo", "ceo/services/PLAYBOOK.md") == SERVICES
    assert refused(h, "root", "services/x.md") == SERVICES


# ------------------------------------------------------------------------------ exact spellings


@pytest.mark.parametrize(
    ("spelling", "exact"),
    [
        ("agent.md", "AGENT.md"), ("Agent.MD", "AGENT.md"), ("AGENT.MD", "AGENT.md"), ("AGENT.md.", "AGENT.md"), ("AGENT.md ", "AGENT.md"),
        ("memory.md", "MEMORY.md"), ("Memory.md", "MEMORY.md"), ("MEMORY.MD", "MEMORY.md"), ("MEMORY.md.", "MEMORY.md"),
        ("MEMORY.md . ", "MEMORY.md"), ("ＭＥＭＯＲＹ.ｍｄ", "MEMORY.md"), ("ｍｅｍｏｒｙ.md", "MEMORY.md"),
        ("org.md", "ORG.md"), ("Org.md", "ORG.md"), ("ORG.md.", "ORG.md"), ("oRG.MD", "ORG.md"),
    ],
)
def test_the_three_special_files_must_be_spelled_exactly(h: OrgFilesHarness, spelling: str, exact: str) -> None:
    assert refused(h, "ceo", f"ceo/{spelling}") == reserved(exact)
    assert refused(h, "root", spelling) == reserved(exact)


def test_the_exact_spelling_decides_before_a_case_twin_is_looked_for(h: OrgFilesHarness) -> None:
    assert (written(h, "ceo", "MEMORY.md"), refused(h, "ceo", "ceo/memory.md")) == ("", reserved("MEMORY.md"))


def test_a_special_name_is_free_below_the_top(h: OrgFilesHarness) -> None:
    for path in ("ceo/work/memory.md", "ceo/work/Agent.md.txt", "ceo/work/org.md"):
        h.writer.write("ceo", path, "x")
    assert written(h, "ceo", "work", "memory.md") == "x"


# ------------------------------------------------------------------------------ case twins


def test_a_case_twin_of_an_existing_file_is_refused_and_the_file_is_untouched(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/work/Plan.md", "a")
    assert refused(h, "ceo", "ceo/work/plan.md") == twin("plan.md", "Plan.md")
    assert refused(h, "ceo", "ceo/work/PLAN.MD") == twin("PLAN.MD", "Plan.md")
    assert written(h, "ceo", "work", "Plan.md") == "a"


def test_a_case_twin_of_a_directory_in_the_middle_of_the_path_is_refused(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/work/Sub/a.md", "a")
    assert refused(h, "ceo", "ceo/work/sub/b.md") == twin("sub", "Sub")
    assert refused(h, "ceo", "ceo/WORK/x.md") == twin("WORK", "work")
    assert refused(h, "ceo", "ceo/Work/Sub/a.md") == twin("Work", "work")  # the first twin on the way decides


def test_the_exact_name_of_an_existing_file_is_a_plain_overwrite(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/work/Plan.md", "a")
    h.writer.write("ceo", "ceo/work/Plan.md", "b")
    assert written(h, "ceo", "work", "Plan.md") == "b"


def test_names_that_differ_by_more_than_case_are_not_twins(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/work/Plan.md", "a")
    h.writer.write("ceo", "ceo/work/Plans.md", "b")
    h.writer.write("ceo", "ceo/work/Plan.txt", "c")
    h.writer.write("ceo", "ceo/work/AnyCase/Notes.md", "d")
    assert written(h, "ceo", "work", "AnyCase", "Notes.md") == "d"


def test_a_twin_is_judged_by_the_names_that_exist_not_by_the_wish(h: OrgFilesHarness) -> None:
    h.put(h.root / "ceo" / "work" / "Behind.md", "put behind the back of the writer")
    assert refused(h, "ceo", "ceo/work/behind.md") == twin("behind.md", "Behind.md")


def test_case_variants_of_a_direct_reports_names_cannot_dodge_the_charter_only_rule(h: OrgFilesHarness) -> None:
    assert refused(h, "ceo", "ceo/ENG/AGENT.md") == twin("ENG", "eng")
    assert refused(h, "ceo", "ceo/Eng/MEMORY.md") == twin("Eng", "eng")
    assert refused(h, "ceo", "ceo/ENG/work/x.md") == twin("ENG", "eng")
    assert refused(h, "ceo", "ceo/eng/agent.md") == twin("agent.md", "AGENT.md")
    assert refused(h, "ceo", "ceo/eng/Memory.md") == twin("Memory.md", "MEMORY.md")
    assert written(h, "ceo", "eng", "MEMORY.md") == ""


# ------------------------------------------------------------------------------ AGENT.md and ORG.md


def test_an_agent_does_not_write_its_own_charter(h: OrgFilesHarness) -> None:
    assert refused(h, "ceo", "ceo/AGENT.md") == OWN_CHARTER
    assert refused(h, "ceo/eng", "ceo/eng/AGENT.md") == OWN_CHARTER
    assert refused(h, "root", "AGENT.md") == OWN_CHARTER


def test_a_parent_edits_the_charter_of_a_direct_report_and_root_of_a_top_level_agent(h: OrgFilesHarness) -> None:
    assert h.writer.resolve_write("ceo", "ceo/eng/AGENT.md") == h.root / "ceo" / "eng" / "AGENT.md"
    assert h.writer.resolve_write("root", "ceo/AGENT.md") == h.root / "ceo" / "AGENT.md"
    assert h.writer.resolve_write("root", "ops/AGENT.md") == h.root / "ops" / "AGENT.md"
    h.writer.write("ceo", "ceo/eng/AGENT.md", CHARTER)
    h.writer.write("root", "ceo/AGENT.md", CHARTER)
    assert "role: Engineer v2" in (written(h, "ceo", "eng", "AGENT.md") or "") and "role: Engineer v2" in (written(h, "ceo", "AGENT.md") or "")


@pytest.mark.parametrize(
    ("actor", "path"),
    [
        ("ceo", "ceo/new/AGENT.md"), ("ceo", "ceo/work/AGENT.md"), ("ceo", "ceo/new/deeper/AGENT.md"), ("ceo", "ceo/eng/sub/AGENT.md"),
        ("ceo", "ceo/eng/work/AGENT.md"), ("ceo", "ceo/work/Agent.md"), ("ceo", "ceo/work/agent.md."), ("ceo", "ceo/work/deep/AGENT.md"),
        ("root", "newagent/AGENT.md"), ("root", "ceo/sub/AGENT.md"), ("root", "work/AGENT.md"), ("ceo/eng", "ceo/eng/work/AGENT.md"),
        ("ceo/eng", "ceo/eng/sub/AGENT.md"),
    ],
)
def test_no_path_creates_an_agent_hire_is_the_way(h: OrgFilesHarness, actor: str, path: str) -> None:
    sneaky = "---\nrole: sneaky\ncan_hire: true\nmax_children: 99\n---\n# x"
    assert refused(h, actor, path) == CREATE_BY_HIRE
    assert refusal(lambda: h.writer.write(actor, path, sneaky)) == CREATE_BY_HIRE
    assert h.store.kind(h.root / path) == "missing"
    assert not any(h.store.kind(h.root / made) != "missing" for made in ("ceo/new", "newagent"))


def test_only_the_charter_of_a_direct_report_may_be_written_by_its_parent(h: OrgFilesHarness) -> None:
    assert refused(h, "ceo", "ops/AGENT.md") == outside_of("ceo/", "ops/AGENT.md")  # a sibling's
    assert refused(h, "ceo/eng", "ceo/AGENT.md") == outside_of("ceo/eng/", "ceo/AGENT.md")  # the manager's
    assert refused(h, "root", "ceo/eng/AGENT.md") == CREATE_BY_HIRE  # a grandchild is no direct report of root


def outside_of(prefix: str, path: str) -> str:
    return (
        f"you may only write inside your own directory. Paths are relative to the org root, so yours start with `{prefix}`: "
        f"e.g. `{prefix}MEMORY.md` or `{prefix}work/notes.md` (got `{path}`)"
    )


def test_org_md_is_root_s_alone(h: OrgFilesHarness) -> None:
    assert refused(h, "ceo", "ceo/ORG.md") == ORG_MD
    assert refused(h, "ceo/eng", "ceo/eng/ORG.md") == ORG_MD
    before = written(h, "ORG.md")
    assert before is not None and h.writer.write("root", "ORG.md", before) == h.root / "ORG.md"
    assert written(h, "ORG.md") == before


# ------------------------------------------------------------------------------ a direct report's directory


@pytest.mark.parametrize("path", ["ceo/eng", "ceo/eng/work/x.md", "ceo/eng/MEMORY.md", "ceo/eng/notes.md", "ceo/eng/sub/deeper/x.md", "ceo/eng/work"])
def test_inside_the_directory_of_a_direct_report_only_its_charter_may_be_edited(h: OrgFilesHarness, path: str) -> None:
    assert refused(h, "ceo", path) == CHARTER_ONLY


def test_root_has_the_same_rule_for_its_direct_reports(h: OrgFilesHarness) -> None:
    for path in ("ceo", "ceo/work/x.md", "ceo/MEMORY.md", "ops/notes.md", "ops/inbox/x.md"):
        assert refused(h, "root", path) == CHARTER_ONLY


def test_the_rule_looks_at_the_charter_of_the_directory_not_at_its_name(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/notes/x.md", "a directory without a charter is just a directory")
    h.put(h.root / "ceo" / "notes" / "AGENT.md", "---\nrole: planted\n---\n")  # behind the back of every guard
    assert refused(h, "ceo", "ceo/notes/x.md") == CHARTER_ONLY
