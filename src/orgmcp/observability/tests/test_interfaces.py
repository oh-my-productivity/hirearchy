"""Every class of the package says which interface it implements (rule D), and the package exports exactly its api."""

from __future__ import annotations

import orgmcp.observability as package
from orgmcp.observability import api
from orgmcp.observability._derive import LogTraceDerivers, MessageTraceDeriver
from orgmcp.observability._events import LogEventQueries
from orgmcp.observability._history import IndexedMessageHistory
from orgmcp.observability._metrics import DerivedMetricQueries
from orgmcp.observability._ports import MessageHistory, RunCollection, TraceDeriver, TraceDerivers
from orgmcp.observability._runs import RunCollector
from orgmcp.observability._trace import DerivedTraceQueries
from orgmcp.observability.api import EventQueries, MetricQueries, TraceQueries
from orgmcp.observability.testing import FixedEventQueries, FixedMetricQueries, FixedTraceQueries


def test_each_class_names_its_interface() -> None:
    assert LogEventQueries.__mro__[1] is EventQueries and FixedEventQueries.__mro__[1] is EventQueries
    assert DerivedTraceQueries.__mro__[1] is TraceQueries and FixedTraceQueries.__mro__[1] is TraceQueries
    assert DerivedMetricQueries.__mro__[1] is MetricQueries and FixedMetricQueries.__mro__[1] is MetricQueries
    assert RunCollector.__mro__[1] is RunCollection and IndexedMessageHistory.__mro__[1] is MessageHistory
    assert MessageTraceDeriver.__mro__[1] is TraceDeriver and LogTraceDerivers.__mro__[1] is TraceDerivers


def test_the_package_exports_exactly_its_api() -> None:
    assert package.__all__ == api.__all__
    assert set(api.__all__) == {"EventQueries", "TraceQueries", "MetricQueries", "percentile", "parse_when", "fmt_rel", "normalize_refusal", "is_error",
                                "format_event"}
    assert all(getattr(package, name) is getattr(api, name) for name in api.__all__)
