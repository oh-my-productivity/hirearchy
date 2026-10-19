"""``LiteralQuoter``: a task's body quoted verbatim (moved from ``Org._quote``)."""

from __future__ import annotations

from ..kernel import Message, OrgLayout
from ._ports import TaskQuoter


class LiteralQuoter(TaskQuoter):
    def __init__(self, layout: OrgLayout) -> None:
        self._root = layout.root

    def quote(self, m: Message) -> str:
        raise NotImplementedError("red: C-prompts")
