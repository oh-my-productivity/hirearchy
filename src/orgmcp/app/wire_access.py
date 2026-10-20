"""Providers of the ``access`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..access import AccessScopes, AuthorityPolicy, ModelResolver, ToolNaming
from ..access._authority import CharterAuthorityPolicy
from ..access._models import CharterModelResolver
from ..access._naming import CharterToolNaming
from ..access._scopes import CharterAccessScopes
from ..agents import AgentDirectory, CharterReader
from ..kernel import OrgLayout
from ..settings import OrgSettings
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(AccessScopes, lambda b: CharterAccessScopes(b.get(AgentDirectory), b.get(CharterReader)))
    b.provide(AuthorityPolicy, lambda b: CharterAuthorityPolicy(b.get(OrgLayout), b.get(CharterReader), b.get(AccessScopes)))
    b.provide(ToolNaming, lambda b: CharterToolNaming(b.get(CharterReader)))
    b.provide(ModelResolver, lambda b: CharterModelResolver(b.get(CharterReader), b.get(OrgSettings)))
