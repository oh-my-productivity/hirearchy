"""``LenientCharterReader``: a charter is parsed once per change of its file; one that cannot be read is a placeholder and is reported
(the dashboard's decorator; it replaces ``LenientOrg.charter``)."""

from __future__ import annotations

import pytest

from orgmcp.agents import CharterReader
from orgmcp.agents._caching import CharterStamps, LenientCharterReader
from orgmcp.kernel import JsonObject

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-agents")


class ScriptedCharters(CharterReader):
    def __init__(self) -> None:
        self.answers: dict[str, tuple[JsonObject, str] | Exception] = {}
        self.reads: list[str] = []
        self.texts: dict[str, str] = {}

    def charter(self, addr: str) -> tuple[JsonObject, str]:
        self.reads.append(addr)
        answer = self.answers.get(addr, ({"role": addr}, "body"))
        if isinstance(answer, Exception):
            raise answer
        return answer

    def memory(self, addr: str) -> str:
        return self.texts[addr]


class ScriptedStamps(CharterStamps):
    def __init__(self) -> None:
        self.values: dict[str, tuple[int, int] | OSError] = {}
        self.asked: list[str] = []

    def stamp(self, addr: str) -> tuple[int, int]:
        self.asked.append(addr)
        value = self.values.get(addr, (1, 10))
        if isinstance(value, OSError):
            raise value
        return value


def make() -> tuple[LenientCharterReader, ScriptedCharters, ScriptedStamps, dict[str, str]]:
    inner, stamps, problems = ScriptedCharters(), ScriptedStamps(), dict[str, str]()
    return LenientCharterReader(inner, stamps, problems), inner, stamps, problems


def test_it_is_a_charter_reader() -> None:
    assert isinstance(make()[0], CharterReader)


def test_building_it_reads_nothing() -> None:
    _, inner, stamps, problems = make()
    assert inner.reads == [] and stamps.asked == [] and problems == {}


def test_roots_charter_is_the_inner_one_and_has_no_stamp() -> None:
    reader, inner, stamps, _ = make()
    inner.answers["root"] = ({"role": "human"}, "")
    assert reader.charter("") == ({"role": "human"}, "") and stamps.asked == []


def test_a_charter_is_read_once_per_stamp_and_the_cached_value_is_handed_out() -> None:
    reader, inner, stamps, _ = make()
    first = reader.charter("ceo")
    assert first == ({"role": "ceo"}, "body") and reader.charter("ceo") is first and reader.charter(" /ceo/ ") is first
    assert inner.reads == ["ceo"]
    stamps.values["ceo"] = (2, 10)
    inner.answers["ceo"] = ({"role": "new"}, "text")
    assert reader.charter("ceo") == ({"role": "new"}, "text") and inner.reads == ["ceo", "ceo"]


def test_a_changed_size_alone_is_a_change() -> None:
    reader, inner, stamps, _ = make()
    reader.charter("ceo")
    stamps.values["ceo"] = (1, 11)
    reader.charter("ceo")
    assert inner.reads == ["ceo", "ceo"]


def test_every_agent_has_its_own_entry() -> None:
    reader, inner, _, _ = make()
    assert reader.charter("a")[0] == {"role": "a"} and reader.charter("b")[0] == {"role": "b"}
    reader.charter("a")
    reader.charter("b")
    assert inner.reads == ["a", "b"]


def test_a_charter_whose_file_cannot_be_looked_at_is_the_placeholder_and_reported() -> None:
    reader, inner, stamps, problems = make()
    stamps.values["ceo/eng"] = FileNotFoundError("gone")
    assert reader.charter("ceo/eng") == ({"role": "?"}, "")
    assert problems == {"ceo/eng/AGENT.md": "FileNotFoundError"} and inner.reads == []


def test_a_charter_that_cannot_be_parsed_is_the_placeholder_and_reported_by_the_name_of_the_error() -> None:
    reader, inner, _, problems = make()
    inner.answers["ceo"] = ValueError("mapping values are not allowed here")
    assert reader.charter("ceo") == ({"role": "?"}, "")
    assert problems == {"ceo/AGENT.md": "ValueError"}


def test_a_failure_is_tried_again_and_is_never_cached_as_a_success() -> None:
    reader, inner, _, _ = make()
    inner.answers["ceo"] = RuntimeError("boom")
    reader.charter("ceo")
    reader.charter("ceo")
    assert inner.reads == ["ceo", "ceo"]


def test_a_charter_that_recovers_is_no_longer_reported() -> None:
    reader, inner, stamps, problems = make()
    stamps.values["ceo"] = PermissionError("no")
    reader.charter("ceo")
    assert problems == {"ceo/AGENT.md": "PermissionError"}
    stamps.values["ceo"] = (5, 5)
    assert reader.charter("ceo") == ({"role": "ceo"}, "body") and problems == {}


def test_a_cached_charter_stays_when_the_file_is_gone_until_it_is_asked_about_again() -> None:
    reader, inner, stamps, problems = make()
    good = reader.charter("ceo")
    stamps.values["ceo"] = FileNotFoundError("gone")
    assert reader.charter("ceo") == ({"role": "?"}, "") and problems == {"ceo/AGENT.md": "FileNotFoundError"}
    stamps.values["ceo"] = (1, 10)  # the file is back, unchanged: the entry of before is still good
    assert reader.charter("ceo") is good and problems == {}


def test_other_problems_in_the_mapping_are_left_alone() -> None:
    reader, _, stamps, problems = make()
    problems["ORG.md"] = "ScannerError"
    problems["x/AGENT.md"] = "ValueError"
    reader.charter("ceo")
    stamps.values["ceo"] = OSError("gone")
    reader.charter("ceo")
    stamps.values["ceo"] = (9, 9)
    reader.charter("ceo")
    assert problems == {"ORG.md": "ScannerError", "x/AGENT.md": "ValueError"}


def test_memory_is_the_inner_one() -> None:
    reader, inner, _, _ = make()
    inner.texts["ceo"] = "notes"
    assert reader.memory("ceo") == "notes"
    with pytest.raises(KeyError):
        reader.memory("nobody")
