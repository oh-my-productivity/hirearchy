# mypy: ignore-errors
"""No refusal of phase 0a.2 can be bypassed through another surface: the same text, and nothing written, whichever door is used.

Each test is parametrized over the surfaces that reach the rule (the MCP tool of the agent, the CLI, the ``Org`` facade; plan 7.3) and asserts the
refusal's whole text and that the files did not change. The file grows commit by commit, one test per refusal family."""

import pytest
from testkit.mcp_server_world import build_server
from testkit.services_world import call, confirmed_amendment, fails, playbook_meta, svc  # noqa: F401  (svc is a fixture)

from hirearchy.kernel import OrgError

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
