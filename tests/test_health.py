import pytest

from orgmcp.core import ROOT, Message, OrgError


# --------------------------------------------------------------------- revises


def test_revises_is_stored_and_rendered(org):
    first = org.delegate(ROOT, "ceo", "Plan", "g", "a")
    second = org.delegate(ROOT, "ceo", "Plan v2", "g", "a", revises=first.id)
    assert second.revises == first.id
    loaded = Message.load(org.dir("ceo") / "inbox" / f"{second.id}.md")
    assert loaded.revises == first.id
    assert f"revises: {first.id}" in loaded.render()
    assert Message.load(org.dir("ceo") / "inbox" / f"{first.id}.md").revises is None


def test_revises_must_be_an_earlier_task_to_the_same_assignee(org):
    org.hire("ceo", "ops", "Ops", "Operate.")
    org.send(ROOT, "ceo", "budget", budget=20)
    for_eng = org.delegate("ceo", "ceo/eng", "Build", "g", "a", budget=1)
    with pytest.raises(OrgError, match="revises"):
        org.delegate("ceo", "ceo/ops", "Build", "g", "a", revises=for_eng.id)  # other assignee
    with pytest.raises(OrgError, match="revises"):
        org.delegate("ceo", "ceo/eng", "Build", "g", "a", revises="nope")  # unknown id
    with pytest.raises(OrgError, match="revises"):
        org.delegate(ROOT, "ceo", "Build", "g", "a", revises=for_eng.id)  # not sent by this delegator
    ok = org.delegate("ceo", "ceo/eng", "Build again", "g", "a", revises=for_eng.id)
    assert ok.revises == for_eng.id
