"""CHARTER-PLAN and CHARTER-ADDED: an agent's charter rewrite keeps the plan's frontmatter and the lines the user approved (design 6.6, review 2's L20;
owner question Q10 for the first).

For a writer that is not root, the merged frontmatter of a report's charter must equal the old one except ``role``, and ``max_children`` at or below its old
value; any other key added, changed or emptied is refused, the bookkeeping keys (``kind``, ``approved_in``, ``onboard``, ``hired_by``, ``created``) included.
The refusal runs after the authority, grant and model-floor checks, so those keep their texts, and before anything is written. An append never changes the
frontmatter. Root is not held by it at the writer (root's MCP refusal is ``mcp_server``'s). CHARTER-ADDED: the lines under ``## Added by your changes`` of the
text that would be written equal the current ones (a lead cannot take out, reword or add one). Runs over both implementations."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import JsonObject, join_frontmatter, split_frontmatter
from hirearchy.orgfiles import OrgFileWriter
from hirearchy.orgfiles.testing import IMPLEMENTATIONS, OrgFilesHarness

from ._support import make, refusal, written

REPORT = "lead/rev"
SUB = "lead/sub"


def plan_refusal(key: str, addr: str = REPORT) -> str:
    return (
        f'refused: {key} of {addr} is the plan\'s, which the user approved; a change goes through the user (propose_org(..., extend="current"), or the '
        'terminal). A charter edit may change its body (outside "## Added by your changes"), its role, and lower max_children. Nothing was written.'
    )


@pytest.fixture(params=IMPLEMENTATIONS[OrgFileWriter], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> OrgFilesHarness:
    """root -> lead (a manager with read, shell, a workspace and inputs) -> rev (a worker: read, a model, inputs, the bookkeeping keys) and sub (a lead)."""
    made = make(request, tmp_path)
    notes = str(made.outside / "notes")
    made.add_agent(
        "lead", {"role": "Lead", "tools": ["read", "shell"], "inputs": [notes], "workspace": str(made.outside / "ws"), "can_hire": True, "max_children": 5},
    )
    made.add_agent(
        REPORT,
        {"role": "Reviewer", "tools": ["read"], "model": "m-1", "inputs": [notes], "can_hire": False, "max_children": 3, "kind": "worker",
         "approved_in": "plan p1", "onboard": "no", "hired_by": "lead", "created": "2026-01-01"},
    )
    made.add_agent(SUB, {"role": "Sub-lead", "tools": ["read"], "inputs": [], "can_hire": True, "max_children": 2, "hired_by": "lead", "created": "2026-01-01"})
    return made


def text(role: str = "Reviewer", body: str = "New body.", /, **extra: object) -> str:
    meta: JsonObject = {"role": role, **extra}
    return join_frontmatter(meta, body)


def charter(h: OrgFilesHarness, addr: str = REPORT) -> JsonObject:
    return split_frontmatter(written(h, *addr.split("/"), "AGENT.md") or "")[0]


def raw(h: OrgFilesHarness, addr: str = REPORT) -> str:
    return written(h, *addr.split("/"), "AGENT.md") or ""


def test_a_lead_cannot_raise_a_reports_max_children_or_grant_can_hire_by_rewrite(h: OrgFilesHarness) -> None:
    before = raw(h)
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", text(max_children=4))) == plan_refusal("max_children")
    grant = refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", text(can_hire=True)))
    assert "you cannot grant `can_hire: true`" in grant  # (the grant check runs first and keeps its text)
    assert raw(h) == before


@pytest.mark.parametrize(
    "key, value",
    [
        pytest.param("tools", ["read", "shell"], id="tools"),
        pytest.param("model", "claude-opus-5.5", id="model"),
        pytest.param("inputs", [], id="inputs"),
        pytest.param("workspace", "WS", id="workspace"),
        pytest.param("kind", "verifier", id="kind"),
        pytest.param("approved_in", "plan other", id="approved_in"),
        pytest.param("onboard", "yes", id="onboard"),
        pytest.param("hired_by", "someone", id="hired_by"),
        pytest.param("created", "2027-02-02", id="created"),
        pytest.param("pet", "an unknown key added", id="an_unknown_key_added"),
        pytest.param("hired_by", "", id="a_key_emptied"),  # set explicitly, so the merge keeps nothing of the old value
    ],
)
def test_every_key_but_role_and_a_lower_max_children_is_refused(h: OrgFilesHarness, key: str, value: object) -> None:
    value = str(h.outside / "ws") if value == "WS" else value
    before = raw(h)
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", text(**{key: value}))) == plan_refusal(key)
    assert raw(h) == before


def test_can_hire_taken_away_is_refused_too(h: OrgFilesHarness) -> None:
    before = raw(h, SUB)
    assert refusal(lambda: h.writer.write("lead", f"{SUB}/AGENT.md", text("Sub-lead", can_hire=False))) == plan_refusal("can_hire", SUB)
    assert raw(h, SUB) == before


def test_role_a_lower_max_children_and_the_body_pass(h: OrgFilesHarness) -> None:
    h.writer.write("lead", f"{REPORT}/AGENT.md", text("Sharper reviewer", "A new body.", max_children=2))
    after = charter(h)
    assert after["role"] == "Sharper reviewer" and after["max_children"] == 2
    assert {k: v for k, v in after.items() if k not in ("role", "max_children")} == {k: v for k, v in charter_before(h).items() if k not in ("role", "max_children")}
    assert split_frontmatter(raw(h))[1] == "A new body.\n"
    h.writer.write("lead", f"{REPORT}/AGENT.md", text("Sharper reviewer", "Only the body.", max_children=2))  # the same limit is not a change
    h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: Sharper reviewer\n---\nA body without keys: all kept.\n")
    assert charter(h)["max_children"] == 2 and charter(h)["model"] == "m-1"


def charter_before(h: OrgFilesHarness) -> JsonObject:
    """The keys the fixture gave the report (the bookkeeping ones included)."""
    return {
        "role": "Reviewer", "tools": ["read"], "model": "m-1", "inputs": [str(h.outside / "notes")], "can_hire": False, "max_children": 3, "kind": "worker",
        "approved_in": "plan p1", "onboard": "no", "hired_by": "lead", "created": "2026-01-01",
    }


def test_an_append_passes(h: OrgFilesHarness) -> None:
    """GREEN when written: an append never changes the frontmatter (today's rule), whatever the appended chunk says."""
    old = raw(h)
    chunk = "---\nrole: More\n---\nOne more thing to keep in mind.\n"
    h.writer.write("lead", f"{REPORT}/AGENT.md", chunk, append=True)
    assert raw(h) == old + chunk
    h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: X\ntools: [shell]\n---\nan append that looks like a rewrite", append=True)
    assert charter(h) == split_frontmatter(old)[0]  # (the old frontmatter is the file's)


def test_the_refusal_names_the_first_differing_key_in_sorted_order(h: OrgFilesHarness) -> None:
    changed = text(tools=["read", "shell"], model="claude-opus-5.5", inputs=[], onboard="yes")
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", changed)) == plan_refusal("inputs")
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", text("Other", model="claude-opus-5.5", onboard="yes"))) == plan_refusal("model")


def test_root_is_not_held_by_it_at_the_writer(h: OrgFilesHarness) -> None:
    """GREEN when written: the writer admits root (its MCP write of a charter is refused by ``mcp_server``, and the human edits by hand)."""
    h.writer.write("root", "lead/AGENT.md", text("Lead", tools=["read"], model="claude-opus-5.5", max_children=9, onboard="yes", can_hire=False))
    after = charter(h, "lead")
    assert after["tools"] == ["read"] and after["model"] == "claude-opus-5.5" and after["max_children"] == 9 and after["onboard"] == "yes"
    assert after["can_hire"] is False


# ------------------------------------------------------------------------------ CHARTER-ADDED

CHARTER_ADDED = (
    'refused: the lines under "## Added by your changes" are the user\'s (approved in a plan); keep them exactly as they are, and put your own text under '
    "another heading. Nothing was written."
)
LINES = "- Ada (Checker) was added to your team to check weekly-brief: it checks every claim. [change p1]\n- Your hiring limits were set by the user's change: up to 0 direct reports; may hire: no. [change p1]"


def with_section(h: OrgFilesHarness, body: str) -> None:
    """The report's charter holds ``body`` (the user's extension wrote the section; the file is put behind the writer)."""
    h.put(h.root / "lead" / "rev" / "AGENT.md", join_frontmatter(charter(h), body))


def section_body(before: str = "# Role\n\nReview.\n\n", after: str = "") -> str:
    return f"{before}## Added by your changes\n{LINES}\n{after}"


def test_deleting_a_line_under_added_by_your_changes_is_charter_added(h: OrgFilesHarness) -> None:
    with_section(h, section_body())
    before = raw(h)
    only_one = "---\nrole: Reviewer\n---\n# Role\n\nReview.\n\n## Added by your changes\n" + LINES.splitlines()[0] + "\n"
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", only_one)) == CHARTER_ADDED
    none = "---\nrole: Reviewer\n---\n# Role\n\nReview.\n"
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", none)) == CHARTER_ADDED
    assert raw(h) == before


def test_rewording_one_is_charter_added(h: OrgFilesHarness) -> None:
    with_section(h, section_body())
    before = raw(h)
    reworded = "---\nrole: Reviewer\n---\n# Role\n\nReview.\n\n## Added by your changes\n" + LINES.replace("every claim", "every other claim") + "\n"
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", reworded)) == CHARTER_ADDED
    assert raw(h) == before


def test_an_append_under_that_heading_is_charter_added(h: OrgFilesHarness) -> None:
    with_section(h, section_body())  # (the section is the last of the body, so an append lands under its heading)
    before = raw(h)
    chunk = "---\nrole: More\n---\n- A line of my own.\n"
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", chunk, append=True)) == CHARTER_ADDED
    assert raw(h) == before


def test_text_under_another_heading_passes(h: OrgFilesHarness) -> None:
    with_section(h, section_body())
    body = "# Role\n\nA sharper review.\n\n## My notes\nThings I learned.\n\n## Added by your changes\n" + LINES + "\n\n## After\nMore of my own.\n"
    h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: Sharper\n---\n" + body)
    assert "A sharper review." in raw(h) and "## My notes" in raw(h) and "## After" in raw(h)
    h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: Sharper\n---\n" + body.replace("- Ada", "-   Ada"))  # spacing and bullets are not a reword
    with_section(h, "# Role\n\nReview.\n\n## Added by your changes\n" + LINES + "\n\n## Mine\nx\n")
    h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: More\n---\nOne more thing.\n", append=True)  # an append after another heading
    assert raw(h).endswith("One more thing.\n")


def test_a_charter_without_the_section_may_not_get_one(h: OrgFilesHarness) -> None:
    before = raw(h)
    text_with = "---\nrole: Reviewer\n---\n# Role\n\nReview.\n\n## Added by your changes\n- A line of my own.\n"
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", text_with)) == CHARTER_ADDED
    assert raw(h) == before


def test_root_is_not_held_by_charter_added_at_the_writer(h: OrgFilesHarness) -> None:
    """GREEN when written: the writer admits root (the extension applier writes the section through the registry, not through this writer)."""
    h.put(h.root / "lead" / "AGENT.md", join_frontmatter(charter(h, "lead"), section_body()))
    h.writer.write("root", "lead/AGENT.md", "---\nrole: Lead\n---\nNo section any more.\n")
    assert "Added by your changes" not in (written(h, "lead", "AGENT.md") or "")
