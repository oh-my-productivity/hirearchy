# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.hirearchy.core import ROOT
from testkit.services_world import BRIEF, cli, contract_meta, define, deliver, playbook_meta, request


@pytest.fixture
def svc(org):
    define(org, notes="Mind the sources.", locked=True, playbook="Steps: search, write.")
    return org


def test_cli_amendment(svc, capsys, tmp_path):
    cli(svc, "define-service", "ceo", "weekly-brief", "--add-acceptance", "Never longer than one page", "--words", "One page at most.")
    out = capsys.readouterr().out
    assert "v1 -> v2" in out and "C3: Never longer than one page" in out
    meta = contract_meta(svc)[0]
    assert meta["acceptance"][-1] == "Never longer than one page" and meta["budget"] == 10 and meta["deliverable"] == BRIEF["deliverable"]

    more = tmp_path / "more.txt"
    more.write_text("First extra\n- Second extra\n")
    cli(svc, "define-service", "ceo", "weekly-brief", "--remove-acceptance", "At most 600 words",
        "--remove-acceptance", "Never longer than one page", "--add-acceptance", f"@{more}", "--words", "Change them, please.")
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
    rejected = [m for m in org.sent(ROOT) if m.feedback][-1]
    cli(org, "feedback", task.id, "reject", "--note", "A one-off.", "--source", "human", "--confirms", rejected.id, "--criterion", "none")  # its answer
    capsys.readouterr()
    cli(org, "retire-service", "ceo", "weekly-brief", "--reason", "done with it")
    assert "retired service" in capsys.readouterr().out and org.service_names("ceo") == []
    log = __import__("subprocess").run(["git", "log", "--format=%s"], cwd=org.root, capture_output=True, text=True).stdout
    assert "root: service weekly-brief of ceo" in log and "root: retired service" in log


# ----------------------------------------------------------------------------------------------- the user's answer at the terminal (D16, DR-46)
def test_a_terminal_reject_with_criterion_records_the_answer_so_define_service_answers_is_answered(svc, capsys):
    task = request(svc)
    deliver(svc, "ceo", task)
    cli(svc, "feedback", task.id, "reject", "--note", "Always add a summary.", "--criterion", "C1")
    out = capsys.readouterr().out
    verdict = [m for m in svc.sent(ROOT) if m.feedback][-1]
    (link,) = [m for m in svc.sent(ROOT) if m.reply_to == verdict.id and m.criterion]
    assert f"feedback reject on {task.id} -> ceo (message {verdict.id}, source human, about C1)" in out
    assert f"link on {verdict.id} -> ceo: C1 (message {link.id}, source human)" in out  # the terminal is the user's seat: --criterion is their answer
    with pytest.raises(SystemExit):
        cli(svc, "define-service", "ceo", "weekly-brief", "--add-acceptance", "Starts with a summary.", "--answers", verdict.id, "--about", "C1",
            "--words", "Yes, add it.")
    err = capsys.readouterr().err
    assert f"rejection R1 (message {verdict.id}) already has its answer (link note {link.id}): one rejection gets one answer." in err
    assert contract_meta(svc)[0]["version"] == 1


def test_a_terminal_reject_without_criterion_then_define_service_answers_records_the_answer(svc, capsys):
    task = request(svc)
    deliver(svc, "ceo", task)
    cli(svc, "feedback", task.id, "reject", "--note", "Always add a summary.")
    capsys.readouterr()
    verdict = [m for m in svc.sent(ROOT) if m.feedback][-1]
    assert not [m for m in svc.sent(ROOT) if m.reply_to == verdict.id and m.criterion]  # no link yet: the rejection waits for its answer
    cli(svc, "define-service", "ceo", "weekly-brief", "--add-acceptance", "Starts with a summary.", "--answers", verdict.id, "--about", "C1",
        "--words", "Yes, add it.")
    out = capsys.readouterr().out
    assert f"Recorded as the user's answer to R1 (rejection {verdict.id}; your question named C1): link " in out and "names C3." in out
    meta = contract_meta(svc)[0]
    assert (meta["version"], meta["answers"], meta["about"], meta["words"]) == (2, verdict.id, "C1", "Yes, add it.")
    (link,) = [m for m in svc.sent(ROOT) if m.reply_to == verdict.id and m.criterion]
    assert (link.criterion, link.source) == ("C3", "human")


def test_a_cli_rework_with_nothing_left_is_sent_with_one_run_and_prints_the_top_up(org, capsys):
    """D-E5-1 (4.5): ``ceo`` has two agents below (a round of the team is 5). The first request's team uses all but... none of the 10 runs come back,
    so a rework the user asks for at the terminal gets 1 run, and the next line asks for the 5 it needs, with the CLI form of the grant. D-E7-2 A1
    (14 Rule A1, item 7): that 1 run is beyond the user's approval, so the ask and the grant include it (5, was 4) and the line names it."""
    org.hire("ceo", "qa", "Tester", "Test things.")
    define(org)
    first = request(org)
    deliver(org, "ceo", first, runs=10)  # all 10 handed down used, none back
    capsys.readouterr()
    cli(org, "request", "weekly-brief", "--input", "topic=ai", "--revises", first.id)
    line, step = capsys.readouterr().out.splitlines()
    (rework,) = [m for m in org.sent(ROOT) if m.revises == first.id]
    assert line == f"request {rework.id} -> ceo (service weekly-brief, budget 1)" and rework.budget == 1 and rework.source == "human"
    assert step == (
        "This rework has 1 run(s), and a rework of this team needs about 5 (1, plus 2 for each agent below ceo). Nothing else was left of the runs the "
        "user approved for this case when this rework was sent: its own run is beyond them, and the ask includes it. Ask the user now for 5 more "
        "run(s), with that number; on yes, grant 5: send(to=\"ceo\", budget=5, body=<why>) (CLI: hirearchy send ceo \"<why>\" --budget 5)."
    )


def test_a_cli_rework_of_a_blocked_request_with_unspent_runs_prints_that_the_team_holds_them(org, capsys):
    """D-E6-2 (B2): the first request is blocked with 2 of its 10 runs used: the team holds 8, so the line after the request line is the HELD
    sentence and nothing is asked (0a.3 printed the top-up for 4 more runs). D-E7-2 A1 (14 Rule A1, item 12): the HELD sentence is followed by the one
    that names the default's run as beyond the user's approval (still one line)."""
    org.hire("ceo", "qa", "Tester", "Test things.")
    define(org)
    first = request(org)
    deliver(org, "ceo", first, status="blocked", runs=2)
    capsys.readouterr()
    cli(org, "request", "weekly-brief", "--input", "topic=ai", "--revises", first.id)
    line, step = capsys.readouterr().out.splitlines()
    (rework,) = [m for m in org.sent(ROOT) if m.revises == first.id]
    assert line == f"request {rework.id} -> ceo (service weekly-brief, budget 1)" and rework.budget == 1
    assert step == (
        f"The team still holds 8 of the user's runs for {first.id}; the rework can use them. Nothing else was left of the runs the user approved for "
        "this case when this rework was sent: its own run is beyond them, and the runs the team holds cover the round without it. Ask for nothing; "
        "tell the user that this 1 run is beyond their approval."
    )


def test_the_cli_prints_no_step_after_a_one_off_verdict(svc, capsys):
    """PC-5: the CLI prints the receipt line only, for a one-off verdict as for a service verdict; the next step is the MCP reply's."""
    plain = svc.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    deliver(svc, "ceo", plain)
    cli(svc, "feedback", plain.id, "reject", "--note", "Too long.")
    verdict = [m for m in svc.sent(ROOT) if m.feedback][-1]
    assert (verdict.reply_to, verdict.source, verdict.criterion) == (plain.id, "human", None)  # the CLI keeps --source human
    assert capsys.readouterr().out == f"feedback reject on {plain.id} -> ceo (message {verdict.id}, source human)\n"


def test_feedback_help_names_the_one_off_task(org, capsys):
    with pytest.raises(SystemExit):
        cli(org, "feedback", "--help")
    assert "task_id the service request, rework or one-off task the verdict is on" in " ".join(capsys.readouterr().out.split())


def test_hirearchy_request_meets_request_unanswered(svc, capsys):
    """Clause 2 (design 13.1): the CLI's new request waits for the user's answer to a rejection since the previous one; a rework does not."""
    first = request(svc)
    deliver(svc, "ceo", first)
    cli(svc, "feedback", first.id, "reject", "--note", "Too long.")
    verdict = [m for m in svc.sent(ROOT) if m.feedback][-1]
    capsys.readouterr()
    sent = len(svc.sent(ROOT))
    with pytest.raises(SystemExit):
        cli(svc, "request", "weekly-brief", "--input", "topic=next")
    err = capsys.readouterr().err
    assert f"rejection R1 (message {verdict.id}) on task {first.id} of `weekly-brief` has no recorded answer yet, so the next request of `weekly-brief` waits" in err
    assert "CLI: hirearchy define-service ... --answers, --about, --words" in err and len(svc.sent(ROOT)) == sent
    cli(svc, "request", "weekly-brief", "--input", "topic=ai", "--revises", first.id)  # a rework is not held
    assert len(svc.sent(ROOT)) == sent + 1


def test_cli_feedback_accept_is_human_by_default_and_waits_for_the_answer(svc, capsys):
    """Clause 2 (design 13.2): the CLI's accept defaults to ``--source human``, so it waits for the answer to an earlier rejection of its case."""
    first = request(svc)
    deliver(svc, "ceo", first)
    cli(svc, "feedback", first.id, "reject", "--note", "Too long.")
    verdict = [m for m in svc.sent(ROOT) if m.feedback][-1]
    capsys.readouterr()
    sent = len(svc.sent(ROOT))
    with pytest.raises(SystemExit):
        cli(svc, "feedback", first.id, "accept")
    err = capsys.readouterr().err
    assert f"rejection R1 (message {verdict.id}) on task {first.id} of this case of `weekly-brief` has no recorded answer yet, so the user's accept waits" in err
    assert "CLI: hirearchy feedback <task> reject --confirms ... --criterion ... --source human --note ..." in err and len(svc.sent(ROOT)) == sent
    cli(svc, "feedback", first.id, "reject", "--confirms", verdict.id, "--criterion", "none", "--note", "No: as it is.")  # the user's answer
    cli(svc, "feedback", first.id, "accept")
    assert [m.feedback for m in svc.sent(ROOT) if m.feedback][-1] == "accept"
