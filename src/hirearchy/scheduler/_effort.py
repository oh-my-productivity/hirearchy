"""The credit of a run the launcher stopped because kiro-cli did not set its effort: the runtime gives its run back, the relaunch is free
(batch 1.1, design 2.4)."""

from __future__ import annotations

from ..budget import effort_credit
from ..delivery import MessageDelivery
from ..kernel import OrgError
from ..kiro import EffortStop, effort_stop
from ..mail import MailboxReader
from ..runs import RunLogReader
from ._credit import return_run
from ._ports import Console, EffortStops
from ._run import RunRecord

TAIL_BYTES, TAIL_LINES = 4096, 80  # the end of the log that carries kiro's warning, the launcher's mark and the closing line
OUTCOMES = {"free": "not charged, relaunched", "counted": "not charged, counted as a failure", "": "charged as a failed run"}


def effort_text(stop: EffortStop, kind: str) -> str:
    """The error of the ``run.end`` event of a stopped run; the outcome comes first because observe cuts a run's error at 120 characters."""
    effects = "none" if stop.effects == 0 else stop.effects
    return f"effort not set: run stopped, {OUTCOMES[kind]} (kiro-cli: {stop.warning}; tool effects: {effects})"


class CreditingEffortStops(EffortStops):
    """Reads the launcher's effort stop from the end of a run log and credits a stop that had no tool effect (the exit -9 that the scheduler did
    not cause decided to ask; the mark is the second check). Every fallible read comes first and the delivery of the note is the last fallible
    step, so ``""`` always means that no credit exists."""

    def __init__(self, logs: RunLogReader, mail: MailboxReader, delivery: MessageDelivery, console: Console) -> None:
        self._logs, self._mail, self._delivery, self._console = logs, mail, delivery, console

    def stop_of(self, run: RunRecord) -> EffortStop | None:
        try:
            return effort_stop(self._logs.tail(run.log, TAIL_BYTES, TAIL_LINES)[0])
        except (OSError, OrgError) as error:  # not recognised: the run takes today's failure path
            self._console.say(f"{run.addr}: run log not read for the effort check: {error}")
            return None

    def credit(self, run: RunRecord, stop: EffortStop) -> str:
        if stop.effects > 0:
            return ""
        try:
            return return_run(run, self._logs, self._mail, self._delivery, effort_credit(run.addr, run.log.stem))
        except (OSError, OrgError) as error:  # charged as today
            self._console.say(f"{run.addr}: effort credit not given: {error}")
            return ""
