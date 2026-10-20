# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import time

import pytest
from testkit.cli_world import main
from testkit.legacy.orgmcp.core import ROOT, join_frontmatter, split_frontmatter


ENG = "ceo/eng"


def configure(org, **changes):
    path = org.root / "ORG.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(join_frontmatter({**meta, **changes}, body), encoding="utf-8")


def flag_idle(org):
    configure(org, health={"idle_after_seconds": -1})


def fund(org, addr="ceo", budget=10):
    """Give an agent budget and let it read the mail, so only `idle` can flag it."""
    org.send(ROOT, addr, "budget", budget=budget)
    org.begin_run(addr)
    org.end_run(addr, ok=True)


def runtime_notes(org, addr):
    return [m for m in org.received(addr) if m.sender == "runtime" and m.title.startswith("health review")]


def snapshot(org):
    # the event log (.runtime/events) records even a dry run, so it is not part of the organization's content
    return {p: p.read_bytes() for p in org.root.rglob("*") if p.is_file() and ".git" not in p.parts and "events" not in p.parts}


SCHEDULERS = []


@pytest.fixture(autouse=True)
def settled():
    """Let the runs a test's schedulers started end and be reaped, so no process and no run log is left open."""
    yield
    for sched in SCHEDULERS:
        for _ in range(500):
            if not sched.state.runs:
                break
            time.sleep(0.02)
            sched.reap()
    SCHEDULERS.clear()


# ------------------------------------------------------------------ CLI
def test_cli_review_dry_run_then_real(org, capsys):
    flag_idle(org)
    fund(org)
    root = ["--root", str(org.root)]
    before = snapshot(org)
    main([*root, "review", "--dry-run"])
    out = capsys.readouterr().out
    assert "would send 2 note(s)" in out and "-> ceo: health review" in out and "-> root: health review" in out
    assert snapshot(org) == before

    main([*root, "review"])
    out = capsys.readouterr().out
    assert " sent 2 note(s)" in out and "would" not in out
    assert len(runtime_notes(org, "ceo")) == 1 and len(runtime_notes(org, ROOT)) == 1
    assert org.ledger("reviews")["notified"]["ceo"] == [f"{ENG}:idle"]


def test_cli_review_on_a_healthy_org(org, capsys):
    main(["--root", str(org.root), "review"])
    assert "0 flagged agent(s); nothing to send" in capsys.readouterr().out
    assert org.ledger("reviews")
