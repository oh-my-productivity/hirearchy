"""Git snapshots of the organization (snapshots).

``commit`` delegates to ``OrgSnapshotter`` (ARCHITECTURE.md 5.3 and 6.4)."""

from __future__ import annotations

from .runtime import OrgRuntime


class SnapshotsMixin:
    """Git snapshots of the organization (snapshots)."""

    runtime: OrgRuntime

    def commit(self, message: str) -> None:
        """Snapshot the organization in git (if it is a repo). Called by the runtime after each run."""
        return self.runtime.snapshotter.commit(message)
