"""What an upgrade of the rules did (or, in a dry run, would do)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class UpgradeView(Protocol):
    def text(self, max_diff_lines: int = 80) -> str:
        """The report for the user: nothing to change, or what was (would be) rewritten and the start of the diff."""
        ...


@dataclass
class Upgrade(UpgradeView):
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
