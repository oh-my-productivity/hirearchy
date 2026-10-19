"""The kiro functions of ``orgmcp.scheduler`` (``kiro_profile_name ensure_kiro_profile file_confinement kiro_runner mcp_server_command``)
and the settings next to them stay in force as thin wrappers over ``orgmcp.kiro`` until D-sched-1, with every patch point the tests use:
``scheduler.KIRO_AGENTS_DIR``, ``scheduler.mcp_server_command``, ``scheduler.file_confinement`` and ``scheduler.ensure_kiro_profile``."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from orgmcp import scheduler
from orgmcp.app import Org
from orgmcp.kernel import ROOT

GOLDEN = Path(scheduler.__file__).resolve().parent.parent / "kiro" / "tests" / "golden"
SERVER = {"command": "<BIN>", "args": ["mcp"]}


@pytest.fixture
def org(tmp_path: Path) -> Org:
    o = Org.init(tmp_path / "team" / "org", "Test mission", {"poll_seconds": 0.05})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    return o


def test_the_wrappers_and_settings_are_still_module_attributes() -> None:
    for name in ("kiro_profile_name", "ensure_kiro_profile", "file_confinement", "kiro_runner", "mcp_server_command"):
        assert callable(getattr(scheduler, name))
    assert isinstance(scheduler.PROJECT_DIR, Path) and isinstance(scheduler.KIRO_AGENTS_DIR, Path)


def test_the_profile_names_are_those_of_main() -> None:
    for case in json.loads((GOLDEN / "names.json").read_text(encoding="utf-8")):
        assert scheduler.kiro_profile_name(case["root"], case["tools"]) == case["name"], case


def test_the_profile_name_accepts_a_path_and_a_string(tmp_path: Path) -> None:
    assert scheduler.kiro_profile_name(tmp_path, ["read"]) == scheduler.kiro_profile_name(str(tmp_path), ["read"])


def test_the_confinement_is_that_of_main() -> None:
    for case in json.loads((GOLDEN / "confinement.json").read_text(encoding="utf-8")):
        workspace = Path(case["workspace"]) if case["workspace"] else None
        got = scheduler.file_confinement(Path("/golden/org"), case["tools"], workspace, [Path(p) for p in case["inputs"]])
        assert got == (case["allowedTools"], case["toolsSettings"]), case


def test_the_profiles_are_those_of_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler, "mcp_server_command", lambda: dict(SERVER))
    stub = SimpleNamespace(root=Path("/golden/org"))  # ensure_kiro_profile reads nothing but the root of the organization
    for label, case in json.loads((GOLDEN / "profiles.json").read_text(encoding="utf-8")).items():
        args = dict(case["args"])
        tools = args.pop("tools")
        if "workspace" in args:
            args["workspace"] = Path(args["workspace"])
        if "inputs" in args:
            args["inputs"] = [Path(p) for p in args["inputs"]]
        directory = tmp_path / label
        name = scheduler.ensure_kiro_profile(tools, directory, org=cast(Org, stub), **args)
        assert name == case["name"] and (directory / f"{name}.json").read_text(encoding="utf-8") == case["text"], label
        assert [p.name for p in directory.iterdir()] == [f"{name}.json"]


def test_the_agents_directory_is_read_when_the_function_is_called(org: Org, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler, "KIRO_AGENTS_DIR", tmp_path / "one")
    first = scheduler.ensure_kiro_profile(["read"], org=org)
    monkeypatch.setattr(scheduler, "KIRO_AGENTS_DIR", tmp_path / "two")
    assert scheduler.ensure_kiro_profile(["read"], org=org) == first
    assert (tmp_path / "one" / f"{first}.json").is_file() and (tmp_path / "two" / f"{first}.json").is_file()


def test_an_explicit_directory_beats_the_setting(org: Org, tmp_path: Path) -> None:
    name = scheduler.ensure_kiro_profile([], tmp_path / "explicit", org=org)
    assert [p.name for p in (tmp_path / "explicit").iterdir()] == [f"{name}.json"]
    assert not (scheduler.KIRO_AGENTS_DIR / f"{name}.json").exists()


def test_a_replaced_mcp_server_command_is_the_one_in_the_profile(org: Org, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler, "mcp_server_command", lambda: {"command": "/replaced/orgmcp", "args": ["mcp"]})
    name = scheduler.ensure_kiro_profile([], tmp_path / "agents", org=org)
    server = json.loads((tmp_path / "agents" / f"{name}.json").read_text(encoding="utf-8"))["mcpServers"]["orgmcp"]
    assert server["command"] == "/replaced/orgmcp"


def test_a_replaced_file_confinement_is_the_one_a_confined_profile_uses(org: Org, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[Path, list[str], Path | None, list[Path]]] = []

    def replaced(org_root: Path, tools: list[str], workspace: Path | None, inputs: list[Path]) -> tuple[list[str], dict[str, object]]:
        seen.append((org_root, tools, workspace, inputs))
        return ["shell"], {"read": {"allowedPaths": ["/replaced"], "deniedPaths": []}}

    monkeypatch.setattr(scheduler, "file_confinement", replaced)
    name = scheduler.ensure_kiro_profile(["shell", "read"], tmp_path / "agents", org=org, workspace=tmp_path / "ws", inputs=[tmp_path / "in"], confine=True)
    assert seen == [(org.root, ["read", "shell"], tmp_path / "ws", [tmp_path / "in"])]
    profile = json.loads((tmp_path / "agents" / f"{name}.json").read_text(encoding="utf-8"))
    assert profile["toolsSettings"] == {"read": {"allowedPaths": ["/replaced"], "deniedPaths": []}} and profile["allowedTools"] == ["@orgmcp", "shell"]
    scheduler.ensure_kiro_profile(["read"], tmp_path / "agents2", org=org)
    assert len(seen) == 1  # an unconfined profile does not ask


def test_the_runner_asks_the_ensure_function_that_is_in_force(org: Org, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def replaced(tools: list[str], **kw: object) -> str:
        calls.append((tools, kw))
        return "replaced-profile"

    org.hire(ROOT, "plain", "Plain", "x", tools=["shell"])
    org.hire(ROOT, "writer", "Writer", "x", tools=["write"], workspace=str(org.root.parent / "ws"))
    monkeypatch.setattr(scheduler, "ensure_kiro_profile", replaced)
    plain = scheduler.kiro_runner()(org, "plain", "P")
    writer = scheduler.kiro_runner("/bin/kiro")(org, "writer", "P")
    assert plain[0][:5] == ["kiro-cli", "chat", "--no-interactive", "--agent", "replaced-profile"]
    assert writer[0][:5] == ["/bin/kiro", "chat", "--no-interactive", "--agent", "replaced-profile"]
    assert calls[0] == (["shell"], {"org": org})  # a shared profile is asked for with the organization alone
    assert calls[1][0] == ["write"] and set(calls[1][1]) == {"org", "workspace", "inputs", "confine"} and calls[1][1]["confine"] is True


def test_the_runner_returns_a_list_a_path_and_a_dictionary(org: Org) -> None:
    cmd, cwd, env = scheduler.kiro_runner()(org, "ceo", "P")
    assert isinstance(cmd, list) and isinstance(cwd, Path) and type(env) is dict
    assert cwd == org.dir("ceo") and env["ORG_AGENT"] == "ceo" and env["ORG_ROOT"] == str(org.root)


def test_the_runner_reads_the_process_environment_when_it_runs(org: Org, monkeypatch: pytest.MonkeyPatch) -> None:
    build = scheduler.kiro_runner()
    monkeypatch.setenv("LATE_VARIABLE", "seen")
    assert build(org, "ceo", "P")[2]["LATE_VARIABLE"] == "seen"
