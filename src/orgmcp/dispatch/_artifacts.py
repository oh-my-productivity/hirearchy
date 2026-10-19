"""An artifact of a report, checked and annotated. Skeleton: RED."""

from __future__ import annotations

from ..access import AccessScopes
from ..kernel import OrgLayout
from ._protocols import ArtifactNormalizer


class ArtifactAnnotator(ArtifactNormalizer):
    """Inside the organization or the reporter's own workspace; shown with its words and its modification time."""

    def __init__(self, layout: OrgLayout, scopes: AccessScopes) -> None:
        self._layout = layout
        self._scopes = scopes

    def normalize(self, actor: str, path: str, since: str = "") -> str:
        raise NotImplementedError
