# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.reach.orgmcp.core import ROOT
from testkit.services_world import ENG, svc


def test_messages_between_agents_keep_angle_brackets_too(svc):
    svc.delegate(ROOT, "ceo", "Plan", "Plan", "a plan", budget=10)
    msg = svc.delegate("ceo", ENG, "T", "Resolve 'before <weekday>' & \"for <date>\"", "c", budget=1)
    assert "before <weekday>" in msg.body and "&lt;" not in msg.body
    sent = svc.sent("ceo")[-1]
    assert "before <weekday>" in sent.body and "&lt;" not in sent.body
