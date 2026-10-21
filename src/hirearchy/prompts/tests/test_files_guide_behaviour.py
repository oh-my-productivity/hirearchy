# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.hirearchy.core import ROOT, Org


@pytest.fixture
def dirs(tmp_path):
    d = {n: (tmp_path / n).resolve() for n in ("proj", "proj/out", "handbook", "handbook/hr", "elsewhere")}
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    (d["handbook"] / "a.md").write_text("one two three\n")
    (d["handbook/hr"] / "b.md").write_text("four five\n")
    return d


@pytest.fixture
def team(tmp_path, dirs):
    """root -> lead (ws proj, inputs handbook) -> writer (ws proj/out, inputs handbook/hr); root -> other (ws elsewhere)."""
    o = Org.init(tmp_path / "org", "confinement", {"poll_seconds": 0.05})
    o.hire(ROOT, "lead", "Lead", "Lead.", can_hire=True, tools=["read", "shell", "write"], workspace=str(dirs["proj"]),
           inputs=[str(dirs["handbook"])])
    o.hire("lead", "writer", "Writer", "Write.", tools=["read", "write"], workspace=str(dirs["proj/out"]),
           inputs=[str(dirs["handbook/hr"])])
    o.hire(ROOT, "other", "Other", "Other.", tools=["write"], workspace=str(dirs["elsewhere"]))
    return o


# --------------------------------------------------------------------------------------- prompt
def test_prompt_has_a_files_section_with_workspace_and_inputs(team, dirs):
    text = team.run_prompt("lead/writer", [])
    assert "- Files:" in text
    assert f"Workspace (kiro read/write/shell, and the working directory of kiro tools): `{dirs['proj/out']}`" in text
    assert f"Read-only inputs (kiro `read` or hirearchy `org_read` by absolute path): `{dirs['handbook/hr']}`" in text
    assert "`lead/writer/MEMORY.md`" in text and "`lead/writer/work/` (hirearchy `org_write` only)" in text
    assert "Never create org files (MEMORY.md, `<address>/...`) in the workspace. Report workspace artifacts by absolute path." in text
    assert "kiro `write` is limited to the workspace" in text and "cannot confine" not in text.split("# New messages")[0].split("- Files:")[1]


def test_prompt_states_the_shell_rule_only_for_agents_with_shell(team, dirs):
    team.hire("lead", "dev", "Dev", "x", tools=["read", "write", "shell"], workspace=str(dirs["proj/out"]))
    assert "`shell`, which the runtime cannot confine" in team.run_prompt("lead/dev", [])
    assert "cannot confine" not in team.run_prompt("lead/writer", [])


def test_prompt_has_no_files_section_without_workspace_or_inputs(team):
    team.hire("lead", "plain", "Plain", "x")
    assert "- Files:" not in team.run_prompt("lead/plain", []) and "- Files:" not in team.whoami("lead/plain")
    assert "- Files:" in team.whoami("lead")


def test_inputs_only_agent_is_told_it_has_no_workspace(team, dirs):
    team.hire("lead", "ro", "RO", "x", inputs=[str(dirs["handbook/hr"])])
    text = team.state_summary("lead/ro")
    assert "You have no workspace" in text and f"`{dirs['handbook/hr']}`" in text


# ----------------------------------------------------------------------- tool names in the prompts
def hire_writer(org, tmp_path, tools):
    ws = tmp_path / "ws"
    ws.mkdir(exist_ok=True)
    org.hire(ROOT, "dev", "Developer", "Build.", tools=tools, workspace=str(ws))
    return ws


def test_prompt_of_an_agent_with_built_ins_separates_the_two_kinds_of_tools(org, tmp_path):
    hire_writer(org, tmp_path, ["read", "write", "shell"])
    text = org.run_prompt("dev", [])
    files = text.split("- Files:")[1].split("# New messages")[0]
    # the built-ins `read`/`write` hide hirearchy's tools of the same name (studies/F-read-experiment, F2-tool-names):
    # this agent has them as `org_read` / `org_write`
    assert "hirearchy tools (shown as `@hirearchy/org_write`, `@hirearchy/org_read`, ...)" in files
    assert "kiro's built-in `read`, `shell`, `write`" in files and "they write and run only in the workspace and never change the org" in files
    assert "`dev/MEMORY.md`, `dev/work/`" in files
    assert "written with `@hirearchy/org_write`, never with the built-in `write`" in files
    assert "the hirearchy write tool is `@hirearchy/org_write` for you: use it for MEMORY.md and org files" in files
    assert "Your `read` is kiro's built-in: it reads org files too" in files and "`@hirearchy/org_read` for you" in files
    assert f"ABSOLUTE path, `{org.root}/<path in the org>`" in files
    assert '`@hirearchy/org_write`(path="dev/MEMORY.md", ...) (the hirearchy tool, not a built-in `write`)' in text


def test_agent_with_only_a_built_in_read_and_no_workspace_gets_the_naming_text(org):
    org.hire(ROOT, "rd", "Reader", "Read.", tools=["read"])
    files = org.run_prompt("rd", []).split("- Files:")[1]
    assert "kiro's built-in `read`" in files and "`@hirearchy/org_read`" in files


def test_agent_without_built_ins_has_no_files_section_but_the_hirearchy_memory_line(org):
    text = org.run_prompt("ceo", [])
    assert "- Files:" not in text and "never with the built-in" not in text
    assert '`@hirearchy/write`(path="ceo/MEMORY.md", ...)' in text
