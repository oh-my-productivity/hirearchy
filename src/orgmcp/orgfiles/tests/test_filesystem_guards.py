"""The guards that need a real filesystem: symbolic links and the case-insensitivity of macOS and Windows.

The reader and the writer judge a path after the store has resolved it, so a link cannot lead them anywhere its target is not allowed
to go. The folding of names (``test_guard.py``) makes the writer behave the same on every filesystem; the test of case-insensitive
aliasing below is the one that can only run on such a volume (it is skipped on a case-sensitive one, like ``test_qa_findings``'s)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from orgmcp.kernel import OrgError
from orgmcp.orgfiles.testing import OrgFilesHarness, guarded_on_disk

from ._support import refusal, team, written

pytestmark = pytest.mark.xfail(strict=True, reason="red: B-orgfiles")

CHARTER_ONLY = "inside a direct report's directory you may only edit its charter (AGENT.md)"


@pytest.fixture
def h(tmp_path: Path) -> OrgFilesHarness:
    made = team(guarded_on_disk(tmp_path))
    made.add_agent("lead", {"workspace": str(made.outside / "ws"), "inputs": [str(made.outside / "handbook")]})
    return made


def link(h: OrgFilesHarness, name: str, target: Path) -> None:
    os.symlink(target, h.root / name)


# ------------------------------------------------------------------------------ the writer follows links before it judges


def test_a_link_to_another_agents_directory_does_not_lead_there(h: OrgFilesHarness) -> None:
    link(h, "ceo/work/to-ops", h.root / "ops")
    said = refusal(lambda: h.writer.write("ceo", "ceo/work/to-ops/work/x.md", "x"))
    assert said.startswith("you may only write inside your own directory.") and said.endswith("(got `ceo/work/to-ops/work/x.md`)")
    assert written(h, "ops", "work", "x.md") is None


def test_a_link_out_of_the_organization_does_not_lead_there(h: OrgFilesHarness) -> None:
    link(h, "ceo/work/out", h.outside)
    assert "you may only write inside your own directory" in refusal(lambda: h.writer.write("ceo", "ceo/work/out/x.md", "x"))
    assert not (h.outside / "x.md").exists()


def test_a_link_to_the_own_charter_is_the_own_charter(h: OrgFilesHarness) -> None:
    link(h, "ceo/work/charter", h.root / "ceo" / "AGENT.md")
    assert refusal(lambda: h.writer.write("ceo", "ceo/work/charter", "x")) == "your charter is owned by your parent"


def test_a_link_to_a_runtime_directory_is_that_directory(h: OrgFilesHarness) -> None:
    link(h, "ceo/work/in", h.root / "ceo" / "inbox")
    assert refusal(lambda: h.writer.write("ceo", "ceo/work/in/20260101T000000000000-root-aaaa.md", "forged")) == (
        "inbox is managed by the runtime; use send/delegate/report to communicate"
    )
    link(h, "ceo/work/mem", h.root / "ceo" / "MEMORY.md")
    assert h.writer.resolve_write("ceo", "ceo/work/mem") == (h.root / "ceo" / "MEMORY.md").resolve()  # it is the memory, so the cap applies


def test_a_link_to_a_direct_reports_directory_is_that_directory(h: OrgFilesHarness) -> None:
    link(h, "ceo/work/rep", h.root / "ceo" / "eng")
    assert refusal(lambda: h.writer.write("ceo", "ceo/work/rep/work/x.md", "x")) == CHARTER_ONLY
    assert h.writer.resolve_write("ceo", "ceo/work/rep/AGENT.md") == h.root / "ceo" / "eng" / "AGENT.md"  # its charter, the one allowed file


def test_a_link_inside_the_own_directory_writes_its_target(h: OrgFilesHarness) -> None:
    h.put(h.root / "ceo" / "work" / "real.md", "old")
    link(h, "ceo/work/alias.md", h.root / "ceo" / "work" / "real.md")
    assert h.writer.write("ceo", "ceo/work/alias.md", "new") == h.root / "ceo" / "work" / "real.md"
    assert written(h, "ceo", "work", "real.md") == "new" and (h.root / "ceo" / "work" / "alias.md").is_symlink()


def test_the_memory_cap_applies_to_the_memory_reached_through_a_link(h: OrgFilesHarness) -> None:
    link(h, "ceo/work/mem", h.root / "ceo" / "MEMORY.md")
    with pytest.raises(OrgError, match="would be 900 words"):
        h.writer.write("ceo", "ceo/work/mem", " ".join(["w"] * 900))
    assert written(h, "ceo", "MEMORY.md") == ""


def test_a_name_in_the_own_directory_that_is_a_link_is_compared_as_it_is_spelled_there(h: OrgFilesHarness) -> None:
    link(h, "ceo/work/Plan.md", h.root / "ceo" / "work" / "elsewhere.md")
    assert "differs only by letter case from the existing `Plan.md`" in refusal(lambda: h.writer.write("ceo", "ceo/work/plan.md", "x"))


# ------------------------------------------------------------------------------ the reader follows links before it judges


def test_a_link_out_of_the_organization_is_judged_by_its_target(h: OrgFilesHarness) -> None:
    h.put(h.outside / "secret.md", "s")
    link(h, "ceo/work/leak", h.outside)
    for who in ("root", None):
        assert refusal(lambda: h.reader.read("ceo/work/leak/secret.md", who)) == "you can only read inside the organization"
    assert "you can only read inside the organization (paths relative to the org root)" in refusal(lambda: h.reader.read("ceo/work/leak/secret.md", "ceo"))


def test_a_link_into_the_workspace_of_the_reader_is_readable_by_it_only(h: OrgFilesHarness) -> None:
    h.put(h.outside / "ws" / "p.md", "a b")
    link(h, "lead/work/ws", h.outside / "ws")
    assert h.reader.read("lead/work/ws/p.md", "lead").splitlines()[0].startswith(f"[{h.outside / 'ws' / 'p.md'}: 2 words")
    assert "you can only read inside the organization" in refusal(lambda: h.reader.read("lead/work/ws/p.md", "ops"))
    assert "you can only read inside the organization" in refusal(lambda: h.reader.read("lead/work/ws/p.md"))


def test_a_link_inside_the_organization_is_shown_under_the_name_of_its_target(h: OrgFilesHarness) -> None:
    h.put(h.root / "ops" / "work" / "o.md", "a")
    link(h, "ceo/work/o.md", h.root / "ops" / "work" / "o.md")
    assert h.reader.read("ceo/work/o.md").startswith("[ops/work/o.md: 1 words")


def test_a_directory_listing_marks_links_to_directories_and_not_broken_ones(h: OrgFilesHarness) -> None:
    link(h, "ceo/work/dirlink", h.root / "ops")
    link(h, "ceo/work/broken", h.root / "nothing-here")
    h.put(h.root / "ceo" / "work" / "f.md", "x")
    assert h.reader.read("ceo/work") == "broken\ndirlink/\nf.md"


# ------------------------------------------------------------------------------ case-insensitive volumes


PROTECTED = {
    ("agent.md", "ceo", "AGENT.md"): "---\nrole: boss\ncan_hire: true\nmax_children: 99\ntools: [shell]\n---\n# x",
    ("memory.md", "ceo", "MEMORY.md"): "x",
    ("Inbox/20260101T000000000000-root-aaaa.md", "ceo", "inbox"): "forged",
}


def test_on_a_case_insensitive_volume_no_spelling_reaches_a_protected_file(h: OrgFilesHarness) -> None:
    if h.case_sensitive:
        pytest.skip("needs a case-insensitive filesystem (macOS/Windows default)")
    charter, memory = written(h, "ceo", "AGENT.md"), written(h, "ceo", "MEMORY.md")
    for (spelled, *_), content in PROTECTED.items():
        for path in (f"ceo/{spelled}", f"ceo/{spelled.upper()}", f"ceo/{spelled.title()}"):
            with pytest.raises(OrgError):
                h.writer.write("ceo", path, content)
    assert (written(h, "ceo", "AGENT.md"), written(h, "ceo", "MEMORY.md")) == (charter, memory)
    assert list((h.root / "ceo" / "inbox").iterdir()) == []
