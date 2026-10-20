"""The legacy names of ``orgmcp.telemetry`` that remain until step E3, and what each one is now."""

from __future__ import annotations

import pytest

import orgmcp.telemetry as telemetry
from orgmcp import eventlog, kernel
from orgmcp.telemetry import _process, api

LEGACY = {
    "DAY_RE", "ENVELOPE", "ERROR_MAX", "EVENTS_REL", "LINE_MAX", "PROCS", "SCHEMA_VERSION", "TITLE_MAX", "clip", "dropped", "emit",
    "ensure_ignored", "note_trace", "process", "prune", "reset", "set_process", "single", "summarize_args", "traces_seen",
}


def test_the_package_exports_the_api_and_the_legacy_names_and_nothing_else() -> None:
    assert set(telemetry.__all__) == set(api.__all__) | LEGACY
    assert set(api.__all__) == {"ArgumentSummarizer", "EventRetention", "EventSinks", "ProcessLabel", "TraceScope"}


def test_every_exported_name_exists() -> None:
    assert [name for name in telemetry.__all__ if not hasattr(telemetry, name)] == []


def test_the_text_helpers_are_the_kernels() -> None:
    assert telemetry.clip is kernel.clip and telemetry.single is kernel.single and telemetry.TITLE_MAX == kernel.TITLE_MAX


def test_the_format_is_the_eventlogs() -> None:
    assert telemetry.SCHEMA_VERSION == eventlog.SCHEMA_VERSION and telemetry.LINE_MAX == eventlog.LINE_MAX
    assert telemetry.EVENTS_REL == eventlog.EVENTS_REL and telemetry.PROCS == eventlog.PROCS
    assert telemetry.DAY_RE is eventlog.DAY_RE and telemetry.ENVELOPE is eventlog.ENVELOPE


def test_error_max_is_the_limit_for_error_texts() -> None:
    assert telemetry.ERROR_MAX == 500


def test_the_retry_window_is_not_a_legacy_name_any_more() -> None:
    assert not hasattr(telemetry, "RETRY_AFTER")


def test_datetime_is_not_a_legacy_name_any_more() -> None:
    assert not hasattr(telemetry, "datetime")  # the time of the events is the Clock of the runtime (wiring.overriding), not a module attribute


def test_the_legacy_names_that_need_the_process_say_so_when_nothing_is_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_process, "_installed", None)
    with pytest.raises(RuntimeError, match="orgmcp.app is not loaded"):
        telemetry.process()
    telemetry.emit("/nowhere", "custom.kind")  # the emission never raises, installed or not


def test_the_default_retry_window_of_the_sink_is_five_seconds() -> None:
    from orgmcp.telemetry._sink import RETRY_AFTER

    assert RETRY_AFTER == 5.0
