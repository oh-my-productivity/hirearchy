"""Extra regression tests for the core safety/lifecycle fixes (see QA_REPORT.md and test_qa_findings.py)."""

import pytest

from orgmcp.core import ROOT, OrgError

ENG = "ceo/eng"
CHARTER = "---\nrole: Engineer v2\n---\n# New charter\nDo more."


# ------------------------------------------------------------------- QA-1 / QA-2: write guard


@pytest.mark.parametrize(
    "path",
    [
        "ceo/AGENT.md.", "ceo/Agent.MD", "ceo/MEMORY.MD", "ceo/Memory.md", "ceo/INBOX/x.md", "ceo/Sent/x.md",
        "ceo/inflight/x.md", "ceo/Runs/x.log", "ceo/.PAUSED", "ceo/.Retired/x", "ceo/ORG.md.", "ceo/Org.md",
    ],
)
def test_protected_names_are_refused_in_any_spelling(org, path):
    with pytest.raises(OrgError):
        org.write("ceo", path, "x")


@pytest.mark.parametrize("path", ["ceo/ENG/AGENT.md", "ceo/Eng/MEMORY.md", "ceo/ENG/work/x.md", "ceo/eng/agent.md", "ceo/eng/Memory.md"])
def test_case_variants_of_a_direct_report_cannot_dodge_the_charter_only_rule(org, path):
    with pytest.raises(OrgError):
        org.write("ceo", path, CHARTER)
    assert org.charter(ENG)[0]["role"] == "Engineer"
    assert org.memory(ENG) == ""


def test_report_charter_authority_check_cannot_be_dodged_by_case(org):
    greedy = "---\nrole: Engineer\ntools: [shell]\n---\n# x"  # ceo has no tools, so it cannot grant any
    for path in ("ceo/eng/AGENT.md", "ceo/ENG/AGENT.md", "ceo/eng/agent.md"):
        with pytest.raises(OrgError):
            org.write("ceo", path, greedy)
    assert "tools" not in org.charter(ENG)[0] or not org.charter(ENG)[0]["tools"]


def test_memory_cap_cannot_be_dodged_by_case(org):
    big = "word " * (int(org.config["memory_max_words"]) + 10)
    for path in ("ceo/MEMORY.md", "ceo/memory.md", "ceo/Memory.md"):
        with pytest.raises(OrgError):
            org.write("ceo", path, big)
    assert org.memory("ceo") == ""
    org.write("ceo", "ceo/MEMORY.md", "short")  # the exact spelling still works
    assert org.memory("ceo") == "short"


def test_legitimate_writes_still_work(org):
    org.write("ceo", "ceo/work/notes.md", "n")
    org.write("ceo", "ceo/work/AnyCase/Notes.md", "n")  # case is only policed against protected/existing names
    org.write("ceo", "ceo/eng/AGENT.md", CHARTER)  # a parent edits its direct report's charter
    assert org.charter(ENG)[0]["role"] == "Engineer v2"
    org.write(ROOT, "ceo/AGENT.md", CHARTER)  # root edits a direct report's charter
    org.write(ROOT, "ORG.md", org.root.joinpath("ORG.md").read_text(encoding="utf-8"))


def test_writing_a_case_twin_of_an_existing_file_is_refused(org):
    org.write("ceo", "ceo/work/Plan.md", "a")
    with pytest.raises(OrgError, match="letter case"):
        org.write("ceo", "ceo/work/plan.md", "b")
    with pytest.raises(OrgError, match="letter case"):
        org.write("ceo", "ceo/WORK/x.md", "b")
    assert (org.dir("ceo") / "work" / "Plan.md").read_text() == "a"


def test_agent_md_cannot_create_an_agent_anywhere(org):
    charter = "---\nrole: sneaky\ncan_hire: true\nmax_children: 99\n---\n# x"
    for actor, path in (
        ("ceo", "ceo/new/AGENT.md"),
        ("ceo", "ceo/work/AGENT.md"),
        ("ceo", "ceo/new/deeper/AGENT.md"),  # would be addressable as ceo/new/deeper without a parent agent
        ("ceo", "ceo/eng/sub/AGENT.md"),
        ("ceo", "ceo/NEW/AGENT.md"),
        (ROOT, "newagent/AGENT.md"),
        (ROOT, "AGENT.md"),
    ):
        with pytest.raises(OrgError):
            org.write(actor, path, charter)
    assert org.agents() == ["ceo", ENG]
    assert not (org.dir("ceo") / "new").exists() and not (org.root / "newagent").exists()


def test_hire_is_the_way_to_create_agents(org):
    assert org.hire("ceo", "ops", "Ops", "Do ops.") == "ceo/ops"
    org.write("ceo", "ceo/ops/AGENT.md", CHARTER)  # and then the parent may edit the charter
    assert org.charter("ceo/ops")[0]["role"] == "Engineer v2"


# ------------------------------------------------------------------- QA-12: delivery order and recovery


def _fail_writes_into(monkeypatch, marker):
    from orgmcp import core

    real = core.atomic_write

    def flaky(path, text):
        if marker in str(path):
            raise OSError("disk full")
        return real(path, text)

    monkeypatch.setattr(core, "atomic_write", flaky)
    return lambda: monkeypatch.setattr(core, "atomic_write", real)


def test_sender_copy_is_written_before_the_recipient_copy(org, monkeypatch):
    order = []
    from orgmcp import core

    real = core.atomic_write
    monkeypatch.setattr(core, "atomic_write", lambda path, text: (order.append(path.parent.name), real(path, text))[1])
    org.send(ROOT, "ceo", "hi")
    assert order == ["sent", "inbox"]


def test_recipient_write_failure_is_repaired_by_recover_without_minting_or_losing_budget(org, monkeypatch):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    restore = _fail_writes_into(monkeypatch, "/ceo/eng/inbox/")
    with pytest.raises(OSError):
        org.send("ceo", ENG, "grant", budget=4)
    restore()
    # charged but undelivered: nothing minted, nothing visible to the recipient yet
    assert org.budget("ceo") == 6 and org.budget(ENG) == 0 and org.unread(ENG) == 0
    assert org.recover() == []  # no interrupted runs; the delivery is finished silently
    assert org.budget("ceo") == 6 and org.budget(ENG) == 4 and org.unread(ENG) == 1
    assert org.recover() == [] and org.unread(ENG) == 1  # idempotent
    assert len(list((org.dir(ENG) / "inbox").glob("*.md"))) == 1


def test_recover_redelivers_to_root_too(org, monkeypatch):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    restore = _fail_writes_into(monkeypatch, str(org.root / "inbox"))
    with pytest.raises(OSError):
        org.report("ceo", task.id, "done", "ok")
    restore()
    assert org.unread(ROOT) == 0
    org.recover()
    assert org.unread(ROOT) == 1


def test_recover_does_not_duplicate_handled_messages_or_resurrect_retired_agents(org):
    sent = org.send(ROOT, "ceo", "one")
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)  # now in read/
    note = org.send("ceo", ENG, "to a soon retired agent")
    org.retire("ceo", "eng", "bye")
    assert org.recover() == []
    assert org.unread("ceo") == 0 and not org.exists(ENG) and not (org.dir(ENG)).exists()
    assert [m.id for m in org.messages("ceo", "read")] == [sent.id]
    assert note.id  # the sent copy remains as the audit trail


def test_recover_still_returns_inflight_batches(org):
    org.send(ROOT, "ceo", "x")
    org.begin_run("ceo")
    assert org.recover() == ["ceo"] and org.unread("ceo") == 1
