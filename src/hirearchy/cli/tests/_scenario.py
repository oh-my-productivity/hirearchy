"""The organizations and the command lines of the characterization of ``hirearchy``'s command line, and how to run one.

The expected texts in ``expected/`` were captured from the flat module ``cli.py`` (and ``cli_obs.py``) before the package existed: for every command
line of ``SCENARIOS`` the standard output, the standard error and the exit code of the command, with the machine-specific parts of the text replaced
by placeholders (the capture ran this module against the tree of that commit, where the worlds were built with ``hirearchy.app.Org`` directly; the tests
run the same scenarios against the package).
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import pytest
from testkit.clocks import clock_ports
from testkit.reach.hirearchy.app import wiring

from hirearchy.kernel import TokenSource
from hirearchy.kernel.testing import CounterTokens

from ._org import overriding

START = datetime(2026, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
COLUMNS = "100"  # the width argparse wraps the help at

BLUEPRINT = """\
mission: Golden blueprint mission.
needs:
  scope: a small written deliverable
  deliverable: {description: A one page note, format: markdown, max_words: 300}
  quality_bar: The note is clear.
  budget_runs: 12
agents:
  - name: lead
    template: manager
    children:
      - {name: writer, template: writer}
task:
  to: lead
  title: Write the note
  goal: Write a one page note about the subject.
  acceptance: ["The note has a title.", "The note has a summary of two sentences."]
"""

BAD_BLUEPRINT = """\
mission: A blueprint with an error.
agents:
  - name: lead
    template: no-such-template
task: {to: lead, title: T, goal: g, acceptance: [a]}
"""


# --------------------------------------------------------------------------------------------------------- determinism


class FixedClock:
    """The one clock of a scenario: it starts at ``START`` and only ``tick`` moves it."""

    def __init__(self) -> None:
        self.now = START

    def tick(self, seconds: float = 60) -> datetime:
        self.now += timedelta(seconds=seconds)
        return self.now


def install(mp: pytest.MonkeyPatch, stack: contextlib.ExitStack) -> FixedClock:
    """Fix the clock and the ids of the message files (the ports of every runtime opened until ``stack`` closes), and the width of the help, for the
    length of the ``MonkeyPatch``."""
    clock = FixedClock()
    stack.enter_context(overriding({**clock_ports(lambda: clock.now, events=True), TokenSource: CounterTokens(per_length=True)}))
    mp.setenv("COLUMNS", COLUMNS)
    for name in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT", "ORG_RUN_ID"):
        mp.delenv(name, raising=False)
    return clock


# ------------------------------------------------------------------------------------------------------ the worlds


@dataclass
class World:
    tmp: Path
    org: Path
    clock: FixedClock

    def fill(self, files: dict[str, str]) -> None:
        for name, text in files.items():
            (self.tmp / name).parent.mkdir(parents=True, exist_ok=True)
            (self.tmp / name).write_text(text, encoding="utf-8")


def _team(tmp: Path, clock: FixedClock) -> Path:
    """root -> ceo (manager) -> eng, an open task of root, a note in root's inbox, a service of ceo."""
    from hirearchy.kernel import ROOT

    from ._org import facade

    org = facade().init(tmp / "org", "Golden mission: ship the thing.", {"poll_seconds": 0.05})
    clock.tick()
    org.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    org.hire("ceo", "eng", "Engineer", "Build things.")
    clock.tick()
    org.delegate(ROOT, "ceo", "Ship it", "Ship the thing.", "It is shipped.", budget=8)
    clock.tick()
    org.send("ceo", ROOT, "Hello from the ceo.", title="Greeting")
    clock.tick()
    org.define_service(
        ROOT, "ceo", "weekly", description="A weekly note", inputs=[{"name": "topic", "description": "what to write about", "required": True}],
        acceptance=["The note has a title."], deliverable={"description": "The note", "format": "markdown"}, budget=4,
    )
    clock.tick()
    return Path(org.root)


def _delivered(tmp: Path, clock: FixedClock) -> Path:
    """``_team`` plus a request of the service that the ceo has answered: something to give feedback on."""
    from hirearchy.kernel import ROOT

    from ._org import facade

    root = _team(tmp, clock)
    org = facade()(root)
    request = org.request(ROOT, "weekly", {"topic": "tests"}, title="Weekly")
    clock.tick()
    org.begin_run("ceo")
    org.report("ceo", request.id, "done", "Written.", lessons="Start from the outline.")
    org.end_run("ceo", ok=True)
    clock.tick()
    (tmp / "request_id").write_text(request.id, encoding="utf-8")
    return root


def _old_rules(tmp: Path, clock: FixedClock) -> Path:
    """``_fresh`` whose ORG.md carries rules from an earlier template."""
    root = _fresh(tmp, clock)
    path = root / "ORG.md"
    text = path.read_text(encoding="utf-8")
    cut = text.index("\n## How this organization works")
    path.write_text(text[:cut] + "\n## How this organization works\n\nAn old rule.\n", encoding="utf-8")
    return root


def _fresh(tmp: Path, clock: FixedClock) -> Path:
    from ._org import facade

    return Path(facade().init(tmp / "org", "Fresh mission.", {"poll_seconds": 0.05}).root)


def _none(tmp: Path, clock: FixedClock) -> Path:
    return tmp / "org"  # nothing there


WORLDS: dict[str, Callable[[Path, FixedClock], Path]] = {
    "team": _team, "delivered": _delivered, "fresh": _fresh, "old_rules": _old_rules, "none": _none,
}


# --------------------------------------------------------------------------------------------------- the command lines


@dataclass(frozen=True)
class Scenario:
    argv: tuple[str, ...]
    world: str = "team"
    files: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None  # relative to the temp dir; the command runs there
    before: tuple[tuple[str, ...], ...] = ()  # command lines run first (their output is not kept)


def sc(argv: str, world: str = "team", files: dict[str, str] | None = None, cwd: str | None = None, before: tuple[str, ...] = ()) -> Scenario:
    return Scenario(tuple(argv.split("\x1f")) if "\x1f" in argv else tuple(argv.split()), world, files or {}, cwd,
                    tuple(tuple(b.split()) for b in before))


R = "--root {org}"

SCENARIOS: dict[str, Scenario] = {
    # --- the parser
    "no_command": sc(""),
    "unknown_command": sc("frobnicate"),
    "bad_verdict": sc(f"{R} feedback some-id maybe"),
    "obs_without_view": sc(f"{R} obs"),
    # --- init
    "init": sc("init {tmp}/new --mission Ship-the-thing.", "none"),
    "init_from_file": sc("init {tmp}/new --mission @{tmp}/mission.md --model claude-opus-5.5", "none", {"mission.md": "A mission from a file.\n"}),
    "init_default_path": sc("init", "none", cwd="work"),
    "init_again": sc("init {org}"),
    # --- people and mail
    "hire": sc(f"{R} hire ceo dev --role Dev --charter Write-code. --model claude-opus-5.5 --can-hire --max-children 3"),
    "hire_with_tools_it_does_not_have": sc(f"{R} hire ceo dev --role Dev --charter Write-code. --tools read,write --inputs {{tmp}}/in"),
    "hire_charter_from_file": sc(f"{R} hire ceo qa --role QA --charter @{{tmp}}/charter.md", files={"charter.md": "Check the work.\n"}),
    "hire_unknown_parent": sc(f"{R} hire nobody dev --role Dev --charter Code."),
    "hire_missing_charter_file": sc(f"{R} hire ceo dev --role Dev --charter @{{tmp}}/missing.md"),
    "hire_no_org": sc("--root {tmp}/nowhere hire ceo dev --role Dev --charter Code.", "none"),
    "task": sc(f"{R} task ceo --title Next --goal Do-the-next-thing. --acceptance Done. --budget 3 --input {{tmp}}/in"),
    "task_unknown_agent": sc(f"{R} task nobody --title T --goal g --acceptance a"),
    "task_no_org": sc("--root {tmp}/nowhere task ceo --title T --goal g --acceptance a", "none"),
    "send": sc(f"{R} send ceo Hello-ceo. --title Hi --budget 1"),
    "send_unknown_agent": sc(f"{R} send nobody hi"),
    "inbox": sc(f"{R} inbox"),
    "inbox_again": sc(f"{R} inbox", before=(f"{R} inbox",)),
    "inbox_keep": sc(f"{R} inbox --keep"),
    "inbox_empty": sc(f"{R} inbox", "fresh"),
    "resume": sc(f"{R} resume ceo/"),
    "resume_unknown": sc(f"{R} resume nobody"),
    # --- services
    "services": sc(f"{R} services"),
    "services_none": sc(f"{R} services", "fresh"),
    "define_service": sc(f"{R} define-service ceo monthly --description A-monthly-note --input topic*:what --acceptance Has-a-title. "
                         "--deliverable The-note --format markdown --max-words 400 --budget 5 --locked"),
    "define_service_amend_deliverable": sc(f"{R} define-service ceo weekly --format text --max-words 200"),
    "define_service_amend_acceptance": sc(f"{R} define-service ceo weekly --add-acceptance Has-a-summary. --words Add-a-summary. --no-locked --notes @{{tmp}}/notes.md",
                                          files={"notes.md": "A note for the owner.\n"}),
    "define_service_error": sc(f"{R} define-service nobody weekly --description x"),
    "request": sc(f"{R} request weekly --input topic=tests --title Weekly --note Please. --budget 3"),
    "request_bad_input": sc(f"{R} request weekly --input topic"),
    "request_unknown_service": sc(f"{R} request nothing"),
    "feedback": sc(f"{R} feedback {{request_id}} accept --note Good.", "delivered"),
    "feedback_reject_without_note": sc(f"{R} feedback {{request_id}} reject", "delivered"),
    "retire_service": sc(f"{R} retire-service ceo weekly --reason Not-needed."),
    "retire_service_unknown": sc(f"{R} retire-service ceo nothing --reason x"),
    # --- blueprints
    "plan": sc(f"{R} plan {{tmp}}/bp.yaml --allow-root {{tmp}}", files={"bp.yaml": BLUEPRINT}),
    "plan_without_org": sc("plan {tmp}/bp.yaml --allow-root {tmp}", "none", {"bp.yaml": BLUEPRINT}),
    "plan_with_errors": sc(f"{R} plan {{tmp}}/bp.yaml --allow-root {{tmp}}", files={"bp.yaml": BAD_BLUEPRINT}),
    "plan_missing_file": sc(f"{R} plan {{tmp}}/missing.yaml"),
    "apply": sc(f"{R} apply {{tmp}}/bp.yaml --allow-root {{tmp}}", "fresh", {"bp.yaml": BLUEPRINT}),
    "apply_with_errors": sc(f"{R} apply {{tmp}}/bp.yaml --allow-root {{tmp}}", "fresh", {"bp.yaml": BAD_BLUEPRINT}),
    "apply_no_org": sc("--root {tmp}/nowhere apply {tmp}/bp.yaml", "none", {"bp.yaml": BLUEPRINT}),
    # --- views
    "status": sc(f"{R} status"),
    "status_fresh": sc(f"{R} status", "fresh"),
    "status_no_org": sc("--root {tmp}/nowhere status", "none"),
    "health": sc(f"{R} health"),
    "health_json": sc(f"{R} health --json"),
    "health_agent": sc(f"{R} health --agent ceo"),
    "progress": sc(f"{R} progress"),
    "progress_unknown_task": sc(f"{R} progress nope"),
    "dash_once": sc(f"{R} dash --once"),
    "dash_root_after_the_command": sc("dash --root {org} --once"),
    "dash_global_root_wins_when_alone": sc(f"{R} dash --once --interval 5"),
    "dash_without_a_terminal": sc(f"{R} dash"),
    # --- rules, skill, review, profile
    "upgrade_rules_dry_run": sc(f"{R} upgrade-rules --dry-run"),
    "upgrade_rules": sc(f"{R} upgrade-rules"),
    "upgrade_rules_old_dry_run": sc(f"{R} upgrade-rules --dry-run", "old_rules"),
    "upgrade_rules_old": sc(f"{R} upgrade-rules", "old_rules"),
    "install_skill": sc("install-skill --dest {tmp}/skills"),
    "install_skill_again": sc("install-skill --dest {tmp}/skills", before=("install-skill --dest {tmp}/skills",)),
    "install_skill_conflict": sc("install-skill --dest {tmp}/skills", files={"skills/hirearchy/SKILL.md": "another skill\n"}),
    "install_skill_forced": sc("install-skill --dest {tmp}/skills --force", files={"skills/hirearchy/SKILL.md": "another skill\n"}),
    "review_dry_run": sc(f"{R} review --dry-run"),
    "review": sc(f"{R} review"),
    "kiro_profile": sc(f"{R} kiro-profile --tools read,write"),
    "kiro_profile_no_org": sc("--root {tmp}/nowhere kiro-profile", "none"),
    # --- scheduler
    "run_until_done": sc(f"{R} run --until-done", "fresh"),
    "run_until_done_and_once": sc(f"{R} run --until-done --once", "fresh"),
    "run_once": sc(f"{R} run --once", "fresh"),
    "run_no_org": sc("--root {tmp}/nowhere run --once", "none"),
    # --- obs
    "check": sc(f"{R} check"),
    "check_json": sc(f"{R} check --json"),
    "obs_now": sc(f"{R} obs now"),
    "obs_now_json": sc(f"{R} obs now --json"),
    "obs_trace": sc(f"{R} obs trace {{task_id}}"),
    "obs_trace_json": sc(f"{R} obs trace {{task_id}} --json"),
    "obs_trace_unknown": sc(f"{R} obs trace nope"),
    "obs_metrics": sc(f"{R} obs metrics --since 7d --by agent --limit 5"),
    "obs_metrics_json": sc(f"{R} obs metrics --since 7d --agent ceo --json"),
    "obs_events": sc(f"{R} obs events --since 2026-01-15T00:00:00Z --limit 5"),
    "obs_events_json": sc(f"{R} obs events --since 2026-01-15T00:00:00Z --limit 3 --json"),
    "obs_events_bad_time": sc(f"{R} obs events --since yesterday-ish"),
    "obs_no_org": sc("--root {tmp}/nowhere obs now", "none"),
}

SUBCOMMANDS = (
    "init", "hire", "task", "services", "define-service", "request", "feedback", "retire-service", "plan", "apply", "send", "status", "health",
    "progress", "upgrade-rules", "install-skill", "review", "inbox", "resume", "run", "mcp", "dash", "obs", "check", "kiro-profile",
)
OBS_VIEWS = ("now", "trace", "metrics", "events")


# ----------------------------------------------------------------------------------------------------------- running


@dataclass
class Outcome:
    out: str
    err: str
    code: int
    raised: str = ""  # "<ExceptionType>: <message>" of an exception that is not SystemExit


def run(main: Callable[[list[str]], None], argv: list[str]) -> Outcome:
    """``main(argv)`` with the standard output and error captured; ``code`` is the exit status (0 when ``main`` returns)."""
    out, err = io.StringIO(), io.StringIO()
    code, raised = 0, ""
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            main(argv)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
            if isinstance(exc.code, str):
                err.write(exc.code + "\n")
        except Exception as exc:  # noqa: BLE001
            code, raised = -1, f"{type(exc).__name__}: {exc}"
    return Outcome(out.getvalue(), err.getvalue(), code, raised)


class Normalizer:
    """The machine-specific parts of a text replaced by placeholders (longest first)."""

    def __init__(self) -> None:
        self.pairs: list[tuple[str, str]] = []

    def add(self, real: object, placeholder: str) -> None:
        for form in {str(real), str(Path(str(real)).resolve())}:
            if form and form not in ("/", "."):
                self.pairs.append((form, placeholder))

    def __call__(self, text: str) -> str:
        for real, placeholder in sorted(self.pairs, key=lambda p: -len(p[0])):
            text = text.replace(real, placeholder)
        text = re.sub(r"-x[0-9a-f]{8}\b", "-x<ACCESS_HASH>", text)  # a confined profile's name ends in a hash of its rules (they hold the org's path)
        text = re.sub(r"(hirearchy-[a-z0-9-]*?)-[0-9a-f]{6}\b", r"\1-<HASH>", text)  # the profile name carries a hash of the path of the organization
        text = re.sub(r'("pid": )\d+', r'\1"<PID>"', text)
        return re.sub(r"\bpid \d+", "pid <PID>", text)


def normalizer(tmp: Path, home: Path | None) -> Normalizer:
    spec = importlib.util.find_spec("hirearchy")  # (the location of the package, without running its __init__)
    assert spec is not None and spec.origin is not None

    n = Normalizer()
    n.add(Path(spec.origin).resolve().parents[2], "<PROJECT>")
    n.add(Path(sys.executable).parent, "<VENV_BIN>")
    # the kiro home of the organization, from the same places the command line uses (below the HOME in force: a path that differs by platform and by organization)
    n.add(wiring.open_runtime(tmp / "org").kiro_places.home(), "<KIRO_HOME>")
    if home is not None:
        n.add(home, "<HOME>")
    n.add(tmp / "org", "<ORG>")
    n.add(tmp, "<TMP>")
    return n


def text_of(outcome: Outcome, norm: Callable[[str], str]) -> str:
    """The golden text of an outcome: the output, the error output (when there is any), the exception (when one escaped) and the exit status."""
    text = norm(outcome.out)
    if outcome.err:
        text += "\n[stderr]\n" + norm(outcome.err)
    if outcome.raised:
        text += "\n[raised] " + norm(outcome.raised) + "\n"
    return text + f"\n[exit {outcome.code}]\n"


def _extras(world: World) -> dict[str, str]:
    """The ids that a command line may name: the request that was answered, the first task of root."""
    extras: dict[str, str] = {}
    request = world.tmp / "request_id"
    if request.is_file():
        extras["request_id"] = request.read_text(encoding="utf-8")
    if (world.org / "ORG.md").is_file():
        from hirearchy.kernel import ROOT

        from ._org import facade

        tasks = [m.id for m in facade()(world.org).sent(ROOT) if m.type == "task"]
        extras["task_id"] = min(tasks) if tasks else "no-task"
    return extras


def argv_of(scenario: Scenario, world: World) -> list[str]:
    values = {"org": str(world.org), "tmp": str(world.tmp), **_extras(world)}
    return [part.format(**values) for part in scenario.argv]


def execute(label: str, base: Path, main: Callable[[list[str]], None]) -> str:
    """The golden text of the command line ``SCENARIOS[label]`` run by ``main`` in a new world below the empty directory ``base``."""
    from ._org import process_resources

    scenario = SCENARIOS[label]
    tmp, home = base / "t", base / "home"
    tmp.mkdir()
    home.mkdir()
    before = Path.cwd()
    process_resources().reset()
    try:
        with contextlib.ExitStack() as stack, pytest.MonkeyPatch.context() as mp:
            clock = install(mp, stack)
            mp.setenv("HOME", str(home))
            world = World(tmp, WORLDS[scenario.world](tmp, clock), clock)
            world.fill(scenario.files)
            mp.chdir(tmp)
            if scenario.cwd:
                (tmp / scenario.cwd).mkdir(parents=True, exist_ok=True)
                mp.chdir(tmp / scenario.cwd)
            for first in scenario.before:
                run(main, [part.format(org=str(world.org), tmp=str(tmp)) for part in first])
            outcome = run(main, argv_of(scenario, world))
            return text_of(outcome, normalizer(tmp, home))
    finally:
        os.chdir(before)
        process_resources().reset()


def help_text(main: Callable[[list[str]], None], *command: str) -> str:
    """The ``--help`` of a command (or of the program): argparse's own text, wrapped at ``COLUMNS``."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("COLUMNS", COLUMNS)
        outcome = run(main, [*command, "--help"])
    assert outcome.code == 0 and not outcome.err, outcome
    return outcome.out
