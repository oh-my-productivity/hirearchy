# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.reach.orgmcp import core
from testkit.reach.orgmcp.app import wiring
from testkit.reach.orgmcp.core import ROOT
from testkit.reach.orgmcp.app.wire_stalls import FingerprintTaskViews  # the class the composition root makes the task views of the ladder with

from orgmcp.mail import MessageParser
from orgmcp.mail.testing import CountingMessageParser


def test_message_load_is_cached_by_path_mtime_and_size(org):
    msg = org.send(ROOT, "ceo", "hello")
    path = org.dir("ceo") / "inbox" / f"{msg.id}.md"
    parses = []
    real = core.split_frontmatter
    parser = CountingMessageParser(split=lambda t: (parses.append(1), real(t))[1])
    first = parser.parse(path)
    second = parser.parse(path)
    assert len(parses) == 1 and first == second and first is not second and second.path == path
    first.body = "mutated"  # the cache hands out fresh objects
    assert parser.parse(path).body == "hello"
    path.write_text(path.read_text().replace("hello", "HELLO!"))  # same path, new content: reparsed
    assert parser.parse(path).body == "HELLO!" and len(parses) == 2


def test_cached_load_equals_uncached_parse(org):
    msg = org.delegate(ROOT, "ceo", "Title: with colon", "goal\nline2", "acc", budget=3)
    path = org.dir("ceo") / "inbox" / f"{msg.id}.md"
    parser = CountingMessageParser()
    cold = parser.parse(path)
    assert parser.parse(path) == cold and cold.title == "Title: with colon" and cold.budget == 3
    meta, body = core.split_frontmatter(path.read_text(encoding="utf-8"))
    assert cold.body == body.strip() and meta["id"] == cold.id


def test_crlf_files_parse_like_read_text(tmp_path):
    p = tmp_path / "20260101T000000000000-root-aaaa.md"
    p.write_bytes(b"---\r\nfrom: root\r\nto: ceo\r\ntype: note\r\n---\r\nline1\r\nline2\r\n")
    parser = CountingMessageParser()
    assert parser.parse(p).body == "line1\nline2" and parser.parse(p).sender == "root"


def test_cache_is_bounded(org):
    parser = CountingMessageParser(max_entries=5)
    org.runtime = wiring.open_runtime(org.root, {MessageParser: parser})
    for i in range(12):
        org.send(ROOT, "ceo", f"n{i}")
    org.messages("ceo", "inbox")
    assert len(parser.cache) == 5


def test_stall_view_reparses_only_when_the_mailbox_files_change(org):
    org.send(ROOT, "ceo", "budget", budget=10)
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)
    views = FingerprintTaskViews(org.runtime.task_query, org.runtime.mail_fingerprint)
    assert [t.id for t in views.open_tasks("ceo")] == [task.id]
    counting = CountingMessageParser()
    org.runtime = wiring.open_runtime(org.root, {MessageParser: counting})
    views = views.rebound(org.runtime.task_query, org.runtime.mail_fingerprint)  # the ladder of a scheduler goes on with its memo over the new runtime
    loads = counting.loaded
    for _ in range(3):
        views.open_tasks("ceo")
    assert loads == []  # unchanged mailbox: nothing is parsed
    org.begin_run("ceo")  # inbox -> inflight is the same set of messages
    loads.clear()  # (begin_run itself parses the batch)
    assert [t.id for t in views.open_tasks("ceo")] == [task.id] and loads == []
    org.end_run("ceo", ok=True)
    org.report("ceo", task.id, "done", "ok")  # a new sent message: recomputed, and the task is closed
    assert views.open_tasks("ceo") == [] and loads
