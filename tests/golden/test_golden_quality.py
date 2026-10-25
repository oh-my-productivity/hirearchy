"""The quality view's goldens (0b 9.3). The pre-registered samples (the two empty ones, A5's one-off block, E3's text) are copied by hand from the design,
never generated; the replays build their organizations with ``testkit.org_replay`` from the files the studies kept."""

from __future__ import annotations

import json
import re
import shutil

import pytest
from golden_support import check
from scenarios import BRIEF, PLAYBOOK
from testkit.org_replay import materialize
from testkit.org_replay_manifest import MANIFESTS
from testkit.quality_schema import problems

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


def e3_data(tmp_path) -> tuple[str, dict]:
    """The text and the JSON of the view on E3's kept files."""
    quality = Org(materialize("E3", tmp_path)).runtime.quality_report
    return quality.quality_text(), json.loads(json.dumps(quality.quality_data()))


def test_e3_text(tmp_path) -> None:
    """E3-5 (design 19.3): the text on E3's kept files equals 9.3's E3 sample byte for byte. The golden is the design's sample, copied by hand (method P)."""
    check("quality/e3.txt", e3_data(tmp_path)[0] + "\n")


def test_e3_json(tmp_path) -> None:
    """E3-8: `quality --json` on E3's kept files, `json.dumps(data, indent=2, sort_keys=True)`. Generated once with HIREARCHY_UPDATE_GOLDEN=1 (method N) and
    reviewed key by key against 9.4 and the E3 text sample."""
    check("quality/e3.json", json.dumps(e3_data(tmp_path)[1], indent=2, sort_keys=True) + "\n")


def test_every_corpus_conforms_to_the_schema(tmp_path) -> None:
    """E3-8, DR3-3: the JSON of every replay corpus (the seven of the manifest and E3's two constructed variants) conforms to 9.4: its keys, types and null
    rules, through `testkit.quality_schema.problems`; and so does an error record (a service whose SERVICE.md does not parse: `budget` null, `alarms` empty,
    `history` null)."""
    found: dict[str, list[str]] = {}
    for name, (corpus, variant) in {
        **{corpus: (corpus, None) for corpus in MANIFESTS}, "E3 r2-links-r1": ("E3", "r2-links-r1"), "E3 r3-overspend-12": ("E3", "r3-overspend-12"),
    }.items():
        (tmp_path / name).mkdir()
        found[name] = problems(Org(materialize(corpus, tmp_path / name, variant)).runtime.quality_report.quality_data())
    assert found == {name: [] for name in found}
    broken = materialize("E3", tmp_path / "error")
    (broken / "lead" / "services" / "weekly-meeting-memo" / "SERVICE.md").write_text("---\nkey: [unclosed\n---\nbody\n", encoding="utf-8")
    data = json.loads(json.dumps(Org(broken).runtime.quality_report.quality_data()))
    (record,) = data["services"]
    assert record["error"].startswith("SERVICE.md: does not parse") and (record["budget"], record["alarms"], record["history"]) == (None, {}, None)
    assert problems(data) == []


def test_e3_json_counts_equal_the_text_figures(tmp_path) -> None:
    """E3-8: every count of the JSON equals the figure of the E3 text sample that 9.4's source column names (the design's list), and the figures are those
    the text prints."""
    text, data = e3_data(tmp_path)
    (record,) = data["services"]
    assert (record["deliveries"]["total"], record["deliveries"]["judged"]) == (6, 5)
    assert [c["user_cost"] for c in record["cases"]] == [12, 5, 14] and [c["user_approved"] for c in record["cases"]] == [15, 15, 20]
    assert [c["relayed_runs"] for c in record["cases"]] == [0, 10, 0] and [c["spend"] for c in record["cases"]] == [12, 15, 14]
    assert [c["ratio"] for c in record["cases"]] == ["0.80", "0.33", "0.70"]
    assert record["alarms"]["cost"]["compared"] == 3
    assert record["alarms"]["repeat"]["not_counted"] == {"R1": ["C6", "C3"]}
    assert record["verifiers"][0]["pass_precision"] == [5, 5]
    # ... and each is the figure the text prints
    lines = text.splitlines()
    printed = [re.search(r"^    (\S+) .*: (\d+) of (\d+) approved \((\d\.\d\d)x\)", line) for line in lines if " approved (" in line and line.startswith("    2026")]
    assert [(m[1], int(m[2]), int(m[3]), m[4]) for m in printed if m] == [(c["id"], c["user_cost"], c["user_approved"], c["ratio"]) for c in record["cases"]]
    assert [m[0] for m in [re.search(r"total (\d+)$", line) for line in lines if "your relayed reworks:" in line] if m] == ["total 15"]
    (judged_line,) = [line for line in lines if line.startswith("  judged by the user:")]
    assert judged_line.startswith(f"  judged by the user: {record['deliveries']['judged']} of {record['deliveries']['total']} deliveries;")
    (verifier,) = record["verifiers"]
    (verifier_line,) = [line for line in lines if line.startswith("    lead/reviewer:")]
    not_its = ", ".join(f"{n} {cause}" for cause, n in verifier["escapes"]["not_its"].items())
    assert verifier_line.startswith(
        f"    {verifier['addr']}: escapes {sum(verifier['escapes']['counted'].values())} of {verifier['judged']} judged; not its: {not_its}; "
        f"PASS precision {verifier['pass_precision'][0]} of {verifier['pass_precision'][1]}; its FAILs before delivery: "
        f"{verifier['rechecks']} re-check(s), {verifier['rework_runs']} author rework run(s)"
    )
    assert f"    cost: no (0 of {record['alarms']['cost']['compared']} cases above 1.25x)" in lines
    assert f"  escapes (the team reported done, then the user rejected it): {len(record['escapes'])}" in lines
