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

    def _audit(self) -> tuple[tuple[str, ...], list[tuple[str, str]]]:
        """The allowed models and ``(addr, model)`` of the agents outside them; raises when ORG.md or a charter cannot be read."""
        allowed = config_allowed_models(self._settings.config())
        pairs = ((addr, self._models.model_for(addr)) for addr in self._agents.agents())
        return allowed, [(addr, model) for addr, model in pairs if model not in allowed]

    def below_floor(self) -> list[tuple[str, str]]:
        try:
            return self._audit()[1]
        except Exception:  # noqa: BLE001 - ORG.md that does not parse: the allowed set is unknown, so nobody is claimed to be outside it (as before the floor)
            return []

    def note(self) -> str:
        try:
            allowed, below = self._audit()
        except Exception:  # noqa: BLE001 - the same: root's status and whoami answer as they did before the floor, whatever ORG.md says
            return ""
        if not below:
            return ""
        named = ", ".join(f"{addr} on {model}" for addr, model in below)
        return (
            f"Model floor: below the allowed models ({', '.join(allowed)}): {named}. Fix: set model: {DEFAULT_MODEL} in each one's AGENT.md "
            "(you for your direct reports, the manager for the others); they keep running as they are until then."
        )
