"""``OrgPaths`` (path arithmetic inside an organization) and the path helpers ``inside`` and ``visible``."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgPaths, inside, visible

ROOT_DIR = Path("/orgs/acme")


@pytest.mark.parametrize(("addr", "expected"), [
    ("root", ROOT_DIR), ("", ROOT_DIR), ("ceo", ROOT_DIR / "ceo"), (" /ceo/ ", ROOT_DIR / "ceo"), ("ceo/eng", ROOT_DIR / "ceo" / "eng"),
])
def test_agent_dir(addr: str, expected: Path) -> None:
    assert OrgPaths(ROOT_DIR).agent_dir(addr) == expected


def test_box_is_a_directory_of_the_agent() -> None:
    paths = OrgPaths(ROOT_DIR)
    assert paths.box("ceo/eng", "inbox") == ROOT_DIR / "ceo" / "eng" / "inbox"
    assert paths.box("root", "sent") == ROOT_DIR / "sent"


def test_runtime_places() -> None:
    paths = OrgPaths(ROOT_DIR)
    assert paths.runtime_dir() == ROOT_DIR / ".runtime"
    assert paths.ledger_file("failures") == ROOT_DIR / ".runtime" / "failures.json"
    assert paths.events_dir() == ROOT_DIR / ".runtime" / "events"
    assert paths.retired_dir() == ROOT_DIR / ".retired"


def test_rel_is_the_text_of_the_path_below_the_root() -> None:
    paths = OrgPaths(ROOT_DIR)
    assert paths.rel(ROOT_DIR / "ceo" / "work" / "a.md") == "ceo/work/a.md"
    assert paths.rel(ROOT_DIR) == "."
    with pytest.raises(ValueError):
        paths.rel(Path("/elsewhere/a.md"))


def test_inside_means_equal_or_below() -> None:
    base = Path("/a/b")
    assert inside(base, base) and inside(Path("/a/b/c"), base) and inside(Path("/a/b/c/d"), base)
    assert not inside(Path("/a"), base) and not inside(Path("/a/bc"), base) and not inside(Path("/x/b"), base)


def test_visible_drops_hidden_entries_and_sorts() -> None:
    entries = [Path("/d/b.md"), Path("/d/.hidden"), Path("/d/a.md"), Path("/d/.tmp-1-a.md"), Path("/d/c")]
    assert visible(entries) == [Path("/d/a.md"), Path("/d/b.md"), Path("/d/c")]
    assert visible(p for p in entries) == [Path("/d/a.md"), Path("/d/b.md"), Path("/d/c")]
    assert visible([]) == []
