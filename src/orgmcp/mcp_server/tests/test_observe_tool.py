# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import asyncio
import dataclasses

import pytest
from testkit.legacy.orgmcp.core import ROOT, Org
from testkit.mcp_server_world import build_server
from testkit.obs_fixtures import Story, freeze, stamp

from orgmcp.kernel.testing import FakeClock

NOW = stamp(200)


@pytest.fixture
def org(tmp_path):
    """root -> ceo -> eng with emission OFF (``events: false``): the event files in these tests are written by hand
    (tests/testkit/obs_fixtures.py) so each test controls exactly which events exist. The real emitter is exercised against
    this query layer in tests/test_observability_e2e.py."""
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05, "events": False})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    o.hire("ceo", "eng", "Engineer", "Build things.")
    return o


@pytest.fixture
def clock(monkeypatch):
    return freeze(monkeypatch)


@pytest.fixture
def story(org, clock):
    return Story(org, clock)


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def test_observe_tool_is_root_only_and_read_only(org, story):
    org.runtime = dataclasses.replace(org.runtime, clock=FakeClock(NOW))
    root = build_server(org, ROOT)
    names = {t.name for t in asyncio.run(root.list_tools())}
    assert "observe" in names
    assert "observe" not in {t.name for t in asyncio.run(build_server(org, "ceo").list_tools())}
    assert "observe" not in {t.name for t in asyncio.run(build_server(org, "ceo/eng").list_tools())}
    assert "scheduler:" in call(root, "observe")
    assert "totals: wall" in call(root, "observe", view="trace", target=story.task.id)
    assert "all checks passed" in call(root, "observe", view="check")
    assert "tool.call" in call(root, "observe", view="events", target="ceo", since="2026-10-18T00:00:00Z", limit=5)
    assert call(root, "observe", view="metrics", since="2026-10-18T00:00:00Z", by="tool").count("by tool:") == 1
    with pytest.raises(Exception, match="trace needs target"):
        call(root, "observe", view="trace")


def test_observe_tool_docstring_is_short_and_says_read_only():
    from orgmcp.mcp_server._tools_observe import ObservabilityTools

    class Fake:
        tools = {}

        def tool(self):
            def deco(fn):
                Fake.tools[fn.__name__] = fn
                return fn

            return deco

    ObservabilityTools(lambda: None).register(Fake(), ROOT)
    doc = Fake.tools["observe"].__doc__
    assert doc.startswith("Read-only") and len(doc) < 900
    for view in ("now", "trace", "metrics", "events", "check"):
        assert view in doc
