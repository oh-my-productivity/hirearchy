# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.orgmcp.core import ROOT, Org


@pytest.fixture
def org(tmp_path):
    (tmp_path / "inputs").mkdir()
    (tmp_path / "proj").mkdir()
    o = Org.init(tmp_path / "org", "f-read", {"poll_seconds": 0.05})
    o.hire(ROOT, "lead", "Lead", "Lead.", can_hire=True, tools=["read", "write", "web_search"],
           workspace=str(tmp_path / "proj"), inputs=[str(tmp_path / "inputs")])
    o.hire("lead", "writer", "Writer", "Write.", tools=["read"], inputs=[str(tmp_path / "inputs")])
    return o


# ------------------------------------------------------------------------------------ prompt and plan
def test_the_prompt_tells_a_built_in_read_agent_to_read_org_files_by_absolute_path(org):
    files = org.run_prompt("lead/writer", []).split("- Files:")[1].split("# New messages")[0]
    assert "Your `read` is kiro's built-in: it reads org files too" in files and "`@orgmcp/org_read` for you" in files
    assert f"`{org.root}/<path in the org>`" in files and "ABSOLUTE" in files
    assert "never with the built-in `write`/`read`" not in files
    assert "kiro `read` to workspace + inputs + the organization (read-only)" in files
