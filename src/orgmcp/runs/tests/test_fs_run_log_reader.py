"""``FsRunLogReader`` on real directories, compared with the legacy readers (frozen in ``_oracle``) on a corpus of logs."""

from __future__ import annotations

import os
import random
from collections.abc import Iterator
from pathlib import Path

import pytest

from orgmcp.kernel import OrgPaths
from orgmcp.runs import (
    RunLogReader,
    log_exit,
    log_failed_start,
    log_header,
    log_interrupted,
    log_invocation,
    log_prompt,
    log_retired,
    log_timeout,
)
from orgmcp.runs._reader import FsRunLogReader

from . import _oracle

STAMPS = [f"2026101{day}T{hour:02d}0000{micro:06d}" for day in (7, 8) for hour in (9, 10, 11) for micro in (1, 999999)]
def footers() -> list[str]:
    return [
        "", log_exit(0, 3), log_exit(1, 2), log_exit(-9, 60), log_timeout(60) + log_exit(-9, 60), log_retired() + log_exit(-9, 4),
        log_interrupted(), log_failed_start("no such file"), "\n# exit 0 after 1s\n# exit 3 after 9s\n", "\n# exit 3 after 1s\n# exit 0 after 9s\n",
    ]


SENDERS = [["root"], ["runtime"], ["runtime", "root"], ["ceo/eng"], []]
BODIES = [b"short\n", b"x" * 100 + b"\n", b"x" * 2500 + b"\n", b"x" * 5000 + b"\n", b"binary \xff\xfe junk\n"]


def corpus(rng: random.Random) -> Iterator[tuple[str, bytes]]:
    for stamp in rng.sample(STAMPS, 9):
        head = log_header("ceo", rng.randint(1, 3), rng.choice(SENDERS)) + log_invocation("/w", ["kiro"]) + log_prompt("p" * rng.choice([5, 5000]))
        yield f"{stamp}.log", head.encode("utf-8") + rng.choice(BODIES) + rng.choice(footers()).encode("utf-8")


@pytest.fixture
def org(tmp_path: Path) -> Path:
    (tmp_path / "ceo").mkdir()
    return tmp_path


def fill(org: Path, seed: int) -> Path:
    runs = org / "ceo" / "runs"
    runs.mkdir(exist_ok=True)
    rng = random.Random(seed)
    for name, content in corpus(rng):
        path = runs / name
        path.write_bytes(content)
        os.utime(path, (1_790_000_000 + rng.randint(0, 10_000_000), 1_790_000_000 + rng.randint(0, 10_000_000)))
    (runs / ".hidden.log").write_bytes(b"# exit 1 after 1s\n")
    (runs / "manual.log").write_bytes(b"# exit 1 after 1s\n")
    (runs / "notes.txt").write_bytes(b"x")
    return runs


def test_the_reader_implements_the_port(org: Path) -> None:
    assert isinstance(FsRunLogReader(OrgPaths(org)), RunLogReader)


@pytest.mark.parametrize("seed", range(8))
def test_it_answers_as_the_legacy_readers_did(org: Path, seed: int) -> None:
    runs = fill(org, seed)
    reader = FsRunLogReader(OrgPaths(org))
    outcomes = reader.outcomes("ceo")
    assert reader.count("ceo") == _oracle.runs_used(runs)
    assert [(w.start, w.end) for w in reader.windows("ceo")] == _oracle.run_windows(runs)
    assert (set(outcomes.failed), set(outcomes.runtime_only)) == _oracle.run_outcomes(runs)
    assert reader.last_end("ceo") == _oracle.last_run_end(runs)
    for log in sorted(runs.iterdir()):
        assert reader.facts(log) == _oracle.log_facts(log)


def test_it_answers_as_the_legacy_readers_did_for_an_agent_without_logs(org: Path) -> None:
    reader = FsRunLogReader(OrgPaths(org))
    runs = org / "ceo" / "runs"
    assert (reader.count("ceo"), reader.windows("ceo"), reader.last_end("ceo")) == (_oracle.runs_used(runs), _oracle.run_windows(runs), 0.0)
    assert reader.facts(runs / "x.log") == _oracle.log_facts(runs / "x.log") == {}


def test_a_directory_that_looks_like_a_log_is_skipped_by_the_judgement_and_has_no_facts(org: Path) -> None:
    runs = org / "ceo" / "runs"
    (runs / "20261018T100000000001.log").mkdir(parents=True)
    reader = FsRunLogReader(OrgPaths(org))
    assert reader.outcomes("ceo").failed == frozenset() and reader.facts(runs / "20261018T100000000001.log") == {}
    assert reader.count("ceo") == _oracle.runs_used(runs) == 1


def test_the_root_agent_reads_the_logs_in_the_organization_directory(org: Path) -> None:
    (org / "runs").mkdir()
    (org / "runs" / "20261018T100000000001.log").write_text("x", encoding="utf-8")
    assert FsRunLogReader(OrgPaths(org)).count("root") == 1


def test_a_log_is_read_by_bytes_not_by_lines(org: Path) -> None:
    """A log can be very large: only the end (or the start) is read, whatever the size."""
    runs = org / "ceo" / "runs"
    runs.mkdir()
    big = runs / "20261018T100000000001.log"
    with open(big, "wb") as f:
        f.write(b"# run of ceo, 1 message(s)\n")
        f.seek(64 * 1024 * 1024)  # a sparse file: no disk is used for the hole
        f.write(b"\n# exit 2 after 9s\n")
    reader = FsRunLogReader(OrgPaths(org))
    assert reader.facts(big) == {"exit_code": 2, "seconds": 9}
    assert len(reader.outcomes("ceo").failed) == 1
    assert reader.tail(big, 100, 5) == ("# exit 2 after 9s\n", True)
    assert reader.head(big, 10) == "# run of c"
