"""``TextHealthRenderer``: the human report of an organization's health."""

from __future__ import annotations

from .api import HealthRenderer, OrgHealth


class TextHealthRenderer(HealthRenderer):
    def render_text(self, health: OrgHealth) -> str:
        raise NotImplementedError("red: C-health")
