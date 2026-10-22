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


def test_a_v3_start_gives_the_transcript_and_exit_0(tmp_path: Path, session: bool) -> None:
    code, out, _ = launch(tmp_path, START + hello("Hello") + FINISHED, session=session)
    assert code == 0
    assert out == ["# kiro: run started (engine v3)", "Hello", "[run finished] success (end_turn)"]


def test_exit_3_passes_through(tmp_path: Path, session: bool) -> None:
    code, out, _ = launch(tmp_path, START + "exit 3\n", session=session)
    assert code == 3 and out == ["# kiro: run started (engine v3)"]


def test_silence_gives_up_and_kills_the_run(tmp_path: Path, session: bool) -> None:
    code, out, _ = launch(tmp_path, "echo $$ > pid\nexec sleep 30\n", deadline=1, session=session, timeout=20)
    assert code == (-9 if session else 1)
    assert len(out) == 1 and out[0].startswith("# kiro: gave up after 1s: kiro-cli did not start the run")
    assert "KIRO_API_KEY" in out[0] and "browser sign-in" in out[0]
    assert gone(read_pid(tmp_path))


def test_a_spinner_without_a_newline_is_given_up_on_the_same_way(tmp_path: Path, session: bool) -> None:
    code, out, _ = launch(tmp_path, "echo $$ > pid\nprintf '\\r- waiting for sign-in'\nexec sleep 30\n", deadline=1, session=session, timeout=20)
    assert code == (-9 if session else 1)
    assert out[-1].startswith("# kiro: gave up after 1s")
    assert any("waiting for sign-in" in line for line in out[:-1])  # the log shows what kiro printed
    assert gone(read_pid(tmp_path))


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
