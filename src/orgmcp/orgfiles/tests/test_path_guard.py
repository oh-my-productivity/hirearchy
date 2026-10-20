"""The pure parts of the write guard: the key under which names count as the same, and the case twin of a name."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import RUNTIME_NAMES
from orgmcp.orgfiles import _guard
from orgmcp.orgfiles._guard import case_twin, case_twin_in


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("inbox", "inbox"), ("INBOX", "inbox"), ("Inbox.", "inbox"), ("inbox ", "inbox"), ("inbox. .", "inbox"), ("ｉｎｂｏｘ", "inbox"),
        ("ＭＥＭＯＲＹ.ｍｄ", "memory.md"), ("MEMORY.MD ", "memory.md"), ("Straße", "strasse"), ("ǅ", "dž"), ("ﬁle", "file"), ("", ""),
        ("...", ""), (" . ", ""), ("a b", "a b"), (".paused", ".paused"), (".PAUSED.", ".paused"),
    ],
)
def test_names_that_one_filesystem_or_another_would_confuse_have_one_key(name: str, key: str) -> None:
    assert _guard._fold(name) == key


def test_leading_dots_and_blanks_are_part_of_the_name() -> None:
    assert _guard._fold(" x") == " x" and _guard._fold("..x") == "..x"


def test_the_protected_names_are_kept_by_their_key() -> None:
    assert _guard._FOLDED_RUNTIME_NAMES == {_guard._fold(name) for name in RUNTIME_NAMES}
    assert {"inbox", "inflight", "read", "sent", "runs", "services", ".paused", ".kiro", ".runtime", ".retired", ".git", ".gitignore"} <= _guard._FOLDED_RUNTIME_NAMES
    assert "work" not in _guard._FOLDED_RUNTIME_NAMES  # a reserved name for agents, but an ordinary directory to write in


def test_the_files_that_have_one_spelling_are_agent_memory_and_org() -> None:
    assert _guard._EXACT_FILES == {"agent.md": "AGENT.md", "memory.md": "MEMORY.md", "org.md": "ORG.md"}


def test_the_case_twin_is_the_existing_name_that_differs_only_by_case() -> None:
    assert case_twin(["Plan.md", "other.md"], "plan.md") == "Plan.md"
    assert case_twin(["Plan.md"], "PLAN.MD") == "Plan.md"
    assert case_twin(("Work",), "work") == "Work"


def test_a_name_that_is_there_has_no_twin_even_when_another_spelling_is_too() -> None:
    assert case_twin(["plan.md", "Plan.md"], "plan.md") is None
    assert case_twin(["plan.md", "Plan.md"], "Plan.md") is None


def test_no_twin_when_nothing_is_like_it() -> None:
    assert case_twin([], "x") is None
    assert case_twin(["plans.md", "plan.txt"], "plan.md") is None


def test_the_first_twin_in_the_order_given_is_the_one_named() -> None:
    assert case_twin(["PLAN.md", "Plan.md"], "plan.md") == "PLAN.md"


def test_names_that_fold_to_the_same_key_are_twins_whatever_the_difference() -> None:
    assert case_twin(["ｉｎｂｏｘ"], "inbox") == "ｉｎｂｏｘ"
    assert case_twin(["a.md."], "A.MD") == "a.md."



def test_the_case_twin_in_a_directory_is_found_by_listing_it(tmp_path: Path) -> None:
    (tmp_path / "Plan.md").write_text("x", encoding="utf-8")
    assert case_twin_in(tmp_path, "plan.md") == "Plan.md" and case_twin_in(tmp_path, "Plan.md") is None
    assert case_twin_in(tmp_path, "other.md") is None


def test_a_directory_that_cannot_be_listed_has_no_case_twin(tmp_path: Path) -> None:
    (tmp_path / "file").write_text("x", encoding="utf-8")
    assert case_twin_in(tmp_path / "missing", "x") is None and case_twin_in(tmp_path / "file", "x") is None
