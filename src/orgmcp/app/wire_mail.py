"""Providers of the ``mail`` ports (ARCHITECTURE.md 6.1), and the dashboard's lenient variant for the legacy ``LenientOrg``.

``lenient`` goes away with ``LenientOrg`` (C-dashdata), whose caching roles for the mailboxes are the decorator of this package.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from ..agents import AgentDirectory
from ..kernel import AtomicWriter, OrgLayout
from ..mail import BatchStore, MailboxReader, MailboxWriter, MailFingerprint, MessageIndex, MessageParser, TaskQuery
from ..mail._batch import FsBatchStore
from ..mail._caching import DirectoryProbe, DirMtimeCachingMailbox
from ..mail._index import FsMessageIndex
from ..mail._mailbox import FsMailbox
from ..mail._tasks import DerivedTaskQuery
from ..mail._wakes import wakes
from ._builder import Builder
from ._resources import ProcessResources
from .runtime import OrgRuntime
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


def lenient(runtime: OrgRuntime, probe: DirectoryProbe) -> tuple[OrgRuntime, DirMtimeCachingMailbox]:
    """``runtime`` with the dashboard's decorator on the mailbox reader (the boxes read per change of their directory, ``probe`` tells
    when; files that do not parse are left out and listed in the decorator's ``bad``), the task views derived from it, and the index
    walking the agents of ``runtime`` (so the lenient ones, when ``wire_agents.lenient`` was applied first)."""
    mailbox = DirMtimeCachingMailbox(runtime.mailbox, runtime.paths, runtime.message_parser, probe, runtime.clock)
    index = FsMessageIndex(runtime.paths, runtime.agents, runtime.resources.meta_cache)
    return dataclasses.replace(runtime, mailbox=mailbox, task_query=DerivedTaskQuery(mailbox), message_index=index), mailbox


def message_wakes(path: Path) -> bool:
    """Does the inbox file at ``path`` wake its agent? Read through the parser of this process (``Org._wakes`` is static: it has no runtime)."""
    return wakes(process_resources().message_parser, path)
