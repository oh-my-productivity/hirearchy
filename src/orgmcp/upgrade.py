"""Bring an existing organization's rules up to the current template.

``ORG.md`` holds a copy of the rules from the time the organization was created, so an organization does not get
rules added later. ``upgrade_rules`` rewrites only the body of ``ORG.md`` from the current template, keeping the
frontmatter byte for byte (settings, comments) and the mission text the organization already has.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from . import templates
from .core import Org, OrgError, atomic_write

MISSION_HEADING = "## Mission\n"
RULES_HEADING = "\n## How this organization works"


@dataclass
class Upgrade:
    changed: bool
    added: int
    removed: int
    diff: list[str]  # unified diff of the body, without the file headers
    written: bool

    def text(self, max_diff_lines: int = 80) -> str:
        if not self.changed:
            return "ORG.md rules are already up to date; nothing to change."
        verb = "rewrote" if self.written else "would rewrite"
        head = (f"{verb} the rules in ORG.md: +{self.added} -{self.removed} lines "
                "(frontmatter and mission unchanged)")
        shown = self.diff[:max_diff_lines]
        more = [f"... {len(self.diff) - max_diff_lines} more diff lines"] if len(self.diff) > max_diff_lines else []
        return "\n".join([head, *shown, *more])


def _split_raw(text: str) -> tuple[str, str]:
    """(frontmatter exactly as written including the closing line, body)."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[: end + 5], text[end + 5 :]
    return "", text


def extract_mission(body: str) -> str:
    """The mission text of an ORG.md body made from the rules template."""
    start = body.find(MISSION_HEADING)
    if start == -1:
        raise OrgError("ORG.md has no '## Mission' section, so the rules cannot be upgraded automatically; "
                       "edit ORG.md by hand")
    start += len(MISSION_HEADING)
    end = body.find(RULES_HEADING, start)
    if end == -1:  # the rules heading was edited away: stop at the next level-2 heading instead
        end = body.find("\n## ", start)
    return (body[start:] if end == -1 else body[start:end]).strip()


def upgrade_rules(org: Org, dry_run: bool = False) -> Upgrade:
    """Rewrite the body of ORG.md to the current rules template (the mission is kept). ``dry_run`` writes nothing."""
    path = org.root / "ORG.md"
    text = path.read_text(encoding="utf-8")
    front, body = _split_raw(text)
    new_body = templates.org_rules(extract_mission(body)).rstrip() + "\n"
    old_lines, new_lines = body.rstrip().splitlines(), new_body.rstrip().splitlines()
    diff = [ln for ln in difflib.unified_diff(old_lines, new_lines, "ORG.md (current)", "ORG.md (new)", lineterm="", n=1)][2:]
    added = sum(1 for ln in diff if ln.startswith("+"))
    removed = sum(1 for ln in diff if ln.startswith("-"))
    changed = body.rstrip() != new_body.rstrip()
    if changed and not dry_run:
        atomic_write(path, front + new_body)
        org.commit("root: upgrade ORG.md rules to the current template")
    return Upgrade(changed, added, removed, diff, written=changed and not dry_run)
