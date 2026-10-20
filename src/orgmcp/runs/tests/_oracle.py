"""The legacy readers of run logs, frozen verbatim from commit ``48fe55e`` (``r1-integration``).

``health._run_windows/_run_outcomes``, ``observe._log_facts`` and ``dashboard_data._read_tail`` become calls of ``RunLogReader`` in step
A-runs, so the live legacy functions can no longer serve as the oracle for the package; these copies do (only the receiver changed: the
directory of the agent's logs is a parameter instead of ``org.dir(addr) / "runs"``, the helpers ``_stamp`` etc. are the kernel's).
Delete this module together with the oracle tests when the last legacy reader is gone (step E1).
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orgmcp.kernel import ROOT, norm, stamp_of, visible

from ._legacy import legacy

_stamp = stamp_of


def runs_used(d: Path) -> int:
    """``RunsMixin.runs_used`` of M2 with ``d = org.dir(addr) / "runs"``."""
    return len(visible(d.glob("*.log"))) if d.is_dir() else 0


def run_windows(d: Path) -> list[tuple[datetime, datetime]]:
    """(start, end) of every run, oldest first: start = log file name, end = log mtime."""
    out = []
    for p in sorted(d.glob("*.log")) if d.is_dir() else []:
        start = None if p.name.startswith(".") else _stamp(p.stem)
        if start:
            out.append((start, max(start, datetime.fromtimestamp(p.stat().st_mtime, timezone.utc))))
    return out


_EXIT_RE = re.compile(r"^# exit (-?\d+) after", re.MULTILINE)
_FAILED_MARKS = ("# failed to start", "# killed after", "# interrupted by scheduler shutdown")
_SENDERS_RE = re.compile(r"^# senders: (.*)$", re.MULTILINE)


def run_outcomes(d: Path) -> tuple[set[datetime], set[datetime]]:
    failed: set[datetime] = set()
    runtime_only: set[datetime] = set()
    for p in sorted(d.glob("*.log")) if d.is_dir() else []:
        start = None if p.name.startswith(".") else _stamp(p.stem)
        if start is None:
            continue
        try:
            with open(p, "rb") as f:
                head = f.read(4096).decode("utf-8", "replace")
                size = f.seek(0, 2)
                f.seek(max(0, size - 2048))
                tail = f.read().decode("utf-8", "replace")
        except OSError:
            continue
        exits = _EXIT_RE.findall(tail)
        if (exits and exits[-1] != "0") or any(f"\n{mark}" in "\n" + tail for mark in _FAILED_MARKS):
            failed.add(start)
        header = head.split("# ---- prompt ----", 1)[0]
        senders = _SENDERS_RE.search(header)
        if senders and {x.strip() for x in senders.group(1).split(",") if x.strip()} == {"runtime"}:
            runtime_only.add(start)
    return failed, runtime_only


_EXIT = re.compile(r"^# exit (-?\d+) after (\d+)s", re.M)


def log_facts(path: Path) -> dict[str, Any]:
    """What the scheduler wrote at the end of a run log (the last ~4 KB): exit code, seconds, how it ended."""
    try:
        with open(path, "rb") as f:
            size = f.seek(0, 2)
            f.seek(max(0, size - 4096))
            tail = f.read().decode("utf-8", "replace")
    except OSError:
        return {}
    facts: dict[str, Any] = {}
    m = list(_EXIT.finditer(tail))
    if m:
        facts["exit_code"], facts["seconds"] = int(m[-1].group(1)), int(m[-1].group(2))
    if re.search(r"^# killed after \d+s timeout", tail, re.M):
        facts["timed_out"] = True
    if re.search(r"^# (killed:|interrupted by scheduler shutdown)", tail, re.M):
        facts["killed"] = True
    if re.search(r"^# failed to start", tail, re.M):
        facts["failed_start"] = True
    return facts


def last_run_end(d: Path) -> float:
    """``Scheduler._last_run_end`` with ``d = org.dir(addr) / "runs"``."""
    logs = d.glob("*.log")
    return max((p.stat().st_mtime for p in logs), default=0.0)


def read_tail(path: Path, rel: str, live: bool) -> Any:
    """``dashboard_data._read_tail`` as it was (the ``RunLog`` it returns and the constants and ``clean_text`` are those of ``dashdata``)."""
    dd = legacy("dashdata")
    LOG_BYTES, LOG_LINES, clean_text, RunLog = dd.LOG_BYTES, dd.LOG_LINES, dd.clean_text, dd.RunLog
    log = RunLog(path=path, rel=rel, running=live)
    try:
        with open(path, "rb") as f:
            size = f.seek(0, 2)
            log.size = size
            f.seek(max(0, size - LOG_BYTES))
            data = f.read()
            head_raw = b""
            if size > len(data):
                f.seek(0)
                head_raw = f.read(4096)
    except OSError:
        log.note = "the run log could not be read"
        return log
    text = data.decode("utf-8", errors="replace")
    cut = size > len(data)
    if cut and "\n" in text:
        text = text.split("\n", 1)[1]  # the first line is cut
    lines = clean_text(text).split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # no trailing empty line (a partial last line is kept as it is)
    if len(lines) > LOG_LINES:
        lines = lines[-LOG_LINES:]
        cut = True
    log.truncated = cut
    log.lines = lines
    head_text = clean_text((head_raw or data[:4096]).decode("utf-8", errors="replace"))
    stem_time = _stamp(path.stem)
    header = [f"started {stem_time:%Y-%m-%d %H:%M:%S}Z" if stem_time else f"log {path.name}"]
    for ln in head_text.split("\n")[:8]:
        if ln.startswith(("# run of", "# senders:")):
            header.append(ln[2:])
    tail = "\n".join(lines[-40:])
    ends = re.findall(r"^# (exit -?\d+ after \d+s|failed to start.*|killed after.*|interrupted by scheduler shutdown.*|killed:.*)$",
                      tail, re.M)
    header.append(ends[-1] if ends else ("still running" if live else "no exit line (still running or interrupted)"))
    log.header = header
    return log


class LenientRuns:
    """``LenientOrg.runs_used`` of the dashboard, frozen verbatim from the class that was dissolved in C-dashdata: one ``stat`` per directory per ``tick``, and a
    count that is reused while the ``runs`` directory has the modification time it had when it was counted, if it had been quiet for ``CACHE_TRUST`` seconds."""

    CACHE_TRUST = 2.0  # a directory modified less than this many seconds before it was listed is listed again next time

    def __init__(self, root: Path) -> None:
        self._root_s = str(root)
        self._runs_cache: dict[str, tuple[int, bool, int]] = {}
        self._stat_memo: dict[tuple[str, str], int] = {}

    def tick(self) -> None:
        self._stat_memo.clear()

    def mtime(self, addr: str, name: str) -> int:
        a = norm(addr)
        key = (a, name)
        v = self._stat_memo.get(key)
        if v is None:
            path = self._root_s if a == ROOT else os.path.join(self._root_s, a)
            try:
                v = os.stat(os.path.join(path, name) if name else path).st_mtime_ns
            except OSError:
                v = -1
            self._stat_memo[key] = v
        return v

    def _trusted(self, listed_at: int, mtime: int) -> bool:
        return (listed_at - mtime) > self.CACHE_TRUST * 1e9

    def runs_used(self, addr: str) -> int:
        mtime = self.mtime(addr, "runs")
        if mtime < 0:
            return 0
        key = norm(addr)
        hit = self._runs_cache.get(key)
        if hit is not None and hit[0] == mtime and hit[1]:
            return hit[2]
        listed_at = time.time_ns()
        n = runs_used(Path(self._root_s) / key / "runs")
        self._runs_cache[key] = (mtime, self._trusted(listed_at, mtime), n)
        return n
