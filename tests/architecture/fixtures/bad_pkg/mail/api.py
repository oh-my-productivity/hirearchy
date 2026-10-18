from typing import Protocol

__all__ = ["Mailbox"]


class Mailbox(Protocol):
    """Violation: no tests/test_contract_mailbox.py and no testing.IMPLEMENTATIONS entry."""

    def put(self, text: str) -> None: ...
