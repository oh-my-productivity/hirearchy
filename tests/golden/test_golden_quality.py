"""The quality view's goldens (0b 9.3). The two empty samples are pre-registered: their files are copied by hand from the design, never generated."""

from __future__ import annotations

import shutil

from golden_support import check
from scenarios import BRIEF, PLAYBOOK

from hirearchy.core import ROOT


def test_empty_org(gorg, norm) -> None:
    """An organization with no service and no task, and an ORG.md whose settings block does not parse."""
    (gorg.root / "ORG.md").write_text("---\nkey: [unclosed\n---\nMission.\n", encoding="utf-8")
    check("quality/empty_org.txt", norm(gorg.runtime.quality_report.quality_text()) + "\n")


def test_empty_service(gorg, norm) -> None:
    """One top-level agent offering `weekly-report`, defined with its playbook at the clock's start; no request, no git."""
    gorg.hire(ROOT, "lead", "Lead", "Run the reports.", can_hire=True, max_children=2)
    gorg.define_service(ROOT, "lead", "weekly-report", playbook=PLAYBOOK, **BRIEF)
    shutil.rmtree(gorg.root / ".git")  # `Org.init` makes the organization a git repository; the sample is one without history
    check("quality/empty_service.txt", norm(gorg.runtime.quality_report.quality_text()) + "\n")
