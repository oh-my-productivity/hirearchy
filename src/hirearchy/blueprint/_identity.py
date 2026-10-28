"""``HashPlanIdentity``: which blueprint a plan was made for."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from ._loader import normalize
from ._plan_texts import PLAN_ID_LENGTH
from ._protocols import Fingerprinting
from .api import PlanIdentity, is_extension


class HashPlanIdentity(PlanIdentity):
    def __init__(self, fingerprint: Fingerprinting | None = None) -> None:
        self._fingerprint = fingerprint

    def plan_id(self, bp: Mapping[str, object]) -> str:
        """A short stable hash of the normalized blueprint: the same blueprint (whatever its YAML layout, comments or
        key order) always gives the same id; any change to a value gives another. ``apply_org`` requires it, so what is
        applied is what ``propose_org`` showed. Stateless: nothing is stored, it survives restarts.

        An extension of the current organization (design 5.4) is hashed together with the fingerprint of the parts of the organization it touches, so
        its id goes stale when one of them changes; a full blueprint's id does not depend on the organization."""
        blueprint = normalize(bp)
        if is_extension(blueprint) and self._fingerprint is not None:
            canon = json.dumps({"extension": blueprint, "fingerprint": self._fingerprint.fingerprint(blueprint)}, sort_keys=True, ensure_ascii=True,
                               separators=(",", ":"), default=str)
        else:
            canon = json.dumps(blueprint, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:PLAN_ID_LENGTH]
