"""``retro_thresholds``: the tunable defaults of the retro brief, read from the optional ``retro:`` mapping of ORG.md (pure; design 4.9).

It mirrors ``reflection.quality_thresholds``: a value that fails keeps its default and adds a note (the brief's Details show the notes); an unknown key
and a ``retro`` that is no mapping are ignored with a note."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from fractions import Fraction

from .api import ITEMS_MAX, RETRO_DEFAULTS, RetroThresholds

_COUNTS = (  # (key, the lowest value it may have)
    ("after_verdicts", 1), ("window", 1), ("carry", 0), ("shape_cases", 2), ("criterion_cases", 2), ("escapes", 1), ("window_cases", 3),
    ("added_words", 1), ("accepted_cases", 1),
)
_KEYS = ", ".join(RETRO_DEFAULTS)


def _whole(value: object) -> int | None:
    """``value`` as a whole number: an int (not a bool), an integral float or a string of digits; else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None  # inf and nan are not integral
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        return int(value)
    return None


def _decimal(value: object) -> tuple[Fraction, str] | None:
    """``value`` as a ratio with the text it was written as: an int or a finite float (not a bool) or a decimal string; else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (int, float)):
        text = str(value)
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+(\.[0-9]+)?", value):
        text = value
    else:
        return None
    return Fraction(text), text


def retro_thresholds(config: Mapping[str, object]) -> tuple[RetroThresholds, tuple[str, ...]]:
    """The thresholds from the optional ``retro:`` mapping of ORG.md's frontmatter ``config``, and the notes for what was ignored (pure; design 4.9).
    A value that fails keeps its default and adds a note; an unknown key and a ``retro`` that is no mapping are ignored with a note."""
    if "retro" not in config:
        return RetroThresholds(), ()
    raw = config["retro"]
    if not isinstance(raw, Mapping):
        return RetroThresholds(), ("retro in ORG.md is not a mapping: the defaults are used.",)
    notes: list[str] = []
    counts: dict[str, int] = {}
    ratios: dict[str, tuple[Fraction, str]] = {}
    for key, lowest in _COUNTS:
        if key in raw:
            value = _whole(raw[key])
            if value is None or value < lowest:
                notes.append(f"retro.{key} in ORG.md is not a whole number of at least {lowest}: the default {RETRO_DEFAULTS[key]} is used.")
            else:
                counts[key] = value
    if "items" in raw:
        value = _whole(raw["items"])
        if value is None or value < 1:
            notes.append("retro.items in ORG.md is not 1, 2 or 3: the default 3 is used.")
        else:
            counts["items"] = min(value, ITEMS_MAX)
            if value > ITEMS_MAX:
                notes.append(f"retro.items in ORG.md is above {ITEMS_MAX}: {ITEMS_MAX} is used (a brief has at most {ITEMS_MAX} items).")
    for key, bound in (("shape_overlap", "above 0 and at most 1"), ("saturation", "above 0 and below 1")):
        if key in raw:
            read = _decimal(raw[key])
            if read is None or read[0] <= 0 or read[0] > 1 or (key == "saturation" and read[0] >= 1):
                notes.append(f"retro.{key} in ORG.md is not a decimal {bound}: the default {RETRO_DEFAULTS[key]} is used.")
            else:
                ratios[key] = read
    notes += [f"retro.{key} in ORG.md is not a threshold: ignored (the thresholds are {_KEYS})." for key in raw if str(key) not in RETRO_DEFAULTS]
    base = RetroThresholds()

    def count(key: str) -> int:
        return counts.get(key, int(RETRO_DEFAULTS[key]))

    overlap = ratios.get("shape_overlap", (base.shape_overlap, base.shape_overlap_text))
    saturation = ratios.get("saturation", (base.saturation, base.saturation_text))
    source = "ORG.md" if counts or ratios else "defaults"
    return RetroThresholds(
        count("after_verdicts"), count("window"), count("carry"), count("items"), count("shape_cases"), overlap[0], overlap[1],
        count("criterion_cases"), count("escapes"), count("window_cases"), saturation[0], saturation[1], count("added_words"), count("accepted_cases"),
        source,
    ), tuple(notes)
