"""``init hire task send inbox resume`` over fakes of the features they use: what each asks of them, in what order, and what it says."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.cli._commands_org import HireCommand, InboxCommand, InitCommand, ResumeCommand, SendCommand, TaskCommand
from orgmcp.cli.testing import MemoryText
from orgmcp.kernel import Message, OrgError

from ._fakes import FakeMail, FakeOffice, new_mail, new_office
from ._support import Fixture, go, parse

pytestmark = pytest.mark.xfail(strict=True, reason="red: D-cli")

TEXT = MemoryText({"charter.md": "Check the work.\n", "goal.md": "The goal.\n", "body.md": "A long note.\n", "mission.md": "The mission.\n"})


def hire_world(tmp_path: Path) -> tuple[Fixture, FakeOffice, HireCommand]:
    f, office = Fixture(tmp_path), new_office()
    return f, office, HireCommand(f.session, lambda: office, lambda: office, TEXT, f.out)


# --------------------------------------------------------------------------------------------------------------- init


def test_init_announces_and_makes_the_organization_where_the_path_says(tmp_path: Path) -> None:
    f, office = Fixture(tmp_path), new_office()
    path = str(tmp_path / "new")
    go(InitCommand(f.session, lambda: office, TEXT, f.out), "init", path, "--mission", "@mission.md", "--model", "claude-x")
    assert f.session.calls == [("create", path)]
    assert office.last("init") == ((Path(path), "The mission.\n", {"default_model": "claude-x"}), {})
    assert f.out.stdout == f"initialized organization at {path}\nedit {Path(path) / 'ORG.md'} to set the mission and limits\n"


def test_init_reads_the_mission_from_a_file_and_has_no_config_without_a_model(tmp_path: Path) -> None:
    f, office = Fixture(tmp_path), new_office()
    go(InitCommand(f.session, lambda: office, MemoryText({"m.md": "Mission text.\n"}), f.out), "init", "x", "--mission", "@m.md")
    assert office.last("init")[0][1:] == ("Mission text.\n", None)
    go(InitCommand(f.session, lambda: office, TEXT, f.out), "init")
    assert office.last("init")[0] == (Path("org"), None, None)  # the default path


def test_init_says_nothing_when_the_organization_cannot_be_made(tmp_path: Path) -> None:
    f, office = Fixture(tmp_path), new_office()
    office.refuse = OrgError("already an organization: x")
    with pytest.raises(OrgError, match="already an organization"):
        go(InitCommand(f.session, lambda: office, TEXT, f.out), "init", "x")
    assert f.out.stdout == ""


# --------------------------------------------------------------------------------------------------------------- hire


def test_hire_opens_for_a_change_and_hires_then_snapshots_then_says(tmp_path: Path) -> None:
    f, office, command = hire_world(tmp_path)
    go(command, "hire", "ceo", "dev", "--role", "Dev", "--charter", "@charter.md", "--model", "m", "--tools", "read,,write", "--can-hire",
       "--max-children", "3", "--workspace", "/w", "--inputs", "/a", "--inputs", "/b")
    assert f.session.calls == [("open", True)]
    assert office.last("hire") == (
        ("ceo", "dev", "Dev", "Check the work.\n"),
        {"model": "m", "tools": ["read", "write"], "can_hire": True, "max_children": 3, "workspace": "/w", "inputs": ["/a", "/b"]},
    )
    assert office.names() == ["hire", "commit"] and office.last("commit") == (("root: hired ceo/dev",), {})
    assert f.out.stdout == "hired ceo/dev\n"


def test_hire_defaults_are_no_model_no_tools_no_inputs(tmp_path: Path) -> None:
    f, office, command = hire_world(tmp_path)
    go(command, "hire", "root", "ceo", "--role", "CEO", "--charter", "Run it.")
    assert office.last("hire")[1] == {"model": None, "tools": [], "can_hire": False, "max_children": 5, "workspace": None, "inputs": None}


def test_hire_announces_before_it_reads_the_charter_file(tmp_path: Path) -> None:
    f, office, command = hire_world(tmp_path)
    with pytest.raises(FileNotFoundError):
        go(command, "hire", "ceo", "dev", "--role", "Dev", "--charter", "@missing.md")
    assert f.session.calls == [("open", True)] and office.calls == []


def test_a_refused_hire_is_not_snapshotted_or_announced_as_done(tmp_path: Path) -> None:
    f, office, command = hire_world(tmp_path)
    office.refuse = OrgError("no such agent: nobody")
    with pytest.raises(OrgError, match="no such agent"):
        go(command, "hire", "nobody", "dev", "--role", "Dev", "--charter", "x")
    assert office.names() == ["hire"] and f.out.stdout == ""


def test_hire_needs_a_role_and_a_charter(tmp_path: Path) -> None:
    f, office, command = hire_world(tmp_path)
    with pytest.raises(SystemExit):
        parse(command, "hire", "ceo", "dev")


# --------------------------------------------------------------------------------------------------------------- task


def test_task_delegates_as_root_snapshots_and_says_the_budget(tmp_path: Path) -> None:
    f, office = Fixture(tmp_path), new_office()
    go(TaskCommand(f.session, lambda: office, lambda: office, TEXT, f.out), "task", "ceo", "--title", "T", "--goal", "@goal.md", "--acceptance", "Done.",
       "--input", "/a", "--input", "/b", "--budget", "3", "--revises", "t-0")
    assert f.session.calls == [("open", True)]
    assert office.last("delegate") == (("root", "ceo", "T", "The goal.\n", "Done.", ["/a", "/b"], 3, "t-0"), {})
    assert office.last("commit") == (("root: task m-1 -> ceo",), {})
    assert f.out.stdout == "task m-1 -> ceo (budget 3)\n"


def test_task_without_inputs_or_budget(tmp_path: Path) -> None:
    f, office = Fixture(tmp_path), new_office()
    go(TaskCommand(f.session, lambda: office, lambda: office, TEXT, f.out), "task", "ceo", "--title", "T", "--goal", "g", "--acceptance", "a")
    assert office.last("delegate")[0][5:] == ([], None, None)
    assert f.out.stdout == "task m-1 -> ceo (budget 0)\n"


# --------------------------------------------------------------------------------------------------------------- send


def test_send_posts_a_note_as_root(tmp_path: Path) -> None:
    f, office = Fixture(tmp_path), new_office()
    go(SendCommand(f.session, lambda: office, lambda: office, TEXT, f.out), "send", "ceo", "@body.md", "--title", "Hi", "--reply-to", "x-1", "--budget", "2")
    assert f.session.calls == [("open", True)]
    assert office.last("send") == (("root", "ceo", "A long note.\n"), {"title": "Hi", "reply_to": "x-1", "budget": 2})
    assert office.last("commit") == (("root: note m-1 -> ceo",), {})
    assert f.out.stdout == "sent m-1 -> ceo\n"


# -------------------------------------------------------------------------------------------------------------- inbox


def mail_with_two(mail: FakeMail) -> str:
    mail.inbox = [Message("ceo", "root", "note", "First.", title="One", id="a-1"), Message("ceo", "root", "note", "Second.", id="a-2")]
    return "\n".join(m.render() for m in mail.inbox) + "\n"


def test_inbox_takes_the_mail_and_marks_it_read(tmp_path: Path) -> None:
    f, mail = Fixture(tmp_path), new_mail()
    shown = mail_with_two(mail)
    go(InboxCommand(f.session, lambda: mail, lambda: mail, f.out), "inbox")
    assert f.session.calls == [("open", True)]  # reading marks the mail as read: it changes the organization
    assert mail.names() == ["begin", "end"] and mail.last("end") == (("root", True), {})
    assert f.out.stdout == shown


def test_inbox_keep_only_looks(tmp_path: Path) -> None:
    f, mail = Fixture(tmp_path), new_mail()
    shown = mail_with_two(mail)
    go(InboxCommand(f.session, lambda: mail, lambda: mail, f.out), "inbox", "--keep")
    assert f.session.calls == [("open", False)]
    assert mail.calls == [("messages", ("root", "inbox"), {})]
    assert f.out.stdout == shown


def test_an_empty_inbox_says_so(tmp_path: Path) -> None:
    f, mail = Fixture(tmp_path), new_mail()
    go(InboxCommand(f.session, lambda: mail, lambda: mail, f.out), "inbox")
    assert f.out.stdout == "(no new messages)\n"


# ------------------------------------------------------------------------------------------------------------- resume


def test_resume_clears_the_pause_and_the_failures_of_the_agent_it_names(tmp_path: Path) -> None:
    f, mail = Fixture(tmp_path), new_mail()
    go(ResumeCommand(f.session, lambda: mail, lambda: mail, lambda: mail, f.out), "resume", "ceo/")
    assert f.session.calls == [("open", True)]
    assert mail.names() == ["require", "resume", "clear"]
    assert mail.last("resume") == (("ceo", "", None), {}) and mail.last("clear") == (("ceo",), {})
    assert f.out.stdout == "resumed ceo\n"


def test_resume_of_an_unknown_agent_changes_nothing(tmp_path: Path) -> None:
    f, mail = Fixture(tmp_path), new_mail()
    with pytest.raises(OrgError, match="no such agent: nobody"):
        go(ResumeCommand(f.session, lambda: mail, lambda: mail, lambda: mail, f.out), "resume", "nobody")
    assert mail.names() == ["require"] and f.out.stdout == ""
