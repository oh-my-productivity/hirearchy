"""The text format of a run log, written and parsed in one place.

A log is the header the scheduler writes before it starts the agent (``log_header``, ``log_invocation``, ``log_prompt``), then
whatever the agent prints, then one closing line (``log_exit`` and the others). Budget, health, observe and the dashboard read
these lines back; before this module existed the two sides agreed by convention. Everything here is pure text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from pathlib import Path

from ..kernel import JsonObject

HEAD_BYTES = 4096  # how much of the start of a log is looked at for the header (outcomes)
TAIL_BYTES = 2048  # how much of the end of a log is looked at for the closing line (outcomes)
FACTS_BYTES = 4096  # how much of the end of a log is looked at for the facts about how it ended

PROMPT_MARK = "# ---- prompt ----"
OUTPUT_MARK = "# ---- output ----"

# ------------------------------------------------------------------------------------------------------------- what is written


def run_id_of(addr: str, log: Path | str) -> str:
    """The id of a run: ``<agent>@<run log stem>`` (the stem is the start timestamp)."""
    return f"{addr}@{Path(log).stem}"


def run_record(*, pgid: int, lstart: str | None, started: float, scheduler: int, log: str) -> JsonObject:
    """The registry entry of a run in flight; ``log`` is the path of its log below the organization. The process was started in its own
    session, so its process group is ``pgid``; ``lstart`` is what ``ps`` said about its start time (None: unknown)."""
    return {"pgid": pgid, "lstart": lstart, "started": started, "scheduler": scheduler, "log": log}


def log_header(addr: str, messages: int, senders: Iterable[str]) -> str:
    """The first lines of a log: the agent, the size of the batch, and who sent it (health tells runtime-only runs apart by this)."""
    names = ", ".join(sorted(set(senders)))
    return f"# run of {addr}, {messages} message(s)\n# senders: {names}\n"


def log_invocation(cwd: Path | str, cmd: Sequence[str]) -> str:
    """Where and how the agent is started."""
    return f"# cwd: {cwd}\n# cmd: {' '.join(cmd)} <prompt on stdin>\n"


def log_prompt(prompt: str) -> str:
    """The prompt the agent gets, between two marks; the agent's output follows."""
    return f"{PROMPT_MARK}\n{prompt}\n{OUTPUT_MARK}\n"


def log_exit(code: int, elapsed: float) -> str:
    """The closing line of a run that ended; ``code`` is negative when a signal ended it."""
    return f"\n# exit {code} after {elapsed:.0f}s\n"


def log_timeout(seconds: float) -> str:
    """The run was killed because it ran longer than the timeout (``log_exit`` follows)."""
    return f"\n# killed after {seconds:.0f}s timeout\n"


def log_retired() -> str:
    """The run was killed because its agent was retired during it (``log_exit`` follows)."""
    return "\n# killed: the agent was retired during its run\n"


def log_interrupted() -> str:
    """The scheduler was shut down while the run was in flight."""
    return "\n# interrupted by scheduler shutdown\n"


def log_failed_start(reason: object) -> str:
    """The agent could not be started."""
    return f"\n# failed to start: {reason}\n"


def log_note(text: str) -> str:
    """A comment added to a log after the fact (e.g. ``killed: orphaned run of a scheduler that died``)."""
    return f"\n# {text}\n"


# ---------------------------------------------------------------------------------------------------------------- what is read

_EXIT_CODE = re.compile(r"^# exit (-?\d+) after", re.MULTILINE)
_FAILED_MARKS = ("# failed to start", "# killed after", "# interrupted by scheduler shutdown")
_SENDERS = re.compile(r"^# senders: (.*)$", re.MULTILINE)
_EXIT_FACT = re.compile(r"^# exit (-?\d+) after (\d+)s", re.M)


def is_failed(tail: str) -> bool:
    """The end of a log says the run failed: its last exit code is not 0, or it failed to start, timed out or was interrupted."""
    exits = _EXIT_CODE.findall(tail)
    return bool((exits and exits[-1] != "0") or any(f"\n{mark}" in "\n" + tail for mark in _FAILED_MARKS))


def is_runtime_only(head: str) -> bool:
    """The start of a log says every message of the batch came from the runtime itself."""
    header = head.split(PROMPT_MARK, 1)[0]
    senders = _SENDERS.search(header)
    return bool(senders and {x.strip() for x in senders.group(1).split(",") if x.strip()} == {"runtime"})


def parse_facts(tail: str) -> JsonObject:
    """What the closing lines in ``tail`` say: ``exit_code`` and ``seconds`` (the last exit line), ``timed_out``, ``killed``, ``failed_start``."""
    facts: JsonObject = {}
    m = list(_EXIT_FACT.finditer(tail))
    if m:
        facts["exit_code"], facts["seconds"] = int(m[-1].group(1)), int(m[-1].group(2))
    if re.search(r"^# killed after \d+s timeout", tail, re.M):
        facts["timed_out"] = True
    if re.search(r"^# (killed:|interrupted by scheduler shutdown)", tail, re.M):
        facts["killed"] = True
    if re.search(r"^# failed to start", tail, re.M):
        facts["failed_start"] = True
    return facts


def cut_tail(data: bytes, size: int, max_lines: int) -> tuple[str, bool]:
    """The text of ``data``, the last bytes of a file of ``size`` bytes, cut to its last ``max_lines`` lines.

    A file longer than ``data`` was cut in the middle of a line: the first line is dropped (even when the cut fell on a line start).
    A final newline is kept but is not a line.
    """
    text = data.decode("utf-8", errors="replace")
    cut = size > len(data)
    if cut and "\n" in text:
        text = text.split("\n", 1)[1]
    lines = text.split("\n")
    ended = len(lines) > 1 and lines[-1] == ""
    body = lines[:-1] if ended else lines
    if len(body) > max_lines:
        body, cut = body[-max_lines:], True
    return "\n".join(body) + ("\n" if ended else ""), cut
