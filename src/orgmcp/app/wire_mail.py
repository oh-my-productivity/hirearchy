"""Providers of the ``mail`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from pathlib import Path

from ..agents import AgentDirectory
from ..kernel import AtomicWriter, OrgLayout
from ..mail import BatchStore, MailboxReader, MailboxWriter, MailFingerprint, MessageIndex, MessageParser, TaskQuery
from ..mail._batch import FsBatchStore
from ..mail._index import FsMessageIndex
from ..mail._mailbox import FsMailbox
from ..mail._tasks import DerivedTaskQuery
from ..mail._wakes import wakes
from ._builder import Builder
from ._resources import ProcessResources
from .wiring import process_resources


def register(b: Builder) -> None:
    b.provide(MessageParser, lambda b: b.get(ProcessResources).message_parser)  # the parse cache is shared by the whole process
    b.provide(MailboxReader, lambda b: FsMailbox(b.get(OrgLayout), b.get(MessageParser), b.get(AtomicWriter)))
    b.provide(MailboxWriter, lambda b: FsMailbox(b.get(OrgLayout), b.get(MessageParser), b.get(AtomicWriter)))
    b.provide(MailFingerprint, lambda b: FsMailbox(b.get(OrgLayout), b.get(MessageParser), b.get(AtomicWriter)))
    b.provide(
        BatchStore,
        lambda b: FsBatchStore(b.get(OrgLayout), b.get(AgentDirectory), b.get(MailboxReader), b.get(MessageParser), b.get(AtomicWriter)),
    )
    b.provide(TaskQuery, lambda b: DerivedTaskQuery(b.get(MailboxReader)))
    b.provide(MessageIndex, lambda b: FsMessageIndex(b.get(OrgLayout), b.get(AgentDirectory), b.get(ProcessResources).meta_cache))


def message_wakes(path: Path) -> bool:
    """Does the inbox file at ``path`` wake its agent? Read through the parser of this process (``Org._wakes`` is static: it has no runtime)."""
    return wakes(process_resources().message_parser, path)
