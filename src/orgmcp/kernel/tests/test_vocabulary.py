"""The data of the vocabulary: constants, the name pattern, the shape of the value objects. These are definitions, not
behaviour, so they are green from the first commit."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import (
    BOXES,
    MESSAGE_TYPES,
    NAME_RE,
    RENDER_BODY_CHARS,
    RESERVED,
    RESULT_STATUSES,
    ROOT,
    RUNTIME,
    RUNTIME_NAMES,
    Message,
    MessageView,
    OrgError,
    OrgLayout,
    OrgPaths,
)


def test_the_vocabulary() -> None:
    assert (ROOT, RUNTIME) == ("root", "runtime")
    assert BOXES == ("inbox", "inflight", "read", "sent")
    assert RUNTIME_NAMES == {
        "inbox", "inflight", "read", "sent", "runs", "services", ".paused", ".kiro", ".runtime", ".retired", ".git", ".gitignore",
    }
    assert RESERVED == RUNTIME_NAMES | {"work", "root", "runtime", "agent", "memory", "org"}


@pytest.mark.parametrize("name", ["a", "ceo", "a-b-1", "x" * 32, "a1", "q-"])
def test_valid_agent_names(name: str) -> None:
    assert NAME_RE.fullmatch(name)


@pytest.mark.parametrize("name", ["", "Ceo", "1a", "-a", "a_b", "x" * 33, "ops\n", "a b", "a/b", ".hidden", "é"])
def test_invalid_agent_names(name: str) -> None:
    assert not NAME_RE.fullmatch(name)


def test_message_constants() -> None:
    assert MESSAGE_TYPES == ("task", "result", "note") and RESULT_STATUSES == ("done", "failed", "blocked")
    assert RENDER_BODY_CHARS == 8000


def test_the_base_error_is_a_value_error_with_the_agent_facing_text() -> None:
    assert issubclass(OrgError, ValueError) and str(OrgError("no such agent: x")) == "no such agent: x"


def test_a_message_is_a_mutable_value() -> None:
    m = Message("a", "b", "note", "x")
    assert isinstance(m, MessageView)
    m.id, m.created, m.trace = "i", "c", "t"  # Org.deliver completes a message in place
    assert (m.id, m.created, m.trace) == ("i", "c", "t")
    assert Message("a", "b", "note", "x", path=Path("/p")) == Message("a", "b", "note", "x", path=Path("/q"))  # path is not compared
    assert Message("a", "b", "note", "x") != Message("a", "b", "note", "y")


def test_org_paths_is_a_layout_and_a_value() -> None:
    paths = OrgPaths(Path("/orgs/acme"))
    assert isinstance(paths, OrgLayout) and paths.root == Path("/orgs/acme")
    assert paths == OrgPaths(Path("/orgs/acme")) and hash(paths) == hash(OrgPaths(Path("/orgs/acme"))) and paths != OrgPaths(Path("/other"))
    with pytest.raises(AttributeError):
        paths.root = Path("/x")  # type: ignore[misc]
