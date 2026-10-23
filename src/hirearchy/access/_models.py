"""``CharterModelResolver``: the model of a run: the charter's, else the organization's."""

from __future__ import annotations

from ..agents import CharterReader
from ..settings import DEFAULT_EFFORT, OrgSettings, config_effort
from .api import ModelResolver


class CharterModelResolver(ModelResolver):
    def __init__(self, charters: CharterReader, settings: OrgSettings) -> None:
        self._charters = charters
        self._settings = settings

    def default_model(self) -> str:
        return self._settings.default_model()

    def model_for(self, addr: str) -> str:
        meta, _ = self._charters.charter(addr)
        return str(meta.get("model") or "").strip() or self.default_model()

    def effort(self) -> str:
        try:
            return config_effort(self._settings.config())
        except Exception:  # noqa: BLE001 - ORG.md that does not parse: the built-in effort, so a run is neither refused nor skipped (it shows in the run's cmd)
            return DEFAULT_EFFORT
