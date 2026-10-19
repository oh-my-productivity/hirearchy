"""The history of the messages from the index. (RED: skeleton.)"""

from __future__ import annotations

from ..mail import MessageIndex
from ._messages import Msg
from ._ports import MessageHistory


class IndexedMessageHistory(MessageHistory):
    def __init__(self, index: MessageIndex) -> None:
        self._index = index

    def messages(self) -> dict[str, Msg]:
        raise NotImplementedError("red: C-obs-1")
