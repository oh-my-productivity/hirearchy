"""``HashPlanIdentity``: which blueprint a plan was made for."""

from __future__ import annotations

from collections.abc import Mapping

from .api import PlanIdentity


class HashPlanIdentity(PlanIdentity):
    def plan_id(self, bp: Mapping[str, object]) -> str:
        raise NotImplementedError
