"""Cross-branch behavior after integrating confinement (X1), assistant UX (X2) and verifier templates (X3)."""

import asyncio
import json
from pathlib import Path

import pytest

from orgmcp import blueprint as bpm
from orgmcp.cli import main
from orgmcp.core import ROOT, Org
from orgmcp.server import OrgBinding, build_server


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


@pytest.fixture
def dirs(tmp_path):
    d = {n: (tmp_path / n).resolve() for n in ("docs", "docs/hr", "other", "proj")}
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def org(tmp_path, dirs):
    o = Org.init(tmp_path / "org", "round 7", {"poll_seconds": 0.05})
    o.hire(ROOT, "lead", "Lead", "Lead.", can_hire=True, tools=["read"], inputs=[str(dirs["docs"])])
    return o


# ---------------------------------------------------------------------------------------- hire with inputs


def test_root_hire_tool_takes_inputs(org, dirs):
    server = build_server(OrgBinding(org.root), ROOT)
    assert "hired reader" in call(server, "hire", name="reader", role="R", charter="Read.", tools=["read"], inputs=[str(dirs["docs"])])
    assert org.charter("reader")[0]["inputs"] == [str(dirs["docs"])] and org.inputs_of("reader") == [dirs["docs"]]
    call(server, "hire", name="plain", role="P", charter="Nothing.")  # old calls without inputs keep working
    assert "inputs" not in org.charter("plain")[0]
    assert "absolute path" in fails(server, "hire", name="rel", role="R", charter="x", tools=["read"], inputs=["docs"])
    assert "organization directory" in fails(server, "hire", name="bad", role="R", charter="x", inputs=[str(org.dir("lead"))])


def test_manager_hire_tool_narrows_inputs(org, dirs):
    server = build_server(OrgBinding(org.root), "lead")
    call(server, "hire", name="kid", role="K", charter="x", tools=["read"], inputs=[str(dirs["docs/hr"])])
    assert org.inputs_of("lead/kid") == [dirs["docs/hr"]]
    assert "inside your inputs or workspace" in fails(server, "hire", name="far", role="F", charter="x", inputs=[str(dirs["other"])])
    assert "cannot grant tools" in fails(server, "hire", name="big", role="B", charter="x", tools=["write"], inputs=[str(dirs["docs"])])


def test_cli_hire_inputs_is_repeatable(org, dirs, capsys):
    main(["--root", str(org.root), "hire", "root", "reader", "--role", "R", "--charter", "Read.", "--tools", "read",
          "--inputs", str(dirs["docs"]), "--inputs", str(dirs["other"])])
    assert org.inputs_of("reader") == [dirs["docs"], dirs["other"]]
    main(["--root", str(org.root), "hire", "root", "plain", "--role", "P", "--charter", "x"])
    assert "inputs" not in org.charter("plain")[0]
