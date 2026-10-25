"""The quality view's goldens (0b 9.3). The pre-registered samples (the two empty ones, A5's one-off block, E3's text) are copied by hand from the design,
never generated; the replays build their organizations with ``testkit.org_replay`` from the files the studies kept."""

from __future__ import annotations

import shutil

from golden_support import check
from scenarios import BRIEF, PLAYBOOK
from testkit.org_replay import materialize

from hirearchy.core import ROOT, Org


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


def test_a5_one_off_block(tmp_path) -> None:
    """A5-4 (design 19.3): the one-off block the view prints on A5's kept files equals the block of 9.3's A5 sample byte for byte. A5 kept no run log, so
    its done, uncut case reads `runs not counted (no run log in its window)`. The golden is the design's sample, copied by hand (method P)."""
    text = Org(materialize("A5", tmp_path)).runtime.quality_report.quality_text()
    (block,) = [part for part in text.split("\n\n") if part.startswith("One-off tasks you gave (")]
    check("quality/a5_one_off_block.txt", block + "\n")
