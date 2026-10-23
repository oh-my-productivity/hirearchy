# mypy: ignore-errors
"""No refusal of phase 0a.2 can be bypassed through another surface: the same text, and nothing written, whichever door is used.

Each test is parametrized over the surfaces that reach the rule (the MCP tool of the agent, the CLI, the ``Org`` facade; plan 7.3) and asserts the
refusal's whole text and that the files did not change. The file grows commit by commit, one test per refusal family."""

import pytest
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
        f"refused: rejection R1 (message {no.id}) already has its answer (link note {link.id}): one rejection gets one answer. A new lasting rule "
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
