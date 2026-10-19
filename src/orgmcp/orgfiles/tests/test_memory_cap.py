"""The cap on ``MEMORY.md``: an agent's memory is read into every run, so the writer refuses a memory over ``memory_max_words``.

The cap is read from ORG.md when the write happens, counts the words of what the file would hold (an append adds to the old text), and
applies to the exact file ``<own directory>/MEMORY.md`` only. Runs over both implementations."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgError
from orgmcp.orgfiles import OrgFileWriter
from orgmcp.orgfiles.testing import IMPLEMENTATIONS, OrgFilesHarness

from ._support import make, refusal, team, written

pytestmark = pytest.mark.xfail(strict=True, reason="red: B-orgfiles")


def words(n: int) -> str:
    return " ".join(["word"] * n)


def over(count: int, cap: int) -> str:
    return (
        f"MEMORY.md would be {count} words; the limit is {cap}. Do not append: condense it. "
        "Rewrite the whole file (append=false) keeping only what your next run needs, "
        "and move detail into files under your work/ directory."
    )


@pytest.fixture(params=IMPLEMENTATIONS[OrgFileWriter], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> OrgFilesHarness:
    made = make(request, tmp_path)
    assert isinstance(made.writer, OrgFileWriter)
    return team(made)


def with_cap(h: OrgFilesHarness, cap: int) -> None:
    h.put_org_md(f"---\nmemory_max_words: {cap}\n---\n# Organization\n")


def test_the_default_cap_is_eight_hundred_words(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/MEMORY.md", words(800))  # exactly at the cap is fine
    assert refusal(lambda: h.writer.write("ceo", "ceo/MEMORY.md", words(801))) == over(801, 800)
    assert written(h, "ceo", "MEMORY.md") == words(800)


def test_an_append_that_goes_over_is_refused_and_leaves_the_memory_as_it_was(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/MEMORY.md", words(790))
    h.writer.write("ceo", "ceo/MEMORY.md", " " + words(10), append=True)
    assert refusal(lambda: h.writer.write("ceo", "ceo/MEMORY.md", " one more", append=True)) == over(802, 800)
    assert written(h, "ceo", "MEMORY.md") == words(790) + " " + words(10)


def test_a_rewrite_after_the_refusal_is_always_possible(h: OrgFilesHarness) -> None:
    h.writer.write("ceo", "ceo/MEMORY.md", words(800))
    with pytest.raises(OrgError):
        h.writer.write("ceo", "ceo/MEMORY.md", " more", append=True)
    h.writer.write("ceo", "ceo/MEMORY.md", "condensed")
    assert written(h, "ceo", "MEMORY.md") == "condensed"


def test_the_cap_is_read_from_org_md_when_the_write_happens(h: OrgFilesHarness) -> None:
    with_cap(h, 5)
    assert refusal(lambda: h.writer.write("ceo", "ceo/MEMORY.md", words(6))) == over(6, 5)
    h.writer.write("ceo", "ceo/MEMORY.md", words(5))
    with_cap(h, 7)
    h.writer.write("ceo", "ceo/MEMORY.md", words(7))
    assert written(h, "ceo", "MEMORY.md") == words(7)


def test_the_cap_does_not_apply_to_other_files(h: OrgFilesHarness) -> None:
    with_cap(h, 5)
    h.writer.write("ceo", "ceo/work/notes.md", words(50))
    h.writer.write("ceo", "ceo/work/MEMORY.md", words(50))
    h.writer.write("ceo", "ceo/notes.md", words(50))
    assert written(h, "ceo", "work", "notes.md") == words(50)


def test_every_agent_and_root_have_their_own_memory_with_the_same_cap(h: OrgFilesHarness) -> None:
    with_cap(h, 5)
    for actor, path in (("ceo/eng", "ceo/eng/MEMORY.md"), ("ops", "ops/MEMORY.md"), ("root", "MEMORY.md")):
        assert refusal(lambda: h.writer.write(actor, path, words(6))) == over(6, 5)
        h.writer.write(actor, path, words(5))


def test_words_are_the_blank_separated_pieces_of_the_text_markup_included(h: OrgFilesHarness) -> None:
    with_cap(h, 5)
    assert refusal(lambda: h.writer.write("ceo", "ceo/MEMORY.md", "# a\n- b\n- c")) == over(6, 5)  # '#' and '-' count, unlike word_count
    h.writer.write("ceo", "ceo/MEMORY.md", "# a\n- b\n  c")  # five pieces
    assert written(h, "ceo", "MEMORY.md") == "# a\n- b\n  c"
    h.writer.write("ceo", "ceo/MEMORY.md", "  a   b\tc\n\n d  e  ")  # runs of blanks are one separator


@pytest.mark.parametrize("spelling", ["memory.md", "Memory.md", "MEMORY.MD", "MEMORY.md."])
def test_the_cap_cannot_be_dodged_by_spelling_the_name_differently(h: OrgFilesHarness, spelling: str) -> None:
    with_cap(h, 5)
    big = words(50)
    assert refusal(lambda: h.writer.write("ceo", f"ceo/{spelling}", big)) == "that name is reserved: it must be spelled exactly `MEMORY.md`"
    assert written(h, "ceo", "MEMORY.md") == ""
    h.writer.write("ceo", "ceo/MEMORY.md", "short")  # the exact spelling still works
    assert written(h, "ceo", "MEMORY.md") == "short"


def test_an_absolute_path_to_the_memory_is_the_memory(h: OrgFilesHarness) -> None:
    with_cap(h, 5)
    assert refusal(lambda: h.writer.write("ceo", str(h.root / "ceo" / "MEMORY.md"), words(6))) == over(6, 5)


def test_the_memory_of_a_report_is_not_the_parents_to_write(h: OrgFilesHarness) -> None:
    with_cap(h, 5)
    assert refusal(lambda: h.writer.write("ceo", "ceo/eng/MEMORY.md", words(2))) == (
        "inside a direct report's directory you may only edit its charter (AGENT.md)"
    )
