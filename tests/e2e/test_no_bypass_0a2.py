# mypy: ignore-errors
"""No refusal of phase 0a.2 can be bypassed through another surface: the same text, and nothing written, whichever door is used.

Each test is parametrized over the surfaces that reach the rule (the MCP tool of the agent, the CLI, the ``Org`` facade; plan 7.3) and asserts the
refusal's whole text and that the files did not change. The file grows commit by commit, one test per refusal family."""

import pytest
import testkit
from testkit.mcp_server_world import build_server
from testkit.services_world import (  # noqa: F401  (svc is a fixture)
    call, cli, confirmed_amendment, contract_meta, deliver, fails, playbook_meta, request, svc, write_version,
)

from hirearchy.kernel import ROOT, OrgError

SERVICE = "weekly-brief"
STEPS = "## Steps\n1. Search.\n2. Write.\n3. Check every claim."
CRITERION = "Every claim names its source"


def revise(org, surface: str, content: str, evidence: list[str]) -> str:
    """The lead's ``revise_playbook`` on ``surface``; returns the reply, or the refusal text."""
    if surface == "mcp":
        return call(build_server(org, "ceo"), "revise_playbook", service=SERVICE, content=content, reason="why", evidence=evidence)
    return str(org.revise_playbook("ceo", SERVICE, content, "why", evidence))


def refused(org, surface: str, content: str, evidence: list[str]) -> str:
    """The refusal text of a ``revise_playbook`` that must be refused on ``surface`` (the CLI has no revise command)."""
    if surface == "mcp":
        return fails(build_server(org, "ceo"), "revise_playbook", service=SERVICE, content=content, reason="why", evidence=evidence)
    with pytest.raises(OrgError) as info:
        org.revise_playbook("ceo", SERVICE, content, "why", evidence)
    return str(info.value)


@pytest.mark.parametrize("surface", ["mcp", "org"])
def test_p1_refusal_on_every_surface(svc, surface):
    """P1-REFUSED: a line that is neither the cited criterion's own words nor tagged is refused with the same text on both doors, and the playbook
    stays at its version; the criterion's own words, as one line with its id, are admitted."""
    svc.revise_playbook("ceo", SERVICE, STEPS, "first draft", [])
    c3 = confirmed_amendment(svc, CRITERION)
    offending = "4. Cite each source while drafting."
    text = refused(svc, surface, STEPS + "\n" + offending, [c3])
    assert c3 == "C3" and (
        "refused: every line a revision adds or changes must rest on the evidence it cites, and 1 line(s) do not:\n"
        f'- "{offending}"\n'
        "Rule (c) admits only the cited confirmed criterion's own words, one line each with its id: these lines are not C3's words. "
        f'Write it as "- C3: {CRITERION}". '
        "A change of punctuation, spacing, list numbering or markdown alone needs nothing. Nothing was written: revise again without these "
        "lines, or send root (`send`) this question once: "
        f'"We would add to how we deliver {SERVICE}: {offending}. Is that what you want from now on? '
        'If yes, please add it to the contract as a criterion."'
    ) in text
    assert playbook_meta(svc)[0]["version"] == 1
    revise(svc, surface, STEPS + f"\n- C3: {CRITERION}", [c3])
    meta, body = playbook_meta(svc)
    assert meta["version"] == 2 and meta["admitted"] == "c" and body.rstrip().endswith(f"- C3: {CRITERION}")


# ------------------------------------------------------------------------------------------------------------ P2: the answer path (plan 7.3, commit 11)
SURFACES = ["mcp", "cli", "org"]
NOTE = "Sam's CI item says before Friday, so that has a date. And always start with a Summary."
YES = "Yes, add it."
RULE = "The memo starts with a Summary line"
A_ID = "20261018T100000000012-root-0004"


def rejection(org):
    """The user rejects a fresh delivery; returns (task, verdict)."""
    task = request(org)
    deliver(org, "ceo", task)
    return task, org.feedback(ROOT, task.id, "reject", NOTE, source="human")


def define_args(**kw) -> list[str]:
    """The terminal's form of the keywords of ``define_service``."""
    flags = {"add_acceptance": "--add-acceptance", "remove_acceptance": "--remove-acceptance", "answers": "--answers", "about": "--about", "words": "--words",
             "budget": "--budget", "acceptance": "--acceptance"}
    out: list[str] = []
    for key, value in kw.items():
        for item in value if isinstance(value, list) else [value]:
            out += [flags[key], str(item)]
    return out


def amend_on(org, surface: str, capsys, **kw) -> tuple[bool, str]:
    """root's ``define_service`` of ``weekly-brief`` on ``surface``: (refused, the reply or the refusal text)."""
    try:
        if surface == "mcp":
            return False, call(build_server(org, ROOT), "define_service", owner="ceo", name=SERVICE, **kw)
        if surface == "cli":
            capsys.readouterr()
            try:
                cli(org, "define-service", "ceo", SERVICE, *define_args(**kw))
            except SystemExit:
                return True, capsys.readouterr().err
            return False, capsys.readouterr().out
        return False, org.define_service(ROOT, "ceo", SERVICE, **kw)
    except Exception as error:  # noqa: BLE001  (an MCP tool error and an OrgError are both a refusal)
        return True, str(error)


def state(org) -> tuple:
    """What a refusal must leave as it was: the contract version, root's sent box and the owner's inbox."""
    return contract_meta(org)[0]["version"], len(org.sent(ROOT)), len(org.messages("ceo", "inbox"))


def refusal_cases(org, no):
    """name -> (keywords of the call, the whole refusal text)."""
    return {
        "not-an-amendment": (
            {"budget": 12, "words": YES},
            "refused: answers, about and words record the user's answer to a change of the acceptance criteria; this call changes none. Pass them only "
            "with acceptance, add_acceptance or remove_acceptance on an existing service (CLI: --acceptance, --add-acceptance, --remove-acceptance). "
            "Nothing was written.",
        ),
        "pair": (
            {"add_acceptance": [RULE], "answers": no.id, "words": YES},
            "refused: answers and about go together: answers=<the rejection's message id>, about=<the C or R id your question named> (CLI: --answers, "
            "--about). Nothing was written.",
        ),
        "words-long": (
            {"add_acceptance": [RULE], "words": "x" * 1001},
            "refused: words (CLI: --words) is 1001 characters; the limit is 1000: the user's answer, verbatim, not a summary. Nothing was written.",
        ),
        "not-a-rejection": (
            {"add_acceptance": [RULE], "answers": A_ID, "about": "C1", "words": YES},
            "refused: answers (CLI: --answers) must be the message id of a rejection you recorded with feedback(..., source=\"human\") (CLI: hirearchy "
            f"feedback <task id> reject --note ...) on a request of `weekly-brief`: {A_ID}. Its rejections: R1 (message {no.id}). Nothing was written.",
        ),
        "about": (
            {"add_acceptance": [RULE], "answers": no.id, "about": "C9", "words": YES},
            "refused: about (CLI: --about) must be the id your one question named: a criterion of contract v1, in force when R1 was recorded (C1, C2), "
            "or an earlier rejection (none): C9. A criterion this change creates cannot be what the question was about. Nothing was written.",
        ),
        "words-are-the-rejection": (
            {"add_acceptance": [RULE], "answers": no.id, "about": "C1", "words": "No, not right yet. " + NOTE},
            "refused: words (CLI: --words) repeats rejection R1's own note (or the note is part of it). The answer is what the user said to your one "
            "question after the rejection (e.g. \"Yes, add it.\"); an \"always ...\" inside the rejection is not it. Nothing was written.",
        ),
    }


@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("case", ["not-an-amendment", "pair", "words-long", "not-a-rejection", "about", "words-are-the-rejection"])
def test_p2_refusals_of_given_values_on_every_surface(svc, capsys, surface, case):
    """The refusals of the values root gives (answers, about, words) are the same text on MCP root, the CLI and the Org facade, and write nothing."""
    _, no = rejection(svc)
    kw, text = refusal_cases(svc, no)[case]
    before = state(svc)
    refused_it, got = amend_on(svc, surface, capsys, **kw)
    assert refused_it and text in got, got
    assert state(svc) == before


@pytest.mark.parametrize("surface", SURFACES)
def test_p2_answered_on_every_surface(svc, capsys, surface):
    """One rejection gets one answer, whichever door the second one comes through."""
    _, no = rejection(svc)
    svc.define_service(ROOT, "ceo", SERVICE, add_acceptance=[RULE], answers=no.id, about="C1", words=YES)
    (link,) = [m for m in svc.sent(ROOT) if m.reply_to == no.id and m.criterion]
    before = state(svc)
    refused_it, got = amend_on(svc, surface, capsys, add_acceptance=["Names its week"], answers=no.id, about="C1", words="Yes, that too.")
    assert refused_it and (
        f"refused: rejection R1 (message {no.id}) already has its answer (contract v2): one rejection gets one answer. A new lasting rule "
        "needs a new rejection and its question, or words alone (CLI: --words) when the user asks for it on their own. Nothing was written."
    ) in got, got
    assert state(svc) == before


@pytest.mark.parametrize("surface", ["mcp", "org"])
def test_p2_root_only_and_the_agent_schema(svc, surface):
    """answers, about and words are root's: an agent client is refused on the facade, and the agents' MCP tool has no such argument (the terminal
    always acts as root, so the command line has no agent door to close)."""
    svc.define_service("ceo", "ceo/eng", "inner", description="d", acceptance=["Short"], deliverable={"description": "f"}, budget=2)
    if surface == "org":
        with pytest.raises(OrgError) as info:
            svc.define_service("ceo", "ceo/eng", "inner", add_acceptance=["Brief"], answers=A_ID, about="C1", words=YES)
        assert str(info.value) == (
            "refused: answers, about and words are root's: they record the human client's answer. An agent client amends its report's contract without "
            "them. Nothing was written."
        )
        return
    import asyncio

    def properties(who: str) -> set[str]:
        return set({t.name: t for t in asyncio.run(build_server(svc, who).list_tools())}["define_service"].inputSchema["properties"])

    assert not {"answers", "about", "words"} & properties("ceo")
    assert {"answers", "about", "words"} <= properties(ROOT)


@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("kind", ["answered", "recovery"])
def test_confirms_after_an_answer_on_every_surface(svc, capsys, surface, kind):
    """After define_service answered a rejection, a `confirms` on it is refused with the same text on MCP root, the CLI and the Org facade."""
    task, no = rejection(svc)
    if kind == "answered":
        svc.define_service(ROOT, "ceo", SERVICE, add_acceptance=[RULE], answers=no.id, about="C1", words=YES)
        (link,) = [m for m in svc.sent(ROOT) if m.reply_to == no.id and m.criterion]
        text = (
            f"refused: rejection {no.id} was answered by contract v2 of `weekly-brief` (define_service(..., answers=\"{no.id}\"); CLI: define-service "
            f"--answers) and its link {link.id} records the user's yes: one rejection gets one answer. A different answer needs a new rejection and its "
            "question. Nothing was recorded."
        )
        ids = ["C3"]
    else:
        write_version(svc, 2, [*svc.runtime.service_catalog.read_contract("ceo", SERVICE).acceptance, RULE], answers=no.id, about="C1", words=YES)
        text = (
            f"refused: rejection {no.id} was answered by contract v2 of `weekly-brief`, and its link is missing (its write failed). The only link it "
            f'still takes is that one: feedback(task_id="{task.id}", verdict="reject", confirms="{no.id}", criterion=["C3"], source="human", '
            "note=<the user's answer, verbatim>) (CLI: --confirms, --criterion, --source human, --note). Nothing was recorded."
        )
        ids = ["none"]  # not the link the contract's version names
    before = state(svc)
    if surface == "mcp":
        got = fails(build_server(svc, ROOT), "feedback", task_id=task.id, verdict="reject", note="Also.", source="human", criterion=ids, confirms=no.id)
    elif surface == "cli":
        capsys.readouterr()
        with pytest.raises(SystemExit):
            cli(svc, "feedback", task.id, "reject", "--note", "Also.", "--source", "human", "--confirms", no.id, *[x for i in ids for x in ("--criterion", i)])
        got = capsys.readouterr().err
    else:
        with pytest.raises(OrgError) as info:
            svc.feedback(ROOT, task.id, "reject", "Also.", source="human", criterion=ids, confirms=no.id)
        got = str(info.value)
    assert text in got, got
    assert state(svc) == before


# ------------------------------------------------------------------------------------------------------------ P2: the gate (plan 7.3, commit 14)
@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("case", ["unrated", "needs-words", "open-rejection"])
def test_p2_gate_refusals_on_every_surface(svc, capsys, surface, case):
    """P2-UNRATED, P2-NEEDS-WORDS and P2-OPEN-REJECTION: a change of the criteria by root is refused with the same text on MCP root, the CLI and
    the Org facade, and nothing is written."""
    if case == "unrated":
        task = request(svc)
        deliver(svc, "ceo", task)
        kw = {"add_acceptance": [RULE], "words": YES}
        text = (
            f"refused: 1 delivered request(s) of `weekly-brief` have no verdict yet: {task.id}. Record a verdict on each with feedback first: "
            "on a delivery the user saw, the user's own, a rejection then its one question (CLI: hirearchy feedback <task id> accept|reject --note ...); "
            'on a relayed rework the user never saw, your own, with source="relayed" (CLI: --source relayed), settles it. The contract changes only '
            "after the verdicts. Nothing was written."
        )
    elif case == "needs-words":
        kw = {"add_acceptance": [RULE]}
        text = (
            "refused: a change of the acceptance criteria of `weekly-brief` records the user's words. If it answers a rejection, pass "
            "answers=<the rejection's message id>, about=<the C or R id your one question named> and words=<the user's answer, verbatim> "
            "(CLI: --answers, --about, --words), after they answered yes to that question. If the user asked for this change on their own, outside "
            "any rejection, pass words=<their request, verbatim> alone (CLI: --words): it is recorded as user-initiated and never admits a playbook "
            "revision. Nothing was written."
        )
    else:
        task, no = rejection(svc)
        kw = {"add_acceptance": [RULE], "words": YES}
        text = (
            f"refused: rejection R1 (message {no.id}) on task {task.id} has no answer yet, so this change is not one the user asked for on their own. "
            'Ask the user the one question first (About <its id>: add "<the rule, in their words>" as a lasting rule? Yes or no.). '
            f'On yes: define_service(owner="ceo", name="weekly-brief", ..., answers="{no.id}", about=<the id you asked about>, words=<their answer, '
            'verbatim>) (CLI: --answers, --about, --words). On no, a one-off or "as it is": '
            f'feedback(task_id="{task.id}", verdict="reject", confirms="{no.id}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", '
            "note=<their answer, verbatim>) (CLI: --confirms, --criterion, --source human, --note). Nothing was written."
        )
    before = state(svc)
    refused_it, got = amend_on(svc, surface, capsys, **kw)
    assert refused_it and text in got, got
    assert state(svc) == before


# ------------------------------------------------------------------------------------------------------------ P2: retire_service (plan 7.3, commit 17)
def retire_on(org, surface: str, capsys) -> tuple[bool, str]:
    """root's ``retire_service`` of ``weekly-brief`` on ``surface`` (the CLI or the Org facade): (refused, the reply or the refusal text)."""
    try:
        if surface == "cli":
            capsys.readouterr()
            try:
                cli(org, "retire-service", "ceo", SERVICE, "--reason", "not needed")
            except SystemExit:
                return True, capsys.readouterr().err
            return False, capsys.readouterr().out
        return False, org.retire_service(ROOT, "ceo", SERVICE, "not needed")
    except Exception as error:  # noqa: BLE001  (a refusal)
        return True, str(error)


@pytest.mark.parametrize("surface", ["cli", "org"])
@pytest.mark.parametrize("case", ["unrated", "open"])
def test_retire_service_gate_on_every_surface(svc, capsys, surface, case):
    """P2-RETIRE-UNRATED and P2-RETIRE-OPEN: the same text from the CLI ``retire-service`` and the Org facade, and the service stays where it is,
    with nobody told. The two doors are all there are: root's MCP surface has no tool that retires a service (pinned below)."""
    if case == "unrated":
        task = request(svc)
        deliver(svc, "ceo", task)
        text = (
            f"refused: 1 delivered request(s) of `weekly-brief` have no verdict yet: {task.id}. Record the user's verdict on each with feedback "
            "first (CLI: hirearchy feedback <task id> accept|reject --note ...); a service is retired only after its verdicts, so that its record "
            "stays complete. Nothing was retired."
        )
    else:
        task, no = rejection(svc)
        text = (
            f"refused: rejection R1 (message {no.id}) on task {task.id} of `weekly-brief` has no answer yet. Ask the user the one question first "
            '(About <its id>: add "<the rule, in their words>" as a lasting rule? Yes or no.) and record the answer: '
            f'define_service(..., answers="{no.id}", about=<the id you asked about>, words=<their answer, verbatim>) on yes '
            "(CLI: --answers, --about, --words), "
            f'feedback(task_id="{task.id}", verdict="reject", confirms="{no.id}", criterion=["none"], ["R<j>"] or ["C<k>"], source="human", '
            "note=<their answer, verbatim>) otherwise (CLI: --confirms, --criterion, --source human, --note). A service is retired only after its "
            "rejections are answered. Nothing was retired."
        )
    before = state(svc)
    refused_it, got = retire_on(svc, surface, capsys)
    assert refused_it and text in got, got
    assert state(svc) == before and svc.service_names("ceo") == [SERVICE]
    if case == "unrated":
        svc.feedback(ROOT, task.id, "accept", "fine", source="human")
    else:
        svc.feedback(ROOT, task.id, "reject", "A one-off.", source="human", criterion=["none"], confirms=no.id)
    refused_it, got = retire_on(svc, surface, capsys)
    assert not refused_it and "retired service `weekly-brief` of ceo" in got, got
    assert svc.service_names("ceo") == []


def test_no_mcp_tool_retires_a_service(svc):
    """The retirement of a service has two doors, the CLI and the Org facade (above). If an MCP tool ever offers it, it reaches the same rule class
    and this test must grow that surface."""
    import asyncio

    names = {t.name for t in asyncio.run(build_server(svc, ROOT).list_tools())}
    assert "retire_service" not in names and "retire" in names


# ------------------------------------------------------------------------------------------------------------ P2: the continuation (plan 7.3, commit 18)
def restructure_on(org, surface: str) -> str:
    """root retires ceo's team and hires ceo again on ``surface``; returns the reply of the retirement. No terminal command retires a team, so the
    CLI leg retires through the facade and hires at the terminal."""
    if surface == "mcp":
        server = build_server(org, ROOT)
        said = call(server, "retire", name="ceo", reason="restructure")
        call(server, "hire", name="ceo", role="Chief executive", charter="Run the company.", can_hire=True, max_children=2)
        return said
    org.retire_team(ROOT, "ceo", "restructure")
    if surface == "cli":
        cli(org, "hire", "root", "ceo", "--role", "Chief executive", "--charter", "Run the company.", "--can-hire", "--max-children", "2")
    else:
        org.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    return ""


def service_files(org) -> dict:
    """The files of the services below the organization, with their bytes (what a refusal must leave as it was)."""
    return {str(p.relative_to(org.root)): p.read_bytes() for p in org.root.glob("**/services/**/*.md")}


CONTINUES_TEXT = (
    "refused: `weekly-brief` of ceo continues the retired service kept at {path} (1 request(s) with a result), so defining it again keeps its "
    "contract v1, its playbook (none yet) and its record. Leave out {what} and define it again; then change the criteria as an amendment, the "
    "user's answer to a rejection (answers=, about=, words=) or a change they asked for on their own (words= alone) (CLI: --answers, --about, "
    "--words). Nothing was written."
)
CRITERIA = (
    "the change of the criteria: give no acceptance, add_acceptance or remove_acceptance, or acceptance exactly as in v1 "
    "(CLI: --acceptance, --add-acceptance, --remove-acceptance)"
)


@pytest.mark.parametrize("surface", SURFACES)
def test_retire_team_hire_and_define_continues_on_every_surface(svc, capsys, surface):
    """P2-CONTINUES: after the owner and its team were retired and hired again, defining the service with other criteria is refused with the same
    text on MCP root, the CLI and the Org facade, and nothing is written; with its criteria the definition continues the record, and the amendment
    that follows meets the gate with the whole rejection."""
    import re

    task, no = rejection(svc)
    said = restructure_on(svc, surface)
    if surface == "mcp":  # root's retire names what the service keeps and what is open in it (design 5.10)
        assert said.startswith("retired ceo\nKept with ceo: weekly-brief. Defining one of them again for ceo continues its contract, playbook and cases")
        assert f"Still open in `weekly-brief`: rejection R1 (message {no.id}) has no answer. Tell the user." in said, said
    before = service_files(svc)
    refused_it, got = amend_on(svc, surface, capsys, acceptance=["A different criterion"])
    path = re.search(r"kept at (\S+) \(", got).group(1)
    assert re.fullmatch(r"\.retired/ceo-\d{8}T\d{6}/services/weekly-brief", path)
    assert refused_it and CONTINUES_TEXT.format(path=path, what=CRITERIA) in got, got
    assert service_files(svc) == before and svc.service_names("ceo") == []
    refused_it, got = amend_on(svc, surface, capsys, budget=10)  # (the CLI cannot say "no field": the budget it already has)
    assert not refused_it and f"it continues the retired one kept at {path} (contract v1 -> v2, no playbook yet, 1 request(s) with a result" in got, got
    assert f"Still open: rejection R1 (message {no.id}) has no answer." in got and contract_meta(svc)[0]["version"] == 2
    refused_it, got = amend_on(svc, surface, capsys, add_acceptance=[RULE], words=YES)
    assert refused_it and f"rejection R1 (message {no.id}) on task {task.id} has no answer yet" in got, got


@pytest.mark.parametrize("surface", ["mcp", "cli"])
def test_apply_of_a_continued_name_is_refused(svc, capsys, surface, tmp_path):
    """A blueprint always carries a playbook for its services, so applying one that defines the name of a retired service with a record is refused
    with P2-CONTINUES (the playbook) through MCP ``apply_org`` and the CLI ``apply``; the agents it hired are retired again."""
    import re
    import time

    import yaml

    rejection(svc)
    svc.retire_team(ROOT, "ceo", "restructure")
    time.sleep(1.1)  # a retired tree is named after the second it was retired in
    plan = yaml.safe_load((testkit.REPO / "examples" / "blueprint-service.yaml").read_text())
    plan["agents"][0]["name"] = "ceo"
    service = plan["services"][0]
    service["owner"] = "ceo"
    service["deliverable"]["path"] = str(tmp_path / "briefs")
    del plan["task"]
    text = yaml.safe_dump(plan, sort_keys=False)
    server = build_server(svc, ROOT)
    if surface == "mcp":
        pid = re.search(r"^plan_id: (\w+)$", call(server, "propose_org", blueprint=text), re.M).group(1)
        got = fails(server, "apply_org", blueprint=text, approved=True, plan_id=pid)
    else:
        file = tmp_path / "blueprint.yaml"
        file.write_text(text)
        capsys.readouterr()
        with pytest.raises(SystemExit):
            cli(svc, "apply", str(file))
        got = capsys.readouterr().err
    assert "refused: `weekly-brief` of ceo continues the retired service kept at .retired/ceo-" in got, got
    assert "Leave out playbook (CLI: --playbook) and the change of the criteria: give no acceptance" in got  # (the blueprint's criteria are not v1's either)
    assert svc.agents() == [] and svc.service_names("ceo") == []  # what the apply hired was retired again


# ------------------------------------------------------------------------------------------------------------ P4: a human rework names its base (plan 7.3, commit 27)
MEMO = "ceo/work/memo.md"


def memo(org, task, text: str):
    """The lead writes the memo and reports it as the artifact of ``task``."""
    path = org.dir("ceo") / "work" / "memo.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    org.begin_run("ceo")
    msg = org.report("ceo", task.id, "done", "Delivered.", artifacts=[str(path)], lessons="Worked.")
    org.end_run("ceo", ok=True)
    return msg


def after_relayed_change(org):
    """The user rejects the first delivery; root's own (relayed) rework changes the memo. Returns (the request, its judged result, the relayed rework)."""
    first = request(org)
    result = memo(org, first, "| Marta | 2026-10-14 |\n")
    org.feedback(ROOT, first.id, "reject", "Marta's date is wrong.", source="human")
    again = request(org, revises=first.id)
    memo(org, again, "| Marta | none |\n")
    return first, result, again


def ask_on(org, surface: str, capsys, *, revises=None, source=None, base=None) -> tuple[bool, str]:
    """root's ``request`` of ``weekly-brief`` on ``surface``: (refused, the reply or the refusal text)."""
    fields = {k: v for k, v in dict(revises=revises, source=source, base=base).items() if v is not None}
    try:
        if surface == "mcp":
            return False, call(build_server(org, ROOT), "request", service=SERVICE, inputs={"topic": "ai"}, **fields)
        if surface == "cli":
            args = ["request", SERVICE, "--input", "topic=ai"]
            for key, value in fields.items():
                args += [f"--{key}", value]
            capsys.readouterr()
            try:
                cli(org, *args)
            except SystemExit as stop:
                return True, capsys.readouterr().err + ("" if stop.code in (None, 0, 1) else f"(exit {stop.code})")
            return False, capsys.readouterr().out
        return False, org.request(ROOT, SERVICE, {"topic": "ai"}, **fields).id
    except Exception as error:  # noqa: BLE001  (an MCP tool error and an OrgError are both a refusal)
        return True, str(error)


@pytest.mark.parametrize("surface", SURFACES)
def test_p4_refusals_on_every_surface(svc, capsys, surface):
    """P4-NEEDS-BASE and P4-BASE-WHERE are refused with the same text on the MCP tool, the CLI and the facade; P4-BASE-VALUE on the MCP tool and the
    facade (the CLI's choices refuse a bad value first, exit 2). Nothing is sent by any of them; a named base is admitted."""
    first, result, again = after_relayed_change(svc)
    sent, inbox = len(svc.sent(ROOT)), len(svc.messages("ceo", "inbox"))
    needs = (
        f"refused: since the delivery the client judged (task {first.id}, result {result.id}), relayed rework {again.id} (your own reading, not the "
        f"client's) changed {MEMO}. Say which version the user's corrections apply to: base=\"delivered\" (the lead restores the version they "
        "judged, then applies their corrections) or base=\"latest\" (the relayed changes stay; tell the user) (CLI: --base delivered or --base latest). "
        "Nothing was sent."
    )
    where = (
        'refused: base goes only with a rework the user asked for: revises=<an earlier request of this service>, source="human" '
        "(CLI: --revises <task id> --source human). Nothing was sent."
    )
    refused_, text = ask_on(svc, surface, capsys, revises=first.id, source="human")
    assert refused_ and needs in text
    refused_, text = ask_on(svc, surface, capsys, revises=first.id, source="relayed", base="delivered")
    assert refused_ and where in text
    refused_, text = ask_on(svc, surface, capsys, base="latest")
    assert refused_ and where in text
    refused_, text = ask_on(svc, surface, capsys, revises=first.id, source="human", base="both")
    if surface == "cli":
        assert refused_ and "invalid choice: 'both'" in text and "(exit 2)" in text
    else:
        assert refused_ and 'refused: base must be "delivered" or "latest": both. Nothing was sent.' in text
    assert (len(svc.sent(ROOT)), len(svc.messages("ceo", "inbox"))) == (sent, inbox)
    refused_, text = ask_on(svc, surface, capsys, revises=first.id, source="human", base="delivered")
    assert not refused_ and len(svc.sent(ROOT)) == sent + 1


# ------------------------------------------------------------------------------------------------------------ P4: root reworks a service request with request only (plan 7.3, commit 28)
def use_request(first_id: str) -> str:
    return (
        f"refused: {first_id} is a request for the service `{SERVICE}`: send it back with request(service=\"{SERVICE}\", inputs=..., "
        f"revises=\"{first_id}\", source=...) (CLI: hirearchy request {SERVICE} --revises {first_id}) so the rework stays in its case under the contract "
        "(and names its base when a relayed rework changed the delivery). Nothing was sent."
    )


def delegate_on(org, surface: str, capsys, first_id: str) -> tuple[bool, str]:
    """root's ``delegate`` (the CLI's ``task``) sending ``first_id`` back to ``ceo``: (refused, the reply or the refusal text)."""
    fields = dict(title="Again", goal="Fix the date.", acceptance="the date is right")
    try:
        if surface == "mcp":
            return False, call(build_server(org, ROOT), "delegate", to="ceo", revises=first_id, source="human", **fields)
        if surface == "cli":
            capsys.readouterr()
            try:
                cli(org, "task", "ceo", "--title", fields["title"], "--goal", fields["goal"], "--acceptance", fields["acceptance"], "--revises", first_id)
            except SystemExit:
                return True, capsys.readouterr().err
            return False, capsys.readouterr().out
        return False, org.delegate(ROOT, "ceo", fields["title"], fields["goal"], fields["acceptance"], revises=first_id, source="human").id
    except Exception as error:  # noqa: BLE001
        return True, str(error)


@pytest.mark.parametrize("surface", SURFACES)
def test_p4_use_request_on_every_surface(svc, capsys, surface):
    """P4-USE-REQUEST: root sends a service request back with ``request``; ``delegate`` (the CLI's ``task``) with ``revises`` on one is refused with the
    same text on the MCP tool, the CLI and the facade, and nothing is sent. A rework of a task that is not a request still goes."""
    first = request(svc)
    deliver(svc, "ceo", first)
    plain = svc.delegate(ROOT, "ceo", "Other", "g", "c", budget=2)
    sent = len(svc.sent(ROOT))
    refused_, text = delegate_on(svc, surface, capsys, first.id)
    assert refused_ and use_request(first.id) in text and len(svc.sent(ROOT)) == sent
    refused_, text = delegate_on(svc, surface, capsys, plain.id)
    assert not refused_ and len(svc.sent(ROOT)) == sent + 1


SERVICE_OR_REWORK = (
    "refused: a root task for a service, or a rework, goes through request(...) or delegate(...), which apply the case rules (the contract, the "
    "base, the verdicts). Nothing was sent."
)


def test_org_send_refuses_a_root_service_task_or_rework(svc):
    """FACADE-ROOT-TASK: the facade's free-form ``send`` cannot send root's service task or rework (MCP and the CLI have no such argument: pinned in
    ``tests/architecture/test_policy_free_primitives.py``). Root's other messages, and an agent's, go as before."""
    first = request(svc)
    deliver(svc, "ceo", first)
    sent = len(svc.sent(ROOT))
    for fields in ({"service": SERVICE}, {"revises": first.id}, {"revises": first.id, "source": "human", "service": SERVICE}):
        with pytest.raises(OrgError) as refusal:
            svc.send(ROOT, "ceo", "again", type="task", **fields)
        assert str(refusal.value) == SERVICE_OR_REWORK
    assert len(svc.sent(ROOT)) == sent
    assert svc.send(ROOT, "ceo", "one-off work", type="task", budget=1).type == "task" and svc.send(ROOT, "ceo", "a note").type == "note"


VERDICT_OR_LINK = (
    "refused: a verdict or a link from root goes through feedback(...), which applies the rules of a case (a delivered request, one answer per "
    "rejection). Nothing was sent."
)


def test_org_send_refuses_a_root_verdict_or_link(svc):
    """FACADE-ROOT-VERDICT: the facade's free-form ``send`` cannot write a verdict note or a link note for root (``feedback`` can: it applies the rules of a
    case). A refusal sends nothing; root's other notes, and the verdict ``feedback`` writes, are unchanged."""
    first = request(svc)
    deliver(svc, "ceo", first)
    sent = len(svc.sent(ROOT))
    for fields in ({"feedback": "reject"}, {"feedback": "accept", "source": "human"}, {"criterion": "C1"}, {"feedback": "reject", "criterion": "C1"}):
        with pytest.raises(OrgError) as refusal:
            svc.send(ROOT, "ceo", "words", reply_to=first.id, **fields)
        assert str(refusal.value) == VERDICT_OR_LINK
    assert len(svc.sent(ROOT)) == sent
    verdict = svc.feedback(ROOT, first.id, "reject", "No.", source="human")  # the rules of a case write the same note
    assert verdict.feedback == "reject" and len(svc.sent(ROOT)) == sent + 1
    assert svc.send(ROOT, "ceo", "a note").type == "note"
