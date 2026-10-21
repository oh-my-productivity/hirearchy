"""``KiroConfinementPolicy``: which paths kiro's built-in ``read``/``write`` may use."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .api import FILE_TOOLS, ConfinementPolicy


class KiroConfinementPolicy(ConfinementPolicy):
    def file_confinement(
        self, org_root: Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]
    ) -> tuple[list[str], dict[str, object]]:
        """(allowedTools, toolsSettings) that confine kiro's built-in ``read``/``write`` by path.

        Verified against kiro-cli 2.29.1 (see README, "Workspaces, inputs and confinement"):
        * ``read``/``write`` must NOT be in ``allowedTools``: a tool there ignores ``allowedPaths``. Left out, a call inside
          ``allowedPaths`` runs unprompted and any other path asks for an approval, which ``--no-interactive`` cannot
          give, so it is refused.
        * ``write``: only under the workspace (``[]`` without one: nowhere). ``read``: workspace + inputs + the organization
          (read-only: hirearchy's own ``read`` may read anything in the org, and an agent that holds the built-in ``read``
          sees only that one: it hides hirearchy's ``read``, same short name, see studies/F-read-experiment); a directory
          needs both ``P`` and ``P/**`` to be listable.
        * ``deniedPaths`` on the org directory is a hard deny even for kiro's own "current directory is readable" rule:
          the org is never written with kiro's tools (hirearchy ``write`` does that), so ``write`` keeps the deny. ``read``
          has none: a deny would beat the allow above. Skipped when the workspace is inside the org.
        * ``shell`` stays in ``allowedTools`` and is NOT confined (kiro has no path rule for it).
        """
        org_root = Path(org_root).resolve()
        deny = [] if workspace is not None and (workspace == org_root or org_root in workspace.parents) else [str(org_root), f"{org_root}/**"]
        settings: dict[str, object] = {}
        if "write" in tools:
            settings["write"] = {"allowedPaths": [f"{workspace}/**"] if workspace is not None else [], "deniedPaths": deny}
        if "read" in tools:
            bases = [p for p in (workspace, *inputs, org_root) if p is not None]
            settings["read"] = {"allowedPaths": list(dict.fromkeys(x for p in bases for x in (str(p), f"{p}/**"))), "deniedPaths": []}
        return [t for t in tools if t not in FILE_TOOLS], settings
