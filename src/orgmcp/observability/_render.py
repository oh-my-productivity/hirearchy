"""The text of the views. (RED: skeleton.)"""

from __future__ import annotations

from ..kernel import JsonObject
from .api import ObservabilityRenderer


class TextObservabilityRenderer(ObservabilityRenderer):
    def render_events(self, view: JsonObject, max_lines: int | None = None) -> str:
        raise NotImplementedError("red: C-obs-2")

    def render_trace(self, tr: JsonObject, max_lines: int | None = None) -> str:
        raise NotImplementedError("red: C-obs-2")

    def render_metrics(self, m: JsonObject, limit: int = 50) -> str:
        raise NotImplementedError("red: C-obs-2")

    def render_now(self, v: JsonObject, max_lines: int | None = None) -> str:
        raise NotImplementedError("red: C-obs-2")

    def render_check(self, res: JsonObject) -> str:
        raise NotImplementedError("red: C-obs-2")
