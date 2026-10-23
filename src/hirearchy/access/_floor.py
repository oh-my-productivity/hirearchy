"""``CharterModelFloorAudit``: the agents that run on a model outside the allowed set (docs/design/org-agent-model-floor.md)."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..settings import DEFAULT_MODEL, OrgSettings, config_allowed_models
from .api import ModelFloorAudit, ModelResolver


class CharterModelFloorAudit(ModelFloorAudit):
    def __init__(self, agents: AgentDirectory, models: ModelResolver, settings: OrgSettings) -> None:
        self._agents = agents
        self._models = models
        self._settings = settings

    def below_floor(self) -> list[tuple[str, str]]:
        allowed = config_allowed_models(self._settings.config())
        pairs = ((addr, self._models.model_for(addr)) for addr in self._agents.agents())
        return [(addr, model) for addr, model in pairs if model not in allowed]

    def note(self) -> str:
        below = self.below_floor()
        if not below:
            return ""
        allowed = ", ".join(config_allowed_models(self._settings.config()))
        named = ", ".join(f"{addr} on {model}" for addr, model in below)
        return (
            f"Model floor: below the allowed models ({allowed}): {named}. Fix: set model: {DEFAULT_MODEL} in each one's AGENT.md "
            "(you for your direct reports, the manager for the others); they keep running as they are until then."
        )
