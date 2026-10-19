"""``BatchRenderer``: a message of a batch, a result followed by the task it answers (moved from ``Org._render_in_context``)."""

from __future__ import annotations

from ..kernel import Message
from ..mail import MailboxReader
from ._ports import ContextRenderer, TaskQuoter, UpstreamTasks


class BatchRenderer(ContextRenderer):
    def __init__(self, mail: MailboxReader, quoter: TaskQuoter, upstream: UpstreamTasks) -> None:
        self._mail = mail
        self._quoter = quoter
        self._upstream = upstream

    def render(self, addr: str, m: Message) -> str:
        """A batch message; a result is followed by the task it answers, so it is judged against what was asked."""
        text = m.render()
        if m.type != "result" or not m.reply_to:
            return text
        task = next((t for t in self._mail.sent(addr) if t.type == "task" and t.id == m.reply_to), None)
        if task is None:
            return text
        out = (
            f"{text}\n[The task you delegated to {task.to} that this result answers ({task.id}). "
            f"Judge the result against these criteria, verbatim:]\n{self._quoter.quote(task)}\n"
        )
        # Which of your own tasks does it serve? Derivable only if exactly one was already yours at the time.
        up = self._upstream.upstream(addr, task)
        if up is not None:
            mine, reported = up
            if reported is None:
                out += (
                    f"[It was the only task assigned to you before you delegated this, so it probably serves your open task "
                    f"{mine.id} \"{mine.title}\": the result must also satisfy that task's criteria (shown in full in this prompt).]\n"
                )
            elif reported.status == "blocked":
                out += (
                    f"[It was the only task assigned to you before you delegated this, so it probably serves your task "
                    f"{mine.id} \"{mine.title}\", which you already reported blocked. That is not final: you may `report` "
                    "it again, once, if the blocker is resolved (its criteria are shown in your state). The new report must meet "
                    "rule 6: `done` only if every criterion is met and verified by you, including any required review of "
                    "the FINAL version, not an earlier draft; otherwise report `blocked` or `failed`. Do not claim in a note "
                    "that criteria are met.]\n"
                )
            else:
                out += (
                    f"[It was the only task assigned to you before you delegated this, so it probably serves your task "
                    f"{mine.id} \"{mine.title}\", which you already reported {reported.status}: that is final. Do not claim "
                    "in a note that its criteria are met or try to change its outcome; if you have information for "
                    f"{mine.sender}, send it as information only, saying what was and was not verified.]\n"
                )
        return out
