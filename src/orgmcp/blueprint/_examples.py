"""``TemplateBlueprintExamples``: the ready-to-edit blueprint templates."""

from __future__ import annotations

from pathlib import Path

from .api import BlueprintExamples


class TemplateBlueprintExamples(BlueprintExamples):
    def example(self, kind: str = "research", base: Path | str = ".", service: bool = False) -> str:
        raise NotImplementedError
