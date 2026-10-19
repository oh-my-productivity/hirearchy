"""Contract of ``OrgFileReader``: where each agent may look, and what it is shown.

The reader is logic, so the suite runs the real ``GuardedOrgFileReader`` twice: over the files and charters on disk and over the in-memory
store with in-memory agents. The texts of the refusals are the ones agents are shown. What needs a real filesystem (symbolic links) is in
``test_filesystem_guards.py``."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orgmcp.orgfiles import OrgFileReader
from orgmcp.orgfiles.testing import IMPLEMENTATIONS, OrgFilesHarness

from ._support import make, refusal


INSIDE_ONLY = "you can only read inside the organization"
AGENT_RULE = (
    "you can only read inside the organization (paths relative to the org root), or by absolute path inside "
    "your workspace, your read-only inputs, or the workspace of an agent in your team"
)


@pytest.fixture(params=IMPLEMENTATIONS[OrgFileReader], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> OrgFilesHarness:
    made = make(request, tmp_path)
    assert isinstance(made.reader, OrgFileReader)
    made.add_agent("lead", {"workspace": str(made.outside / "ws-lead"), "inputs": [str(made.outside / "handbook")]})
    made.add_agent("lead/dev", {"workspace": str(made.outside / "ws-dev"), "inputs": [str(made.outside / "handbook" / "dev")]})
    made.add_agent("ops", {"workspace": str(made.outside / "ws-ops")})
    return made


# ------------------------------------------------------------------------------ resolve_read: the organization


def test_a_relative_path_is_relative_to_the_organization_root(h: OrgFilesHarness) -> None:
    assert h.reader.resolve_read("lead/work/x.md") == h.root / "lead" / "work" / "x.md"
    assert h.reader.resolve_read(".") == h.root
    assert h.reader.resolve_read("lead/work/x.md", "lead/dev") == h.root / "lead" / "work" / "x.md"


def test_an_absolute_path_inside_the_organization_is_read_by_everyone(h: OrgFilesHarness) -> None:
    where = h.root / "ops" / "work" / "n.md"
    assert h.reader.resolve_read(str(where)) == where
    assert h.reader.resolve_read(str(where), "root") == where
    assert h.reader.resolve_read(str(where), "lead/dev") == where


def test_the_files_do_not_have_to_exist_to_be_resolved(h: OrgFilesHarness) -> None:
    assert h.reader.resolve_read("nothing/here.md") == h.root / "nothing" / "here.md"


def test_dots_are_resolved_before_the_path_is_judged(h: OrgFilesHarness) -> None:
    assert h.reader.resolve_read("lead/../ops/work") == h.root / "ops" / "work"
    assert refusal(lambda: h.reader.resolve_read("../outside.md", "lead")) == AGENT_RULE
    assert refusal(lambda: h.reader.resolve_read("lead/../../outside.md")) == INSIDE_ONLY


def test_the_organization_root_itself_is_readable(h: OrgFilesHarness) -> None:
    assert h.reader.resolve_read(str(h.root), "lead") == h.root


# ------------------------------------------------------------------------------ resolve_read: outside the organization


def test_root_and_a_reader_without_an_actor_read_the_organization_only(h: OrgFilesHarness) -> None:
    for path in (str(h.outside / "ws-lead" / "a.md"), str(h.outside), str(h.root.parent)):
        assert refusal(lambda: h.reader.resolve_read(path)) == INSIDE_ONLY
        assert refusal(lambda: h.reader.resolve_read(path, "root")) == INSIDE_ONLY
        assert refusal(lambda: h.reader.resolve_read(path, None)) == INSIDE_ONLY


def test_an_agent_reads_by_absolute_path_inside_its_workspace_and_its_inputs(h: OrgFilesHarness) -> None:
    mine = h.outside / "ws-lead" / "notes" / "a.md"
    handbook = h.outside / "handbook" / "hr.md"
    assert h.reader.resolve_read(str(mine), "lead") == mine
    assert h.reader.resolve_read(str(handbook), "lead") == handbook
    assert h.reader.resolve_read(str(h.outside / "ws-lead"), "lead") == h.outside / "ws-lead"
    assert h.reader.resolve_read(str(h.outside / "handbook" / "dev" / "d.md"), "lead/dev") == h.outside / "handbook" / "dev" / "d.md"


def test_a_manager_reads_the_workspace_of_every_agent_in_its_team(h: OrgFilesHarness) -> None:
    theirs = h.outside / "ws-dev" / "out.md"
    assert h.reader.resolve_read(str(theirs), "lead") == theirs
    assert h.reader.resolve_read(str(theirs), "lead/dev") == theirs


def test_an_agent_does_not_read_the_workspace_of_its_manager_or_of_someone_elses_team(h: OrgFilesHarness) -> None:
    assert refusal(lambda: h.reader.resolve_read(str(h.outside / "ws-lead" / "a.md"), "lead/dev")) == AGENT_RULE
    assert refusal(lambda: h.reader.resolve_read(str(h.outside / "ws-ops" / "a.md"), "lead")) == AGENT_RULE
    assert refusal(lambda: h.reader.resolve_read(str(h.outside / "handbook" / "hr.md"), "ops")) == AGENT_RULE
    assert refusal(lambda: h.reader.resolve_read(str(h.outside / "handbook" / "hr.md"), "lead/dev")) == AGENT_RULE  # only its own inputs


def test_a_path_that_merely_starts_like_a_granted_directory_is_not_inside_it(h: OrgFilesHarness) -> None:
    assert refusal(lambda: h.reader.resolve_read(str(h.outside / "ws-lead-evil" / "a.md"), "lead")) == AGENT_RULE
    assert refusal(lambda: h.reader.resolve_read(str(h.outside), "lead")) == AGENT_RULE


def test_the_actor_is_taken_in_its_canonical_form(h: OrgFilesHarness) -> None:
    mine = h.outside / "ws-lead" / "a.md"
    assert h.reader.resolve_read(str(mine), " /lead/ ") == mine
    assert refusal(lambda: h.reader.resolve_read(str(mine), " /root/ ")) == INSIDE_ONLY


def test_an_actor_that_is_not_an_agent_has_nothing_outside_the_organization(h: OrgFilesHarness) -> None:
    assert refusal(lambda: h.reader.resolve_read(str(h.outside / "ws-lead" / "a.md"), "ghost")) == AGENT_RULE
    assert h.reader.resolve_read("lead/work", "ghost") == h.root / "lead" / "work"


# ------------------------------------------------------------------------------ read: files


def test_a_file_is_shown_with_a_header_and_its_text(h: OrgFilesHarness) -> None:
    h.put(h.root / "lead" / "work" / "n.md", "one two\nthree\n")
    h.touch(h.root / "lead" / "work" / "n.md", datetime(2026, 5, 6, 7, 8, 9, tzinfo=timezone.utc))
    assert h.reader.read("lead/work/n.md") == "[lead/work/n.md: 3 words, 2 lines, modified 07:08:09 UTC]\none two\nthree\n"


def test_the_header_counts_words_like_the_kernel_and_lines_by_newlines(h: OrgFilesHarness) -> None:
    h.put(h.root / "lead" / "work" / "w.md", "- bullet\n```\ncode fence\n```\nlast")
    head = h.reader.read("lead/work/w.md").split("\n", 1)[0]
    assert re.fullmatch(r"\[lead/work/w\.md: 4 words, 4 lines, modified \d\d:\d\d:\d\d UTC\]", head), head


def test_an_empty_file_has_a_header_and_no_text(h: OrgFilesHarness) -> None:
    head = h.reader.read("lead/MEMORY.md")
    assert re.fullmatch(r"\[lead/MEMORY\.md: 0 words, 0 lines, modified \d\d:\d\d:\d\d UTC\]\n", head), head


def test_a_file_outside_the_organization_is_named_by_its_absolute_path(h: OrgFilesHarness) -> None:
    target = h.outside / "ws-lead" / "p.md"
    h.put(target, "x y z")
    assert re.fullmatch(rf"\[{re.escape(str(target))}: 3 words, 0 lines, modified \d\d:\d\d:\d\d UTC\]\nx y z", h.reader.read(str(target), "lead"))


def test_a_file_inside_the_organization_is_named_relative_to_it_even_when_given_absolute(h: OrgFilesHarness) -> None:
    h.put(h.root / "ops" / "work" / "a.md", "a")
    head = h.reader.read(str(h.root / "ops" / "work" / "a.md"), "lead").split("\n", 1)[0]
    assert head.startswith("[ops/work/a.md: 1 words, 0 lines, modified ")


def test_a_text_of_exactly_one_hundred_thousand_characters_is_shown_whole(h: OrgFilesHarness) -> None:
    h.put(h.root / "lead" / "work" / "big.md", "x" * 100_000)
    shown = h.reader.read("lead/work/big.md")
    assert shown.endswith("x" * 100_000) and "truncated" not in shown


def test_a_longer_text_is_cut_and_says_how_long_it_is(h: OrgFilesHarness) -> None:
    h.put(h.root / "lead" / "work" / "big.md", "x" * 100_000 + "TAIL")
    shown = h.reader.read("lead/work/big.md")
    assert shown.endswith("x" * 100_000 + "\n... (truncated, 100004 chars total)") and "TAIL" not in shown


# ------------------------------------------------------------------------------ read: directories


def test_a_directory_lists_its_visible_entries_sorted_and_marks_directories(h: OrgFilesHarness) -> None:
    h.put(h.root / "lead" / "work" / "b.md", "1")
    h.put(h.root / "lead" / "work" / "A.md", "2")
    h.put(h.root / "lead" / "work" / ".hidden", "3")
    h.put_dir(h.root / "lead" / "work" / "sub")
    h.put_dir(h.root / "lead" / "work" / "Zed")
    assert h.reader.read("lead/work") == "A.md\nZed/\nb.md\nsub/"


def test_an_empty_directory_says_so(h: OrgFilesHarness) -> None:
    assert h.reader.read("lead/work") == "(empty directory)"
    h.put(h.root / "lead" / "work" / ".only-hidden", "x")
    assert h.reader.read("lead/work") == "(empty directory)"


def test_no_path_is_the_organization_root(h: OrgFilesHarness) -> None:
    listing = h.reader.read("").splitlines()
    assert listing == h.reader.read(".").splitlines()
    assert "lead/" in listing and "ops/" in listing and "ORG.md" in listing
    assert not any(name.startswith(".") for name in listing)


def test_an_agents_directory_lists_its_boxes_without_the_hidden_ones(h: OrgFilesHarness) -> None:
    assert h.reader.read("lead", "lead").splitlines() == ["AGENT.md", "MEMORY.md", "dev/", "inbox/", "inflight/", "read/", "runs/", "sent/", "work/"]


def test_a_workspace_directory_outside_the_organization_lists_too(h: OrgFilesHarness) -> None:
    h.put(h.outside / "ws-lead" / "o.md", "x")
    h.put_dir(h.outside / "ws-lead" / "d")
    assert h.reader.read(str(h.outside / "ws-lead"), "lead") == "d/\no.md"


# ------------------------------------------------------------------------------ read: refusals and misses


def test_a_missing_path_is_reported_as_it_was_given(h: OrgFilesHarness) -> None:
    assert refusal(lambda: h.reader.read("lead/nope.md")) == "not found: lead/nope.md (relative paths are relative to the org root)"
    assert refusal(lambda: h.reader.read(str(h.outside / "ws-lead" / "no.md"), "lead")) == (
        f"not found: {h.outside / 'ws-lead' / 'no.md'} (relative paths are relative to the org root)"
    )


def test_the_rules_of_resolve_read_apply_to_read(h: OrgFilesHarness) -> None:
    assert refusal(lambda: h.reader.read(str(h.outside / "ws-lead" / "a.md"))) == INSIDE_ONLY
    assert refusal(lambda: h.reader.read(str(h.outside / "ws-ops" / "a.md"), "lead")) == AGENT_RULE
    assert refusal(lambda: h.reader.read("../outside.md", "lead")) == AGENT_RULE


def test_a_reader_that_is_not_an_agent_is_refused(h: OrgFilesHarness) -> None:
    assert refusal(lambda: h.reader.read("lead/work", "ghost")) == "no such agent: ghost"
    assert refusal(lambda: h.reader.read("lead/work", "lead/ghost")) == "no such agent: lead/ghost"


def test_root_reads_as_the_actor_root_and_every_agent_reads_the_whole_organization(h: OrgFilesHarness) -> None:
    h.put(h.root / "ops" / "work" / "o.md", "a b")
    assert h.reader.read("ops/work/o.md", "root").startswith("[ops/work/o.md: 2 words")
    assert h.reader.read("ops/work/o.md", "lead/dev").startswith("[ops/work/o.md: 2 words")
    assert h.reader.read("ops/work", "lead/dev") == "o.md"
