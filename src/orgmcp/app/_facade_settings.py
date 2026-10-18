"""ORG.md: the org root lookup, the settings block and the rules text (settings, locator).

The bodies call the ports of ``self.runtime`` (step A-settings; ARCHITECTURE.md 5.3 and 6.4). The constants and helpers that
``core.Org`` used to define here are the ``settings`` package's, re-exported under their old names for ``orgmcp.core``."""

from __future__ import annotations

from pathlib import Path

from ..settings import DEFAULT_CONFIG, DEFAULT_MODEL, config_default_model
from ..settings import config_message_cap as _message_cap
from .runtime import OrgRuntime
from .wire_locator import os_locator

__all__ = ["DEFAULT_CONFIG", "DEFAULT_MODEL", "SettingsMixin", "_message_cap", "config_default_model"]


class SettingsMixin:
    """ORG.md: the org root lookup, the settings block and the rules text (settings, locator)."""

    runtime: OrgRuntime

    @staticmethod
    def find_root(start: str | Path | None = None) -> Path:
        return os_locator().find_root(Path(start) if start else None)

    @property
    def config(self) -> dict[str, object]:
        return self.runtime.settings.config()

    def rules(self) -> str:
        return self.runtime.settings.rules()
