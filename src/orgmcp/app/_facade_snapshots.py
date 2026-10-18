"""Git snapshots of the organization (snapshots).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

import subprocess


class SnapshotsMixin:
    """Git snapshots of the organization (snapshots)."""

    def commit(self, message: str) -> None:
        """Snapshot the organization in git (if it is a repo). Called by the runtime after each run."""
        if not (self.root / ".git").exists():
            return
        git = ["git", "-c", "user.name=orgmcp", "-c", "user.email=orgmcp@localhost"]
        subprocess.run([*git, "add", "-A"], cwd=self.root, capture_output=True)
        subprocess.run([*git, "commit", "-q", "-m", message], cwd=self.root, capture_output=True)
