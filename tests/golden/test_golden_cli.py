"""Golden: the output of the command line (status, progress, services, health, inbox, obs ..., check, dash --once)
and ``--help`` of every subcommand."""

import re

import pytest
from golden_support import check
from scenarios import busy_org

from hirearchy import main


@pytest.fixture
def busy(tmp_path, clock, norm, monkeypatch):
    org = busy_org(tmp_path, clock)
    norm.add(org.root, "<ORG>")
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.delenv("ORG_ROOT", raising=False)
    return org


def cli(capsys, org, *argv, code: int | None = 0) -> str:
    """Run ``hirearchy --root <org> <argv>``; stdout (and stderr, when there is any) as one text; checks the exit code."""
    try:
        main(["--root", str(org.root), *argv])
        status = 0
    except SystemExit as exc:
        status = exc.code if isinstance(exc.code, int) else 1
    out = capsys.readouterr()
    if code is not None:
        assert status == code, out.err
    text = out.out
    if out.err:
        text += "\n[stderr]\n" + out.err
    return text + f"\n[exit {status}]\n"


READ_ONLY = {
    "status": ["status"],
    "progress": ["progress"],
    "services": ["services"],
    "health": ["health"],
    "health_json": ["health", "--json"],
    "check": ["check"],
    "check_json": ["check", "--json"],
    "obs_now": ["obs", "now"],
    "obs_now_json": ["obs", "now", "--json"],
    "obs_metrics": ["obs", "metrics", "--since", "7d"],
    "obs_metrics_by_agent": ["obs", "metrics", "--since", "7d", "--by", "agent"],
    "obs_metrics_by_tool_json": ["obs", "metrics", "--since", "7d", "--by", "tool", "--json"],
    "obs_events": ["obs", "events", "--since", "7d", "--limit", "200"],
    "obs_events_errors": ["obs", "events", "--since", "7d", "--errors"],
    "obs_events_json": ["obs", "events", "--since", "7d", "--limit", "20", "--json"],
    "dash_once": ["dash", "--once"],
    "inbox_keep": ["inbox", "--keep"],
}


@pytest.mark.parametrize("label", sorted(READ_ONLY))
def test_cli_output(label, busy, capsys, norm):
    check(f"cli/{label}.txt", norm(cli(capsys, busy, *READ_ONLY[label])))


def test_cli_obs_trace_of_the_planning_task(busy, capsys, norm):
    root_task = min(m.id for m in busy.sent("root") if m.type == "task" and m.title == "Plan the launch")
    check("cli/obs_trace.txt", norm(cli(capsys, busy, "obs", "trace", root_task)))
    check("cli/progress_one_task.txt", norm(cli(capsys, busy, "progress", root_task)))
    check("cli/obs_events_of_trace.txt", norm(cli(capsys, busy, "obs", "events", "--since", "7d", "--trace", root_task)))


def test_cli_inbox_marks_mail_as_read(busy, capsys, norm):
    first = norm(cli(capsys, busy, "inbox"))
    second = norm(cli(capsys, busy, "inbox"))
    check("cli/inbox.txt", first)
    check("cli/inbox_again.txt", second)


def test_cli_status_of_a_fresh_org(tmp_path, clock, norm, capsys, monkeypatch):
    from hirearchy.core import Org

    monkeypatch.setenv("COLUMNS", "100")
    org = Org.init(tmp_path / "org", "Fresh")
    norm.add(org.root, "<ORG>")
    for label, argv in (("status", ["status"]), ("progress", ["progress"]), ("health", ["health"]), ("services", ["services"]),
                        ("check", ["check"]), ("obs_now", ["obs", "now"]), ("obs_metrics", ["obs", "metrics"]),
                        ("obs_events", ["obs", "events"]), ("dash_once", ["dash", "--once"]), ("inbox", ["inbox"])):
        check(f"cli/fresh_{label}.txt", norm(cli(capsys, org, *argv, code=None)))


def test_cli_errors(busy, capsys, norm):
    check("cli/error_unknown_task.txt", norm(cli(capsys, busy, "obs", "trace", "no-such-task", code=None)))
    check("cli/error_no_org.txt", norm(cli(capsys, busy, "--root", "/nonexistent-golden-dir", "status", code=None)))


SUBCOMMANDS = [
    "init", "hire", "task", "services", "define-service", "request", "feedback", "retire-service", "plan", "apply", "send",
    "status", "health", "progress", "upgrade-rules", "install-skill", "review", "inbox", "resume", "run", "mcp", "dash",
    "obs", "obs now", "obs trace", "obs metrics", "obs events", "check", "kiro-profile",
]


def help_of(capsys, monkeypatch, *argv) -> str:
    monkeypatch.setenv("COLUMNS", "100")
    with pytest.raises(SystemExit) as info:
        main([*argv, "--help"])
    assert info.value.code == 0
    return capsys.readouterr().out


def test_every_subcommand_is_covered_by_the_help_snapshots(capsys, monkeypatch):
    top = help_of(capsys, monkeypatch)
    listed = re.search(r"\{([a-z\-,]+)\}", top).group(1).split(",")
    assert sorted(listed) == sorted(c for c in SUBCOMMANDS if " " not in c), "a subcommand was added or removed: update SUBCOMMANDS"
    obs = help_of(capsys, monkeypatch, "obs")
    assert sorted(re.search(r"\{([a-z,]+)\}", obs).group(1).split(",")) == sorted(c.split()[1] for c in SUBCOMMANDS if c.startswith("obs "))
    check("cli/help.txt", top)


@pytest.mark.parametrize("command", SUBCOMMANDS)
def test_help_of_every_subcommand(command, capsys, monkeypatch):
    check(f"cli/help_{command.replace(' ', '_')}.txt", help_of(capsys, monkeypatch, *command.split()))
