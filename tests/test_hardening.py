import re

import pytest

from orgmcp.core import ROOT, OrgError


def h1s(text):
    return re.findall(r"^# .*$", text, flags=re.M)


@pytest.mark.parametrize(
    "charter, heading",
    [
        ("Build things.", "# Role: Builder"),
        ("# Role: Builder\n\nBuild things.", "# Role: Builder"),
        ("\n# Lead builder\n\nBuild things.\n", "# Lead builder"),
        ("## Duties\nBuild things.", "# Role: Builder"),  # a lower-level heading is not an H1
    ],
)
def test_charter_has_exactly_one_h1(org, charter, heading):
    addr = org.hire("ceo", "builder", "Builder", charter)
    _, body = org.charter(addr)
    assert h1s(body) == [heading]
    assert "Build things." in body


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


def test_prompt_asks_to_condense_an_oversized_memory(org):
    org.write("ceo", "ceo/MEMORY.md", words(10))
    assert "condense" not in org.run_prompt("ceo", []).split("# Your memory")[1].split("# Your state")[0]

    (org.root / "ceo/MEMORY.md").write_text(words(900))  # edited by a human, bypassing the cap
    memory_section = org.run_prompt("ceo", []).split("# Your memory")[1].split("# Your state")[0]
    assert words(900) in memory_section  # shown as is
    assert "900 words, over the 800-word limit" in memory_section and "condense" in memory_section
