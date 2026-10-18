"""The safe summary of the arguments of a tool call."""

from __future__ import annotations

from collections.abc import Mapping

from ..kernel import JsonObject
from .api import ArgumentSummarizer


class JsonArgumentSummarizer(ArgumentSummarizer):
    def summarize(self, arguments: Mapping[str, object]) -> JsonObject:
        raise NotImplementedError("red: A-telemetry")
