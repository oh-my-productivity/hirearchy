"""``OrgRuntime`` has one field per port of ARCHITECTURE.md section 3 (3.1-3.35; 3.36 are the entry points' own ports).

The ports whose step has not run yet are strict xfails (``STEP`` below names the step): the step that adds the field marks itself done in
its ``app/fields_<pkg>.py``, which turns the xfail into a requirement. The pending set only shrinks.
"""

from __future__ import annotations

import re
import typing
from dataclasses import fields
from pathlib import Path

import pytest

from orgmcp.app.runtime import OrgRuntime

from . import _parts

DOCUMENT = Path(__file__).resolve().parents[4] / "ARCHITECTURE.md"

# section of ARCHITECTURE.md -> the step that adds the fields of its ports
STEP = {
    "3.1": "M2", "3.2": "A-templates", "3.3": "A-settings", "3.4": "A-settings", "3.5": "A-snapshots", "3.6": "A-eventlog",
    "3.7": "A-telemetry", "3.8": "A-processes", "3.9": "A-agents", "3.10": "A-mail", "3.11": "A-runs", "3.12": "B-eligibility",
    "3.13": "B-strays", "3.14": "B-traces", "3.15": "B-delivery", "3.16": "B-access", "3.17": "B-orgfiles", "3.18": "B-budget",
    "3.19": "B-hierarchy", "3.20": "B-dispatch", "3.21": "C-services", "3.22": "C-reflection", "3.23": "C-overview",
    "3.24": "C-prompts", "3.25": "C-health", "3.26": "C-review", "3.27": "C-stalls", "3.28": "C-attention", "3.29": "C-daemon",
    "3.30": "C-progress", "3.31": "C-obs-2", "3.32": "C-blueprint-2", "3.33": "A-bootstrap", "3.34": "B-kiro", "3.35": "C-dashdata",
}
# Steps that are done: their ports have a field (or are in NOT_A_FIELD). Neither is listed here: a step marks itself in the part it fills
# (``STEP = "<step>"`` and ``NOT_A_FIELD = {port: why}`` of ``app/fields_<pkg>.py``), so that no two steps edit the same line.
DONE = _parts.done_steps()
NOT_A_FIELD = _parts.not_a_field()
# kernel ports whose real implementation another step writes (kernel/tests: contract_debt.PENDING), and the ports of 3.33 that A-skill (not A-bootstrap) adds
ELSEWHERE = {"EventSink": "A-telemetry", "TraceTap": "A-telemetry", "SkillSource": "A-skill", "SkillStore": "A-skill", "SkillInstaller": "A-skill"}


def protocols() -> list[tuple[str, str]]:
    """(port, step) for every ``class X(Protocol)`` of sections 3.1-3.35."""
    found, section = [], ""
    start = False
    for line in DOCUMENT.read_text(encoding="utf-8").splitlines():
        if line.startswith("## 3. "):
            start = True
        elif line.startswith("## 4. "):
            break
        if not start:
            continue
        if heading := re.match(r"### (3\.\d+) ", line):
            section = heading.group(1)
        elif (port := re.match(r"class (\w+)\(Protocol", line)) and section in STEP and port.group(1) not in NOT_A_FIELD:
            found.append((port.group(1), ELSEWHERE.get(port.group(1), STEP[section])))
    return found


def field_types() -> set[str]:
    return {getattr(hint, "__name__", str(hint)) for name, hint in typing.get_type_hints(OrgRuntime).items() if name != "root"}


def params() -> list[object]:
    return [
        pytest.param(port, id=port, marks=[] if step in DONE else pytest.mark.xfail(strict=True, reason=f"pending: {step}"))
        for port, step in protocols()
    ]


def test_the_document_is_parsed() -> None:
    ports = dict(protocols())
    assert len(ports) >= 120 and {"Clock", "AtomicWriter", "MailboxReader", "Hiring", "SchedulerStatus"} <= set(ports)
    assert ports["Clock"] == "M2" and ports["MailboxReader"] == "A-mail" and ports["EventSink"] == "A-telemetry"


@pytest.mark.parametrize("port", params())
def test_the_runtime_has_a_field_typed_by_the_port(port: str) -> None:
    assert port in field_types()


def test_the_runtime_is_data_only() -> None:
    assert all(not callable(getattr(OrgRuntime, f.name, None)) for f in fields(OrgRuntime))
    assert {f.name for f in fields(OrgRuntime)} >= {"root", "resources", "paths", "clock", "ids", "atomic_writer", "ledgers", "environment"}
