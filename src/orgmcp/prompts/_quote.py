"""``LiteralQuoter``: a task's body quoted verbatim (moved from ``Org._quote``)."""

from __future__ import annotations

from ..kernel import Message, OrgLayout
from ._ports import TaskQuoter


class LiteralQuoter(TaskQuoter):
    def __init__(self, layout: OrgLayout) -> None:
        self._root = layout.root

    def quote(self, m: Message) -> str:
        """Quote a task's body verbatim, so its own headings do not mix with the prompt's structure.

        A very long body is cut like ``Message.render`` does, with the real path of the file to read the rest."""
        where = str(m.path.relative_to(self._root)) if m.path and m.path.is_relative_to(self._root) else None
        return "\n".join(f"> {line}".rstrip() for line in m.cut_body(where=where).strip().splitlines())
