"""Providers of the ``settings`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

from ..kernel import AtomicWriter, OrgLayout
from ..settings import EventSwitch, OrgDocumentStore, OrgLimits, OrgSettings
from ..settings._fs import FsOrgSettings
from ..settings._stamp import FsOrgDocumentStamp
from ..settings._switch import StampedEventSwitch
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(OrgSettings, lambda b: FsOrgSettings(b.get(OrgLayout), b.get(AtomicWriter)))
    b.provide(OrgDocumentStore, lambda b: FsOrgSettings(b.get(OrgLayout), b.get(AtomicWriter)))
    b.provide(OrgLimits, lambda b: FsOrgSettings(b.get(OrgLayout), b.get(AtomicWriter)))
    b.provide(EventSwitch, lambda b: StampedEventSwitch(FsOrgDocumentStamp(b.get(OrgLayout)), b.get(OrgDocumentStore)))
