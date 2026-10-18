"""``wire_templates``: the runtime carries the real, pure implementations of the two ports of ``templates``."""

from __future__ import annotations

from pathlib import Path

from orgmcp.app import wiring
from orgmcp.templates import DocumentTemplates, Notices
from orgmcp.templates._documents import StaticDocumentTemplates
from orgmcp.templates._notices import StaticNotices
from orgmcp.templates.testing import RecordingNotices


def test_the_runtime_has_the_static_templates(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.documents, StaticDocumentTemplates) and isinstance(runtime.notices, StaticNotices)
    assert runtime.documents.charter_body("Builder", "x") == "# Role: Builder\n\nx\n"
    assert runtime.notices.nudge("T-1", "t").startswith("Task T-1 (t) is still open")


def test_an_override_replaces_a_port(tmp_path: Path) -> None:
    recording = RecordingNotices()
    runtime = wiring.open_runtime(tmp_path, {Notices: recording})
    assert runtime.notices is recording and isinstance(runtime.documents, DocumentTemplates)
