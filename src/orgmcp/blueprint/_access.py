"""``PolicyAccessReport``: what the runtime lets an agent reach with kiro's file tools, asked of the same policy that writes the profile."""
from __future__ import annotations
from collections.abc import Collection, Iterable
from pathlib import Path
from typing import cast
from ..kiro import ConfinementPolicy
from ._protocols import AccessReport
from ._shapes import AccessFacts
from ._view import mapping_or_empty
from .api import Agent
ORG_PLACEHOLDER = Path('/orgmcp-org-root')

class PolicyAccessReport(AccessReport):

    def __init__(self, policy: ConfinementPolicy) -> None:
        self._policy = policy

    def org_files_readable(self, a: Agent) -> bool:
        """Can this agent open files in the organization (its own and its teammates' ``work/``) with the tools it holds?

        Without built-in ``read`` it uses orgmcp's ``read``. With it, the built-in ``read`` is the only ``read`` the model
        sees (it hides orgmcp's, same short name), so the answer comes from what the runtime really allows it: the same
        confinement policy that writes the profile, asked about a stand-in org directory.
        """
        raise NotImplementedError('red: C-blueprint-1')

    def facts(self, a: Agent) -> AccessFacts:
        """What the runtime lets this agent reach with kiro's file tools: the ONE computation behind both the technical
        ``Access:`` line (``line``, in the details and each agent's prompt) and the plain-words line of the PLAN FOR YOU,
        so the user is shown exactly what is enforced. Mirrors the confinement policy: ``write`` only under the workspace,
        ``read`` in workspace + inputs + the organization (read-only), ``shell`` not confined.
        """
        raise NotImplementedError('red: C-blueprint-1')

    def line(self, a: Agent) -> str:
        """One line on what the runtime lets this agent reach with kiro's file tools (and what it only instructs)."""
        raise NotImplementedError('red: C-blueprint-1')
