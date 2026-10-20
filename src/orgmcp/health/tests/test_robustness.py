# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
from testkit.health_world import agent_health, org_health, thresholds
from testkit.legacy.orgmcp.core import ROOT, join_frontmatter, split_frontmatter, utcnow


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


@pytest.mark.parametrize("bad", ["1h", None, [], {}, True, float("nan"), "nan", float("inf")])
def test_bad_health_thresholds_fall_back_to_defaults(org, bad):
    configure(org, health={"idle_after_seconds": bad, "max_runs_per_task": bad, "min_runs_for_waste": 7})
    limits = thresholds(org)
    assert limits["idle_after_seconds"] == 86400 and limits["max_runs_per_task"] == 5
    assert limits["min_runs_for_waste"] == 7
    org_health(org)  # no TypeError
    agent_health(org, "ceo")


def test_numeric_string_thresholds_are_accepted(org):
    configure(org, health={"idle_after_seconds": "120", "max_problem_ratio": "0.25"})
    assert thresholds(org)["idle_after_seconds"] == 120 and thresholds(org)["max_problem_ratio"] == 0.25


def write_run(org, addr, i, text):
    (org.dir(addr) / "runs" / f"20260101T{i:012d}.log").write_text(text)


HEADER = "# run of ceo, 1 message(s)\n# senders: {senders}\n# cwd: /x\n# cmd: kiro-cli chat <prompt on stdin>\n"
PROMPT = "# ---- prompt ----\nplease do things\n# ---- output ----\n"


def test_failed_runs_do_not_make_an_agent_wasteful(org):
    org.send(ROOT, "ceo", "budget", budget=20)
    for i, tail in enumerate(["\n# exit 1 after 2s\n", "\n# failed to start: boom\n", "\n# killed after 5s timeout\n\n# exit -9 after 5s\n",
                              "\n# interrupted by scheduler shutdown\n", "\n# exit 2 after 1s\n"]):
        write_run(org, "ceo", i, HEADER.format(senders="root") + PROMPT + tail)
    h = agent_health(org, "ceo", utcnow())
    assert "wasteful" not in h.flags and h.empty_runs == 0 and h.failed_runs == 5 and h.runs_used == 5


def test_successful_empty_runs_are_still_wasteful(org):
    org.send(ROOT, "ceo", "budget", budget=20)
    for i in range(5):
        write_run(org, "ceo", i, HEADER.format(senders="root") + PROMPT + "\n# exit 0 after 2s\n")
    h = agent_health(org, "ceo", utcnow())
    assert "wasteful" in h.flags and h.empty_runs == 5 and "5 of 5" in h.flags["wasteful"]


def test_runs_that_only_handled_runtime_notes_are_not_empty(org):
    org.send(ROOT, "ceo", "budget", budget=20)
    for i in range(6):
        write_run(org, "ceo", i, HEADER.format(senders="runtime") + PROMPT + "\n# exit 0 after 2s\n")
    write_run(org, "ceo", 6, HEADER.format(senders="root, runtime") + PROMPT + "\n# exit 0 after 2s\n")  # mixed: counts
    h = agent_health(org, "ceo", utcnow())
    assert h.runtime_runs == 6 and h.empty_runs == 1 and "wasteful" not in h.flags  # 1 judged run < min_runs_for_waste


def test_failures_mixed_with_real_empty_runs_judge_only_the_real_ones(org):
    org.send(ROOT, "ceo", "budget", budget=20)
    for i in range(10):
        write_run(org, "ceo", i, HEADER.format(senders="root") + PROMPT + "\n# exit 1 after 1s\n")
    for i in range(10, 14):
        write_run(org, "ceo", i, HEADER.format(senders="root") + PROMPT + "\n# exit 0 after 1s\n")
    h = agent_health(org, "ceo", utcnow())
    assert h.empty_runs == 4 and "4 of 4" in h.flags["wasteful"]
