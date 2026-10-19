"""``CachedRunLogViews``: the tail of a run log, cleaned and cut, read again only when the file changed."""

from __future__ import annotations

import re
from pathlib import Path

from ..kernel import OrgLayout, stamp_of
from ..runs import RunLogReader, RunRegistry
from ._const import LOG_BYTES, LOG_LINES
from ._data import RunLog
from ._ports import RunLogViews
from ._text import clean_text

LOGS_KEPT = 40  # run logs whose tail is kept


def read_tail(reader: RunLogReader, path: Path, rel: str, live: bool) -> RunLog:
    log = RunLog(path=path, rel=rel, running=live)
    try:
        size = path.stat().st_size
        # Two lines more than are shown: the last line may be nothing but escape codes, which ``clean_text`` empties and the pop
        # below drops, and the lines are counted after that (as they always were).
        text, cut = reader.tail(path, LOG_BYTES, LOG_LINES + 2)
        head_raw = reader.head(path, 4096)
    except OSError:
        log.note = "the run log could not be read"
        return log
    log.size = size
    lines = clean_text(text).split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # no trailing empty line (a partial last line is kept as it is)
    if len(lines) > LOG_LINES:
        lines = lines[-LOG_LINES:]
        cut = True
    log.truncated = cut
    log.lines = lines
    head_text = clean_text(head_raw)
    stem_time = stamp_of(path.stem)
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


class CachedRunLogViews(RunLogViews):
    """The tail of the agent's current run log (in flight) or latest run log. Reads at most the last ~1 MB, only when the file changed."""

    def __init__(self, layout: OrgLayout, registry: RunRegistry, runs: RunLogReader) -> None:
        self._layout = layout
        self._registry = registry
        self._runs = runs
        self._logs: dict[Path, tuple[tuple[int, int, bool], RunLog]] = {}

    def run_log(self, addr: str, live: bool) -> RunLog:
        root = self._layout.root
        path: Path | None = None
        if live:
            rec = self._registry.all().get(addr) or {}
            if rec.get("log"):
                cand = root / str(rec["log"])
                if cand.is_file() and root in cand.resolve().parents:
                    path = cand
        if path is None:
            logs = self._runs.files(addr)
            path = logs[-1].path if logs else None
        if path is None:
            return RunLog(note="this agent has not run yet")
        try:
            st = path.stat()
        except OSError:
            return RunLog(note="the run log is gone")
        key = (st.st_size, st.st_mtime_ns, live)
        hit = self._logs.get(path)
        if hit is not None and hit[0] == key:
            return hit[1]
        log = read_tail(self._runs, path, self._rel(path), live)
        self._logs[path] = (key, log)
        if len(self._logs) > LOGS_KEPT:
            self._logs.pop(next(iter(self._logs)))
        return log

    def _rel(self, p: Path) -> str:
        try:
            return str(p.relative_to(self._layout.root))
        except ValueError:
            return str(p)
