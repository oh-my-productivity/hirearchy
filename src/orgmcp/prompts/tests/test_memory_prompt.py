# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.


def words(n):
    return " ".join(["word"] * n)


def test_prompt_asks_to_condense_an_oversized_memory(org):
    org.write("ceo", "ceo/MEMORY.md", words(10))
    assert "condense" not in org.run_prompt("ceo", []).split("# Your memory")[1].split("# Your state")[0]

    (org.root / "ceo/MEMORY.md").write_text(words(900))  # edited by a human, bypassing the cap
    memory_section = org.run_prompt("ceo", []).split("# Your memory")[1].split("# Your state")[0]
    assert words(900) in memory_section  # shown as is
    assert "900 words, over the 800-word limit" in memory_section and "condense" in memory_section
