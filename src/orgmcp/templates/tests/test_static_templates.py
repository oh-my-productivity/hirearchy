"""The two real implementations: stateless renderers that subclass their Protocol."""

from __future__ import annotations

import pytest

from orgmcp.templates import DocumentTemplates, Notices
from orgmcp.templates._documents import StaticDocumentTemplates
from orgmcp.templates._notices import StaticNotices

def test_they_subclass_the_protocol_they_implement() -> None:
    assert DocumentTemplates in StaticDocumentTemplates.__mro__ and Notices in StaticNotices.__mro__


def test_they_hold_no_state() -> None:
    assert vars(StaticDocumentTemplates()) == {} and vars(StaticNotices()) == {}


def test_two_instances_render_the_same_text() -> None:
    assert StaticDocumentTemplates().org_rules("m") == StaticDocumentTemplates().org_rules("m")
    assert StaticNotices().nudge("T-1", "t") == StaticNotices().nudge("T-1", "t")
