"""The deliveries health counts, from the case records of ``reflection`` (design 10).

``health`` may not import ``reflection``, so the composition root converts: the deliveries, who signed them off and the cause of each escape are
``reflection``'s rules, read once; what counts against a verifier is ``reflection.attribution``. Nothing is decided here."""

from __future__ import annotations

from ..health._ports import Signed, SignedDelivery, SignedDeliveries
from ..reflection import CaseRecords, Cause, Delivery, attribution


class CaseSignedDeliveries(SignedDeliveries):
    def __init__(self, records: CaseRecords) -> None:
        self._records = records

    def deliveries(self, owner: str) -> Signed:
        found = self._records.deliveries(owner)
        return Signed(tuple(_signed(d, cause) for d, cause in zip(found.deliveries, found.causes, strict=True)), found.unknown)


def _signed(delivery: Delivery, cause: Cause | None) -> SignedDelivery:
    if cause is None:
        return SignedDelivery(delivery.signer, delivery.judged, delivery.escape, True, "")
    return SignedDelivery(delivery.signer, delivery.judged, delivery.escape, attribution(cause) == "counted", cause.type)
