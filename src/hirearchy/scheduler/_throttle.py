"""The credit of a run that ended on a model-service throttle before any tool effect: the runtime gives its run back, the retry is free."""

from __future__ import annotations

from ..budget import run_credit
from ..delivery import MessageDelivery
from ..kernel import OrgError
from ..kiro import throttled_without_effect
from ..mail import MailboxReader
from ..runs import RunLogReader
from ._credit import return_run
from ._ports import Console, ThrottleCredits
from ._run import RunRecord

TAIL_BYTES, TAIL_LINES = 4096, 80  # the end of the log that carries the launcher's mark and the closing line


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
        return return_run(run, self._logs, self._mail, self._delivery, run_credit(run.addr, run.log.stem))
