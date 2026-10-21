"""What ``Org`` delegates to, as data: one ``Case`` per method of the facade (ARCHITECTURE.md 6.4), grouped by mixin.

A case names the method, how to call it and which call of which port of the runtime it must make (``field``/``port_method``; the arguments the
port must receive are those of the facade call unless ``expect`` says otherwise). A ``FunctionCase`` is a method that has no runtime to go
through (a static or class method): it delegates to a function of a feature, which the test replaces by a spy (``module`` and ``attribute``).
``test_facade_contract`` runs every case twice: on a runtime of spy fakes and on the real runtime.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hirearchy.app import Org
from hirearchy.kernel import Message


@dataclass(frozen=True)
class World:
    """The organization the real runtime works on: root -> ceo -> (eng, qa), and one task from root to ceo."""

    root: Path
    task: Message


def build_world(root: Path) -> World:
    org = Org.init(root, "mission")
    org.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=3)
    org.hire("ceo", "eng", "Engineer", "Build.")
    org.hire("ceo", "qa", "Tester", "Test.")
    task = org.delegate("root", "ceo", "Work", "Do it.", "Done when it is.", budget=8)
    return World(org.root, task)


Call = tuple[tuple[Any, ...], dict[str, Any]]
Args = Callable[[World], Call]


def args(*positional: Any, **keywords: Any) -> Args:
    return lambda world: (positional, keywords)


def with_task(make: Callable[[Message], Call]) -> Args:
    return lambda world: make(world.task)


def a_message() -> Args:
    return lambda world: ((Message(sender="ceo", to="ceo/eng", type="note", body="hello", title="hi"),), {})


@dataclass(frozen=True)
class Case:
    """``Org.<name>`` called with ``args`` makes ``runtime.<field>.<port_method>(<expect, else the same arguments>)`` and returns its result."""

    name: str
    mixin: str
    field: str
    port_method: str
    args: Args = args()
    expect: Args | None = None  # what the port receives, when the facade does not pass its arguments in the same shape


@dataclass(frozen=True)
class FunctionCase:
    """``Org.<name>`` called with ``args`` returns what ``<module>.<attribute>(<same arguments>)`` returns (a function of a feature)."""

    name: str
    mixin: str
    module: str  # the facade module that imports the function
    attribute: str  # the name it imports it as
    args: Args = args()
    wrap: bool = False  # the facade builds an ``Org`` around the result (``Org.init``)


def _send_all() -> Call:
    return (("ceo", "ceo/eng", "body"), dict(
        type="task", title="T", reply_to="r1", status="done", budget=3, revises="r2", supersedes="r3", service="svc", contract=2, playbook=4,
        feedback="accept", wake=False, _skip_route_check=True,
    ))


def _send_expected() -> Call:
    (positional, keywords) = _send_all()
    renamed = {("skip_route_check" if k == "_skip_route_check" else k): v for k, v in keywords.items()}
    return positional, renamed


CASES: list[Case | FunctionCase] = [
    # core
    FunctionCase("norm", "core", "hirearchy.app._facade_core", "_norm", args("/ceo/")),
    Case("dir", "core", "paths", "agent_dir", args("ceo")),
    FunctionCase("parent", "core", "hirearchy.app._facade_core", "_parent", args("ceo/eng")),
    FunctionCase("depth", "core", "hirearchy.app._facade_core", "_depth", args("ceo/eng")),
    FunctionCase("child_addr", "core", "hirearchy.app._facade_core", "_child_addr", args("ceo", "eng")),
    Case("new_id", "core", "ids", "message_id", args("ceo")),
    Case("ledger", "core", "ledgers", "read", args("failures")),
    Case("save_ledger", "core", "ledgers", "write", args("failures", {"ceo": 1})),
    # settings
    FunctionCase("find_root", "settings", "hirearchy.app._facade_settings", "find_org_root", args("somewhere")),
    Case("config", "settings", "settings", "config"),
    Case("rules", "settings", "settings", "rules"),
    # snapshots
    Case("commit", "snapshots", "snapshotter", "commit", args("snap")),
    # bootstrap
    FunctionCase("init", "bootstrap", "hirearchy.app._facade_bootstrap", "initialize_org", args("new-org", "a mission", {"k": 1}), wrap=True),
    # agents
    Case("exists", "agents", "agents", "exists", args("ceo")),
    Case("require", "agents", "agents", "require", args("ceo")),
    Case("children", "agents", "agents", "children", args("ceo")),
    Case("agents", "agents", "agents", "agents"),
    Case("subtree", "agents", "agents", "subtree", args("ceo")),
    Case("charter", "agents", "charters", "charter", args("ceo")),
    Case("memory", "agents", "charters", "memory", args("ceo")),
    # runs
    Case("runs_used", "runs", "run_log_reader", "count", args("ceo")),
    Case("start_run_log", "runs", "run_log_writer", "create", args("ceo")),
    # mail
    Case("messages", "mail", "mailbox", "messages", args("ceo", "inbox", "read")),
    Case("received", "mail", "mailbox", "received", args("ceo")),
    Case("sent", "mail", "mailbox", "sent", args("root")),
    Case("unread", "mail", "mailbox", "unread", args("ceo")),
    FunctionCase("_wakes", "mail", "hirearchy.app._facade_mail", "message_wakes", args(Path("nowhere.md"))),
    Case("find_received", "mail", "mailbox", "find_received", with_task(lambda t: (("ceo", t.id), {}))),
    Case("open_tasks", "mail", "task_query", "open_tasks", args("ceo")),
    Case("outstanding", "mail", "task_query", "outstanding", args("root")),
    Case("_blocked_tasks", "mail", "task_query", "blocked_tasks", args("ceo")),
    Case("begin_run", "mail", "batches", "begin", args("ceo")),
    Case("end_run", "mail", "batches", "end", args("ceo", True)),
    Case("recover", "mail", "batches", "recover"),
    Case("redeliver_orphans", "mail", "batches", "redeliver_orphans"),
    Case("running", "mail", "mailbox", "has_inflight", args("ceo")),
    # telemetry
    Case("emit", "telemetry", "events", "emit", args("test.event", actor="ceo", run="r1", count=3)),
    # access
    Case("default_model", "access", "settings", "default_model"),
    Case("model_for", "access", "model_resolver", "model_for", args("ceo")),
    Case("_check_authority", "access", "authority_policy", "check_authority", args("ceo", ["read"], None, ["/data"])),
    Case("workspace_of", "access", "access_scopes", "workspace_of", args("ceo")),
    Case("inputs_of", "access", "access_scopes", "inputs_of", args("ceo")),
    FunctionCase("unconfined_read", "access", "hirearchy.app._facade_access", "_unconfined_read", args({"workspace": "w"})),
    Case("_check_inputs", "access", "authority_policy", "check_inputs", args(["/data"])),
    Case("readable_roots", "access", "access_scopes", "readable_roots", args("ceo")),
    Case("tool_names", "access", "tool_naming", "tool_names", args("ceo")),
    # traces
    Case("trace_of", "traces", "trace_lookup", "trace_of", with_task(lambda t: (("ceo", t.id), {}))),
    Case("open_task_traces", "traces", "trace_lookup", "open_task_traces", args("ceo")),
    Case("context_trace", "traces", "trace_lookup", "context_trace", args("ceo")),
    Case("stamp_trace", "traces", "trace_stamper", "stamp", with_task(lambda t: ((t,), {}))),
    # delivery
    Case("deliver", "delivery", "delivery", "deliver", a_message()),
    Case("notify", "delivery", "delivery", "notify", args("ceo", "A title", "A body", False, "T1")),
    # files
    Case("resolve_read", "files", "org_file_reader", "resolve_read", args("ceo/AGENT.md", "ceo")),
    Case("read", "files", "org_file_reader", "read", args("ceo/AGENT.md", "ceo")),
    Case("resolve_write", "files", "org_file_writer", "resolve_write", args("ceo", "ceo/work/a.md")),
    Case("write", "files", "org_file_writer", "write", args("ceo", "ceo/work/a.md", "text", True)),
    Case("write_noted", "files", "org_file_writer", "write_noted", args("ceo", "ceo/work/a.md", "text", True)),
    # strays
    Case("stray_notice", "strays", "stray_registry", "take_notice", args("ceo")),
    # budget
    Case("budget", "budget", "budget_query", "budget", args("ceo")),
    Case("delegable", "budget", "budget_query", "delegable", args("ceo")),
    Case("grant_hint", "budget", "budget_query", "grant_hint", args("ceo")),
    Case("_check_allocation", "budget", "allocation_policy", "check_allocation", args("ceo", 2, True)),
    Case("_default_budget", "budget", "allocation_policy", "default_budget", args("ceo")),
    Case("_budget_to_return", "budget", "allocation_policy", "budget_to_return", with_task(lambda t: (("ceo", t, "done"), {}))),
    Case("reclaim", "budget", "budget_reclaimer", "reclaim", args("ceo", "eng", 1)),
    # eligibility
    Case("paused", "eligibility", "pause_store", "paused", args("ceo")),
    Case("pause", "eligibility", "pause_store", "pause", args("ceo", "why", "root")),
    Case("resume", "eligibility", "pause_store", "resume", args("ceo", "again", "root")),
    Case("record_failure", "eligibility", "failure_counter", "record", args("ceo")),
    Case("clear_failures", "eligibility", "failure_counter", "clear", args("ceo")),
    Case("state", "eligibility", "agent_states", "state", args("ceo")),
    # hierarchy
    Case("hire", "hierarchy", "hiring", "hire", args(
        "ceo", "dev", "Developer", "Code.", model="m1", tools=["read"], can_hire=True, max_children=2, workspace="/ws", inputs=["/data"],
        approved=True)),
    Case("retire", "hierarchy", "retirement", "retire", args("ceo", "qa", "gone")),
    Case("retire_team", "hierarchy", "retirement", "retire_team", args("ceo", "eng", "gone")),
    # dispatch
    Case("can_message", "dispatch", "route_policy", "can_message", args("ceo", "ceo/eng", "r1")),
    Case("_next_hops", "dispatch", "hop_counter", "next_hops", args("ceo")),
    Case("send", "dispatch", "message_sender", "send", lambda w: _send_all(), lambda w: _send_expected()),
    Case("delegate", "dispatch", "task_assigner", "delegate", args("ceo", "ceo/eng", "T", "goal", "accept", ["/in"], 2, "r2")),
    Case("_normalize_artifact", "dispatch", "artifact_normalizer", "normalize", args("ceo", "ceo/AGENT.md", "2020-01-01T00:00:00")),
    Case("report", "dispatch", "task_reporter", "report", with_task(lambda t: (("ceo", t.id, "done", "summary", ["ceo/AGENT.md"], "lessons"), {}))),
    FunctionCase("_check_lessons", "dispatch", "hirearchy.app._facade_dispatch", "check_lessons", with_task(lambda t: ((t, "done", "lessons"), {}))),
    # services
    Case("service_names", "services", "service_catalog", "service_names", args("ceo")),
    Case("define_service", "services", "service_commands", "define_service", args(
        "root", "ceo", "svc", description="d", inputs=[{"name": "x"}], acceptance=["a"], deliverable={"format": "md"}, budget=3, playbook="p",
        locked=True, notes="n", add_acceptance=["b"], remove_acceptance=["c"])),
    Case("retire_service", "services", "service_commands", "retire_service", args("root", "ceo", "svc", "gone")),
    Case("request", "services", "service_commands", "request", args(
        "root", "svc", {"x": "1"}, title="T", note="n", extra_acceptance=["e"], budget=2, revises="r1")),
    Case("revise_playbook", "services", "service_commands", "revise_playbook", args("ceo", "svc", "content", "why", ["R1"])),
    Case("feedback", "services", "service_commands", "feedback", args("root", "t1", "accept", "good")),
    # overview
    Case("tree", "overview", "org_tree", "tree"),
    # prompts
    Case("_agent_line", "prompts", "agent_lines", "agent_line", args("ceo")),
    FunctionCase("_indent", "prompts", "hirearchy.app._facade_prompts", "indent", args("a\nb", 4)),
    Case("_quote", "prompts", "task_quoter", "quote", with_task(lambda t: ((t,), {}))),
    Case("state_summary", "prompts", "state_summarizer", "state_summary", args("ceo", {"t1"})),
    Case("_files_lines", "prompts", "files_lines", "lines", args("ceo", {"workspace": "w"})),
    Case("whoami", "prompts", "agent_whoami", "whoami", args("ceo")),
    Case("_render_in_context", "prompts", "context_renderer", "render", with_task(lambda t: (("ceo", t), {}))),
    Case("_upstream", "prompts", "upstream_tasks", "upstream", with_task(lambda t: (("ceo", t), {}))),
    Case("run_prompt", "prompts", "run_prompt_builder", "run_prompt", with_task(lambda t: (("ceo", [t]), {}))),
]


def case_id(case: Case | FunctionCase) -> str:
    return f"{case.mixin}.{case.name}"


def kind_of(name: str) -> str:
    """``method``, ``staticmethod``, ``classmethod`` or ``property``: what ``Org.<name>`` is (the recorded surface keeps it)."""
    raw = inspect.getattr_static(Org, name)
    return type(raw).__name__ if isinstance(raw, (staticmethod, classmethod, property)) else "method"


def invoke(org: Org, name: str, call: Call) -> Any:
    """``org.<name>(*args, **kwargs)``; a property is read."""
    positional, keywords = call
    target = getattr(org, name)
    return target if kind_of(name) == "property" else target(*positional, **keywords)


def binds(port: type, method: str, call: Call) -> dict[str, Any]:
    """The call as the Protocol method names its arguments (so that a positional and a keyword spelling of one call are the same call)."""
    signature = inspect.signature(getattr(port, method))
    bound = signature.bind(None, *call[0], **call[1])
    bound.apply_defaults()
    return dict(list(bound.arguments.items())[1:])


@dataclass
class Made:
    """One call of a port, as recorded: which port, which method, with what, and the outcome (the result, or the exception)."""

    port: type
    method: str
    call: Call
    result: Any = None
    error: BaseException | None = None


class Returned:
    """What a spy answers: a distinct object per call, so that ``is`` proves the facade returned what the port returned."""

    def __init__(self, label: str) -> None:
        self.label = label

    def __repr__(self) -> str:
        return f"<returned by {self.label}>"


@dataclass
class Tape:
    calls: list[Made] = field(default_factory=list)


class Spy:
    """A port that does nothing but record its calls and answer ``Returned`` (the fake of any Protocol)."""

    def __init__(self, port: type, tape: Tape) -> None:
        self._port, self._tape = port, tape

    def __getattr__(self, method: str) -> Callable[..., Any]:
        if method.startswith("_") or not callable(getattr(self._port, method, None)):
            raise AttributeError(method)

        def call(*positional: Any, **keywords: Any) -> Returned:
            made = Made(self._port, method, (positional, keywords), Returned(f"{self._port.__name__}.{method}"))
            self._tape.calls.append(made)
            return made.result  # type: ignore[no-any-return]

        return call


class Recording:
    """A real port that is asked as usual and remembers every call with its outcome."""

    def __init__(self, port: type, real: object, tape: Tape) -> None:
        self._port, self._real, self._tape = port, real, tape

    def __getattr__(self, method: str) -> Callable[..., Any]:
        target = getattr(self._real, method)

        def call(*positional: Any, **keywords: Any) -> Any:
            made = Made(self._port, method, (positional, keywords))
            self._tape.calls.append(made)
            try:
                made.result = target(*positional, **keywords)
            except BaseException as error:
                made.error = error
                raise
            return made.result

        return call

