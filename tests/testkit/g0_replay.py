"""The kit of the deterministic replays of G0's recorded streams (0b.1 design 6, A4): E5's kit (``testkit.e5_replay``) pointed at ``EVG0`` and G0's
service, ``weekly-meeting-memo``, with four options the 0b.1 replays need.

``materialize(stream, cut, root, *, inflight=None, deliverables=(), team_files=False, history=False)`` writes the organization ``EVG0/<stream>`` had at
the 21-character stamp ``cut`` (inclusive) at ``root/org`` and returns it; see ``e5_replay`` for the rest (messages, run logs, charters).

* ``inflight={ROOT: [id, ...]}`` puts those messages of root in the organization's own ``inflight/`` box (the key ``ROOT`` is mapped to the empty
  address, root's boxes being the organization directory itself).
* The contract is ``service/history--SERVICE.v1.md``. Its ``deliverable.path`` line is rewritten to ``root/deliverables`` when ``deliverables`` are
  pinned, else to ``root/no-deliverables`` (never created): the only edit of a kept record, as in ``org_replay``. The kept contracts name G0's
  ``/tmp/hirearchy-g0-<stream>-<epoch>/deliverables``, which must never be read by a test.
* A pin is ``(name, version file under memos/versions/, UTC mtime, 1-based line of deliverables-log.txt)``: the line must be the header of a logged
  command at exactly that time (``org_replay.log_block``), the version file's md5 must be the one INDEX.txt lists, and the file is written at
  ``root/deliverables/<name>`` with the version's bytes and that mtime.
* ``team_files``: for each path of ``memos/versions/INDEX.txt`` the newest version committed at or before ``cut`` is written at its path in the
  organization (md5 checked against INDEX). A path with no version at or before ``cut`` is not written, and this is no failure (A4).
* ``history`` (needs ``team_files``): the organization becomes a git repository of ONE commit holding everything materialized, so that
  ``CheckedVersions.at_result`` answers every result's artifact with its version at the cut. That is faithful only when no listed file changed between
  a result and the cut, so the kit first checks that no INDEX version of a path a ``done`` result of root's boxes lists was committed after the result's
  stamp and at or before ``cut``.

Every error (a missing evidence file, a bad cut, a bad pin, a version file that is missing or has another md5, an unfaithful history, a failing git)
FAILS the test (``pytest.fail``), never skips it: a replay that quietly did not run proves nothing. The kit reads the evidence only."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.kernel import ROOT, artifact_paths, split_frontmatter

from . import REPO, e5_replay, org_replay

EVG0 = REPO / "studies" / "G0-noise-baseline" / "evidence"  # read when called, so a test can point the module at a copy
SERVICE_NAME = "weekly-meeting-memo"  # the service of every G0 stream, offered by ``lead``
RECEIVED = ("inbox", "inflight", "read")
GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "g0-replay", "GIT_AUTHOR_EMAIL": "g0-replay@example.invalid",
    "GIT_COMMITTER_NAME": "g0-replay", "GIT_COMMITTER_EMAIL": "g0-replay@example.invalid",
}

Pin = tuple[str, str, str, int]


def _stamp_us(stamp: str) -> int:
    """Microseconds since the epoch, UTC, of the 21-character stamp of a message id or a cut (``20261026T062305224870``)."""
    try:
        moment = datetime.strptime(stamp[:21], "%Y%m%dT%H%M%S%f").replace(tzinfo=timezone.utc)
    except ValueError:
        pytest.fail(f"{stamp!r} is not a 21-character stamp")
    delta = moment - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


def _version_file(index: Path, name: str, expected: Mapping[str, list[dict[str, object]]]) -> Path:
    """The kept version file ``name`` (``<stem>.v<k>.<sha7>.md``) with its md5 checked against the INDEX entry that names it."""
    listed = [v for path, versions in expected.items() for v in versions if f"{Path(path).stem}.v{v['k']}.{v['hash']}.md" == name]
    if not listed:
        pytest.fail(f"{index} lists no version file {name}")
    file = index.parent / name
    if not file.is_file():
        pytest.fail(f"no evidence file {file}")
    actual = org_replay.md5_of(file)
    if actual != listed[0]["md5"]:
        pytest.fail(f"{file} has md5 {actual}, but {index.name} lists {listed[0]['md5']}")
    return file


def _pin(source: Path, folder: Path, pin: Pin, entries: Mapping[str, list[dict[str, object]]]) -> None:
    name, version, mtime, line = pin
    time, _ = org_replay.log_block(source / "deliverables-log.txt", line)
    if time != mtime:
        pytest.fail(f"line {line} of {source / 'deliverables-log.txt'} is at {time}, not at the pinned {mtime}")
    target = folder / name
    folder.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_version_file(source / "memos" / "versions" / "INDEX.txt", version, entries).read_bytes())
    pinned = org_replay.utc_us(mtime) * 1000
    os.utime(target, ns=(pinned, pinned))


def _team_files(source: Path, org: Path, cut_us: int, entries: Mapping[str, list[dict[str, object]]]) -> None:
    index = source / "memos" / "versions" / "INDEX.txt"
    for path, versions in entries.items():
        before = [v for v in versions if int(str(v["time"])) <= cut_us]
        if not before:
            continue  # A4: no version of this path at the cut yet
        best = max(before, key=lambda v: (int(str(v["time"])), int(str(v["k"]))))
        file = _version_file(index, f"{Path(path).stem}.v{best['k']}.{best['hash']}.md", entries)
        target = org / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(file.read_bytes())


def _faithful(org: Path, cut: str, entries: Mapping[str, list[dict[str, object]]]) -> None:
    """Fail unless one commit of the organization at ``cut`` gives every done result of root's boxes the version its team had when it reported."""
    cut_us = _stamp_us(cut)
    for box in RECEIVED:
        for message in sorted((org / box).glob("*.md")) if (org / box).is_dir() else []:
            meta, body = split_frontmatter(message.read_text(encoding="utf-8"))
            if meta.get("type") != "result" or meta.get("status") != "done":
                continue
            reported = _stamp_us(str(meta["id"]))
            for path in artifact_paths(body):
                late = [v for v in entries.get(path, []) if reported < int(str(v["time"])) <= cut_us]
                if late:
                    pytest.fail(
                        f"the one-commit history is not faithful at {cut}: {path} listed by the done result {meta['id']} has the version "
                        f"v{late[0]['k']} {late[0]['hash']} committed after the result and at or before the cut"
                    )


def _commit(org: Path) -> None:
    env = {**os.environ, **GIT_IDENTITY}
    for args in (["init", "-q"], ["add", "-A"], ["-c", "commit.gpgsign=false", "commit", "-q", "-m", "the organization at the cut"]):
        try:
            done = subprocess.run(["git", *args], cwd=org, env=env, capture_output=True, text=True)
        except OSError as error:
            pytest.fail(f"git {args[0]} could not run: {error}")
        if done.returncode != 0:
            pytest.fail(f"git {args[0]} failed ({done.returncode}): {done.stderr.strip()}")


def materialize(
    stream: str,
    cut: str,
    root: Path,
    *,
    inflight: Mapping[str, Sequence[str]] | None = None,
    deliverables: Sequence[Pin] = (),
    team_files: bool = False,
    history: bool = False,
) -> Path:
    """Write the organization ``EVG0/<stream>`` had at ``cut`` at ``root/org`` and return it; see the module docstring."""
    if history and not team_files:
        pytest.fail("history needs team_files: the commit would hold no version of the team's files")
    org, source = root / "org", EVG0 / stream
    mapped = {("" if address == ROOT else address): ids for address, ids in (inflight or {}).items()}
    e5_replay.materialize(stream, cut, org, mapped, evidence=EVG0, service=SERVICE_NAME)
    folder = root / ("deliverables" if deliverables else "no-deliverables")
    contract = org / "lead" / "services" / SERVICE_NAME / "SERVICE.md"
    contract.write_bytes(org_replay._contract_text(source / "service" / "history--SERVICE.v1.md", folder))
    entries = org_replay.index_entries(source / "memos" / "versions" / "INDEX.txt") if deliverables or team_files else {}
    for pin in deliverables:
        _pin(source, folder, pin, entries)
    if team_files:
        _team_files(source, org, _stamp_us(cut), entries)
    if history:
        _faithful(org, cut, entries)
        _commit(org)
    return org
