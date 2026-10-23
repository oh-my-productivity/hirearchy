"""Contract of ``ContinuedServices`` (``RecordedContinuations``) and ``ServiceRestorer``: the retired copy a root definition continues, over files
on disk and over files in memory (design 5.10, as amended by DR-41).

A copy is a directory with a regular ``SERVICE.md`` under ``<owner>/services/.retired/<name>-<stamp>/`` or in a retired tree of the owner
(``.retired/<owner>-<stamp>/services/<name>/`` and its own ``services/.retired/``). The newest one by ``defined`` is continued when a request of the
service has a result of any status (DR-41). Every candidate path is built from the layout and the archive, never from a name read in a file."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from hirearchy.kernel import AtomicWriter, OrgPaths, join_frontmatter, msg_time, split_frontmatter
from hirearchy.kernel.testing import fs_atomic_writer
from hirearchy.services._places import OrgServicePlaces
from hirearchy.services._protocols import RetiredService, ServiceRestorer
from hirearchy.services._store import FsServiceStore
from hirearchy.services.testing import MemoryServiceStore, ServicesWorld, StoreHarness, fs_store, fs_world, memory_store, memory_world

from ._support import answer, define, implementations, populated
from ._support import request as ask

CONTRACT = "ceo/services/weekly-brief/SERVICE.md"
OLDER, NEWER = "2026-01-01T00:00:00+00:00", "2026-02-01T00:00:00+00:00"


@pytest.fixture(params=implementations([fs_world, memory_world]))
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ServicesWorld:
    return populated(request.param(tmp_path))


def variant(text: str, **meta: object) -> str:
    """``text`` (a ``SERVICE.md``) with these frontmatter keys set; a key given as ``None`` is dropped."""
    front, body = split_frontmatter(text)
    for key, value in meta.items():
        if value is None:
            front.pop(key, None)
        else:
            front[key] = value
    return join_frontmatter(front, body)


def recorded_service(w: ServicesWorld, status: str = "done", name: str = "weekly-brief") -> str:
    """``ceo`` offers ``weekly-brief`` and one request of it has a result of ``status``; returns the text of its ``SERVICE.md``."""
    define(w, name=name)
    task = w.commands.request("root", name, {"topic": "ai"})
    answer(w, task, status)
    text = w.text(f"ceo/services/{name}/SERVICE.md")
    assert text is not None
    return text


def copy_in(w: ServicesWorld, where: str, text: str) -> str:
    """A retired copy of the service at ``where`` (below the organization); returns the directory."""
    w.put(f"{where}/SERVICE.md", text)
    return where


def continued(w: ServicesWorld, name: str = "weekly-brief", owner: str = "ceo") -> RetiredService | None:
    return w.continued.continued(owner, name)


# ------------------------------------------------------------------------------ which copy


def test_no_retired_copy_continues_nothing(w: ServicesWorld) -> None:
    assert continued(w) is None
    recorded_service(w)  # a live service is no retired copy
    assert continued(w) is None


def test_the_newest_copy_by_defined_wins_ties_to_the_greater_path(w: ServicesWorld) -> None:
    text = recorded_service(w)
    old = copy_in(w, "ceo/services/.retired/weekly-brief-20261018T100000000001", variant(text, defined=OLDER))
    found = continued(w)
    assert found is not None and found.path == old and found.recorded == 1
    newer = copy_in(w, ".retired/ceo-20261018T100000/services/weekly-brief", variant(text, defined=NEWER))
    found = continued(w)
    assert found is not None and found.path == newer  # the newest by defined, not the greatest path
    tied = copy_in(w, ".retired/ceo-20261018T110000/services/weekly-brief", variant(text, defined=NEWER))
    found = continued(w)
    assert found is not None and found.path == tied  # a tie goes to the greater path
    copy_in(w, ".retired/ceo-20261018T120000/services/.retired/weekly-brief-20261018T120000000001", variant(text, defined=None))
    found = continued(w)
    assert found is not None and found.path == tied  # a copy without defined sorts first, whatever its path


def test_the_name_must_match_exactly_weekly_is_not_weekly_memo(w: ServicesWorld) -> None:
    recorded_service(w, name="weekly-memo")
    w.commands.retire_service("root", "ceo", "weekly-memo", "redo")
    memo = continued(w, "weekly-memo")
    assert memo is not None and memo.path.startswith("ceo/services/.retired/weekly-memo-")
    assert continued(w, "weekly") is None
    assert continued(w, "weekly-memo-2") is None


def test_a_tree_of_another_agent_is_not_a_copy(w: ServicesWorld) -> None:
    text = recorded_service(w)
    for tree in ("cto-20261018T100000", "ceo.eng-20261018T100000", "ceo-S", "ceo-20261018T10"):
        copy_in(w, f".retired/{tree}/services/weekly-brief", text)
        assert continued(w) is None, tree
    mine = copy_in(w, ".retired/ceo-20261018T100000/services/weekly-brief", text)
    found = continued(w)
    assert found is not None and found.path == mine
    assert continued(w, owner="ops") is None  # another top-level agent has no copy of its own


# ------------------------------------------------------------------------------ whether it has a record to keep (DR-41)


def test_a_copy_without_a_recorded_request_continues_nothing(w: ServicesWorld) -> None:
    define(w)
    w.commands.retire_service("root", "ceo", "weekly-brief", "redo")  # no request at all
    assert continued(w) is None
    define(w)
    ask(w)  # a request that has no result
    w.commands.retire_service("root", "ceo", "weekly-brief", "again")
    assert continued(w) is None


@pytest.mark.parametrize("status", ["done", "blocked", "failed"])
def test_a_request_with_a_blocked_or_failed_result_is_recorded(w: ServicesWorld, status: str) -> None:
    """A verdict, a rejection and a judged delivery rest on a result of any status, so any status keeps the record (DR-41)."""
    recorded_service(w, status)
    w.commands.retire_service("root", "ceo", "weekly-brief", "redo")
    found = continued(w)
    assert found is not None and found.recorded == 1 and found.path.startswith("ceo/services/.retired/weekly-brief-")


def test_recorded_counts_requests_since_created_and_all_without_created(w: ServicesWorld) -> None:
    text = recorded_service(w)
    second = ask(w, "chips")
    answer(w, second, "blocked")
    ask(w, "open")  # no result: not recorded
    time = msg_time(second)
    assert time is not None
    where = ".retired/ceo-20261018T100000/services/weekly-brief"
    copy_in(w, where, variant(text, created=time.isoformat()))
    found = continued(w)
    assert found is not None and found.recorded == 1  # the request at created counts, the earlier one belongs to an older service
    copy_in(w, where, variant(text, created=None, defined=None))
    found = continued(w)
    assert found is not None and found.recorded == 2  # without created there is no floor
    copy_in(w, where, variant(text, created=None, defined="2026-01-01T00:00:00+00:00"))
    found = continued(w)
    assert found is not None and found.recorded == 2  # created is defined when the file has no created


def test_a_copy_holds_the_four_file_shapes_and_nothing_else(w: ServicesWorld) -> None:
    text = recorded_service(w)
    where = copy_in(w, ".retired/ceo-20261018T100000/services/weekly-brief", text)
    for rel in ("PLAYBOOK.md", "history/SERVICE.v1.md", "history/PLAYBOOK.v1.md", "history/notes.md", "history/SERVICE.v2.md.bak", "work.md"):
        w.put(f"{where}/{rel}", f"text of {rel}")
    w.put(f"{where}/history/deeper/SERVICE.v3.md", "too deep")
    found = continued(w)
    assert found is not None
    assert sorted(name for name, _ in found.files) == ["PLAYBOOK.md", "SERVICE.md", "history/PLAYBOOK.v1.md", "history/SERVICE.v1.md"]
    assert dict(found.files)["PLAYBOOK.md"] == "text of PLAYBOOK.md" and dict(found.files)["SERVICE.md"] == text


def test_an_unreadable_copy_raises(w: ServicesWorld) -> None:
    text = recorded_service(w)
    where = copy_in(w, ".retired/ceo-20261018T100000/services/weekly-brief", text)
    w.unreadable(f"{where}/SERVICE.md")
    with pytest.raises(OSError):
        continued(w)  # a skipped copy would reset the record: the definer fails closed on this


# ------------------------------------------------------------------------------ where it looks


def test_candidate_paths_come_from_the_layout_and_the_archive(w: ServicesWorld) -> None:
    """Only the retired places of the owner are looked at, and a name read in a file is never followed: a SERVICE.md anywhere else is no copy."""
    text = recorded_service(w)
    elsewhere = [
        "ceo/work/.retired/weekly-brief-20261018T100000000001",
        "ceo/services/other/.retired/weekly-brief-20261018T100000000001",
        "ceo/services/weekly-brief-20261018T100000000001",  # not under .retired
        "ceo/services/.retired/weekly-brief-2026",  # not a stamp
        "ceo/services/.retired/weekly-brief",
        "ceo/eng/services/.retired/weekly-brief-20261018T100000000001",  # another agent's services
        ".retired/ceo-20261018T100000/work/weekly-brief",
        ".retired/ceo-20261018T100000/services/weekly-brief-20261018T100000000001",  # not under services/.retired
        ".retired/ceo-20261018T100000/services/other/weekly-brief",
        ".retired/ceo-20261018T100000/ceo/services/weekly-brief",  # a tree nested by a second retirement in the same second
        "elsewhere/weekly-brief",
    ]
    for where in elsewhere:
        copy_in(w, where, text)
    assert continued(w) is None
    named = copy_in(w, "ceo/services/.retired/weekly-brief-20261018T100000000001", variant(text, name="other-name"))
    found = continued(w)  # the name in the file is not what makes it the copy of weekly-brief
    assert found is not None and found.path == named
    in_tree = copy_in(w, ".retired/ceo-20261018T100000/services/.retired/weekly-brief-20261018T100000000002", variant(text, defined="2027-01-01T00:00:00+00:00"))
    found = continued(w)  # a service retired before its owner was is a copy in the owner's tree
    assert found is not None and found.path == in_tree


# ------------------------------------------------------------------------------ restore


FILES: Sequence[tuple[str, str]] = (
    ("history/PLAYBOOK.v1.md", "---\nversion: 1\n---\nSteps one.\n"),
    ("history/SERVICE.v1.md", "---\nversion: 1\nname: weekly-brief\n---\nTwo  spaces and ünïcode, no trailing newline"),
    ("PLAYBOOK.md", "---\nversion: 2\n---\nSteps two.\n"),
    ("SERVICE.md", "---\nversion: 2\nname: weekly-brief\n---\nThe notes.\n"),
)
RESTORED = "ceo/services/weekly-brief"


@pytest.fixture(params=implementations([fs_store, memory_store]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> StoreHarness:
    made: StoreHarness = request.param(tmp_path)
    assert isinstance(made.restorer, ServiceRestorer)
    return made


def retired(files: Sequence[tuple[str, str]] = FILES) -> RetiredService:
    return RetiredService(".retired/ceo-20261018T100000/services/weekly-brief", tuple(files), 1)


def test_restore_writes_the_copy_byte_for_byte_service_md_last(h: StoreHarness) -> None:
    h.restorer.restore("ceo", "weekly-brief", retired())
    for rel, text in FILES:
        assert h.text(f"{RESTORED}/{rel}") == text
    assert h.store.names("ceo") == ["weekly-brief"]
    assert [v for v, _, _ in h.store.versions("ceo", "weekly-brief", "SERVICE")] == [1, 2]  # the kept version and the current one, as the store reads them


def test_restore_ignores_files_of_other_shapes(h: StoreHarness) -> None:
    """Only ``SERVICE.md``, ``PLAYBOOK.md`` and the kept versions are written, whatever the retired copy holds; nothing leaves the service's directory."""
    odd = ("notes.md", "history/notes.md", "history/SERVICE.v1.md.bak", "history/deeper/SERVICE.v2.md", "../escape.md", "history/../../escape.md",
           "/absolute.md", "SERVICE.md.bak", "history/SERVICE.vX.md", "services/SERVICE.md")
    h.restorer.restore("ceo", "weekly-brief", retired([*FILES, *((name, "other") for name in odd)]))
    assert h.rels() == sorted(f"{RESTORED}/{rel}" for rel, _ in FILES)


def test_restore_writes_the_files_in_order_service_md_last_on_disk(tmp_path: Path) -> None:
    class Recording(AtomicWriter):
        def __init__(self, inner: AtomicWriter) -> None:
            self.inner = inner
            self.written: list[str] = []

        def write(self, path: Path, text: str) -> None:
            self.written.append(path.relative_to(tmp_path).as_posix())
            self.inner.write(path, text)

    writer = Recording(fs_atomic_writer(tmp_path).writer)
    FsServiceStore(OrgServicePlaces(OrgPaths(tmp_path)), writer).restore("ceo", "weekly-brief", retired(FILES[::-1]))  # given in any order
    assert writer.written[-1] == f"{RESTORED}/SERVICE.md" and len(writer.written) == len(FILES)


def test_restore_writes_the_files_in_order_service_md_last_in_memory(tmp_path: Path) -> None:
    h = memory_store(tmp_path)
    assert isinstance(h.store, MemoryServiceStore)
    h.restorer.restore("ceo", "weekly-brief", retired(FILES[::-1]))
    assert [h.places.rel(path) for path in h.store.files][-1] == f"{RESTORED}/SERVICE.md"
