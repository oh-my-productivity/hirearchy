"""``CharterAuthorityPolicy``: what a grantor may hand down, judged by its own charter."""

from __future__ import annotations

from collections.abc import Sequence

from ..agents import CharterReader
from ..kernel import OrgLayout
from .api import AccessScopes, AuthorityPolicy


class CharterAuthorityPolicy(AuthorityPolicy):
    def __init__(self, paths: OrgLayout, charters: CharterReader, scopes: AccessScopes) -> None:
        self._paths = paths
        self._charters = charters
        self._scopes = scopes

    def check_authority(self, actor: str, tools: Sequence[str], workspace: str | None, inputs: Sequence[str] | None = None) -> None:
        raise NotImplementedError

    def check_inputs(self, inputs: object) -> list[str]:
        raise NotImplementedError
