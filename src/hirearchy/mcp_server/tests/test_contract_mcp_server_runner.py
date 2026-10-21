"""Contract of ``McpServerRunner``: running names the process ``mcp`` and serves the identity the environment resolves to. Over the stdio runner (on a server that does not
read stdin) and over the recording runner."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from hirearchy.mcp_server import McpServerRunner
from hirearchy.mcp_server.testing import IMPLEMENTATIONS, RunnerWorld



@pytest.fixture(params=IMPLEMENTATIONS[McpServerRunner], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> RunnerWorld:
    made = cast(RunnerWorld, request.param(tmp_path))
    assert isinstance(made.runner, McpServerRunner)
    return made


def test_the_process_is_named_mcp_and_the_identity_is_served(w: RunnerWorld) -> None:
    assert w.label.get() == "cli" and w.served() == []
    w.runner.run()
    assert w.label.get() == "mcp"
    assert w.served() == ["ceo"]
