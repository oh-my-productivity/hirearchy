"""An artifact of a report, checked and annotated (moved from ``Org._normalize_artifact``)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..access import AccessScopes
from ..kernel import OrgError, OrgLayout, inside, word_count
from ._protocols import ArtifactNormalizer


class ArtifactAnnotator(ArtifactNormalizer):
    """Inside the organization or the reporter's own workspace; shown with its words and its modification time."""

    def __init__(self, layout: OrgLayout, scopes: AccessScopes) -> None:
        self._layout = layout
        self._scopes = scopes

    def normalize(self, actor: str, path: str, since: str = "") -> str:
        """Resolve an artifact path and annotate it with facts a manager can check claims against.

        Inside the organization (paths relative to the org root, or absolute) or, as an absolute path, inside the
        reporter's own workspace. Anything else is refused before existence is checked: no probing of the host.
        """
        root = self._layout.root
        p = Path(path).expanduser()
        ws = self._scopes.workspace_of(actor)
        if not p.is_absolute():
            p = next((b / p for b in (root, self._layout.agent_dir(actor)) if (b / p).exists()), root / p)
        p = p.resolve()
        in_org = p == root or root in p.parents
        if not in_org and not (ws is not None and inside(p, ws)):
            where = f"inside your workspace ({ws})" if ws is not None else "(you have no workspace)"
            raise OrgError(
                f"artifacts must be inside the organization (paths relative to the org root) or, by absolute path, "
                f"{where}: {path}"
            )
        if not p.exists():
            hint = ""
            if ws is not None and not Path(path).expanduser().is_absolute() and (ws / path).exists():
                hint = f" It exists in your workspace: report it by absolute path ({(ws / path).resolve()})."
            raise OrgError(f"artifact not found: {path} (relative paths are relative to the org root).{hint}")
        shown = str(p.relative_to(root)) if in_org else str(p)
        if p.is_dir():
            return f"{shown}/ (directory)"
        modified = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
        note = f"{word_count(p.read_text(encoding='utf-8', errors='replace'))} words, modified {modified:%H:%M:%S} UTC"
        if since and modified.isoformat(timespec="seconds") < since:
            note += ", NOT modified since this task was assigned"
        return f"{shown} ({note})"
