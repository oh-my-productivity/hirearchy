"""``wire_templates``: the runtime carries the real, pure implementations of the two ports of ``templates``."""

from __future__ import annotations

from pathlib import Path

from hirearchy.app import wiring
from hirearchy.templates import DocumentTemplates, Notices
from hirearchy.templates._documents import StaticDocumentTemplates
from hirearchy.templates._notices import StaticNotices
from hirearchy.templates.testing import RecordingNotices


def test_the_runtime_has_the_static_templates(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.document_templates, StaticDocumentTemplates) and isinstance(runtime.notices, StaticNotices)
    assert runtime.document_templates.charter_body("Builder", "x") == "# Role: Builder\n\nx\n"
    assert runtime.notices.nudge("T-1", "t").startswith("Task T-1 (t) is still open")


def test_an_override_replaces_a_port(tmp_path: Path) -> None:
    recording = RecordingNotices()
    runtime = wiring.open_runtime(tmp_path, {Notices: recording})
    assert runtime.notices is recording and isinstance(runtime.document_templates, DocumentTemplates)
