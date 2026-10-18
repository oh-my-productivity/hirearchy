"""The real adapters in ``_system.py``: what only the filesystem / the operating system can show.

The behaviour every implementation shares is in ``test_contract_*.py``; this module holds the facts that hold for these
adapters only (temp files, bytes on disk, the process environment)."""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orgmcp.kernel import OrgPaths
from orgmcp.kernel._system import FsAtomicWriter, FsLedgerStore, OsEnvironment, SystemClock, TimestampIdGenerator
from orgmcp.kernel.testing import FakeClock, MemoryAtomicWriter, MemoryLedgerStore

pytestmark = pytest.mark.xfail(strict=True, reason="red: K1")


# ----------------------------------------------------------------------------------------------- FsAtomicWriter


def _temp_files(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir() if p.name.startswith(".tmp-"))


def test_the_text_goes_through_a_temp_file_beside_the_target_which_is_renamed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    renames: list[tuple[str, str]] = []
    real_replace = os.replace

    def spy(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        renames.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    FsAtomicWriter(token_hex=lambda nbytes: "cafe" * (nbytes // 2)).write(tmp_path / "sub" / "file.md", "text")
    assert renames == [(str(tmp_path / "sub" / ".tmp-cafecafe-file.md"), str(tmp_path / "sub" / "file.md"))]
    assert (tmp_path / "sub" / "file.md").read_text(encoding="utf-8") == "text" and _temp_files(tmp_path / "sub") == []


def test_the_default_temp_name_has_eight_random_hex_digits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    real_replace = os.replace

    def spy(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        seen.append(Path(src).name)
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    FsAtomicWriter().write(tmp_path / "f.txt", "x")
    assert re.fullmatch(r"\.tmp-[0-9a-f]{8}-f\.txt", seen[0])


def test_a_failed_rename_leaves_no_temp_file_and_the_old_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "f.txt"
    FsAtomicWriter().write(target, "old")

    def boom(src: object, dst: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        FsAtomicWriter().write(target, "new")
    assert target.read_text(encoding="utf-8") == "old" and _temp_files(tmp_path) == []


def test_a_failed_write_leaves_no_temp_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def half_write(self: Path, data: str, encoding: str | None = None, errors: str | None = None, newline: str | None = None) -> int:
        with open(self, "w", encoding="utf-8") as f:
            f.write(data[:2])
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(Path, "write_text", half_write)
    with pytest.raises(OSError):
        FsAtomicWriter().write(tmp_path / "f.txt", "complete text")
    assert _temp_files(tmp_path) == [] and not (tmp_path / "f.txt").exists()


def test_the_text_is_written_as_utf_8(tmp_path: Path) -> None:
    FsAtomicWriter().write(tmp_path / "u.txt", "é✓")
    assert (tmp_path / "u.txt").read_bytes() == "é✓".encode("utf-8")


# ---------------------------------------------------------------------------------------------- FsLedgerStore


def test_a_ledger_is_json_with_two_space_indent_and_a_newline_in_the_runtime_directory(tmp_path: Path) -> None:
    store = FsLedgerStore(OrgPaths(tmp_path), FsAtomicWriter())
    store.write("failures", {"ceo": 2, "names": ["é"]})
    expected = '{\n  "ceo": 2,\n  "names": [\n    "\\u00e9"\n  ]\n}\n'  # json.dumps(indent=2), ASCII-escaped, one newline
    assert (tmp_path / ".runtime" / "failures.json").read_text(encoding="utf-8") == expected


def test_the_ledger_is_written_through_the_injected_writer(tmp_path: Path) -> None:
    writer = MemoryAtomicWriter()
    FsLedgerStore(OrgPaths(tmp_path), writer).write("running", {"a": 1})
    assert writer.files == {tmp_path / ".runtime" / "running.json": '{\n  "a": 1\n}\n'}
    assert not (tmp_path / ".runtime").exists()


def test_the_memory_ledger_keeps_the_text_the_real_store_writes(tmp_path: Path) -> None:
    data = {"ceo": 2, "names": ["é"], "nested": {"a": None}}
    memory = MemoryLedgerStore()
    memory.write("failures", data)
    FsLedgerStore(OrgPaths(tmp_path), FsAtomicWriter()).write("failures", data)
    assert memory.texts == {"failures": (tmp_path / ".runtime" / "failures.json").read_text(encoding="utf-8")}


def test_a_ledger_file_written_by_hand_is_read(tmp_path: Path) -> None:
    (tmp_path / ".runtime").mkdir()
    (tmp_path / ".runtime" / "nudges.json").write_text('{"a": {"n": 1}}', encoding="utf-8")
    assert FsLedgerStore(OrgPaths(tmp_path), FsAtomicWriter()).read("nudges") == {"a": {"n": 1}}


def test_a_ledger_with_invalid_utf_8_reads_as_empty(tmp_path: Path) -> None:
    (tmp_path / ".runtime").mkdir()
    (tmp_path / ".runtime" / "nudges.json").write_bytes(b'{"a": "\xff"}')
    assert FsLedgerStore(OrgPaths(tmp_path), FsAtomicWriter()).read("nudges") == {}


# ----------------------------------------------------------------------------------------------- SystemClock


def test_the_system_clock_reads_the_system_time() -> None:
    clock = SystemClock()
    assert abs((clock.now() - datetime.now(timezone.utc)).total_seconds()) < 5
    assert clock.now().tzinfo is timezone.utc
    assert abs(clock.time() - time.time()) < 5
    first = clock.monotonic()
    assert 0 <= clock.monotonic() - first < 5


def test_the_system_clock_really_sleeps() -> None:
    clock = SystemClock()
    before = time.monotonic()
    clock.sleep(0.05)
    assert time.monotonic() - before >= 0.04


# ------------------------------------------------------------------------------------- TimestampIdGenerator


def test_the_id_is_built_from_the_injected_clock_and_token_source() -> None:
    asked: list[int] = []

    def token(nbytes: int) -> str:
        asked.append(nbytes)
        return "ab12"

    ids = TimestampIdGenerator(FakeClock(), token_hex=token)
    assert ids.message_id("ceo/eng") == "20261018T100000000001-ceo.eng-ab12"
    assert ids.message_id("root") == "20261018T100000000002-root-ab12"
    assert asked == [2, 2]


def test_the_default_token_is_four_random_hex_digits() -> None:
    tokens = {TimestampIdGenerator(FakeClock()).message_id("a")[-4:] for _ in range(40)}
    assert all(re.fullmatch(r"[0-9a-f]{4}", t) for t in tokens) and len(tokens) > 1


def test_the_timestamp_is_the_microsecond_utc_time() -> None:
    clock = FakeClock(datetime(2026, 1, 2, 3, 4, 5, 678901, tzinfo=timezone.utc) - timedelta(microseconds=1))
    assert TimestampIdGenerator(clock).message_id("x").startswith("20260102T030405678901-x-")


# ------------------------------------------------------------------------------------------- OsEnvironment


def test_the_os_environment_reads_the_live_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    env = OsEnvironment()
    monkeypatch.setenv("ORGMCP_KERNEL_SYSTEM_TEST", "now")
    assert env.get("ORGMCP_KERNEL_SYSTEM_TEST") == "now"
    monkeypatch.delenv("ORGMCP_KERNEL_SYSTEM_TEST")
    assert env.get("ORGMCP_KERNEL_SYSTEM_TEST") is None


def test_the_os_environment_directories_are_the_process_ones(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    env = OsEnvironment()
    assert env.home() == tmp_path and env.cwd() == tmp_path.resolve()


def test_variables_is_a_copy_of_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORGMCP_KERNEL_SYSTEM_TEST", "x")
    copy = OsEnvironment().variables()
    assert dict(copy) == dict(os.environ)
    assert copy is not os.environ
