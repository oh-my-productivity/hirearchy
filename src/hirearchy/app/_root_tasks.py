"""Root's one-off tasks, read from its sent mail: where a criterion copied from earlier tasks (``from_tasks``) finds the lines it copies (design 5.2)."""

from __future__ import annotations

from ..blueprint._protocols import RootTasks
from ..blueprint._shapes import RootTask
from ..kernel import ROOT, msg_time
from ..mail import MailboxReader

HEADING = "## Acceptance criteria"


def criteria_lines(body: str) -> tuple[str, ...]:
    """The non-empty lines of the ``## Acceptance criteria`` section of a task body (up to the next ``## `` heading)."""
    lines = body.splitlines()
    start = next((n for n, line in enumerate(lines) if line.strip() == HEADING), None)
    if start is None:
        return ()
    end = next((n for n in range(start + 1, len(lines)) if lines[n].startswith("## ")), len(lines))
    return tuple(line.strip() for line in lines[start + 1 : end] if line.strip())


class MailRootTasks(RootTasks):
    """A task is root's one-off task when root sent it, it is a task, it names no service and it revises no other task."""

    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def task(self, task_id: str) -> RootTask | None:
        msg = self._mail.find_anywhere(ROOT, task_id)
        if msg is None or msg.sender != ROOT or msg.type != "task" or msg.service or msg.revises:
            return None
        return RootTask(msg.id, msg_time(msg), criteria_lines(msg.body))
