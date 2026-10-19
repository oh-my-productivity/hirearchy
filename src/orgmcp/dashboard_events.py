"""Events for a human: one readable line per event (``orgmcp dash`` Activity tab, Overview, Events screen, Health).

The names this module has always had, over the wording of :mod:`orgmcp.dashdata` (``describe humanize event_lines`` ...): pure functions, no I/O.
They go with the other legacy modules (step E3); new code imports :mod:`orgmcp.dashdata`.
"""

from __future__ import annotations

from . import dashdata as _dashdata

WHO_WIDTH = _dashdata.WHO_WIDTH
BATCH_SHOWN = _dashdata.BATCH_SHOWN

# (agent, message id) -> (type, title, sender) of a message, or None when it cannot be found
Lookup = _dashdata.Lookup
EventLine = _dashdata.EventLine
clock = _dashdata.clock
who = _dashdata.who
describe = _dashdata.describe
humanize = _dashdata.humanize
event_lines = _dashdata.event_lines
