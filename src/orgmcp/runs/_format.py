"""RED skeleton (step A-runs): the text format of a run log, written and parsed in one place."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from ..kernel import JsonObject

HEAD_BYTES = 4096
TAIL_BYTES = 2048
FACTS_BYTES = 4096


def run_id_of(addr: str, log: Path | str) -> str:
    raise NotImplementedError("red: A-runs")


def run_record(*, pgid: int, lstart: str | None, started: float, scheduler: int, log: str) -> JsonObject:
    raise NotImplementedError("red: A-runs")


def log_header(addr: str, messages: int, senders: Iterable[str]) -> str:
    raise NotImplementedError("red: A-runs")


def log_invocation(cwd: Path | str, cmd: Sequence[str]) -> str:
    raise NotImplementedError("red: A-runs")


def log_prompt(prompt: str) -> str:
    raise NotImplementedError("red: A-runs")


def log_exit(code: int, elapsed: float) -> str:
    raise NotImplementedError("red: A-runs")


def log_timeout(seconds: float) -> str:
    raise NotImplementedError("red: A-runs")


def log_retired() -> str:
    raise NotImplementedError("red: A-runs")


def log_interrupted() -> str:
    raise NotImplementedError("red: A-runs")


def log_failed_start(reason: object) -> str:
    raise NotImplementedError("red: A-runs")


def log_note(text: str) -> str:
    raise NotImplementedError("red: A-runs")


def is_failed(tail: str) -> bool:
    raise NotImplementedError("red: A-runs")


def is_runtime_only(head: str) -> bool:
    raise NotImplementedError("red: A-runs")


def parse_facts(tail: str) -> JsonObject:
    raise NotImplementedError("red: A-runs")


def cut_tail(data: bytes, size: int, max_lines: int) -> tuple[str, bool]:
    raise NotImplementedError("red: A-runs")
