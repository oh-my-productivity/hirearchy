"""``CharterModelResolver``: the model of a run: the charter's, else the organization's."""

from __future__ import annotations

from ..agents import CharterReader
from ..settings import OrgSettings
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
