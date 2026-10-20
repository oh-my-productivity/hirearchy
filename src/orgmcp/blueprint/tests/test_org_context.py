"""The organization a blueprint is planned against."""

from __future__ import annotations

from pathlib import Path

from orgmcp.agents import AgentDirectory
from orgmcp.blueprint._org import NoOrgContext, PresentOrAbsentOrg, RuntimeOrgContext
from orgmcp.blueprint._protocols import OrgContext, OrgContexts
from orgmcp.blueprint.testing import StaticOrgContext
from orgmcp.kernel import OrgPaths
from orgmcp.services import ServiceCatalog
from orgmcp.settings import DEFAULT_CONFIG, OrgSettings




class Settings(OrgSettings):
    def __init__(self, config: dict[str, object]) -> None:
        self.values = config

    def config(self) -> dict[str, object]:
        return self.values

    def rules(self) -> str:
        return ""

    def default_model(self) -> str:
        return ""

    def number(self, key: str, kind: type[float] | type[int] = float) -> float:
        return kind(0)

    def message_cap(self) -> int:
        return 0


class Agents(AgentDirectory):
    def __init__(self, tree: dict[str, list[str]]) -> None:
        self.tree = tree

    def exists(self, addr: str) -> bool:
        return addr == "root" or addr in self.tree

    def require(self, addr: str) -> str:
        return addr

    def children(self, addr: str) -> list[str]:
        return list(self.tree.get(addr, []))

    def agents(self) -> list[str]:
        return list(self.tree)

    def subtree(self, addr: str) -> list[str]:
        return [addr]


class Catalog(ServiceCatalog):
    def __init__(self, names: dict[str, list[str]]) -> None:
        self.names = names

    def service_names(self, addr: str) -> list[str]:
        return list(self.names.get(addr, []))

    def read_contract(self, owner: str, name: str) -> None:
        return None

    def read_playbook(self, owner: str, name: str) -> None:  # type: ignore[override]
        return None

    def owned_services(self, owner: str) -> list[object]:  # type: ignore[override]
        return []

    def requestable_services(self, actor: str) -> list[object]:  # type: ignore[override]
        return []


def test_without_an_organization_the_defaults_apply_and_nothing_is_there() -> None:
    org = NoOrgContext()
    assert isinstance(org, OrgContext)
    assert org.config() == dict(DEFAULT_CONFIG) and org.root() is None and not org.exists("lead") and org.service_names() == set()


def test_the_defaults_are_a_copy_nobody_can_change_for_the_next_caller() -> None:
    NoOrgContext().config()["max_depth"] = 99
    assert NoOrgContext().config()["max_depth"] == DEFAULT_CONFIG["max_depth"]


def test_the_organization_is_its_settings_its_directory_its_agents_and_the_services_of_its_top_level_agents(tmp_path: Path) -> None:
    org = RuntimeOrgContext(Settings({"max_depth": 2}), Agents({"root": ["ceo", "ops"], "ceo": [], "ops": []}), Catalog({"ceo": ["brief"], "ops": ["digest", "brief"], "ceo/x": ["hidden"]}), OrgPaths(tmp_path))
    assert isinstance(org, OrgContext)
    assert org.config() == {"max_depth": 2} and org.root() == tmp_path and org.exists("ceo") and not org.exists("cto")
    assert org.service_names() == {"brief", "digest"}


def test_the_choice_between_the_organization_and_the_defaults() -> None:
    present, absent = StaticOrgContext(agents=["lead"]), NoOrgContext()
    both = PresentOrAbsentOrg(present, absent)
    assert isinstance(both, OrgContexts) and both.context(True) is present and both.context(False) is absent

