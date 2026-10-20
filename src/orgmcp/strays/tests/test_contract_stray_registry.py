"""Contract of ``StrayRegistry``: the ledger ``.runtime/strays.json`` of the real registry and of the fake hold the same entries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orgmcp.strays import StrayRegistry
from orgmcp.strays.testing import IMPLEMENTATIONS, StraysHarness

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[StrayRegistry], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> StraysHarness:
    made = make(request, tmp_path)
    assert isinstance(made.registry, StrayRegistry)
    made.put_agent("dev", {"role": "R", "tools": ["write"]})
    made.put_agent("plain", {"role": "R"})
    return made


def ledger(h: StraysHarness) -> object:
    text = h.ledger_text()
    assert text is not None
    return json.loads(text)


def notice(path_list: str, tool: str, addr: str = "dev") -> str:
    """The exact text, written out here on purpose: it is part of the prompt (GOLDEN ``prompts/stray_notice``)."""
    return (
        "# Notice from the runtime (shown once)\n"
        f"A previous run of yours used kiro's built-in `write` and created org files in your WORKSPACE: {path_list}. "
        "The organization does not see them, so your org memory and notes are not saved. Move that content into "
        f"your org files now: read it, then save it with `@orgmcp/{tool}` (e.g. path=\"{addr}/MEMORY.md\" or "
        f"\"{addr}/work/...\"). Use `@orgmcp/{tool}` for every org file from now on; the built-in `write` is for the "
        "workspace only. The runtime does not move or delete those files; if they are real workspace "
        "deliverables, ignore this."
    )


# ------------------------------------------------------------------------------ record


def test_recording_a_stray_puts_an_entry_in_the_ledger(h: StraysHarness) -> None:
    h.registry.record("dev", ["/ws/dev"])
    assert ledger(h) == {"dev": {"paths": ["/ws/dev"], "told": False}}


def test_the_ledger_has_the_format_it_always_had(h: StraysHarness) -> None:
    h.registry.record("dev", ["/ws/dev", "/ws/dev/MEMORY.md"])
    expected = json.dumps({"dev": {"paths": ["/ws/dev", "/ws/dev/MEMORY.md"], "told": False}}, indent=2) + "\n"
    assert h.ledger_text() == expected


def test_only_the_first_ten_paths_are_kept(h: StraysHarness) -> None:
    h.registry.record("dev", [f"/ws/dev/{n}" for n in range(14)])
    assert ledger(h) == {"dev": {"paths": [f"/ws/dev/{n}" for n in range(10)], "told": False}}


def test_a_later_record_before_the_notice_replaces_the_paths(h: StraysHarness) -> None:
    h.registry.record("dev", ["/ws/dev/a"])
    h.registry.record("dev", ["/ws/dev/b"])
    assert ledger(h) == {"dev": {"paths": ["/ws/dev/b"], "told": False}}


def test_the_entries_of_other_agents_are_kept(h: StraysHarness) -> None:
    h.registry.record("plain", ["/ws/plain"])
    h.registry.record("dev", ["/ws/dev"])
    assert ledger(h) == {"plain": {"paths": ["/ws/plain"], "told": False}, "dev": {"paths": ["/ws/dev"], "told": False}}


def test_once_the_agent_was_told_a_record_changes_nothing(h: StraysHarness) -> None:
    h.registry.record("dev", ["/ws/dev"])
    h.registry.take_notice("dev")
    before = h.ledger_text()
    h.registry.record("dev", ["/ws/dev/again"])
    assert h.ledger_text() == before and h.registry.take_notice("dev") == ""


def test_an_entry_that_is_not_an_object_is_replaced(h: StraysHarness) -> None:
    h.put_ledger_text(json.dumps({"dev": "garbage", "plain": {"paths": ["/p"], "told": True}}))
    h.registry.record("dev", ["/ws/dev"])
    assert ledger(h) == {"dev": {"paths": ["/ws/dev"], "told": False}, "plain": {"paths": ["/p"], "told": True}}


@pytest.mark.parametrize("raw", ["", "not json", "[1, 2]", "null"])
def test_an_unreadable_ledger_starts_afresh(h: StraysHarness, raw: str) -> None:
    h.put_ledger_text(raw)
    h.registry.record("dev", ["/ws/dev"])
    assert ledger(h) == {"dev": {"paths": ["/ws/dev"], "told": False}}


def test_recording_no_path_leaves_the_agent_untold(h: StraysHarness) -> None:
    h.registry.record("dev", [])
    assert ledger(h) == {"dev": {"paths": [], "told": False}} and h.registry.take_notice("dev") == ""


# ------------------------------------------------------------------------------ take_notice


def test_there_is_no_notice_for_an_agent_without_strays(h: StraysHarness) -> None:
    assert h.registry.take_notice("dev") == ""
    assert h.ledger_text() is None  # nothing was written for nothing


def test_the_notice_names_the_paths_and_the_renamed_write_tool(h: StraysHarness) -> None:
    h.registry.record("dev", ["/ws/dev", "/ws/dev/MEMORY.md"])
    assert h.registry.take_notice("dev") == notice("`/ws/dev`, `/ws/dev/MEMORY.md`", "org_write")


def test_an_agent_without_the_built_in_write_is_told_to_use_the_plain_name(h: StraysHarness) -> None:
    h.registry.record("plain", ["/ws/plain"])
    assert h.registry.take_notice("plain") == notice("`/ws/plain`", "write", "plain")


def test_the_notice_is_given_once_and_the_agent_is_marked_told(h: StraysHarness) -> None:
    h.registry.record("dev", ["/ws/dev"])
    assert h.registry.take_notice("dev") != ""
    assert ledger(h) == {"dev": {"paths": ["/ws/dev"], "told": True}}
    assert h.registry.take_notice("dev") == ""


def test_the_notice_names_at_most_five_paths(h: StraysHarness) -> None:
    h.registry.record("dev", [f"/ws/dev/{n}" for n in range(8)])
    text = h.registry.take_notice("dev")
    assert text == notice(", ".join(f"`/ws/dev/{n}`" for n in range(5)), "org_write")
    assert "/ws/dev/5" not in text


def test_telling_one_agent_leaves_the_others_untold(h: StraysHarness) -> None:
    h.registry.record("plain", ["/ws/plain"])
    h.registry.record("dev", ["/ws/dev"])
    h.registry.take_notice("dev")
    assert ledger(h) == {"plain": {"paths": ["/ws/plain"], "told": False}, "dev": {"paths": ["/ws/dev"], "told": True}}
    assert h.registry.take_notice("plain") != ""


@pytest.mark.parametrize(
    "entry", ["garbage", None, 3, {"told": False}, {"paths": [], "told": False}, {"paths": ["/x"], "told": True}, {"paths": None}],
    ids=["string", "null", "number", "no-paths", "empty-paths", "told", "paths-null"],
)
def test_an_entry_with_nothing_to_tell_gives_no_notice_and_is_left_as_it_is(h: StraysHarness, entry: object) -> None:
    h.put_ledger_text(json.dumps({"dev": entry}))
    before = h.ledger_text()
    assert h.registry.take_notice("dev") == ""
    assert h.ledger_text() == before


def test_an_unreadable_ledger_has_no_notice(h: StraysHarness) -> None:
    h.put_ledger_text("not json")
    assert h.registry.take_notice("dev") == ""
