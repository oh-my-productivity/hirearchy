"""RED skeleton (step A-processes): the verdict on the process recorded for a run of a dead scheduler."""

from __future__ import annotations

from collections.abc import Mapping

from .api import OrphanJudge, ProcessInspector


class PsOrphanJudge(OrphanJudge):
    def __init__(self, inspector: ProcessInspector) -> None:
        raise NotImplementedError

    def judge(self, record: Mapping[str, object]) -> str:
        raise NotImplementedError
