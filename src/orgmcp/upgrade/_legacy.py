"""The old module-level names of ``orgmcp.upgrade``.

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``). ``upgrade_rules`` still takes an ``Org``: a duck-typed one, because no
feature may import the facade."""

from __future__ import annotations

import difflib

from .. import templates
from ._host import UpgradedOrg
from ._report import Upgrade
from ._rules import MISSION_HEADING, RULES_HEADING, extract_mission, split_raw

__all__ = ["MISSION_HEADING", "RULES_HEADING", "extract_mission", "upgrade_rules"]


def upgrade_rules(org: UpgradedOrg, dry_run: bool = False) -> Upgrade:
    """Rewrite the body of ORG.md to the current rules template (the mission is kept). ``dry_run`` writes nothing."""
    documents = org.runtime.documents
    text = documents.read_raw()
    front, body = split_raw(text)
    new_body = templates.org_rules(extract_mission(body)).rstrip() + "\n"
    old_lines, new_lines = body.rstrip().splitlines(), new_body.rstrip().splitlines()
    diff = [ln for ln in difflib.unified_diff(old_lines, new_lines, "ORG.md (current)", "ORG.md (new)", lineterm="", n=1)][2:]
    added = sum(1 for ln in diff if ln.startswith("+"))
    removed = sum(1 for ln in diff if ln.startswith("-"))
    changed = body.rstrip() != new_body.rstrip()
    if changed and not dry_run:
        documents.write_raw(front + new_body)
        org.commit("root: upgrade ORG.md rules to the current template")
    return Upgrade(changed, added, removed, diff, written=changed and not dry_run)
