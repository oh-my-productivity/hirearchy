# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.services_world import svc


def test_status_tree_names_the_services_an_agent_offers(svc):
    tree = svc.tree()
    assert "ceo [Chief executive]" in tree and " services: weekly-brief" in tree.split("\n")[1]
    assert "services:" not in tree.split("\n")[2]


def test_the_services_listing_shows_criteria_by_id(svc):
    from testkit.reach.hirearchy.core import ROOT

    svc.define_service(ROOT, "ceo", "weekly-brief", add_acceptance=["Never longer than one page"], remove_acceptance=["At most 600 words"])
    for who in (ROOT, "ceo"):
        out = svc.runtime.service_reports.services_text(who)
        assert "    C2: Every factual claim has a source URL\n    C3: Never longer than one page\n  record:" in out
        assert "C1" not in out and "1. " not in out.split("record:")[0]  # the removed C1 is not listed, and nothing is numbered by position


def reject(svc, words, topic="ai", **kw):
    """The user rejects a delivery (their own judgement); returns the request and the verdict note."""
    from testkit.services_world import deliver, request

    task = request(svc, topic)
    deliver(svc, "ceo", task, lessons="L.")
    return task, svc.feedback(ROOT_ADDR, task.id, "reject", words, source="human", **kw)


ROOT_ADDR = "root"


def assertion_lines(out):
    return out.split("  regression list (the client's rejections):\n")[1].split("\n  playbook")[0].splitlines()


def test_a_service_without_a_rejection_lists_no_regressions(svc):
    assert "regression list" not in svc.runtime.service_reports.services_text("root")


def test_the_services_listing_lists_every_assertion_clipped_to_160(svc):
    first, note = reject(svc, "w " * 100)
    for k in range(12):
        reject(svc, f"Problem {k + 2}.", f"t{k}")
    for who in ("root", "ceo"):
        out = svc.runtime.service_reports.services_text(who)
        assert out.split("record:")[1].split("\n")[1] == "  regression list (the client's rejections):"
        lines = assertion_lines(out)
        assert len(lines) == 13 and lines[0].startswith(f'    R1 (case {first.id}): "w w w ')
        assert lines[0].endswith('w…"') and len(lines[0].split(': "')[1]) == 160 + 1  # 159 characters, the ellipsis, the closing quote
        assert lines[-1].endswith('"Problem 13."') and lines[-1].startswith("    R13 (case ")


def test_the_services_listing_says_what_each_assertion_is_about(svc):
    a, one = reject(svc, "One.", criterion=["C1", "C2"])
    b, two = reject(svc, "Two.", "b", criterion=["none"])
    c, three = reject(svc, "Three.", "c")
    d, four = reject(svc, "Four.", "d")
    svc.feedback("root", d.id, "reject", "Probably.", source="relayed", criterion=["C1"], confirms=four.id)
    e, five = reject(svc, "Five.", "e")
    svc.feedback("root", e.id, "reject", "Probably.", source="relayed", criterion=["none"], confirms=five.id)
    assert assertion_lines(svc.runtime.service_reports.services_text("root")) == [
        f'    R1 (case {a.id}, about C1, C2): "One."',
        f'    R2 (case {b.id}, no lasting rule): "Two."',
        f'    R3 (case {c.id}): "Three."',
        f'    R4 (case {d.id}, about C1 (not confirmed)): "Four."',
        f'    R5 (case {e.id}, possibly a one-off (not confirmed)): "Five."',
    ]


def test_the_services_listing_marks_a_removed_criterion(svc):
    first, note = reject(svc, "Too long.", criterion=["C1", "C2"])
    svc.define_service("root", "ceo", "weekly-brief", add_acceptance=["One page"], remove_acceptance=["Every factual claim has a source URL"])
    assert assertion_lines(svc.runtime.service_reports.services_text("root")) == [
        f'    R1 (case {first.id}, about C1, C2 (removed)): "Too long."'
    ]
