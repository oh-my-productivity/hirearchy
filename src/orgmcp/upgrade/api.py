"""The public surface of ``upgrade``: bringing an organization's ORG.md rules up to the current template.

``ORG.md`` holds a copy of the rules from the time the organization was created, so an organization does not get rules added later.
``RulesUpgrader`` rewrites only the body from the current template and reports what it did (``Upgrade``).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ._report import Upgrade, UpgradeView

__all__ = ["RulesUpgrader", "Upgrade", "UpgradeView"]


@runtime_checkable
class RulesUpgrader(Protocol):
    def upgrade_rules(self, dry_run: bool = False) -> Upgrade:
        """Rewrite the body of ORG.md to the current rules template: the frontmatter byte for byte (settings, comments), the mission the
        organization already has. A changed ORG.md is committed (``root: upgrade ORG.md rules to the current template``). ``dry_run``
        writes and commits nothing. ``OrgError`` when the body has no ``## Mission`` section: nothing is changed."""
        ...
