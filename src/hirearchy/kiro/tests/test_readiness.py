"""``KiroReadiness``: the checks before a scheduler starts or a profile is written (docs/design/kiro-runtime-v3.md 9 and amendment A1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from hirearchy.access.testing import StaticAccess
from hirearchy.kernel import OrgPaths
from hirearchy.kernel.testing import DictEnvironment
from hirearchy.kiro import READINESS_TIMEOUT, START_DEADLINE, CliResult
from hirearchy.kiro._readiness import KiroReadiness
from hirearchy.kiro.testing import FixedKiroPlaces, MemoryKiroState, ScriptedKiroCli

BIN = "kiro-cli"
VERSION = (BIN, "--version")
HELP = (BIN, "chat", "--help")
WHOAMI = (BIN, "whoami")
FLAGS = "Usage: kiro-cli chat [OPTIONS]\n  --v3  --require-mcp-startup\n  --output-format <FORMAT>\n"
READY: dict[tuple[str, ...], CliResult | None] = {VERSION: CliResult(0, "kiro-cli 2.33.0\n"), HELP: CliResult(0, FLAGS), WHOAMI: CliResult(0, "Logged in\n")}
NOT_ANSWERED = "did not answer within 2.5 s or could not be started (a first start after an update can be slow: try again)"


class FailingState(MemoryKiroState):
    def private_dir(self, path: Path) -> None:
        raise OSError("disk full")


@dataclass
class World:
    readiness: KiroReadiness
    cli: ScriptedKiroCli
    state: MemoryKiroState
    access: StaticAccess
    places: FixedKiroPlaces
    environment: DictEnvironment


def world(
    tmp_path: Path, answers: dict[tuple[str, ...], CliResult | None] | None = None, variables: dict[str, str] | None = None,
    state: MemoryKiroState | None = None, problem: str | None = None,
) -> World:
    access = StaticAccess(tmp_path / "org")
    places = FixedKiroPlaces(tmp_path / "state", problem)
    cli = ScriptedKiroCli(READY if answers is None else answers)
    environment = DictEnvironment({"PATH": "/usr/bin", **(variables or {})}, home=tmp_path / "user")
    kiro_state = MemoryKiroState() if state is None else state
    readiness = KiroReadiness(OrgPaths(access.root), access.agents, access, places, kiro_state, kiro_state, cli, environment)
    return World(readiness, cli, kiro_state, access, places, environment)


def test_the_budget_constants_are_the_designed_ones() -> None:
    assert READINESS_TIMEOUT == 2.5 and START_DEADLINE == 60.0


def test_a_ready_world_has_no_problem(tmp_path: Path) -> None:
    w = world(tmp_path)
    assert w.readiness.state_problem() is None and w.readiness.check(BIN) is None


def test_the_home_is_made_private_when_it_is_checked(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.readiness.state_problem()
    assert w.state.private == [w.places.home()]


def test_state_problem_makes_no_cli_call(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.readiness.state_problem()
    assert w.cli.calls == []


def test_a_places_problem_comes_first_and_nothing_is_made(tmp_path: Path) -> None:
    w = world(tmp_path, problem="the places are bad")
    assert w.readiness.state_problem() == "the places are bad" and w.readiness.check(BIN) == "the places are bad"
    assert w.state.private == [] and w.cli.calls == []


def test_a_workspace_inside_the_kiro_state_is_a_problem_before_anything_is_made(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.access.put_agent("dev", {"role": "R", "tools": ["write"], "workspace": str(w.places.roots()[1] / "mine")})
    problem = w.readiness.state_problem()
    assert problem is not None and "workspace of dev" in problem and "is inside hirearchy's kiro state" in problem
    assert w.state.private == [] and w.cli.calls == []


def test_an_input_of_any_agent_is_checked(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.access.put_agent("a", {"role": "R"})
    w.access.put_agent("a/b", {"role": "R", "tools": ["read"], "inputs": [str(w.places.roots()[0] / "other-org")]})
    problem = w.readiness.state_problem()
    assert problem is not None and "input of a/b" in problem


def test_the_organization_itself_is_checked(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.places = FixedKiroPlaces(tmp_path / "org" / "state")  # kiro state inside the organization
    w.readiness = KiroReadiness(OrgPaths(w.access.root), w.access.agents, w.access, w.places, w.state, w.state, w.cli, w.environment)
    problem = w.readiness.state_problem()
    assert problem is not None and "organization" in problem


def test_an_oserror_while_preparing_the_home_is_a_problem_not_an_exception(tmp_path: Path) -> None:
    w = world(tmp_path, state=FailingState())
    home = w.places.home()
    assert w.readiness.state_problem() == f"cannot prepare the kiro home {home}: disk full"
    assert w.readiness.check(BIN) == f"cannot prepare the kiro home {home}: disk full" and w.cli.calls == []


def test_a_planted_entry_is_named(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.state.plant(w.places.home(), "skills")
    w.state.plant(w.places.home(), "settings/mcp.json")
    assert w.readiness.state_problem() == (
        f"the kiro home {w.places.home()} holds configuration kiro-cli would load into every agent: settings/mcp.json, skills; "
        "remove it (this home belongs to hirearchy)"
    )


def test_a_synced_cloud_cache_refuses_with_its_own_message(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.state.plant(w.places.home(), "cloud-cache")
    w.state.plant(w.places.home(), "skills")
    problem = w.readiness.check(BIN)
    assert problem is not None and "holds cloud-cache/, configuration kiro-cli synced for this account" in problem
    assert problem.endswith("this account cannot run hirearchy agents confined") and w.cli.calls == []


def test_a_version_that_cannot_run_is_a_problem(tmp_path: Path) -> None:
    w = world(tmp_path, {VERSION: None})
    assert w.readiness.check(BIN) == f'kiro-cli is not usable: "kiro-cli --version" {NOT_ANSWERED}'
    assert w.cli.calls[-1][0] == VERSION and len(w.cli.calls) == 1


def test_a_version_that_exits_non_zero_names_the_code_and_the_first_line(tmp_path: Path) -> None:
    w = world(tmp_path, {VERSION: CliResult(2, "\nboom happened\nsecond line\n")})
    assert w.readiness.check(BIN) == 'kiro-cli is not usable: "kiro-cli --version" exited 2: boom happened'


def test_help_without_the_v3_flags_names_them(tmp_path: Path) -> None:
    w = world(tmp_path, {**READY, HELP: CliResult(0, "Usage: kiro-cli chat\n  --require-mcp-startup\n")})
    assert w.readiness.check(BIN) == (
        'kiro-cli 2.33.0 does not offer --v3, --output-format in "chat --help": hirearchy runs agents on kiro-cli\'s V3 engine '
        "(verified with kiro-cli 2.33.0); upgrade kiro-cli"
    )


def test_each_missing_flag_is_named_alone(tmp_path: Path) -> None:
    for flag in ("--v3", "--require-mcp-startup", "--output-format"):
        w = world(tmp_path, {**READY, HELP: CliResult(0, FLAGS.replace(flag, "--other"))})
        problem = w.readiness.check(BIN)
        assert problem is not None and f"does not offer {flag} in" in problem


def test_help_that_exits_non_zero_is_not_usable(tmp_path: Path) -> None:
    w = world(tmp_path, {**READY, HELP: CliResult(1, "no such subcommand\n")})
    assert w.readiness.check(BIN) == 'kiro-cli is not usable: "kiro-cli chat --help" exited 1: no such subcommand'


@pytest.mark.parametrize("call,shown", [(VERSION, "--version"), (HELP, "chat --help"), (WHOAMI, "whoami")])
def test_an_overrun_of_each_call_is_did_not_answer(tmp_path: Path, call: tuple[str, ...], shown: str) -> None:
    w = world(tmp_path, {**READY, call: None})
    assert w.readiness.check(BIN) == f'kiro-cli is not usable: "kiro-cli {shown}" {NOT_ANSWERED}'


def test_every_call_uses_the_readiness_timeout(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.readiness.check(BIN)
    assert [call[0] for call in w.cli.calls] == [VERSION, HELP, WHOAMI]
    assert {call[2] for call in w.cli.calls} == {READINESS_TIMEOUT}


def test_the_binary_is_the_one_given(tmp_path: Path) -> None:
    custom = ("/opt/kiro/bin/kiro-cli",)
    w = world(tmp_path, {custom + ("--version",): CliResult(0, "kiro-cli 2.33.0\n"), custom + ("chat", "--help"): CliResult(0, FLAGS),
                         custom + ("whoami",): CliResult(0, "")})
    assert w.readiness.check(custom[0]) is None


def test_whoami_failing_names_the_home_and_how_to_fix_it(tmp_path: Path) -> None:
    w = world(tmp_path, {**READY, WHOAMI: CliResult(1, "Not logged in\n")})
    home = w.places.home()
    assert w.readiness.check(BIN) == (
        f"kiro-cli is not signed in for this organization's kiro home ({home}): set KIRO_API_KEY in the scheduler's environment "
        f'(verified), or make "KIRO_HOME={home} kiro-cli whoami" succeed (a sign-in inside a separate KIRO_HOME is not verified); '
        "hirearchy never falls back to ~/.kiro"
    )


def test_an_api_key_skips_whoami(tmp_path: Path) -> None:
    w = world(tmp_path, {VERSION: READY[VERSION], HELP: READY[HELP]}, {"KIRO_API_KEY": "ksk_secret"})
    assert w.readiness.check(BIN) is None and [call[0] for call in w.cli.calls] == [VERSION, HELP]


def test_an_empty_api_key_does_not_skip_whoami(tmp_path: Path) -> None:
    w = world(tmp_path, variables={"KIRO_API_KEY": ""})
    assert w.readiness.check(BIN) is None and WHOAMI in [call[0] for call in w.cli.calls]


def test_the_environment_is_asked_on_every_check(tmp_path: Path) -> None:
    w = world(tmp_path)
    w.readiness.check(BIN)
    w.environment.set("KIRO_API_KEY", "k")
    w.cli.calls.clear()
    w.readiness.check(BIN)
    assert [call[0] for call in w.cli.calls] == [VERSION, HELP]


def test_every_call_runs_with_the_kiro_home_and_a_scrubbed_environment(tmp_path: Path) -> None:
    w = world(tmp_path, variables={"KIRO_HOME": "/elsewhere", "KIRO_DUMP_REQUESTS": "1", "KIRO_FEATURE_X": "1", "KIRO_LOG_LEVEL": "debug"})
    w.readiness.check(BIN)
    assert len(w.cli.calls) == 3
    for _, env, _ in w.cli.calls:
        assert env["KIRO_HOME"] == str(w.places.home()) and env["PATH"] == "/usr/bin" and env["KIRO_LOG_LEVEL"] == "debug"
        assert "KIRO_DUMP_REQUESTS" not in env and "KIRO_FEATURE_X" not in env


def test_the_value_of_the_key_never_appears_and_every_message_is_one_line(tmp_path: Path) -> None:
    key = "ksk_topsecret_value"
    noisy = CliResult(1, f"line one with {key}\nline two\n")
    cases: list[dict[tuple[str, ...], CliResult | None]] = [
        {VERSION: noisy}, {**READY, HELP: CliResult(0, f"{key}\n--v3\n")}, {**READY, HELP: noisy},
    ]
    for answers in cases:
        problem = world(tmp_path, answers, {"KIRO_API_KEY": key}).readiness.check(BIN)
        assert problem is not None and key not in problem and "\n" not in problem


def test_what_a_command_printed_is_cut_and_the_message_is_bounded(tmp_path: Path) -> None:
    w = world(tmp_path, {VERSION: CliResult(1, "x" * 2000)})
    problem = w.readiness.check(BIN)
    assert problem is not None and problem.endswith(": " + "x" * 200) and len(problem) <= 1000
