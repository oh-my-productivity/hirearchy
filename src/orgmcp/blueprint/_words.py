"""``ServiceWords``: the sentences about services that the block for the user and the details have in common."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import os

from ..kernel import OrgError
from ..services import ContractNormalizer
from ._protocols import PlanWords
from ._rules import delivers_directly, is_code
from ._text import clip
from ._view import mapping_or_empty, needs_of, s, svc_deliverable, task_of
from .api import Agent


class ServiceWords(PlanWords):
    def __init__(self, normalizer: ContractNormalizer) -> None:
        self._normalizer = normalizer

    def input_words(self, sv: Mapping[str, object]) -> str:
        try:
            ins = self._normalizer.inputs(sv.get("inputs"))
        except OrgError:
            return "(see the errors)"
        return ", ".join(f"{i['name']} ({'required' if i['required'] else 'optional'})" for i in ins) or "nothing: every request is the same"

    def delivery(self, sv: Mapping[str, object], agents: Sequence[Agent], bp: Mapping[str, object]) -> str:
        path = s(svc_deliverable(sv).get("path"))
        if not path:
            ws = s(needs_of(bp).get("workspace"))
            if ws and is_code(bp):
                return f"the workspace {ws} (the team works and commits there)"
            return "inside the organization folder (no location given)"
        p = Path(os.path.expanduser(path))
        direct = p.is_absolute() and delivers_directly(agents, p.resolve())
        return f"{path} " + ("(the team writes it there)" if direct else "(I copy each result there after checking it)")

    def request_words(self, bp: Mapping[str, object]) -> str:
        ins = mapping_or_empty(task_of(bp).get("inputs"))
        return ", ".join(f"{k}: {clip(v, 80)}" for k, v in ins.items() if s(v))

    def reflection_line(self, owner: str) -> str:
        who = "the lead" if owner == "lead" else f"the lead ({owner})"
        return (f"After each request {who} records lessons; before the next one it reviews them with your feedback and may improve how the team "
                "works (its playbook). It cannot change these checks: only you can, through me.")
