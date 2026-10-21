"""``Snapshot`` and ``TeamSnapshots``: what a wait compares from look to look."""

from __future__ import annotations

from hirearchy.kernel import ROOT, Message
from hirearchy.progress._liveness import RunnableTeams
from hirearchy.progress._ports import Snapshot, Snapshots, TaskMark
from hirearchy.progress._snapshot import TeamSnapshots, moving
from hirearchy.progress._states import MailTaskStates
from hirearchy.progress._teams import AgentTaskTeams
from hirearchy.progress.testing import ProgressWorld
from hirearchy.progress._listing import MailRootTasks


def snapshots(w: ProgressWorld) -> TeamSnapshots:
    return TeamSnapshots(
        MailRootTasks(w.mail), AgentTaskTeams(w.agents), MailTaskStates(w.mail, w.pauses, w.tasks), RunnableTeams(w.mail, w.runnable), w.queue, w.clock,
    )


def snap(kind: str, alive: bool = False) -> Snapshot:
    return Snapshot({"t": TaskMark(kind, "T", kind)}, {}, frozenset({"t"} if alive else ()))


def test_working_and_waiting_always_move() -> None:
    assert moving(snap("working")) and moving(snap("waiting"))


def test_blocked_and_stalled_move_only_while_someone_below_can_run() -> None:
    assert not moving(snap("blocked")) and not moving(snap("stalled"))
    assert moving(snap("blocked", alive=True)) and moving(snap("stalled", alive=True))


def test_finished_tasks_and_no_tasks_do_not_move() -> None:
    assert not moving(snap("done", alive=True)) and not moving(snap("failed", alive=True))
    assert not moving(Snapshot({}, {}, frozenset()))


def test_it_is_a_source_of_snapshots(w: ProgressWorld) -> None:
    assert isinstance(snapshots(w), Snapshots)


def test_a_snapshot_has_the_first_word_of_each_state_the_queue_and_the_live_tasks(w: ProgressWorld, task: Message) -> None:
    w.queue.entries = [("m1", "line one")]
    other = w.delegate(ROOT, "ceo/eng", "Other", 2)
    w.begin_run("ceo/eng")
    w.end_run("ceo/eng")
    found = snapshots(w).snapshot(None)
    assert found.marks == {task.id: TaskMark("working", "Write the report", "working"), other.id: TaskMark("stalled", "Other", "stalled (ceo/eng has not reported and nothing is running)")}
    assert dict(found.needs) == {"m1": "line one"} and found.alive == {task.id}


def test_a_snapshot_of_one_task_is_that_task_in_any_state(w: ProgressWorld, task: Message) -> None:
    w.answer(task, "done", "ok", 0)
    assert set(snapshots(w).snapshot(task.id).marks) == {task.id} and set(snapshots(w).snapshot("nope").marks) == set()


def test_a_task_whose_assignee_is_gone_has_no_team_to_be_alive(w: ProgressWorld, task: Message) -> None:
    w.retire("ceo")
    found = snapshots(w).snapshot(None)
    assert found.marks[task.id].kind == "failed" and found.alive == frozenset()
