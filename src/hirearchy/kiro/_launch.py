"""The run launcher: starts kiro-cli, checks that it runs the V3 engine, and writes a short transcript of its stream-json output.

Run as a script (``python -I -S _launch.py --start-deadline N -- KIRO_ARGV...``, docs/design/kiro-runtime-v3.md 5.1 and 5.2), so it
imports only the standard library and nothing of ``hirearchy``. Its state is plain data driven by module functions.
"""

from __future__ import annotations

import json
import os
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


# ------------------------------------------------------------------------------------------------------------ the renderer


@dataclass
class RenderState:
    partial: str = ""  # an agent line that is not finished yet
    titles: dict[str, str] = field(default_factory=dict)  # toolCallId -> title
    targets: dict[str, str] = field(default_factory=dict)  # toolCallId -> path or input


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


def _session_update(state: RenderState, update: dict[str, object]) -> list[str]:
    kind = _text(update.get("sessionUpdate"))
    identifier = _text(update.get("toolCallId"))
    if kind == "tool_call":
        title, target = _text(update.get("title")), _target(update)
        state.titles[identifier], state.targets[identifier] = title, target
        return [_mark("[tool]", title, target)]
    if kind == "tool_call_update":
        status = update.get("status")
        if status not in ("completed", "failed"):
            return []
        title = _text(update.get("title")) or state.titles.get(identifier, "")
        target = _target(update) or state.targets.get(identifier, "")
        if status == "completed":
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
        message = _text(body.get("message")).replace("\r", "").replace("\n", " ")[:CUT_ERROR]
        lines = ["[run error] " + ": ".join(part for part in (_text(body.get("stage")), message) if part)]
    else:
        lines = []
    return _flush(state) + lines if lines else []


def finish(state: RenderState) -> list[str]:
    """What is still waiting at the end of the output."""
    return _flush(state)


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


def _stream(proc: subprocess.Popen[bytes], fd: int, rest: bytes) -> None:
    """Render kiro's output until its end, or until 2 s after kiro exited (a background child may hold the pipe open)."""
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
        return code or 1
    emit("# kiro: run started (engine v3)")
    _stream(proc, fd, start.rest)
    proc.stdout.close()
    return _exit_code(proc)


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
