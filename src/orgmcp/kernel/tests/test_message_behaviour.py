# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from testkit.legacy.orgmcp.core import ROOT


def test_short_messages_render_unchanged(org):
    msg = org.send(ROOT, "ceo", "hello")
    assert msg.render().endswith("\n\nhello\n") and "cut" not in msg.render()


# --------------------------------------------------------------- non-waking
def test_wake_flag_roundtrips_and_defaults_to_true(org):
    quiet = org.notify("ceo", "fyi", "x", wake=False)
    loud = org.notify("ceo", "ping", "y")
    assert "wake: false" in (org.dir("ceo") / "inbox" / f"{quiet.id}.md").read_text()
    got = {m.id: m for m in org.messages("ceo", "inbox")}
    assert got[quiet.id].wake is False and got[loud.id].wake is True
    assert "wake" not in loud.meta()  # normal messages stay byte-identical to before
    assert org.unread("ceo") == 1
