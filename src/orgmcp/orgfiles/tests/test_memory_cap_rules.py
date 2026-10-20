# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.orgmcp.core import OrgError


def words(n):
    return " ".join(["word"] * n)


def test_memory_write_over_the_cap_is_refused(org):
    cap = org.config["memory_max_words"]
    assert cap == 800
    org.write("ceo", "ceo/MEMORY.md", words(cap))  # exactly at the cap is fine
    with pytest.raises(OrgError, match="condense"):
        org.write("ceo", "ceo/MEMORY.md", words(cap + 1))
    assert len(org.memory("ceo").split()) == cap  # the refused write changed nothing


def test_memory_append_over_the_cap_is_refused(org):
    org.write("ceo", "ceo/MEMORY.md", words(790))
    org.write("ceo", "ceo/MEMORY.md", " " + words(10), append=True)
    with pytest.raises(OrgError, match="Do not append"):
        org.write("ceo", "ceo/MEMORY.md", " one more", append=True)
    org.write("ceo", "ceo/MEMORY.md", "condensed")  # a rewrite is always possible
    assert org.memory("ceo") == "condensed"


def test_memory_cap_is_configurable_and_only_for_memory(org):
    org.root.joinpath("ORG.md").write_text(
        org.root.joinpath("ORG.md").read_text().replace("memory_max_words: 800", "memory_max_words: 5"))
    with pytest.raises(OrgError, match="limit is 5"):
        org.write("ceo", "ceo/MEMORY.md", words(6))
    org.write("ceo", "ceo/work/notes.md", words(50))  # other files are not capped
