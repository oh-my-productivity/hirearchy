# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio

import pytest
import testkit.reach.yaml as yaml
from testkit.reach.hirearchy.core import ROOT, Org, OrgError, atomic_write
from testkit.orgfiles_server import build_server


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


@pytest.fixture
def team(tmp_path):
    """root -> lead (manager; read+shell, inputs notes/) -> rev (read, confined to notes/, model set)."""
    for d in ("notes", "elsewhere"):
        (tmp_path / d).mkdir()
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05})
    o.hire(ROOT, "lead", "Lead", "Lead.", can_hire=True, tools=["read", "shell"], inputs=[str(tmp_path / "notes")])
    o.hire("lead", "rev", "Reviewer", "Review.", model="claude-opus-5.5", tools=["read"], inputs=[str(tmp_path / "notes")])
    return o


def charter_text(role, body="New body.", **extra):
    meta = {"role": role, **extra}
    return "---\n" + yaml.safe_dump(meta, sort_keys=False) + "---\n" + body + "\n"


# ------------------------------------------------------------------------------------------ 1. charter merge
def test_a_rewrite_with_only_role_keeps_tools_inputs_model_and_the_rest(team, tmp_path):
    before, _ = team.charter("lead/rev")
    assert before["tools"] == ["read"] and before["model"] == "claude-opus-5.5"
    team.write("lead", "lead/rev/AGENT.md", "---\nrole: Sharper reviewer\n---\n# Role\nNew body.\n")
    after, body = team.charter("lead/rev")
    assert after["role"] == "Sharper reviewer" and "New body." in body
    for key in ("model", "tools", "inputs", "can_hire", "max_children", "hired_by", "created"):
        assert after[key] == before[key], key
    assert after["inputs"] == [str(tmp_path / "notes")]


def test_a_key_set_explicitly_wins_even_when_empty(team):
    team.write("lead", "lead/rev/AGENT.md", charter_text("Reviewer", tools=[], model="claude-sonnet-5.5"))
    after, _ = team.charter("lead/rev")
    assert after["tools"] == [] and after["model"] == "claude-sonnet-5.5"
    assert after["inputs"]  # not set in the new text: kept


def test_authority_is_checked_on_the_merged_frontmatter(team, tmp_path):
    # kept `read` + new inputs outside the manager's own authority
    # inputs outside the manager's own authority are refused when set explicitly
    with pytest.raises(OrgError, match="inputs must be inside"):
        team.write("lead", "lead/rev/AGENT.md", charter_text("Reviewer", inputs=[str(tmp_path / "elsewhere")]))
    # a legacy charter (read, no workspace, no `inputs` key) merges to an unconfined read: refused for a confined manager
    atomic_write(team.dir("lead/rev") / "AGENT.md", "---\nrole: R\ntools: [read]\n---\nx\n")
    with pytest.raises(OrgError, match="needs an `inputs:` list"):
        team.write("lead", "lead/rev/AGENT.md", "---\nrole: R2\n---\nnew\n")
    assert "R2" not in (team.dir("lead/rev") / "AGENT.md").read_text()


def test_a_tool_the_manager_lacks_is_still_refused_when_set_explicitly(team):
    with pytest.raises(OrgError):
        team.write("lead", "lead/rev/AGENT.md", charter_text("Reviewer", tools=["read", "write"]))
    assert team.charter("lead/rev")[0]["tools"] == ["read"]  # nothing was written


def test_the_write_reply_lists_kept_and_changed_keys(team):
    server = build_server(team, "lead")
    out = call(server, "write", path="lead/rev/AGENT.md", content=charter_text("Sharper", tools=["read"], max_children=2))
    assert "wrote lead/rev/AGENT.md" in out
    assert "kept from the old frontmatter (not in your text):" in out
    for key in ("model", "inputs", "can_hire", "hired_by", "created"):
        assert key in out.split("kept from the old frontmatter")[1].split("changed")[0]
    assert "role: Reviewer -> Sharper" in out and "max_children: 0 -> 2" in out
    assert "tools" not in out.split("kept from the old frontmatter")[1].split(".")[0]  # set explicitly, unchanged
    out = call(server, "write", path="lead/rev/AGENT.md", content=charter_text("Sharper", tools=[]))
    assert "tools: [read] -> []" in out


def test_other_writes_have_no_note(team):
    server = build_server(team, "lead")
    assert call(server, "write", path="lead/MEMORY.md", content="m") == "wrote lead/MEMORY.md (organization file)"
