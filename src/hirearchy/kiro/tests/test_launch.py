"""The V3 run launcher (docs/design/kiro-runtime-v3.md 5.1, 5.2 and amendment A10): the transcript renderer over recorded and synthetic streams,
and the launcher itself started the way the wiring starts it, over fake kiro scripts."""

from __future__ import annotations

import ast
import json
import os
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from hirearchy.kiro import _launch
from hirearchy.kiro._launch import RenderState, finish, render_line

from ._support import GOLDEN

STREAMS = GOLDEN / "kiro-streams"
LAUNCHER = Path(_launch.__file__).resolve()
CLOSING_MARKS = ("# exit", "# killed", "# failed to start", "# interrupted")  # the closing marks of runs/_format.py


# ----------------------------------------------------------------------------------------------------------- the renderer


def render(lines: list[str]) -> list[str]:
    state, out = RenderState(), []
    for line in lines:
        out += render_line(state, line)
    return out + finish(state)


def event(kind: str, **update: object) -> str:
    return json.dumps({"type": "sessionUpdate", "data": {"sessionId": "s", "update": {"sessionUpdate": kind, **update}}})


def chunk(text: str) -> str:
    return event("agent_message_chunk", content={"type": "text", "text": text})


def call(identifier: str, title: str, path: str | None = None, raw: object = None) -> str:
    extra: dict[str, object] = {}
    if path is not None:
        extra["locations"] = [{"path": path}]
    if raw is not None:
        extra["rawInput"] = raw
    return event("tool_call", toolCallId=identifier, title=title, **extra)


def stream(name: str) -> list[str]:
    return (STREAMS / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()


def test_the_recorded_run_with_denials_renders_tools_and_denials() -> None:
    out = render(stream("ws4a"))
    assert "[tool] Read File /tmp/kirov3-spike/ws-cfg/ws-canary.txt" in out
    assert "[tool ok] Read File /tmp/kirov3-spike/ws-cfg/ws-canary.txt" in out
    assert (
        "[tool failed] Read File /tmp/kirov3-spike/outside/out-canary.txt: Tool call denied by user's permissions. "
        'Rule: deny fs_read matching "/**" Source: agent-profile.'
    ) in out
    assert out[-1] == "[run finished] success (end_turn)"


def test_a_recorded_failed_write_that_carries_only_a_diff_is_the_bare_line() -> None:
    out = render(stream("ws4a"))
    assert "[tool failed] Write File /tmp/kirov3-spike/outside/w-bad.txt" in out


def test_a_recorded_failed_append_without_content_is_the_bare_line() -> None:
    out = render(stream("ws4a"))
    assert [line for line in out if line.startswith("[tool failed] Append to File")] == [
        '[tool failed] Append to File {"path":"/tmp/kirov3-spike/outside/out-canary.txt","text":"A"}'
    ]


def test_no_tool_result_reaches_the_transcript() -> None:
    out = render(stream("ws4a"))
    assert not [line for line in out if "<file name=" in line]
    assert all(len(line) <= 2000 for line in out)


def test_the_recorded_auth_error_is_a_run_error_line() -> None:
    (error,) = [line for line in render(stream("k5b")) if line.startswith("[run error]")]
    assert error.startswith("[run error] prompt: Access denied. Please check your authentication.") and len(error) <= len("[run error] prompt: ") + 500


def test_the_recorded_mcp_failure_is_a_run_error_line() -> None:
    assert render(stream("p15b"))[-1] == "[run error] init: these servers failed to start: hirearchy: Connection closed (--require-mcp-startup enabled)"


def test_the_recorded_streams_hold_no_secret() -> None:
    key = os.environ.get("KIRO_API_KEY", "")
    for name in ("ws4a", "k5b", "p15b"):
        text = (STREAMS / f"{name}.jsonl").read_text(encoding="utf-8")
        assert "ksk_" not in text and "KIRO_API_KEY" not in text and "sk-" not in text
        assert not key or key not in text


def test_chunks_are_merged_and_written_per_completed_line() -> None:
    state = RenderState()
    assert render_line(state, chunk("Hel")) == []
    assert render_line(state, chunk("lo\nWor")) == ["Hello"]
    assert render_line(state, chunk("ld\n\nEnd")) == ["World", ""]
    assert finish(state) == ["End"] and finish(state) == []


def test_a_partial_line_is_flushed_before_any_other_line() -> None:
    assert render([chunk("thinking"), call("a", "Read File", "/x")]) == ["thinking", "[tool] Read File /x"]


def test_a_partial_line_is_flushed_before_a_non_json_line() -> None:
    assert render([chunk("half"), "plain text"]) == ["half", "plain text"]


def test_an_update_without_a_title_uses_the_title_of_its_call() -> None:
    out = render([
        call("a", "Read File", "/x"),
        event("tool_call_update", toolCallId="a", status="in_progress"),
        event("tool_call_update", toolCallId="a", status="completed", content=[{"type": "content", "content": {"type": "text", "text": "SECRET RESULT"}}]),
    ])
    assert out == ["[tool] Read File /x", "[tool ok] Read File /x"]


def test_a_tool_without_a_path_shows_its_input_as_compact_json() -> None:
    assert render([call("a", "Run", raw={"command": "ls -la", "n": 1})]) == ['[tool] Run {"command":"ls -la","n":1}']


def test_the_input_is_cut_at_200_characters() -> None:
    (line,) = render([call("a", "Run", raw={"command": "x" * 500})])
    assert line.startswith("[tool] Run ") and len(line) == len("[tool] Run ") + 200


def test_pending_and_in_progress_updates_and_other_kinds_write_nothing() -> None:
    assert render([
        event("tool_call_update", toolCallId="a", status="pending"),
        event("tool_call_update", toolCallId="a", status="in_progress"),
        event("available_commands_update", availableCommands=[]),
        event("session_info_update"),
        event("config_option_update", configOptions=[]),
        event("something_new", x=1),
        json.dumps({"type": "runStarted", "data": {"engine": "v3"}}),
        json.dumps({"type": "somethingNew"}),
    ]) == []


def denied(text: str) -> str:
    return f"Tool call denied by user's permissions. Rule: deny fs_read matching \"/**\" Source: agent-profile.{text}"


def failed(**fields: object) -> str:
    return event("tool_call_update", toolCallId="a", status="failed", title="Read File", locations=[{"path": "/x"}], **fields)


def test_a_denial_in_a_content_list_is_shown() -> None:
    line = failed(content=[{"type": "content", "content": {"type": "text", "text": denied("")}}])
    assert render([line]) == [f"[tool failed] Read File /x: {denied('')}"]


def test_the_first_list_item_with_text_is_taken() -> None:
    line = failed(content=[{"type": "diff", "path": "", "newText": "w"}, {"type": "content", "content": {"type": "text", "text": denied("")}}])
    assert render([line]) == [f"[tool failed] Read File /x: {denied('')}"]


def test_a_denial_in_a_message_object_is_shown() -> None:
    assert render([failed(content={"message": denied("")})]) == [f"[tool failed] Read File /x: {denied('')}"]


def test_a_denial_is_on_one_line_and_cut_at_300_characters() -> None:
    (line,) = render([failed(content={"message": denied("\n" + "y" * 500)})])
    assert "\n" not in line and line == f"[tool failed] Read File /x: {denied(chr(10) + 'y' * 500).replace(chr(10), ' ')[:300]}"


def test_a_failed_tool_with_a_diff_item_is_the_bare_line() -> None:
    assert render([failed(content=[{"type": "diff", "path": "/x", "oldText": "", "newText": "w"}])]) == ["[tool failed] Read File /x"]


def test_a_failed_shell_command_never_copies_its_output() -> None:
    line = event("tool_call_update", toolCallId="a", status="failed", title="Run", content=[{"type": "content", "content": {"type": "text", "text": "ls: cannot access\nsecret"}}])
    assert render([line]) == ["[tool failed] Run"]


def test_a_failed_tool_without_content_is_the_bare_line() -> None:
    assert render([failed()]) == ["[tool failed] Read File /x"]


def test_the_run_end_lines() -> None:
    finished = json.dumps({"type": "runFinished", "data": {"status": "success", "stopReason": "end_turn", "finalText": "long"}})
    error = json.dumps({"type": "runError", "data": {"stage": "init", "message": "m" * 800}})
    assert render([finished, error]) == ["[run finished] success (end_turn)", "[run error] init: " + "m" * 500]


def test_a_line_that_is_not_a_json_object_is_copied_and_cut_at_2000() -> None:
    assert render(["hello", "[1, 2]", "5", "x" * 3000]) == ["hello", "[1, 2]", "5", "x" * 2000]


def test_blank_lines_are_not_copied() -> None:
    assert render(["", "   "]) == []


@pytest.mark.parametrize(
    "line",
    [
        json.dumps({"type": "sessionUpdate"}),
        json.dumps({"type": "sessionUpdate", "data": "x"}),
        json.dumps({"type": "sessionUpdate", "data": {"update": []}}),
        json.dumps({"type": "sessionUpdate", "data": {"update": {"sessionUpdate": 5}}}),
        json.dumps({"type": "sessionUpdate", "data": {"update": {"sessionUpdate": "agent_message_chunk", "content": "text"}}}),
        json.dumps({"type": "sessionUpdate", "data": {"update": {"sessionUpdate": "agent_message_chunk", "content": {"text": 5}}}}),
        json.dumps({"type": "sessionUpdate", "data": {"update": {"sessionUpdate": "tool_call_update", "status": "failed", "content": 7}}}),
        json.dumps({"type": "sessionUpdate", "data": {"update": {"sessionUpdate": "tool_call", "title": 3, "locations": "x", "rawInput": 4}}}),
        json.dumps({"type": "runFinished"}),
        json.dumps({"type": "runError", "data": 3}),
        json.dumps({"data": {}}),
        json.dumps({"type": ["x"]}),
    ],
)
def test_a_missing_or_mistyped_field_never_raises(line: str) -> None:
    out = render([line])
    assert all(isinstance(text, str) for text in out)


def test_a_call_with_nothing_is_just_the_mark() -> None:
    assert render([json.dumps({"type": "sessionUpdate", "data": {"update": {"sessionUpdate": "tool_call"}}})]) == ["[tool]"]


# ------------------------------------------------------------------------------------------- the launcher as a script


def test_the_launcher_imports_only_the_standard_library() -> None:
    tree = ast.parse(LAUNCHER.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "a relative import cannot work when the file runs as a script"
            modules.append(node.module or "")
    assert modules and all(m.split(".")[0] in sys.stdlib_module_names for m in modules), modules
    assert not [m for m in modules if m.split(".")[0] == "hirearchy"]


def fake(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "fake-kiro"
    script.write_text('#!/bin/sh\ncd "$(dirname "$0")"\n' + body, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


START = """printf '%s\\n' '{"type":"runStarted","data":{"payloadSchema":"acp","engine":"v3"}}'\n"""
FINISHED = """printf '%s\\n' '{"type":"runFinished","data":{"status":"success","stopReason":"end_turn"}}'\n"""


def hello(text: str) -> str:
    return "printf '%s\\n' '" + chunk(text) + "'\n"


def launch(
    tmp_path: Path, body: str, deadline: float = 30, session: bool = True, stdin: bytes = b"", timeout: float = 30
) -> tuple[int, list[str], str]:
    """(exit code, the launcher's stdout lines, stderr) of the launcher started as the wiring starts it."""
    script = fake(tmp_path, body)
    argv = [sys.executable, "-I", "-S", str(LAUNCHER), "--start-deadline", f"{deadline:g}", "--", str(script)]
    done = subprocess.run(argv, input=stdin, capture_output=True, start_new_session=session, timeout=timeout)
    return done.returncode, done.stdout.decode().splitlines(), done.stderr.decode()


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def gone(pid: int) -> bool:
    for _ in range(40):
        if not alive(pid):
            return True
        time.sleep(0.1)
    return False


def read_pid(tmp_path: Path) -> int:
    for _ in range(40):
        text = (tmp_path / "pid").read_text(encoding="utf-8") if (tmp_path / "pid").exists() else ""
        if text.strip():
            return int(text)
        time.sleep(0.05)
    raise AssertionError("the fake kiro did not write its pid")


@pytest.fixture(params=[True, False], ids=["group-leader", "not-leader"])
def session(request: pytest.FixtureRequest) -> bool:
    return bool(request.param)


WRAPPER = "import subprocess, sys; sys.exit(subprocess.call(sys.argv[1:]))"  # leads the group, so the launcher does not


def launch_in_group(
    tmp_path: Path, body: str, deadline: float, leader: bool, timeout: float = 20
) -> tuple[int, list[str], str, int]:
    """(exit code, the launcher's stdout lines, its stderr text, the process group of the run): the launcher in a session of its own, as its
    group's leader (as the scheduler starts it) or, with ``leader`` False, as the only child of a wrapper that leads the group."""
    argv = [sys.executable, "-I", "-S", str(LAUNCHER), "--start-deadline", f"{deadline:g}", "--", str(fake(tmp_path, body))]
    if not leader:
        argv = [sys.executable, "-I", "-S", "-c", WRAPPER, *argv]
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise
    return proc.returncode, out.decode().splitlines(), err.decode(), proc.pid


def group_gone(group: int, within: float = 20.0) -> bool:
    """No process is left in ``group`` (polled every 50 ms, at most ``within`` seconds)."""
    end = time.monotonic() + within
    while time.monotonic() < end:
        try:
            os.killpg(group, 0)
        except ProcessLookupError:
            return True
        except PermissionError:  # the id now names another user's group: ours has ended
            return True
        time.sleep(0.05)
    return False


def test_a_v3_start_gives_the_transcript_and_exit_0(tmp_path: Path, session: bool) -> None:
    code, out, _ = launch(tmp_path, START + hello("Hello") + FINISHED, session=session)
    assert code == 0
    assert out == ["# kiro: run started (engine v3)", "Hello", "[run finished] success (end_turn)"]


def test_exit_3_passes_through(tmp_path: Path, session: bool) -> None:
    code, out, _ = launch(tmp_path, START + "exit 3\n", session=session)
    assert code == 3 and out == ["# kiro: run started (engine v3)"]


def test_silence_gives_up_and_kills_the_run(tmp_path: Path, session: bool) -> None:
    code, out, _, group = launch_in_group(tmp_path, "exec sleep 30\n", deadline=1, leader=session)
    assert code == (-9 if session else 1)
    assert len(out) == 1 and out[0].startswith("# kiro: gave up after 1s: kiro-cli did not start the run")
    assert "KIRO_API_KEY" in out[0] and "browser sign-in" in out[0]
    assert group_gone(group)


def test_a_kiro_killed_before_its_first_line_leaves_no_process(tmp_path: Path) -> None:
    code, out, _, group = launch_in_group(tmp_path, "sleep 15\necho $$ > pid\nexec sleep 30\n", deadline=1, leader=True)
    assert code == -9
    assert not (tmp_path / "pid").exists()  # the kill came before the shell got to its second line
    assert group_gone(group)


def test_a_spinner_without_a_newline_is_given_up_on_the_same_way(tmp_path: Path, session: bool) -> None:
    code, out, _, group = launch_in_group(tmp_path, "printf '\\r- waiting for sign-in'\nexec sleep 30\n", deadline=1, leader=session)
    assert code == (-9 if session else 1)
    assert out[-1].startswith("# kiro: gave up after 1s")
    assert any("waiting for sign-in" in line for line in out[:-1])  # the log shows what kiro printed
    assert group_gone(group)


def test_the_text_copied_before_the_start_is_limited_to_4_kb(tmp_path: Path) -> None:
    body = "yes 'noise noise noise noise noise noise' | head -c 100000\necho\n" + START + FINISHED
    code, out, _ = launch(tmp_path, body)
    assert code == 0 and sum(len(line) + 1 for line in out) < 4096 + 200


def test_engine_v2_is_refused(tmp_path: Path, session: bool) -> None:
    body = "echo $$ > pid\nprintf '%s\\n' '{\"type\":\"runStarted\",\"data\":{\"engine\":\"v2\"}}'\nexec sleep 30\n"
    code, out, _ = launch(tmp_path, body, session=session, timeout=20)
    assert code == (-9 if session else 1)
    assert out == ['# kiro: refused: kiro-cli started engine "v2"; hirearchy needs "v3"']
    assert gone(read_pid(tmp_path))


def test_a_first_event_that_is_not_run_started_is_refused(tmp_path: Path, session: bool) -> None:
    body = "echo $$ > pid\nprintf '%s\\n' '{\"type\":\"sessionUpdate\",\"data\":{}}'\nexec sleep 30\n"
    code, out, _ = launch(tmp_path, body, session=session, timeout=20)
    assert code == (-9 if session else 1)
    assert out == ['# kiro: refused: the first event of kiro-cli was "sessionUpdate", not "runStarted"']
    assert gone(read_pid(tmp_path))


def test_an_end_before_the_start_with_exit_0_is_exit_1(tmp_path: Path, session: bool) -> None:
    code, out, _ = launch(tmp_path, "echo not json\nexit 0\n", session=session)
    assert code == 1
    assert out == ["not json", "# kiro: kiro-cli exited with code 0 before the run started"]


def test_an_end_before_the_start_keeps_a_non_zero_exit(tmp_path: Path, session: bool) -> None:
    code, out, _ = launch(tmp_path, "exit 4\n", session=session)
    assert code == 4 and out == ["# kiro: kiro-cli exited with code 4 before the run started"]


def test_a_kiro_killed_by_sigterm_gives_143(tmp_path: Path, session: bool) -> None:
    code, out, _ = launch(tmp_path, START + "kill -TERM $$\nsleep 5\n", session=session)
    assert code == 128 + signal.SIGTERM and out[0] == "# kiro: run started (engine v3)"


def test_a_kiro_that_cannot_start_gives_127(tmp_path: Path, session: bool) -> None:
    argv = [sys.executable, "-I", "-S", str(LAUNCHER), "--start-deadline", "5", "--", str(tmp_path / "missing")]
    done = subprocess.run(argv, capture_output=True, start_new_session=session, timeout=20)
    assert done.returncode == 127 and done.stdout.decode().startswith(f"# kiro: cannot start {tmp_path / 'missing'}: ")


@pytest.mark.parametrize("args", [[], ["--start-deadline", "x", "--", "true"], ["--start-deadline", "0", "--", "true"],
                                  ["--start-deadline", "5"], ["--start-deadline", "5", "--"], ["--", "true"]])
def test_bad_arguments_are_a_usage_error(args: list[str]) -> None:
    done = subprocess.run([sys.executable, "-I", "-S", str(LAUNCHER), *args], capture_output=True, timeout=20)
    assert done.returncode == 2 and done.stdout == b"" and b"usage" in done.stderr.lower()


def test_stdin_reaches_kiro(tmp_path: Path, session: bool) -> None:
    code, out, _ = launch(tmp_path, START + 'echo "stdin:$(cat | wc -c | tr -d \' \')"\n', stdin=b"hello prompt", session=session)
    assert code == 0 and out[-1] == "stdin:12"


def test_each_launcher_line_comes_before_the_next_line_of_kiros_stderr(tmp_path: Path) -> None:
    script = fake(tmp_path, START + "sleep 0.5\necho E1 >&2\n" + hello("Hello\n") + "sleep 0.5\necho E2 >&2\n" + FINISHED)
    log = tmp_path / "run.log"
    argv = [sys.executable, "-I", "-S", str(LAUNCHER), "--start-deadline", "30", "--", str(script)]
    with log.open("wb") as handle:
        done = subprocess.run(argv, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True, timeout=30)
    assert done.returncode == 0
    assert log.read_text(encoding="utf-8").splitlines() == [
        "# kiro: run started (engine v3)", "E1", "Hello", "E2", "[run finished] success (end_turn)",
    ]


def test_no_launcher_line_starts_with_a_closing_mark_of_the_run_log(tmp_path: Path) -> None:
    outputs: Iterator[list[str]] = iter([
        launch(tmp_path, START + FINISHED)[1],
        launch(tmp_path, "exit 4\n")[1],
        launch(tmp_path, "echo $$ > pid\nexec sleep 30\n", deadline=1, timeout=20)[1],
        launch(tmp_path, "printf '%s\\n' '{\"type\":\"runStarted\",\"data\":{\"engine\":\"v2\"}}'\nexec sleep 30\n", timeout=20)[1],
    ])
    for lines in outputs:
        assert lines and not [line for line in lines if line.startswith(CLOSING_MARKS)]


def test_a_background_child_holding_stdout_does_not_hold_the_run(tmp_path: Path) -> None:
    body = START + "sleep 30 2>/dev/null &\necho $! > pid\nexit 0\n"
    started = time.monotonic()
    try:
        code, out, _ = launch(tmp_path, body, timeout=20)
        assert code == 0 and out[0] == "# kiro: run started (engine v3)"
        assert time.monotonic() - started < 5
    finally:
        if (tmp_path / "pid").exists() and (tmp_path / "pid").read_text(encoding="utf-8").strip():
            try:
                os.kill(int((tmp_path / "pid").read_text(encoding="utf-8")), signal.SIGKILL)
            except ProcessLookupError:
                pass


# ------------------------------------------------------------------------- a throttled run (design 9.1, DR-44)

THROTTLE_STREAM = "f-e4-8-throttle"
NO_EFFECT_MARK = "# kiro: throttled by the model service (retryErrorType THROTTLING); tool effects: none"
THROTTLING_ERROR = json.dumps({"type": "runError", "data": {"stage": "prompt", "message": 'high traffic (code -32000): {"errorType":"ModelThrottleError","retryErrorType":"THROTTLING"}'}})
START_EVENT = json.dumps({"type": "runStarted", "data": {"engine": "v3"}})


def rendered(lines: list[str]) -> tuple[list[str], RenderState]:
    state, out = RenderState(), []
    for line in lines:
        out += render_line(state, line)
    return out + finish(state), state


def call_of_kind(identifier: str, title: str, tool_kind: str) -> str:
    return json.dumps({"type": "sessionUpdate", "data": {"update": {"sessionUpdate": "tool_call", "toolCallId": identifier, "title": title, "kind": tool_kind}}})


def throttle_stream(write: str = "failed") -> list[str]:
    """The fixture with its ``hirearchy::write`` update given another status."""
    lines = []
    for line in stream(THROTTLE_STREAM):
        data = json.loads(line)
        update = data.get("data", {}).get("update", {})
        if update.get("toolCallId") == "tooluse_write":
            update["status"] = write
        lines.append(json.dumps(data))
    return lines


def run_stream(tmp_path: Path, lines: list[str], code: int, session: bool = True) -> tuple[int, list[str]]:
    """The launcher over a fake kiro that prints ``lines`` and exits with ``code``."""
    (tmp_path / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    done, out, _ = launch(tmp_path, f"cat events.jsonl\nexit {code}\n", session=session)
    return done, out


def with_closing(transcript: list[str], code: int = 75) -> str:
    return "\n".join(transcript) + f"\n\n# exit {code} after 3s\n"


def test_the_s2_throttle_stream_ends_with_the_mark_and_tool_effects_none() -> None:
    """``f-e4-8-throttle.jsonl`` is hand-built in the event order of the s2 run log (studies/E4-org-growth-0a1-recheck/evidence/s2/run-logs/
    lead-reviewer/20261022T202454859379.log, lines 169-179: an update-only Tool Load, org_read, Read File, an update-only failed
    ``hirearchy::write``, then the runError) with the event shapes of ws4a.jsonl."""
    out, state = rendered(stream(THROTTLE_STREAM))
    assert out[0] == '[tool ok] Tool Load {"tool_ids":["hirearchy::*"]}' and out[-2].startswith("[run error] prompt: Claude Sonnet 4.6 is experiencing high traffic.")
    assert out[-1] == _launch.THROTTLE_MARK + "none" == NO_EFFECT_MARK
    assert state.throttled and state.effects == 0


def test_main_returns_throttle_exit_for_a_throttle_without_effect(tmp_path: Path, session: bool) -> None:
    code, out = run_stream(tmp_path, stream(THROTTLE_STREAM), code=1, session=session)
    assert _launch.THROTTLE_EXIT == 75 and code == 75 and out[-1] == NO_EFFECT_MARK


def test_a_completed_write_is_one_effect_and_kiros_code_is_returned(tmp_path: Path) -> None:
    out, state = rendered(throttle_stream("completed"))
    assert state.effects == 1 and out[-1] == _launch.THROTTLE_MARK + "1"
    code, lines = run_stream(tmp_path, throttle_stream("completed"), code=1)
    assert code == 1 and lines[-1].endswith("tool effects: 1")


def test_an_update_only_tool_load_is_no_effect() -> None:
    load = event("tool_call_update", toolCallId="t", status="completed", title="Tool Load", rawInput={"tool_ids": ["hirearchy::*"]})
    _, state = rendered([load, THROTTLING_ERROR])
    assert state.effects == 0 and state.throttled


def test_an_mcp_tool_call_without_kind_for_write_is_an_effect() -> None:
    lines = [call("w", "@hirearchy/write", raw={"tool_id": "hirearchy::write"}), event("tool_call_update", toolCallId="w", status="completed"), THROTTLING_ERROR]
    out, state = rendered(lines)
    assert state.effects == 1 and out[-1].endswith("tool effects: 1")
    read = [call("r", "@hirearchy/org_read", raw={"tool_id": "hirearchy::org_read"}), event("tool_call_update", toolCallId="r", status="completed"), THROTTLING_ERROR]
    assert rendered(read)[1].effects == 0


def test_a_completed_update_without_facts_is_an_effect() -> None:
    _, state = rendered([event("tool_call_update", toolCallId="x", status="completed"), THROTTLING_ERROR])
    assert state.effects == 1


def test_an_unknown_kind_is_an_effect() -> None:
    lines = [call_of_kind("a", "Odd", "teleport"), event("tool_call_update", toolCallId="a", status="completed"), THROTTLING_ERROR]
    assert rendered(lines)[1].effects == 1
    for kind in ("read", "search", "think", "fetch"):
        known = [call_of_kind("a", "T", kind), event("tool_call_update", toolCallId="a", status="completed")]
        assert rendered(known)[1].effects == 0, kind
    assert rendered([call_of_kind("a", "W", "edit"), event("tool_call_update", toolCallId="a", status="completed")])[1].effects == 1


def test_a_run_error_without_throttling_writes_no_mark(tmp_path: Path) -> None:
    error = json.dumps({"type": "runError", "data": {"stage": "prompt", "message": "boom (code -32000)"}})
    out, state = rendered([error])
    assert not state.throttled and out == ["[run error] prompt: boom (code -32000)"]
    code, lines = run_stream(tmp_path, [START_EVENT, error], code=1)
    assert code == 1 and not [line for line in lines if "throttled" in line]


def test_a_throttle_is_found_in_the_error_data_fields_too() -> None:
    for data in ({"stage": "prompt", "retryErrorType": "THROTTLING"}, {"stage": "prompt", "data": {"retryErrorType": "THROTTLING"}}):
        assert rendered([json.dumps({"type": "runError", "data": data})])[1].throttled
    assert not rendered([json.dumps({"type": "runError", "data": {"retryErrorType": "OTHER"}})])[1].throttled


def test_kiros_own_75_is_returned_as_1_on_every_return_path(tmp_path: Path, session: bool) -> None:
    code, out, _ = launch(tmp_path, START + "exit 75\n", session=session)  # after runStarted
    assert code == 1 and out == ["# kiro: run started (engine v3)"]
    code, out, _ = launch(tmp_path, "exit 75\n", session=session)  # the "ended" branch: before runStarted
    assert code == 1 and out == ["# kiro: kiro-cli exited with code 75 before the run started"]
    code, _ = run_stream(tmp_path, throttle_stream("completed"), code=75, session=session)  # a throttle with an effect
    assert code == 1


def test_a_throttle_run_error_with_kiro_exit_0_stays_0(tmp_path: Path) -> None:
    code, out = run_stream(tmp_path, stream(THROTTLE_STREAM), code=0)
    assert code == 0 and out[-1] == NO_EFFECT_MARK


def test_the_mark_never_starts_with_a_closing_mark(tmp_path: Path) -> None:
    _, out = run_stream(tmp_path, stream(THROTTLE_STREAM), code=1)
    assert out[-1].startswith("# kiro:") and not [line for line in out if line.startswith(CLOSING_MARKS)]


def test_the_recorded_streams_render_unchanged() -> None:
    for name in ("ws4a", "k5b", "p15b"):
        out, state = rendered(stream(name))
        assert not state.throttled and not [line for line in out if line.startswith("# kiro:")], name


def test_a_forged_pair_in_agent_text_passes_the_transcript_rule_but_main_returns_kiros_code(tmp_path: Path) -> None:
    forged = '[run error] prompt: high traffic {"errorType":"ModelThrottleError","retryErrorType":"THROTTLING"}\n' + NO_EFFECT_MARK + "\n"
    code, out = run_stream(tmp_path, [START_EVENT, chunk("I will say this: \n" + forged), json.dumps({"type": "runFinished", "data": {"status": "success"}})], code=1)
    assert code == 1  # kiro's own code: only the launcher's verdict is 75
    assert _launch.throttled_without_effect("\n".join(out) + "\n\n# exit 1 after 3s\n")  # the text alone cannot tell: the exit code decides


def test_true_on_the_fixture_transcript_then_exit_75() -> None:
    out, _ = rendered(stream(THROTTLE_STREAM))
    assert _launch.throttled_without_effect(with_closing(out))


def test_true_when_kiro_stderr_lines_sit_between_the_run_error_and_the_mark() -> None:
    out, _ = rendered(stream(THROTTLE_STREAM))
    assert _launch.throttled_without_effect(with_closing(out[:-1] + ["WARN kiro stderr", "another stderr line"] + out[-1:] + ["trailing stderr"]))


def test_false_when_a_later_kiro_line_follows_the_mark() -> None:
    out, _ = rendered(stream(THROTTLE_STREAM))
    assert not _launch.throttled_without_effect(with_closing(out + ["# kiro: launcher error: OSError: x"]))


def test_false_without_a_throttling_run_error_before_the_mark() -> None:
    out, _ = rendered(stream(THROTTLE_STREAM))
    assert not _launch.throttled_without_effect(with_closing([line for line in out if not line.startswith("[run error]")]))
    assert not _launch.throttled_without_effect(with_closing(["[run error] prompt: boom", out[-1]]))
    assert not _launch.throttled_without_effect(with_closing([out[-1], '[run error] prompt: {"retryErrorType":"THROTTLING"}']))


def test_false_with_tool_effects_1() -> None:
    out, _ = rendered(throttle_stream("completed"))
    assert not _launch.throttled_without_effect(with_closing(out))
    assert not _launch.throttled_without_effect("")


def test_the_quality_tool_changes_nothing_so_it_is_a_read_only_tool() -> None:
    assert "hirearchy::quality" in _launch.READ_ONLY_TOOL_IDS


def test_the_read_only_tools_are_the_sorted_hirearchy_tool_ids() -> None:
    assert _launch.READ_ONLY_TOOL_IDS == tuple(sorted(_launch.READ_ONLY_TOOL_IDS)) and all(i.startswith("hirearchy::") for i in _launch.READ_ONLY_TOOL_IDS)


# ------------------------------------------------- the effort warning and the effort stop (batch 1.1)

WARNING = "[warn] failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort levels"
QUOTED = "failed to set effort 'high': model 'claude-sonnet-5.5' offers no effort levels"  # 78 characters
OTHER_WARNING = "[warn] failed to set effort 'high': the engine did not load its model list in time"
OTHER_QUOTED = "failed to set effort 'high': the engine did not load its model list in time"  # 75 characters


def mark_a(quoted: str, effects: str = "none") -> str:
    """Text A of the design, written out (not built from ``_launch.EFFORT_MARK``) so that the test pins it."""
    return f"# kiro: effort not set, run stopped (kiro-cli: {quoted}); tool effects: {effects}"


def test_the_effort_warning_is_matched_by_its_prefix() -> None:
    assert _launch.EFFORT_PREFIX == "failed to set effort"
    assert _launch.EFFORT_MARK == "# kiro: effort not set, run stopped (kiro-cli: "


@pytest.mark.parametrize(("line", "quoted"), [(WARNING, QUOTED), (OTHER_WARNING, OTHER_QUOTED)], ids=["offers-no-effort-levels", "model-list-not-loaded"])
def test_effort_warning_gives_kiros_line_from_the_prefix_on(line: str, quoted: str) -> None:
    assert _launch.effort_warning(line) == quoted
    assert len(quoted) in (78, 75)


def test_effort_warning_takes_any_reason_with_or_without_a_level_tag() -> None:
    assert _launch.effort_warning("[warn] failed to set effort 'xhigh': something new") == "failed to set effort 'xhigh': something new"
    assert _launch.effort_warning("failed to set effort 'high': x") == "failed to set effort 'high': x"
    assert _launch.effort_warning("[WARN] failed to set effort 'high': x") == "failed to set effort 'high': x"


def test_effort_warning_drops_carriage_returns_and_cuts_at_300() -> None:
    assert _launch.effort_warning(WARNING + "\r") == QUOTED
    assert len(_launch.effort_warning("failed to set effort " + "x" * 400)) == 300


@pytest.mark.parametrize(
    "line", ["note: failed to set effort 'high'", "[warn] failed to set efforts", "[verboselevel] failed to set effort 'high'", ""]
)
def test_effort_warning_is_empty_unless_the_line_starts_with_the_prefix(line: str) -> None:
    assert _launch.effort_warning(line) == ""


@pytest.mark.parametrize(("line", "quoted"), [(WARNING, QUOTED), (OTHER_WARNING, OTHER_QUOTED)], ids=["offers-no-effort-levels", "model-list-not-loaded"])
def test_effort_stop_reads_the_launchers_mark(line: str, quoted: str) -> None:
    tail = f"# kiro: run started (engine v3)\n{line}\n{mark_a(quoted)}\n\n# exit -9 after 3s\n"
    assert _launch.effort_stop(tail) == _launch.EffortStop(quoted, 0)


def test_effort_stop_reads_the_number_of_tool_effects() -> None:
    tail = f"# kiro: run started (engine v3)\n{WARNING}\n{mark_a(QUOTED, '2')}\n\n# exit -9 after 3s\n"
    assert _launch.effort_stop(tail) == _launch.EffortStop(QUOTED, 2)


def test_effort_stop_is_none_unless_the_mark_is_the_last_kiro_line_with_a_warning_before_it() -> None:
    mark = mark_a(QUOTED)
    throttle = '[run error] prompt: {"retryErrorType":"THROTTLING"}\n' + _launch.THROTTLE_MARK + "none\n\n# exit 75 after 3s\n"
    for tail in (
        f"{WARNING}\n{mark}\n# kiro: launcher error: OSError: x\n\n# exit -9 after 3s\n",
        f"# kiro: run started (engine v3)\n{mark}\n\n# exit -9 after 3s\n",
        f"{mark}\n{WARNING}\n\n# exit -9 after 3s\n",
        f"{WARNING}\n{mark_a(QUOTED, 'two')}\n\n# exit -9 after 3s\n",
        f"{WARNING}\n# kiro: effort not set, run stopped (kiro-cli: {QUOTED}; tool effects: none\n\n# exit -9 after 3s\n",
        "",
        throttle,
    ):
        assert _launch.effort_stop(tail) is None, tail


def test_the_kiro_api_exports_the_effort_names() -> None:
    import hirearchy.kiro as kiro

    assert kiro.EFFORT_PREFIX is _launch.EFFORT_PREFIX
    assert kiro.EffortStop is _launch.EffortStop
    assert kiro.effort_stop is _launch.effort_stop
    assert kiro.effort_warning is _launch.effort_warning


# --------------------------------------------- kiro's stderr reaches the run log in full and in order (batch 1.1, condition 2)


def say(line: str) -> str:
    """A line of the fake kiro that prints ``line`` (no single quote in it) to stdout, as ``hello`` does."""
    return "printf '%s\\n' '" + line + "'\n"


def to_stderr(text: str) -> str:
    """A line of the fake kiro that writes ``text`` (no double quote, ``$`` or backquote) to its stderr."""
    return 'printf \'%s\\n\' "' + text + '" >&2\n'


def err_lines(first: int, count: int) -> tuple[str, list[str]]:
    """A shell loop of the fake kiro that writes ``count`` numbered 80-byte lines to its stderr, and the lines it writes."""
    script = f"i={first}\nwhile [ $i -lt {first + count} ]; do printf 'err-%05d-%069d\\n' $i 0 >&2; i=$((i+1)); done\n"
    return script, [f"err-{i:05d}-{0:069d}" for i in range(first, first + count)]


def launch_logged(tmp_path: Path, body: str, timeout: float = 30) -> tuple[int, list[str]]:
    """(exit code, the run log's lines): the launcher as the scheduler starts it, leader of its group, with fd 1 and fd 2 on one log file."""
    log = tmp_path / "run.log"
    argv = [sys.executable, "-I", "-S", str(LAUNCHER), "--start-deadline", "30", "--", str(fake(tmp_path, body))]
    with log.open("wb") as handle:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise
    return code, log.read_text(encoding="utf-8").splitlines()


def only_err(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith("err-")]


def test_more_than_a_pipe_buffer_of_stderr_is_drained_and_logged_in_order(tmp_path: Path) -> None:
    first, written_first = err_lines(1, 2000)
    second, written_second = err_lines(2001, 2000)
    code, log = launch_logged(tmp_path, first + START + second + FINISHED)
    assert code == 0
    assert only_err(log) == written_first + written_second
    assert "# kiro: run started (engine v3)" in log and "[run finished] success (end_turn)" in log


def test_stderr_written_after_kiro_closed_its_stdout_is_logged_and_the_run_completes(tmp_path: Path) -> None:
    first, written_first = err_lines(1, 2000)
    second, written_second = err_lines(2001, 2000)
    third, written_third = err_lines(4001, 2000)
    code, log = launch_logged(tmp_path, first + START + second + FINISHED + "exec 1>&-\n" + third)
    assert code == 0
    assert only_err(log) == written_first + written_second + written_third
    assert "[run finished] success (end_turn)" in log


def test_kiros_stderr_reaches_the_launchers_stderr_byte_for_byte(tmp_path: Path) -> None:
    first, written_first = err_lines(1, 2000)
    second, written_second = err_lines(2001, 2000)
    last = "printf '%s' 'the last line, without a newline' >&2\n"
    code, out, err = launch(tmp_path, first + START + second + FINISHED + last)
    assert code == 0
    assert err == "".join(line + "\n" for line in written_first + written_second) + "the last line, without a newline"
    assert out == ["# kiro: run started (engine v3)", "[run finished] success (end_turn)"]


def test_stderr_before_an_early_end_is_logged_in_full(tmp_path: Path) -> None:
    script, written = err_lines(1, 2000)
    code, log = launch_logged(tmp_path, "exec 1>&-\n" + script + "exit 4\n")
    assert code == 4
    assert only_err(log) == written
    assert log[-1] == "# kiro: kiro-cli exited with code 4 before the run started"


def test_a_background_child_holding_stderr_does_not_hold_the_run(tmp_path: Path) -> None:
    body = START + "sleep 30 >/dev/null &\necho $! > pid\nexit 0\n"
    started = time.monotonic()
    try:
        code, log = launch_logged(tmp_path, body, timeout=20)
        assert code == 0 and log[0] == "# kiro: run started (engine v3)"
        assert time.monotonic() - started < 5
    finally:
        if (tmp_path / "pid").exists() and (tmp_path / "pid").read_text(encoding="utf-8").strip():
            try:
                os.kill(int((tmp_path / "pid").read_text(encoding="utf-8")), signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_kiro_writes_its_stderr_into_a_pipe_of_the_launcher(tmp_path: Path) -> None:
    body = "if [ -p /dev/fd/2 ]; then echo 'stderr: pipe'; else echo 'stderr: file'; fi\n" + START + FINISHED
    code, log = launch_logged(tmp_path, body)
    assert code == 0
    assert log == ["stderr: pipe", "# kiro: run started (engine v3)", "[run finished] success (end_turn)"]


def test_kiros_stderr_keeps_its_place_when_kiro_writes_without_pause(tmp_path: Path) -> None:
    body = START + to_stderr("E1") + hello("Hello\n") + to_stderr("E2") + FINISHED
    for attempt in range(10):
        code, log = launch_logged(tmp_path, body)
        assert code == 0, attempt
        assert log[0] == "# kiro: run started (engine v3)", (attempt, log)
        assert log.index("E1") < log.index("Hello"), (attempt, log)
        assert log.index("E2") < log.index("[run finished] success (end_turn)"), (attempt, log)  # no order between Hello and E2 is asserted
