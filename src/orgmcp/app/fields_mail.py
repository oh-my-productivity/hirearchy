"""Runtime fields of ``mail`` (ARCHITECTURE.md 3.10): one field per port that ``wire_mail.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..mail import BatchStore, MailboxReader, MailboxWriter, MailFingerprint, MessageIndex, MessageParser, TaskQuery

STEP: str | None = "A-mail"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    message_parser: MessageParser
    mailbox: MailboxReader
    mailbox_writer: MailboxWriter
    batches: BatchStore
    task_query: TaskQuery  # not ``tasks``: a generic name another package may want
    mail_fingerprint: MailFingerprint
    message_index: MessageIndex
