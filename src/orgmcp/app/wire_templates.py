"""Providers of the ports of ``templates`` (ARCHITECTURE.md 3.2): the documents and the notices are pure, so they take no collaborators."""

from __future__ import annotations

from ..templates import DocumentTemplates, Notices
from ..templates._documents import StaticDocumentTemplates
from ..templates._notices import StaticNotices
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(DocumentTemplates, lambda b: StaticDocumentTemplates())
    b.provide(Notices, lambda b: StaticNotices())
