# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.legacy.orgmcp.core import ROOT
from testkit.services_world import BRIEF, cli, contract_meta, define, deliver, playbook_meta


@pytest.fixture
def svc(org):
    define(org, notes="Mind the sources.", locked=True, playbook="Steps: search, write.")
    return org


def test_cli_amendment(svc, capsys, tmp_path):
    cli(svc, "define-service", "ceo", "weekly-brief", "--add-acceptance", "Never longer than one page")
    out = capsys.readouterr().out
    assert "v1 -> v2" in out and "3. Never longer than one page" in out
    meta = contract_meta(svc)[0]
    assert meta["acceptance"][-1] == "Never longer than one page" and meta["budget"] == 10 and meta["deliverable"] == BRIEF["deliverable"]

    more = tmp_path / "more.txt"
    more.write_text("First extra\n- Second extra\n")
    cli(svc, "define-service", "ceo", "weekly-brief", "--remove-acceptance", "At most 600 words",
        "--remove-acceptance", "Never longer than one page", "--add-acceptance", f"@{more}")
    assert contract_meta(svc)[0]["acceptance"] == ["Every factual claim has a source URL", "First extra", "Second extra"]

    cli(svc, "define-service", "ceo", "weekly-brief", "--budget", "7", "--no-locked", "--max-words", "250", "--input", "topic*:the topic")
    meta = contract_meta(svc)[0]
    assert meta["budget"] == 7 and meta["locked"] is False and meta["inputs"] == [{"name": "topic", "description": "the topic", "required": True}]
    assert meta["deliverable"] == {**BRIEF["deliverable"], "max_words": 250}  # single deliverable parts merge over the old one
    capsys.readouterr()

    for args, message in (
        (("weekly-brief", "--acceptance", "Whole new", "--add-acceptance", "x y"), "replaces all criteria"),
        (("weekly-brief", "--budget", "7"), "no change"),
        (("brand-new", "--budget", "3"), "needs description"),
    ):
        with pytest.raises(SystemExit):
            cli(svc, "define-service", "ceo", *args)
        assert message in capsys.readouterr().err


# ----------------------------------------------------------------------------------------------- CLI
def test_cli_commands(org, capsys, tmp_path):
    criteria = tmp_path / "criteria.txt"
    criteria.write_text("At most 600 words\n- Every claim has a URL\n")
    playbook = tmp_path / "pb.md"
    playbook.write_text("## Steps\n1. Search.")
    cli(org, "define-service", "ceo", "weekly-brief", "--description", "A weekly brief.",
        "--input", "topic*:what it is about", "--input", "week:ISO week", "--acceptance", f"@{criteria}",
        "--acceptance", "Mention a risk", "--deliverable", "one file", "--format", "markdown", "--max-words", "600",
        "--path", str(tmp_path / "out"), "--budget", "8", "--playbook", f"@{playbook}", "--locked")
    meta, _ = contract_meta(org)
    assert meta["acceptance"] == ["At most 600 words", "Every claim has a URL", "Mention a risk"]
    assert meta["inputs"] == [{"name": "topic", "description": "what it is about", "required": True},
                              {"name": "week", "description": "ISO week", "required": False}]
    assert meta["deliverable"] == {"description": "one file", "format": "markdown", "max_words": 600, "path": str(tmp_path / "out")}
    assert meta["budget"] == 8 and meta["locked"] is True and playbook_meta(org)[0]["version"] == 1
    assert "defined service `weekly-brief`" in capsys.readouterr().out

    cli(org, "services")
    assert "weekly-brief (offered by ceo; contract v1, playbook v1)" in capsys.readouterr().out
    cli(org, "request", "weekly-brief", "--input", "topic=ai chips", "--input", "week=3", "--note", "Hurry")
    out = capsys.readouterr().out
    (task,) = org.outstanding(ROOT)
    assert task.id in out and task.budget == 8 and "- week: 3" in task.body and "Hurry" in task.body
    deliver(org, "ceo", task)
    cli(org, "feedback", task.id, "reject", "--note", "Too long")
    assert "feedback reject on" in capsys.readouterr().out
    assert [m.feedback for m in org.sent(ROOT) if m.type == "note"] == ["reject"]
    with pytest.raises(SystemExit):
        cli(org, "feedback", task.id, "reject")  # a rejection needs a note
    assert "needs a note" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        cli(org, "request", "weekly-brief", "--input", "no-equals-sign")
    assert "key=value" in capsys.readouterr().err
    cli(org, "retire-service", "ceo", "weekly-brief", "--reason", "done with it")
    assert "retired service" in capsys.readouterr().out and org.service_names("ceo") == []
    log = __import__("subprocess").run(["git", "log", "--format=%s"], cwd=org.root, capture_output=True, text=True).stdout
    assert "root: service weekly-brief of ceo" in log and "root: retired service" in log
