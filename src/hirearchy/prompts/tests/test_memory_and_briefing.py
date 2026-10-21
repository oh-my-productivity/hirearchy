"""``CappedMemory`` and ``PromptBriefing``: the memory as the prompt shows it, and what a run starts from."""

from __future__ import annotations

import pytest

from hirearchy.agents.testing import MemoryAgents
from hirearchy.prompts._briefing import CappedMemory, PromptBriefing
from hirearchy.prompts.testing import FixedMemory
from hirearchy.settings.testing import MemoryOrgSettings



def world(cap: int | str = 5, memory: str | None = None) -> tuple[MemoryAgents, MemoryOrgSettings]:
    agents = MemoryAgents()
    agents.put("ceo/AGENT.md", "---\nrole: Chief\n---\n# Role: Chief\n\nRun it.\n")
    if memory is not None:
        agents.put("ceo/MEMORY.md", memory)
    return agents, MemoryOrgSettings(f"---\nmemory_max_words: {cap}\n---\nThe rules.\n")


def notice(words: int, cap: int) -> str:
    return (
        f"\n\n**Your memory is {words} words, over the {cap}-word limit, and writes that keep it over the limit are refused. This run, "
        "condense it: rewrite ceo/MEMORY.md (not append) with only what your next run needs; move detail into files under your work/ directory.**"
    )


def test_a_memory_is_trimmed() -> None:
    agents, settings = world(memory="\n  notes of the last run \n\n")
    assert CappedMemory(agents, settings).memory_text("ceo") == "notes of the last run"


def test_no_memory_is_a_first_run() -> None:
    agents, settings = world(cap=800)
    assert CappedMemory(agents, settings).memory_text("ceo") == "(empty: this may be your first run)"
    agents.put("ceo/MEMORY.md", "  \n")
    assert CappedMemory(agents, settings).memory_text("ceo") == "(empty: this may be your first run)"


def test_a_memory_over_the_cap_gets_the_notice_and_one_at_the_cap_does_not() -> None:
    agents, settings = world(cap=5, memory="a b c d e f")
    assert CappedMemory(agents, settings).memory_text("ceo") == "a b c d e f" + notice(6, 5)
    agents.put("ceo/MEMORY.md", "a b c d e")
    assert CappedMemory(agents, settings).memory_text("ceo") == "a b c d e"


def test_the_words_of_the_empty_text_count_against_a_tiny_cap() -> None:
    agents, settings = world(cap=3)
    assert CappedMemory(agents, settings).memory_text("ceo") == "(empty: this may be your first run)" + notice(7, 3)


def test_the_cap_is_read_at_each_call() -> None:
    agents, settings = world(cap=100, memory="a b c")
    memory = CappedMemory(agents, settings)
    assert "condense" not in memory.memory_text("ceo")
    settings.write_raw("---\nmemory_max_words: 2\n---\nr\n")
    assert "condense" in memory.memory_text("ceo")


def test_a_cap_that_is_not_a_number_is_an_error_as_it_always_was() -> None:
    agents, settings = world(cap="lots", memory="a")
    with pytest.raises(ValueError):
        CappedMemory(agents, settings).memory_text("ceo")


def test_the_briefing_is_the_rules_the_charter_and_the_memory_under_their_headings() -> None:
    agents, settings = world()
    briefing = PromptBriefing(settings, agents, FixedMemory("MEMORY TEXT"))
    assert briefing.briefing("ceo") == (
        "The rules.\n\n# Your charter (ceo/AGENT.md, owned by your parent)\n# Role: Chief\n\nRun it.\n\n# Your memory (ceo/MEMORY.md)\nMEMORY TEXT"
    )


def test_the_briefing_asks_the_memory_text_of_the_agent() -> None:
    agents, settings = world()
    memory = FixedMemory("m")
    PromptBriefing(settings, agents, memory).briefing("ceo")
    assert memory.asked == ["ceo"]
