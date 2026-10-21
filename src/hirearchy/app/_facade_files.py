"""Guarded reading and writing of org files (orgfiles).

The bodies call the ports of ``self.runtime`` (step B-orgfiles; ARCHITECTURE.md 5.3 and 6.4). The helpers that ``core.Org`` used to
define in this module (``_short``, ``charter_change_note``, ``_fold``, ``_case_twin``, ``_FOLDED_RUNTIME_NAMES``, ``_EXACT_FILES``) are the
``orgfiles`` package's, re-exported under their old names for ``hirearchy.core`` (``_case_twin`` is ``case_twin_in``)."""

from __future__ import annotations

from pathlib import Path

from ..orgfiles._charter_merge import _short, charter_change_note
from ..orgfiles._guard import _EXACT_FILES, _FOLDED_RUNTIME_NAMES, _fold
from ..orgfiles._guard import case_twin_in as _case_twin
from .runtime import OrgRuntime

__all__ = ["FilesMixin", "_EXACT_FILES", "_FOLDED_RUNTIME_NAMES", "_case_twin", "_fold", "_short", "charter_change_note"]


class FilesMixin:
    """Guarded reading and writing of org files (orgfiles)."""

    runtime: OrgRuntime

    def resolve_read(self, path: str, actor: str | None = None) -> Path:
        """Relative paths are relative to the org root. Absolute paths must be inside the organization or, for an agent,
        inside its workspace or inputs or the workspace of an agent in its subtree. Root reads the organization only."""
        return self.runtime.org_file_reader.resolve_read(path, actor)

    def read(self, path: str, actor: str | None = None) -> str:
        return self.runtime.org_file_reader.read(path, actor)

    def resolve_write(self, actor: str, path: str) -> Path:
        """Paths are relative to the org root (like every path in the org) and must be inside your directory."""
        return self.runtime.org_file_writer.resolve_write(actor, path)

    def write(self, actor: str, path: str, content: str, append: bool = False) -> Path:
        return self.runtime.org_file_writer.write(actor, path, content, append)

    def write_noted(self, actor: str, path: str, content: str, append: bool = False) -> tuple[Path, str]:
        """:meth:`write`, plus a note for the writer (non-empty only for a charter rewrite: what was kept/changed).

        A parent rewriting a report's charter does not strip its frontmatter: every key of the old frontmatter that
        the new text does not set is kept (a key the new text sets, even to an empty value, wins). The authority
        checks run on the merged frontmatter.
        """
        return self.runtime.org_file_writer.write_noted(actor, path, content, append)
