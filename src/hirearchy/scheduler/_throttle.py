"""The credit of a run that ended on a model-service throttle before any tool effect: the runtime gives its run back, the retry is free."""

from __future__ import annotations

from ..budget import run_credit
from ..delivery import MessageDelivery
from ..kernel import OrgError, credited_stems
from ..kiro import throttled_without_effect
from ..mail import MailboxReader
from ..runs import RunLogReader
from ._ports import Console, ThrottleCredits
from ._run import RunRecord

TAIL_BYTES, TAIL_LINES = 4096, 80  # the end of the log that carries the launcher's mark and the closing line
STAMP = 21  # characters of a log stem or a message id that are its time


class CreditingThrottles(ThrottleCredits):
    """Credits a run whose transcript says it was throttled without effect (the launcher's exit code decided to ask; this is the second check).

    Every fallible read comes first and the delivery of the note is the last fallible step, so ``""`` always means that no credit exists.
    """

    def __init__(self, logs: RunLogReader, mail: MailboxReader, delivery: MessageDelivery, console: Console) -> None:
        self._logs, self._mail, self._delivery, self._console = logs, mail, delivery, console

    def credit(self, run: RunRecord) -> str:
        try:
            return self._credit(run)
        except (OSError, OrgError) as error:  # charged as today
            self._console.say(f"{run.addr}: throttle credit not given: {error}")
            return ""

    def _credit(self, run: RunRecord) -> str:
        tail, _ = self._logs.tail(run.log, TAIL_BYTES, TAIL_LINES)
        if not throttled_without_effect(tail):
            return ""
        stem = run.log.stem
        if any(message.id[:STAMP] >= stem[:STAMP] for message in self._mail.sent(run.addr)):  # the run sent something: it had an effect
            return ""
        stems = [file.stem for file in self._logs.files(run.addr)]
        before = stems[stems.index(stem) - 1] if stem in stems and stems.index(stem) > 0 else None
        kind = "counted" if before is not None and before in credited_stems(self._mail.received(run.addr)) else "free"
        self._delivery.deliver(run_credit(run.addr, stem))
        return kind
