"""Contract of ``OrgFileWriter``: an agent writes only inside its own directory, and what it writes there.

The writer is logic, so the suite runs the real ``GuardedOrgFileWriter`` twice: over the files and charters on disk and over the in-memory
store with in-memory agents. The names the guard refuses are in ``test_guard.py``, the cap of ``MEMORY.md`` in ``test_memory_cap.py``, the
rewrite of a charter in ``test_charter_rewrite.py``, and what needs a real filesystem in ``test_filesystem_guards.py``."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgError
from orgmcp.orgfiles import OrgFileWriter
from orgmcp.orgfiles.testing import IMPLEMENTATIONS, OrgFilesHarness

from ._support import make, refusal, team, written

pytestmark = pytest.mark.xfail(strict=True, reason="red: B-orgfiles")


def outside_text(prefix: str, path: str) -> str:
    return (
        f"you may only write inside your own directory. Paths are relative to the org root, so yours start with `{prefix}`: "
        f"e.g. `{prefix}MEMORY.md` or `{prefix}work/notes.md` (got `{path}`)"
    )


@pytest.fixture(params=IMPLEMENTATIONS[OrgFileWriter], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> OrgFilesHarness:
    made = make(request, tmp_path)
    assert isinstance(made.writer, OrgFileWriter)
    return team(made)


# ------------------------------------------------------------------------------ what an agent may write


def test_a_file_of_the_own_directory_is_written_and_its_path_returned(h: OrgFilesHarness) -> None:
    path = h.writer.write("ceo", "ceo/work/notes.md", "n")
    assert path == h.root / "ceo" / "work" / "notes.md" and written(h, "ceo", "work", "notes.md") == "n"


def test_the_directories_above_a_new_file_are_made(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/work/a/b/c.md", "deep")
    assert written(h, "ceo", "work", "a", "b", "c.md") == "deep"


def test_any_other_path_of_the_own_directory_is_allowed_too(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/notes.md", "top")
    h.writer.write("ceo", "ceo/new/x.md", "in a directory that is not an agent")
    h.writer.write("ceo", "ceo/work/inbox/x.md", "runtime names are policed at the top level only")
    h.writer.write("ceo", "ceo/work/../work/y.md", "dots that stay inside")
    assert [written(h, "ceo", *p) for p in (("notes.md",), ("new", "x.md"), ("work", "inbox", "x.md"), ("work", "y.md"))] == [
        "top", "in a directory that is not an agent", "runtime names are policed at the top level only", "dots that stay inside"
    ]


def test_an_absolute_path_inside_the_own_directory_is_allowed(h: OrgFilesHarness) -> None:
    assert h.writer.write("ceo", str(h.root / "ceo" / "work" / "abs.md"), "a") == h.root / "ceo" / "work" / "abs.md"
    assert written(h, "ceo", "work", "abs.md") == "a"


def test_a_write_replaces_the_file(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/work/n.md", "a much longer first text")
    h.writer.write("ceo", "ceo/work/n.md", "second")
    assert written(h, "ceo", "work", "n.md") == "second"


def test_an_append_adds_to_the_end_and_makes_a_file_that_is_not_there(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/work/log.md", "one\n")
    h.writer.write("ceo", "ceo/work/log.md", "two\n", append=True)
    h.writer.write("ceo", "ceo/work/fresh.md", "start", append=True)
    assert written(h, "ceo", "work", "log.md") == "one\ntwo\n" and written(h, "ceo", "work", "fresh.md") == "start"


def test_an_append_to_the_empty_memory_of_a_new_agent_works(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/MEMORY.md", "first", append=True)
    assert written(h, "ceo", "MEMORY.md") == "first"


def test_write_noted_has_no_note_for_an_ordinary_file(h: OrgFilesHarness) -> None:
    assert h.writer.write_noted("ceo", "ceo/work/n.md", "x") == (h.root / "ceo" / "work" / "n.md", "")
    assert h.writer.write_noted("ceo", "ceo/work/n.md", "y", append=True)[1] == ""
    assert written(h, "ceo", "work", "n.md") == "xy"


def test_resolve_write_gives_the_path_that_write_writes_and_creates_nothing(h: OrgFilesHarness) -> None:
    path = h.writer.resolve_write("ceo", "ceo/work/later/n.md")
    assert path == h.root / "ceo" / "work" / "later" / "n.md" and h.store.kind(path) == "missing"
    assert h.store.kind(path.parent) == "missing"
    assert h.writer.write("ceo", "ceo/work/later/n.md", "x") == path


def test_the_actor_is_taken_in_its_canonical_form(h: OrgFilesHarness) -> None:
    h.writer.write(" /ceo/ ", "ceo/work/n.md", "x")
    h.writer.write("ceo/eng", "ceo/eng/work/e.md", "x")
    assert written(h, "ceo", "work", "n.md") == "x" and written(h, "ceo", "eng", "work", "e.md") == "x"


def test_an_actor_that_is_not_an_agent_cannot_write(h: OrgFilesHarness) -> None:
    assert refusal(lambda: h.writer.write("ghost", "ghost/work/x.md", "x")) == "no such agent: ghost"
    assert refusal(lambda: h.writer.resolve_write("ceo/ghost", "ceo/ghost/work/x.md")) == "no such agent: ceo/ghost"
    assert refusal(lambda: h.writer.write_noted("ghost", "ghost/x.md", "x")) == "no such agent: ghost"


# ------------------------------------------------------------------------------ only the own directory


@pytest.mark.parametrize("path", ["ops/work/x.md", "work/x.md", "../x.md", "ceo", "ceo/../ops/work/x.md", ".", "", "ceo-evil/x.md", "ceo/../x"])
def test_a_path_outside_the_own_directory_is_refused_with_the_agents_own_prefix(h: OrgFilesHarness, path: str) -> None:
    assert refusal(lambda: h.writer.write("ceo", path, "x")) == outside_text("ceo/", path)
    assert refusal(lambda: h.writer.resolve_write("ceo", path)) == outside_text("ceo/", path)
    assert refusal(lambda: h.writer.write_noted("ceo", path, "x")) == outside_text("ceo/", path)


def test_a_path_outside_the_organization_is_refused(h: OrgFilesHarness) -> None:
    for path in (str(h.outside / "x.md"), str(h.root.parent / "x.md"), "/etc/x.md"):
        assert refusal(lambda: h.writer.write("ceo", path, "x")) == outside_text("ceo/", path)


def test_a_tilde_path_is_expanded_before_it_is_judged(h: OrgFilesHarness, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(h.outside))
    assert refusal(lambda: h.writer.write("ceo", "~/x.md", "x")) == outside_text("ceo/", "~/x.md")
    monkeypatch.setenv("HOME", str(h.root / "ceo" / "work"))
    assert h.writer.resolve_write("ceo", "~/x.md") == h.root / "ceo" / "work" / "x.md"


def test_a_nested_agent_has_its_whole_address_as_prefix(h: OrgFilesHarness) -> None:
    assert refusal(lambda: h.writer.write("ceo/eng", "ceo/x.md", "x")) == outside_text("ceo/eng/", "ceo/x.md")
    assert refusal(lambda: h.writer.write("ceo/eng", "work/x.md", "x")) == outside_text("ceo/eng/", "work/x.md")


def test_root_has_no_prefix_and_cannot_leave_the_organization(h: OrgFilesHarness) -> None:
    for path in ("../x.md", str(h.outside / "x.md"), "", "."):
        assert refusal(lambda: h.writer.write("root", path, "x")) == outside_text("", path)
    assert refusal(lambda: h.writer.write("", "../x.md", "x")) == outside_text("", "../x.md")


def test_root_writes_its_own_files_and_the_charters_of_its_direct_reports_only(h: OrgFilesHarness) -> None:
    h.writer.write("root", "work/n.md", "root's")
    h.writer.write("root", "MEMORY.md", "root memory")
    h.writer.write("root", "notes.md", "top")
    assert written(h, "work", "n.md") == "root's" and written(h, "MEMORY.md") == "root memory" and written(h, "notes.md") == "top"
    assert refusal(lambda: h.writer.write("root", "ceo/work/x.md", "x")) == (
        "inside a direct report's directory you may only edit its charter (AGENT.md)"
    )


def test_a_parent_does_not_write_into_the_directories_of_its_reports_siblings_or_grandchildren(h: OrgFilesHarness) -> None:
    for actor, path in (("ceo", "ceo/eng/work/x.md"), ("ceo", "ceo/eng/sub/deep.md"), ("root", "ops/work/x.md")):
        assert refusal(lambda: h.writer.write(actor, path, "x"))
    assert written(h, "ceo", "eng", "work", "x.md") is None and written(h, "ops", "work", "x.md") is None


def test_the_organization_files_a_refused_write_touches_stay_as_they_were(h: OrgFilesHarness) -> None:
    before = written(h, "ceo", "AGENT.md"), written(h, "ORG.md"), written(h, "ceo", "MEMORY.md")
    for path in ("ceo/AGENT.md", "ceo/ORG.md", "ceo/agent.md", "ceo/memory.md", "ops/x.md"):
        with pytest.raises(OrgError):
            h.writer.write("ceo", path, "overwritten")
    assert (written(h, "ceo", "AGENT.md"), written(h, "ORG.md"), written(h, "ceo", "MEMORY.md")) == before
