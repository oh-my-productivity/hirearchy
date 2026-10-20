"""``HashPlanIdentity``: which blueprint a plan was made for."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from ._loader import normalize
from ._plan_texts import PLAN_ID_LENGTH
from .api import PlanIdentity


class HashPlanIdentity(PlanIdentity):
    def plan_id(self, bp: Mapping[str, object]) -> str:
        """A short stable hash of the normalized blueprint: the same blueprint (whatever its YAML layout, comments or
        key order) always gives the same id; any change to a value gives another. ``apply_org`` requires it, so what is
        applied is what ``propose_org`` showed. Stateless: nothing is stored, it survives restarts."""
        canon = json.dumps(normalize(bp), sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:PLAN_ID_LENGTH]
