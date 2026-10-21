"""What the screens are made of that is not a widget: the names of the screens and tabs, the colours of the states, the help text, and the two records the refresh
passes around (``Ctx``: what the worker needs to know about the screen, captured on the UI thread; ``Tick``: what the worker found, shown on the UI thread)."""

from __future__ import annotations

from dataclasses import dataclass

from ..dashdata import AgentDetail, EventLine, HealthView, RequestRow, Section, ServiceRow, Snapshot
from ..kernel import JsonObject

VIEWS = ("org", "flows", "services", "events", "health")
VIEW_NAMES = {"org": "Org", "flows": "Workflows", "services": "Services", "events": "Events", "health": "Health"}
TABS = ("overview", "activity", "messages", "runlog", "memory", "charter")
TAB_NAMES = {"overview": "Overview", "activity": "Activity", "messages": "Messages", "runlog": "Run log",
             "memory": "Memory", "charter": "Charter"}

KIND_STYLE = {"running": "bold green", "queued": "yellow", "working": "cyan", "waiting": "blue", "idle": "dim",
              "paused": "magenta", "budget": "bold red", "you": "bold white"}

HELP = """\
GLOBAL
  1 2 3 4 5     Org · Workflows · Services · Events · Health
  Tab / Shift+Tab   cycle focus between the panes
  ↑ ↓  j k      move            g / G   top / bottom
  ← →  h l      fold / unfold a node, or switch pane
  Enter         open (agent -> its details, request -> trace, service -> cases, message -> text)
  Esc / Backspace   back (close an overlay, leave a trace or a service, return to the agent list)
  r             refresh now     p   pause / resume the automatic refresh
  ?             this help       q   quit

1 ORG  (agent tree on the left, details of the selected agent on the right)
  [ ]           previous / next tab: Overview · Activity · Messages · Run log · Memory · Charter
  Space         fold / unfold the selected node
  root selected: what needs you and your requests; an agent: its run, tasks, delegations, latest activity
  Messages tab: Enter opens the message.   Run log tab: follows the log while it grows (scroll up to stop).

2 WORKFLOWS   one line per request you gave; Enter opens its trace (messages, runs, tool calls, timings)
3 SERVICES    one line per service; Enter opens its record, cases, playbook and contract
4 EVENTS      the live merged event stream
  e             errors only    /   filter (words: agent, kind, trace, tool)    f   follow on / off
  x             raw events: ids, process groups, budgets, arguments (also on the Org > Activity tab)
5 HEALTH      observe now, health flags;  c  runs the consistency check (on demand)

The dashboard is read-only: grants, start/stop and feedback stay with the assistant and the CLI.
"""


@dataclass
class Ctx:
    """What the worker needs to know about the screen (captured on the UI thread)."""

    view: str
    selected: str
    flow_open: str | None
    service_open: tuple[str, str] | None
    event_text: str
    event_errors: bool
    raw: bool = False


@dataclass
class Tick:
    snap: Snapshot | None = None
    detail: AgentDetail | None = None
    requests: list[RequestRow] | None = None
    services: list[ServiceRow] | None = None
    service_doc: list[Section] | None = None
    events: list[JsonObject] | None = None
    event_lines: list[EventLine] | None = None
    health: HealthView | None = None
    error: str | None = None
    ms: float = 0.0

