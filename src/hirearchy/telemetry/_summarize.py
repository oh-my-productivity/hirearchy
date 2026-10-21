"""The safe summary of the arguments of a tool call."""

from __future__ import annotations

from collections.abc import Mapping

from ..kernel import TITLE_MAX, JsonObject, clip
from .api import ArgumentSummarizer

# String arguments that are short identifiers (ids, addresses, names, paths, verdicts): kept, clipped.
_KEEP_STR = {
    "to": 200, "task_id": 200, "status": 40, "name": 80, "owner": 200, "service": 80, "verdict": 20, "report": 200,
    "agent": 200, "path": 300, "reply_to": 200, "revises": 200, "view": 40, "target": 200, "since": 80, "until": 80,
    "by": 40, "model": 80, "workspace": 300, "kind": 40, "plan_id": 80, "role": 80, "title": TITLE_MAX,
}
# Lists of short strings that are kept (paths, tool names).
_KEEP_LIST = {"inputs", "artifacts", "tools"}


class JsonArgumentSummarizer(ArgumentSummarizer):
    """Ids, addresses, titles (clipped), statuses, budgets, paths, service names, verdicts, booleans and numbers as they are; any other
    text only as its length (``body_chars``); dicts as their keys (``inputs_keys``); other lists as their length (``acceptance_n``)."""

    def summarize(self, arguments: Mapping[str, object]) -> JsonObject:
        out: JsonObject = {}
        for name, value in arguments.items():
            if value is None:
                continue  # an argument left at its default says nothing
            if isinstance(value, (bool, int, float)):
                out[name] = value
            elif isinstance(value, str):
                if name in _KEEP_STR:
                    out[name] = clip(value, _KEEP_STR[name])
                else:
                    out[f"{name}_chars"] = len(value)
            elif isinstance(value, dict):
                out[f"{name}_keys"] = [clip(k, 60) for k in list(value)[:20]]
            elif isinstance(value, (list, tuple)):
                if name in _KEEP_LIST and all(isinstance(v, str) for v in value):
                    out[name] = [clip(v, 200) for v in value[:20]] + (["…"] if len(value) > 20 else [])
                else:
                    out[f"{name}_n"] = len(value)
                    chars = sum(len(v) for v in value if isinstance(v, str))
                    if chars:
                        out[f"{name}_chars"] = chars
            else:
                out[f"{name}_type"] = type(value).__name__
        return out
