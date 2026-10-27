"""Two processes, one writer module (design 4.3): ``FsServiceStore.write_playbook`` is a compare-and-swap under the service's lock.

The watch settler runs in root's process while the owner's ``revise_playbook`` runs in the agent's. Here two real processes write version 6 on
version 5 of one playbook on a real directory: exactly one wins, the other gets ``PlaybookRace``, and no version is lost or overwritten."""

from __future__ import annotations

import multiprocessing
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from hirearchy.services import PlaybookRace
from hirearchy.services._parse import FILE_SHAPE
from hirearchy.services.testing import fs_store

SERVICE_DIR = "ceo/services/brief"
LOCK = ".tmp-playbook.lock"


def seeded(root: Path, versions: int = 5) -> None:
    """``ceo``'s ``brief`` playbook at ``versions``, written by the real store."""
    store = fs_store(root).store
    store.write_contract("ceo", "brief", {"name": "brief", "version": 1}, "", None)
    for version in range(1, versions + 1):
        store.write_playbook("ceo", "brief", version, {"version": version, "by": "seed"}, f"Text {version}.", version - 1 or None)


def attempt(root: str, who: str, gate: Any, outcomes: Any) -> None:
    """Runs in a child process: wait for the other one, then write v6 on v5; report ``("ok", who)`` or ``("race", who, current)``."""
    store = fs_store(Path(root)).store
    gate.wait(timeout=60)
    try:
        store.write_playbook("ceo", "brief", 6, {"version": 6, "by": who}, f"Text 6 by {who}.", 5)
        outcomes.put(("ok", who, 6))
    except PlaybookRace as race:
        outcomes.put(("race", who, race.current))


def raced(root: Path, who: Sequence[str] = ("owner", "settler")) -> list[tuple[str, str, int]]:
    context = multiprocessing.get_context("spawn")
    gate, outcomes = context.Barrier(len(who)), context.Queue()
    children = [context.Process(target=attempt, args=(str(root), name, gate, outcomes)) for name in who]
    for child in children:
        child.start()
    results = [outcomes.get(timeout=120) for _ in children]
    for child in children:
        child.join(timeout=60)
        assert child.exitcode == 0
    return sorted(results)


@pytest.fixture(scope="module")
def race(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[tuple[str, str, int]], str]:
    root = tmp_path_factory.mktemp("race")
    seeded(root)
    v5 = (root / SERVICE_DIR / "PLAYBOOK.md").read_text(encoding="utf-8")  # the bytes of v5 before the race
    return root, raced(root), v5


def test_two_processes_writing_v6_on_v5_one_wins_the_other_gets_playbook_race(
    race: tuple[Path, list[tuple[str, str, int]], str],
) -> None:
    root, results, _ = race
    assert sorted(kind for kind, _, _ in results) == ["ok", "race"]
    (winner,) = [who for kind, who, _ in results if kind == "ok"]
    (loser_current,) = [current for kind, _, current in results if kind == "race"]
    assert loser_current == 6  # the loser is told the version that is there now
    text = (root / SERVICE_DIR / "PLAYBOOK.md").read_text(encoding="utf-8")
    assert f"by: {winner}" in text and f"Text 6 by {winner}." in text  # the file is the winner's v6, whole


def test_history_v5_keeps_v5s_bytes_and_no_version_is_lost(
    race: tuple[Path, list[tuple[str, str, int]], str],
) -> None:
    root, _, v5 = race
    history = root / SERVICE_DIR / "history"
    assert (history / "PLAYBOOK.v5.md").read_text(encoding="utf-8") == v5  # v5, not the winner's v6
    assert sorted(p.name for p in history.iterdir()) == [f"PLAYBOOK.v{n}.md" for n in range(1, 6)]  # no temp file is left behind
    assert [(history / f"PLAYBOOK.v{n}.md").read_text(encoding="utf-8") for n in range(1, 5)] == [
        f"---\nversion: {n}\nby: seed\n---\nText {n}.\n" for n in range(1, 5)
    ]
    store = fs_store(root).store
    assert [v for v, _, _ in store.versions("ceo", "brief", "PLAYBOOK")] == [1, 2, 3, 4, 5, 6]


def test_the_lock_file_is_empty_and_never_read(tmp_path: Path) -> None:
    seeded(tmp_path)
    lock = tmp_path / SERVICE_DIR / LOCK
    assert lock.is_file() and lock.stat().st_size == 0  # created by the first write, holds no state
    assert FILE_SHAPE.fullmatch(LOCK) is None  # a retired copy does not carry it back
    harness = fs_store(tmp_path)
    assert harness.store.names("ceo") == ["brief"] and [v for v, _, _ in harness.store.versions("ceo", "brief", "PLAYBOOK")] == [1, 2, 3, 4, 5]
    lock.write_text("not a version: 99", encoding="utf-8")  # whatever it holds, no write reads it
    harness.store.write_playbook("ceo", "brief", 6, {"version": 6}, "Text 6.", 5)
    assert lock.read_text(encoding="utf-8") == "not a version: 99"  # and no write changes it
    assert [v for v, _ in harness.store.playbook_history("ceo", "brief")] == [1, 2, 3, 4, 5, 6]
