"""The access slice of the ``Org`` facade: workspace, inputs, tools, model and the authority checks behave as they always did, and now go
through the ports of the runtime."""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import pytest

from hirearchy.access import AccessScopes, AuthorityPolicy, ModelResolver, ToolNaming
from hirearchy.access.testing import StaticAccess
from hirearchy.app import Org
from hirearchy.kernel import OrgError
from hirearchy.settings import DEFAULT_MODEL
from hirearchy.settings.testing import MemoryOrgSettings


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    (tmp_path / "ws").mkdir()
    (tmp_path / "in").mkdir()
    made.hire("root", "lead", "Lead", "Leads.", tools=["read", "write"], can_hire=True, workspace=str(tmp_path / "ws"), inputs=[str(tmp_path / "in")])
    made.hire("lead", "dev", "Dev", "Builds.", tools=["read"], workspace=str(tmp_path / "ws" / "dev"), inputs=[str(tmp_path / "in")])
    made.hire("root", "plain", "Plain", "Talks.")
    return made


def test_workspace_inputs_and_readable_roots(org: Org, tmp_path: Path) -> None:
    assert org.workspace_of("lead") == (tmp_path / "ws").resolve() and org.workspace_of(" /lead/dev/ ") == (tmp_path / "ws" / "dev").resolve()
    assert org.workspace_of("plain") is None and org.workspace_of("root") is None and org.workspace_of("nobody") is None
    assert org.inputs_of("lead") == [(tmp_path / "in").resolve()] and org.inputs_of("plain") == [] and org.inputs_of("root") == []
    assert org.readable_roots("lead") == [(tmp_path / "in").resolve(), (tmp_path / "ws").resolve(), (tmp_path / "ws" / "dev").resolve()]
    assert org.readable_roots("lead/dev") == [(tmp_path / "in").resolve(), (tmp_path / "ws" / "dev").resolve()]


def test_tool_names(org: Org) -> None:
    assert org.tool_names("lead") == {"read": "org_read", "write": "org_write"}
    assert org.tool_names("lead/dev") == {"read": "org_read", "write": "write"}
    assert org.tool_names("plain") == {"read": "read", "write": "write"} and org.tool_names("root") == {"read": "read", "write": "write"}


def test_models(org: Org) -> None:
    assert org.default_model == DEFAULT_MODEL and org.model_for("plain") == DEFAULT_MODEL
    (org.root / "ORG.md").write_text("---\ndefault_model: m-org\n---\nrules\n", encoding="utf-8")
    (org.root / "plain" / "AGENT.md").write_text("---\nrole: Plain\nmodel: ' m-own '\n---\nbody\n", encoding="utf-8")
    assert org.default_model == "m-org" and org.model_for("lead") == "m-org" and org.model_for("plain") == "m-own"


def test_the_authority_checks(org: Org, tmp_path: Path) -> None:
    org._check_authority("lead", ["read"], str(tmp_path / "ws" / "x"), [str(tmp_path / "in" / "y")])
    with pytest.raises(OrgError, match="^you cannot grant tools you do not have yourself: shell$"):
        org._check_authority("lead", ["shell", "read"], None)
    with pytest.raises(OrgError, match="^a report's workspace must be inside yours "):
        org._check_authority("lead", [], str(tmp_path / "elsewhere"))
    with pytest.raises(OrgError, match="^you have no workspace, so you cannot assign one$"):
        org._check_authority("plain", [], str(tmp_path / "ws"))
    with pytest.raises(OrgError, match="^a report's inputs must be inside your inputs or workspace "):
        org._check_authority("lead", [], None, [str(tmp_path / "elsewhere")])
    assert org._check_inputs(str(tmp_path / "elsewhere")) == [str(tmp_path / "elsewhere")]
    with pytest.raises(OrgError, match="^an input must be an absolute path \\(got `rel`\\)$"):
        org._check_inputs(["rel"])
    with pytest.raises(OrgError, match="^an input must not overlap the organization directory "):
        org._check_inputs([str(org.root / "lead")])


def test_unconfined_read_is_a_static_method() -> None:
    assert isinstance(inspect.getattr_static(Org, "unconfined_read"), staticmethod)
    assert Org.unconfined_read({}) is True and Org.unconfined_read({"inputs": []}) is False and Org.unconfined_read({"workspace": "/w"}) is False


def test_the_methods_come_from_the_ports_of_the_runtime(org: Org) -> None:
    fake = StaticAccess()
    fake.put_agent("dev", {"role": "R", "tools": ["write"], "workspace": "/w/fake", "inputs": ["/i/fake"], "model": "m-fake"})
    org.runtime = dataclasses.replace(org.runtime, access_scopes=fake, authority_policy=fake, tool_naming=fake, model_resolver=fake)
    assert isinstance(fake, AccessScopes) and isinstance(fake, AuthorityPolicy) and isinstance(fake, ToolNaming) and isinstance(fake, ModelResolver)
    assert org.workspace_of("dev") == Path("/w/fake").resolve() and org.inputs_of("dev") == [Path("/i/fake").resolve()]
    assert org.readable_roots("dev") == [Path("/i/fake").resolve(), Path("/w/fake").resolve()]
    assert org.tool_names("dev") == {"read": "read", "write": "org_write"} and org.model_for("dev") == "m-fake"
    assert org._check_inputs(["/i/ok"]) == ["/i/ok"]
    with pytest.raises(OrgError, match="^an input must not overlap the organization directory \\(/memory/org\\)"):
        org._check_inputs(["/memory/org/x"])
    with pytest.raises(OrgError, match="^you cannot grant tools you do not have yourself: read$"):
        org._check_authority("dev", ["read"], None)


def test_the_default_model_follows_the_config_of_the_org(org: Org, monkeypatch: pytest.MonkeyPatch) -> None:
    """The runtime's settings are read (the dashboard's lenient runtime puts its own ``OrgSettings`` there, where its ``LenientOrg`` used to
    override ``config``)."""

    class Lenient(Org):
        def __init__(self, root: Path) -> None:
            super().__init__(root)
            self.runtime = dataclasses.replace(self.runtime, settings=MemoryOrgSettings("---\ndefault_model: m-lenient\n---\n"))

    assert Lenient(org.root).default_model == "m-lenient"
