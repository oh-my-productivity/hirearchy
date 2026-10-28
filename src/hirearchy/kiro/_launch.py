"""The run launcher: starts kiro-cli, checks that it runs the V3 engine, and writes a short transcript of its stream-json output.

Run as a script (``python -I -S _launch.py --start-deadline N -- KIRO_ARGV...``, docs/design/kiro-runtime-v3.md 5.1 and 5.2), so it
imports only the standard library and nothing of ``hirearchy``. Its state is plain data driven by module functions.
"""

from __future__ import annotations

import json
import os
import re
import select
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field

COPY_LIMIT = 4096  # bytes of non-JSON output copied to the log before the run starts
DRAIN_SECONDS = 2.0  # how long output is read after kiro has exited (a background child may keep the pipe open)
SLICE_SECONDS = 1.0  # one select() turn
CUT_INPUT, CUT_DENIAL, CUT_ERROR, CUT_PLAIN = 200, 300, 500, 2000  # longest piece of a tool input / denial / error / plain line
USAGE = "usage: _launch.py --start-deadline SECONDS -- KIRO_ARGV..."
THROTTLE_EXIT = 75  # EX_TEMPFAIL of sysexits.h: the launcher's verdict "throttled by the model service before any tool effect" (kiro's own 75 becomes 1)
THROTTLE_MARK = "# kiro: throttled by the model service (retryErrorType THROTTLING); tool effects: "  # followed by "none" or the number of effects
THROTTLING = '"retryErrorType":"THROTTLING"'  # as it reads in a run error with its spaces removed
EFFORT_PREFIX = "failed to set effort"  # the stable start of kiro-cli's warning that it did not apply --effort, whatever reason follows it
# A stderr line that starts with the prefix, at once or after one level tag such as "[warn] ": group 1 is kiro's text from the prefix on.
EFFORT_LINE = re.compile(r"(?:\[[A-Za-z]{1,10}\] )?(" + re.escape(EFFORT_PREFIX) + r"\b.*)")
EFFORT_MARK = "# kiro: effort not set, run stopped (kiro-cli: "  # followed by the warning, "); tool effects: " and "none" or the number of effects
EFFORT_EFFECTS = re.compile(r"\); tool effects: (none|[0-9]+)$")
CUT_WARNING = 300  # longest warning kept in the mark
READ_KINDS = ("read", "search", "think", "fetch")  # kinds of tool call that change nothing
# The tools of hirearchy that change nothing, as kiro names them (sorted). Pinned equal to observability's READ_ONLY_TOOLS by
# tests/architecture/test_read_only_tool_ids.py: the launcher is standard library only and cannot import it.
READ_ONLY_TOOL_IDS = (
    "hirearchy::health",
    "hirearchy::inbox",
    "hirearchy::observe",
    "hirearchy::org_read",
    "hirearchy::progress",
    "hirearchy::quality",
    "hirearchy::read",
    "hirearchy::services",
    "hirearchy::status",
    "hirearchy::whoami",
)


# ------------------------------------------------------------------------------------------------------------ the renderer


@dataclass
class RenderState:
    partial: str = ""  # an agent line that is not finished yet
    titles: dict[str, str] = field(default_factory=dict)  # toolCallId -> title
    targets: dict[str, str] = field(default_factory=dict)  # toolCallId -> path or input
    calls: dict[str, tuple[str, str, bool]] = field(default_factory=dict)  # toolCallId -> (kind, tool id, is a tool load) of its tool_call
    effects: int = 0  # completed tool calls that may have changed something
    throttled: bool = False  # the run ended on a model-service throttle (a runError with retryErrorType THROTTLING)


def _obj(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _flush(state: RenderState) -> list[str]:
    lines = [state.partial] if state.partial else []
    state.partial = ""
    return lines


def _target(update: dict[str, object]) -> str:
    """The path of a tool call, else its input as compact JSON (at most 200 characters)."""
    locations = update.get("locations")
    if isinstance(locations, list) and locations:
        path = _text(_obj(locations[0]).get("path"))
        if path:
            return path
    raw = update.get("rawInput")
    if not raw:
        return ""
    return json.dumps(raw, separators=(",", ":"), ensure_ascii=False)[:CUT_INPUT]


def _denial(update: dict[str, object]) -> str:
    """Kiro's denial text of a failed tool, only when it is one (any other content may be a tool's output and is never copied)."""
    content = update.get("content")
    text = ""
    if isinstance(content, list):
        for item in content:
            found = _obj(_obj(item).get("content")).get("text")
            if isinstance(found, str):
                text = found
                break
    elif isinstance(content, dict):
        text = _text(content.get("message"))
    if not text.startswith("Tool call denied"):
        return ""
    return text.replace("\r", "").replace("\n", " ")[:CUT_DENIAL]


def _mark(*parts: str) -> str:
    return " ".join(part for part in parts if part)


def _facts(update: dict[str, object]) -> tuple[str, str, bool | None]:
    """What a tool call or update says of itself: its kind, its tool id, and whether it is a tool load (None: its input does not say)."""
    raw = _obj(update.get("rawInput"))
    tool_id = _text(raw.get("tool_id"))
    is_load = (isinstance(raw.get("tool_ids"), list) and not tool_id) if ("tool_id" in raw or "tool_ids" in raw) else None
    return _text(update.get("kind")), tool_id, is_load


def _completed(state: RenderState, identifier: str, update: dict[str, object]) -> None:
    """Count a completed tool call as an effect unless it is read-only; a fact the update lacks comes from its call, else it is unknown."""
    kind, tool_id, is_load = _facts(update)
    known = state.calls.get(identifier, ("", "", False))
    kind, tool_id = kind or known[0], tool_id or known[1]
    if is_load is None:
        is_load = known[2]
    if not (kind in READ_KINDS or is_load or tool_id in READ_ONLY_TOOL_IDS):
        state.effects += 1


def _session_update(state: RenderState, update: dict[str, object]) -> list[str]:
    kind = _text(update.get("sessionUpdate"))
    identifier = _text(update.get("toolCallId"))
    if kind == "tool_call":
        title, target = _text(update.get("title")), _target(update)
        state.titles[identifier], state.targets[identifier] = title, target
        kind_of, tool_id, is_load = _facts(update)
        state.calls[identifier] = (kind_of, tool_id, bool(is_load))
        if update.get("status") == "completed":
            _completed(state, identifier, update)
        return [_mark("[tool]", title, target)]
    if kind == "tool_call_update":
        status = update.get("status")
        if status not in ("completed", "failed"):
            return []
        title = _text(update.get("title")) or state.titles.get(identifier, "")
        target = _target(update) or state.targets.get(identifier, "")
        if status == "completed":
            _completed(state, identifier, update)
            return [_mark("[tool ok]", title, target)]
        line = _mark("[tool failed]", title, target)
        denial = _denial(update)
        return [f"{line}: {denial}" if denial else line]
    return []


def render_line(state: RenderState, line: str) -> list[str]:
    """The transcript lines of one line of kiro's output (never raises; unknown events write nothing)."""
    stripped = line.strip()
    if not stripped:
        return []
    try:
        data = json.loads(stripped)
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return _flush(state) + [line.rstrip()[:CUT_PLAIN]]
    kind, body = _text(data.get("type")), _obj(data.get("data"))
    lines: list[str]
    if kind == "sessionUpdate":
        update = _obj(body.get("update"))
        if update.get("sessionUpdate") == "agent_message_chunk":
            state.partial += _text(_obj(update.get("content")).get("text"))
            *done, state.partial = state.partial.split("\n")
            return done
        lines = _session_update(state, update)
    elif kind == "runFinished":
        stop = _text(body.get("stopReason"))
        lines = [_mark("[run finished]", _text(body.get("status")), f"({stop})" if stop else "")]
    elif kind == "runError":
        whole = _text(body.get("message")).replace("\r", "").replace("\n", " ")
        message = whole[:CUT_ERROR]
        if "THROTTLING" in (body.get("retryErrorType"), _obj(body.get("data")).get("retryErrorType")) or THROTTLING in whole.replace(" ", ""):
            state.throttled = True
        lines = ["[run error] " + ": ".join(part for part in (_text(body.get("stage")), message) if part)]
    else:
        lines = []
    return _flush(state) + lines if lines else []


def finish(state: RenderState) -> list[str]:
    """What is still waiting at the end of the output, then the mark of a throttled run (its tool effects: ``none`` or a number)."""
    lines = _flush(state)
    if state.throttled:
        lines.append(THROTTLE_MARK + (str(state.effects) if state.effects else "none"))
    return lines


def throttled_without_effect(tail: str) -> bool:
    """The transcript of a run says it ended on a throttle before any tool effect (design 9.1, DR-44): the mark ``...; tool effects: none``
    is the last ``# kiro:`` line before the runtime's closing ``# exit`` line, and a ``[run error]`` line carrying the throttle stands before it.

    Kiro's own stderr lines may sit between them or after the mark; a later ``# kiro:`` line, no throttling run error, or an effect makes it
    false. An agent's text can forge both lines, so the exit code ``THROTTLE_EXIT`` of the launcher is the verdict and this is its second check."""
    lines = tail.splitlines()
    closing = [i for i, line in enumerate(lines) if line.startswith("# exit ")]
    before = lines[: closing[-1]] if closing else lines
    marks = [i for i, line in enumerate(before) if line.startswith("# kiro:")]
    if not marks or before[marks[-1]] != THROTTLE_MARK + "none":
        return False
    return any(line.startswith("[run error] ") and THROTTLING in line.replace(" ", "") for line in before[: marks[-1]])


def effort_warning(line: str) -> str:
    """Kiro's warning that it did not set the effort, as the mark quotes it (from the prefix on, without trailing space and ``\\r``, cut at 300
    characters), or ``""`` when ``line`` is not one."""
    found = EFFORT_LINE.match(line.rstrip())
    return found.group(1).replace("\r", "")[:CUT_WARNING] if found else ""


@dataclass(frozen=True)
class EffortStop:
    warning: str  # kiro's warning from the prefix on, as the mark quotes it
    effects: int  # tool effects before the stop; 0 = none


def effort_stop(tail: str) -> EffortStop | None:
    """The launcher's stop of a run whose kiro-cli did not set its effort, as the end of the run log records it (never raises): the mark
    ``EFFORT_MARK ... ; tool effects: none|<n>`` is the last ``# kiro:`` line before the runtime's closing ``# exit`` line, and kiro's warning
    stands on a line before it. An agent's text or shell can forge both lines, so the exit -9 the scheduler did not cause is the verdict and
    this is its second check."""
    lines = tail.splitlines()
    closing = [i for i, line in enumerate(lines) if line.startswith("# exit ")]
    before = lines[: closing[-1]] if closing else lines
    marks = [i for i, line in enumerate(before) if line.startswith("# kiro:")]
    if not marks or not before[marks[-1]].startswith(EFFORT_MARK):
        return None
    mark = before[marks[-1]]
    ending = EFFORT_EFFECTS.search(mark)
    if ending is None or not any(effort_warning(line) for line in before[: marks[-1]]):
        return None
    effects = ending.group(1)
    return EffortStop(mark[len(EFFORT_MARK) : ending.start()], 0 if effects == "none" else int(effects))


# ----------------------------------------------------------------------------------------------------------- the launcher


def emit(text: str) -> None:
    """One line to the run log, at once (no buffering: it stays in order with kiro's own stderr)."""
    data = (text + "\n").encode("utf-8", errors="replace")
    try:
        while data:
            data = data[os.write(1, data) :]
    except OSError:
        pass


@dataclass
class Start:
    outcome: str  # "started", "refused", "gave_up" or "ended"
    text: str = ""  # why, for "refused"
    rest: bytes = b""  # output read after the start line


def _json_object(raw: bytes) -> dict[str, object] | None:
    try:
        data = json.loads(raw.decode("utf-8", errors="replace").strip())
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _copy(raw: bytes, room: int) -> int:
    """Copy non-JSON output to the log (at most ``room`` bytes); the number of bytes used."""
    piece = raw[: max(room, 0)]
    for line in piece.decode("utf-8", errors="replace").replace("\r", "\n").split("\n"):
        if line.strip():
            emit(line)
    return len(piece)


def _decide(first: dict[str, object], rest: bytes) -> Start:
    kind = first.get("type")
    if kind != "runStarted":
        return Start("refused", f'the first event of kiro-cli was "{kind}", not "runStarted"')
    engine = _obj(first.get("data")).get("engine")
    if engine != "v3":
        return Start("refused", f'kiro-cli started engine "{engine}"; hirearchy needs "v3"')
    return Start("started", rest=rest)


def _wait_for_start(fd: int, limit: float) -> Start:
    stop = time.monotonic() + limit
    buffer, copied = b"", 0
    while True:
        left = stop - time.monotonic()
        if left <= 0:
            _copy(buffer, COPY_LIMIT - copied)
            return Start("gave_up")
        if not select.select([fd], [], [], min(left, SLICE_SECONDS))[0]:
            continue
        data = os.read(fd, 65536)
        if not data:
            _copy(buffer, COPY_LIMIT - copied)
            return Start("ended")
        buffer += data
        while b"\n" in buffer:
            raw, buffer = buffer.split(b"\n", 1)
            first = _json_object(raw)
            if first is not None:
                return _decide(first, buffer)
            copied += _copy(raw, COPY_LIMIT - copied)
        if len(buffer) > 65536:  # a flood without a newline: what fits is copied, the rest is dropped
            copied += _copy(buffer, COPY_LIMIT - copied)
            buffer = b""


def _stream(proc: subprocess.Popen[bytes], fd: int, rest: bytes) -> RenderState:
    """Render kiro's output until its end, or until 2 s after kiro exited (a background child may hold the pipe open); what it learned."""
    state, buffer, exited_at = RenderState(), rest, None
    while True:
        while b"\n" in buffer:
            raw, buffer = buffer.split(b"\n", 1)
            for text in render_line(state, raw.decode("utf-8", errors="replace")):
                emit(text)
        if exited_at is None and proc.poll() is not None:
            exited_at = time.monotonic()
        if exited_at is not None and time.monotonic() - exited_at >= DRAIN_SECONDS:
            break
        if select.select([fd], [], [], SLICE_SECONDS)[0]:
            data = os.read(fd, 65536)
            if not data:
                break
            buffer += data
    if buffer:
        for text in render_line(state, buffer.decode("utf-8", errors="replace")):
            emit(text)
    for text in finish(state):
        emit(text)
    return state


def _exit_code(proc: subprocess.Popen[bytes]) -> int:
    code = proc.wait()
    return 128 - code if code < 0 else code  # killed by signal s: 128 + s


def _end_run(proc: subprocess.Popen[bytes]) -> int:
    """End the run after its ``# kiro:`` line: the whole process group when this launcher leads it, else the child alone."""
    if os.getpgrp() == os.getpid():
        try:
            os.killpg(os.getpgrp(), signal.SIGKILL)  # kiro, its MCP server and this launcher end together (exit -9)
        except OSError:
            pass
    proc.kill()
    proc.wait()
    return 1


def _supervise(proc: subprocess.Popen[bytes], limit: float) -> int:
    assert proc.stdout is not None
    fd = proc.stdout.fileno()
    start = _wait_for_start(fd, limit)
    if start.outcome == "refused":
        emit(f"# kiro: refused: {start.text}")
        return _end_run(proc)
    if start.outcome == "gave_up":
        emit(
            f'# kiro: gave up after {limit:g}s: kiro-cli did not start the run (no "runStarted" event); without KIRO_API_KEY '
            'it may be waiting for a browser sign-in (see README, "Kiro integration")'
        )
        return _end_run(proc)
    if start.outcome == "ended":
        code = _exit_code(proc)
        emit(f"# kiro: kiro-cli exited with code {code} before the run started")
        return 1 if code in (0, THROTTLE_EXIT) else code  # 75 is the launcher's verdict alone
    emit("# kiro: run started (engine v3)")
    state = _stream(proc, fd, start.rest)
    proc.stdout.close()
    code = _exit_code(proc)
    if code != 0 and state.throttled and state.effects == 0:
        return THROTTLE_EXIT
    return 1 if code == THROTTLE_EXIT else code


def _parse(argv: list[str]) -> tuple[float, list[str]] | None:
    if len(argv) < 4 or argv[0] != "--start-deadline" or argv[2] != "--":
        return None
    try:
        limit = float(argv[1])
    except ValueError:
        return None
    return (limit, argv[3:]) if 0 < limit < float("inf") else None


def main(argv: list[str]) -> int:
    parsed = _parse(argv)
    if parsed is None:
        sys.stderr.write(USAGE + "\n")
        return 2
    limit, kiro = parsed
    try:
        proc = subprocess.Popen(kiro, stdout=subprocess.PIPE)  # stdin (the prompt) and stderr (the run log) are inherited; same process group
    except OSError as error:
        emit(f"# kiro: cannot start {kiro[0]}: {error}")
        return 127
    try:
        return _supervise(proc, limit)
    except Exception as error:  # the launcher must never leave kiro running
        emit(f"# kiro: launcher error: {type(error).__name__}: {error}")
        return _end_run(proc)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
