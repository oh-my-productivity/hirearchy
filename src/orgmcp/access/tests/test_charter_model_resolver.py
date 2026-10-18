"""``CharterModelResolver`` asks the settings only when the charter names no model."""

from __future__ import annotations

from orgmcp.access import ModelResolver
from orgmcp.access._models import CharterModelResolver
from orgmcp.agents.testing import MemoryAgents
from orgmcp.kernel import JsonObject
from orgmcp.settings import DEFAULT_MODEL, OrgSettings
from orgmcp.settings.testing import MemoryOrgSettings


class BrokenSettings(MemoryOrgSettings):
    """An ORG.md that cannot be read."""

    def __init__(self) -> None:
        super().__init__("---\nkey: [unclosed\n---\n")
        self.asked = 0

    def default_model(self) -> str:
        self.asked += 1
        return super().default_model()

    def config(self) -> JsonObject:
        self.asked += 1
        return super().config()


def agents_with(charter: str) -> MemoryAgents:
    agents = MemoryAgents()
    agents.put("dev/AGENT.md", charter)
    return agents


def test_it_is_a_model_resolver() -> None:
    assert isinstance(CharterModelResolver(MemoryAgents(), MemoryOrgSettings("x")), ModelResolver)


def test_the_default_model_is_the_one_the_settings_port_reports() -> None:
    class Fixed(MemoryOrgSettings):
        def default_model(self) -> str:
            return "from-the-port"

    assert CharterModelResolver(MemoryAgents(), Fixed("x")).default_model() == "from-the-port"
    assert CharterModelResolver(MemoryAgents(), MemoryOrgSettings("x")).default_model() == DEFAULT_MODEL


def test_a_charter_with_a_model_never_consults_the_settings() -> None:
    settings = BrokenSettings()
    resolver = CharterModelResolver(agents_with("---\nrole: R\nmodel: m-1\n---\nb\n"), settings)
    assert resolver.model_for("dev") == "m-1"
    assert settings.asked == 0


def test_a_charter_without_a_model_consults_the_settings_once() -> None:
    class Counting(MemoryOrgSettings):
        asked = 0

        def default_model(self) -> str:
            Counting.asked += 1
            return "m-org"

    settings: OrgSettings = Counting("x")
    assert CharterModelResolver(agents_with("---\nrole: R\n---\nb\n"), settings).model_for("dev") == "m-org"
    assert Counting.asked == 1
