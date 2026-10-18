"""The legacy names of ``orgmcp.telemetry`` that remain until step E3, and what each one is now."""

from __future__ import annotations

import pytest

import orgmcp.telemetry as telemetry
from orgmcp import eventlog, kernel
from orgmcp.telemetry import api

RED = pytest.mark.xfail(strict=True, reason="red: A-telemetry")

LEGACY = {
    "DAY_RE", "ENVELOPE", "ERROR_MAX", "EVENTS_REL", "LINE_MAX", "PROCS", "SCHEMA_VERSION", "TITLE_MAX", "clip", "datetime", "dropped", "emit",
    "ensure_ignored", "note_trace", "process", "prune", "reset", "set_process", "single", "summarize_args", "traces_seen",
}


@RED
def test_the_package_exports_the_api_and_the_legacy_names_and_nothing_else() -> None:
    assert set(telemetry.__all__) == set(api.__all__) | LEGACY
    assert set(api.__all__) == {"ArgumentSummarizer", "EventRetention", "EventSinks", "ProcessLabel", "TraceScope"}


def test_every_exported_name_exists() -> None:
    assert [name for name in telemetry.__all__ if not hasattr(telemetry, name)] == []


@RED
def test_the_text_helpers_are_the_kernels() -> None:
    assert telemetry.clip is kernel.clip and telemetry.single is kernel.single and telemetry.TITLE_MAX == kernel.TITLE_MAX


def test_the_format_is_the_eventlogs() -> None:
    assert telemetry.SCHEMA_VERSION == eventlog.SCHEMA_VERSION and telemetry.LINE_MAX == eventlog.LINE_MAX
    assert telemetry.EVENTS_REL == eventlog.EVENTS_REL and telemetry.PROCS == eventlog.PROCS
    assert telemetry.DAY_RE is eventlog.DAY_RE and telemetry.ENVELOPE is eventlog.ENVELOPE


def test_error_max_is_the_limit_for_error_texts() -> None:
    assert telemetry.ERROR_MAX == 500


@RED
def test_the_retry_window_is_not_a_legacy_name_any_more() -> None:
    assert not hasattr(telemetry, "RETRY_AFTER")


def test_datetime_stays_for_the_fixtures_that_fix_the_clock() -> None:
    import datetime as stdlib

    assert telemetry.datetime is stdlib.datetime


@RED
def test_the_legacy_names_that_need_the_process_say_so_when_the_composition_root_is_not_loaded() -> None:
    from orgmcp.telemetry import _legacy

    assert callable(_legacy.install)


def test_the_default_retry_window_of_the_sink_is_five_seconds() -> None:
    from orgmcp.telemetry._sink import RETRY_AFTER

    assert RETRY_AFTER == 5.0
