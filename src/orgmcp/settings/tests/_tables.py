"""Input tables with the answers the legacy code (``health._number``, ``health.config_number``, ``core.config_default_model``,
``core._message_cap``) gives. They were produced by running the legacy functions; they pin the behaviour the move must keep."""

from __future__ import annotations

import math

# (value, finite_number(value))
FINITE_NUMBER: list[tuple[object, float | None]] = [
    (0, 0), (1, 1), (-3, -3), (2.5, 2.5), (-0.0, -0.0), (1e300, 1e300), (10**30, 10**30),
    (True, None), (False, None),
    ("1800", 1800), ("0", 0), ("-7", -7), ("2.5", 2.5), ("2.0", 2), ("1e3", 1000), (" 90 ", 90), ("\t5\n", 5), ("+4", 4),
    ("1_000", 1000), ("0x10", None), ("", None), ("abc", None), ("12abc", None), ("1,5", None),
    ("nan", None), ("NaN", None), ("inf", None), ("-inf", None), ("Infinity", None),
    (math.nan, None), (math.inf, None), (-math.inf, None),
    (None, None), ([], None), ([1], None), ({}, None), ((1,), None), (b"5", None), (object, None), (1 + 2j, None),
]

# (config, key, kind, config_number(config, key, kind))
CONFIG_NUMBER: list[tuple[dict[str, object], str, type, float]] = [
    ({}, "max_parallel", int, 3), ({}, "poll_seconds", float, 2.0), ({}, "run_timeout", float, 1800.0),
    ({}, "heartbeat_seconds", float, 60.0), ({}, "events_keep_days", int, 30),
    ({"max_parallel": 5}, "max_parallel", int, 5), ({"max_parallel": 2.9}, "max_parallel", int, 2),
    ({"max_parallel": "4"}, "max_parallel", int, 4), ({"max_parallel": " 4 "}, "max_parallel", int, 4),
    ({"max_parallel": "4.5"}, "max_parallel", int, 4),
    ({"max_parallel": True}, "max_parallel", int, 3), ({"max_parallel": False}, "max_parallel", int, 3),
    ({"max_parallel": None}, "max_parallel", int, 3), ({"max_parallel": "abc"}, "max_parallel", int, 3),
    ({"max_parallel": [2]}, "max_parallel", int, 3), ({"max_parallel": {"a": 1}}, "max_parallel", int, 3),
    ({"max_parallel": math.nan}, "max_parallel", int, 3), ({"max_parallel": math.inf}, "max_parallel", int, 3),
    ({"max_parallel": "inf"}, "max_parallel", int, 3), ({"max_parallel": "nan"}, "max_parallel", int, 3),
    ({"poll_seconds": 0.05}, "poll_seconds", float, 0.05), ({"poll_seconds": "0.5"}, "poll_seconds", float, 0.5),
    ({"poll_seconds": 3}, "poll_seconds", float, 3.0), ({"poll_seconds": True}, "poll_seconds", float, 2.0),
    ({"poll_seconds": -1}, "poll_seconds", float, -1.0), ({"poll_seconds": 0}, "poll_seconds", float, 0.0),
    ({"run_timeout": "1800"}, "run_timeout", float, 1800.0), ({"run_timeout": "1e3"}, "run_timeout", int, 1000),
    ({"run_timeout": 10}, "run_timeout", int, 10),
    ({"other": 1}, "max_parallel", int, 3),
]

# (config, config_default_model(config))
DEFAULT_MODEL_OF: list[tuple[dict[str, object] | None, str]] = [
    (None, "claude-sonnet-5.5"), ({}, "claude-sonnet-5.5"), ({"default_model": None}, "claude-sonnet-5.5"),
    ({"default_model": ""}, "claude-sonnet-5.5"), ({"default_model": "   "}, "claude-sonnet-5.5"),
    ({"default_model": "claude-haiku-4.5"}, "claude-haiku-4.5"), ({"default_model": "  m1  "}, "m1"),
    ({"default_model": 5}, "5"), ({"default_model": 0}, "claude-sonnet-5.5"), ({"default_model": False}, "claude-sonnet-5.5"),
    ({"default_model": True}, "True"), ({"default_model": ["a"]}, "['a']"), ({"default_model": []}, "claude-sonnet-5.5"),
    ({"other": "x"}, "claude-sonnet-5.5"),
]

# (config, config_message_cap(config)); the default is 20000
MESSAGE_CAP: list[tuple[dict[str, object], int]] = [
    ({"max_message_chars": 20000}, 20000), ({"max_message_chars": 500}, 500), ({"max_message_chars": 1}, 1),
    ({"max_message_chars": "500"}, 500), ({"max_message_chars": " 500 "}, 500), ({"max_message_chars": 12.7}, 12),
    ({"max_message_chars": 0}, 20000), ({"max_message_chars": -5}, 20000), ({"max_message_chars": "0"}, 20000),
    ({"max_message_chars": "-1"}, 20000), ({"max_message_chars": 0.5}, 20000),
    ({"max_message_chars": None}, 20000), ({"max_message_chars": "abc"}, 20000), ({"max_message_chars": ""}, 20000),
    ({"max_message_chars": "12.5"}, 20000), ({"max_message_chars": [5]}, 20000), ({"max_message_chars": {}}, 20000),
    ({"max_message_chars": True}, 1),  # int(True) == 1: a boolean is a cap of one character (kept as it is)
    ({"max_message_chars": False}, 20000),
]
