import re

import pytest


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


def test_prompt_asks_to_condense_an_oversized_memory(org):
    org.write("ceo", "ceo/MEMORY.md", words(10))
    assert "condense" not in org.run_prompt("ceo", []).split("# Your memory")[1].split("# Your state")[0]

    (org.root / "ceo/MEMORY.md").write_text(words(900))  # edited by a human, bypassing the cap
    memory_section = org.run_prompt("ceo", []).split("# Your memory")[1].split("# Your state")[0]
    assert words(900) in memory_section  # shown as is
    assert "900 words, over the 800-word limit" in memory_section and "condense" in memory_section
