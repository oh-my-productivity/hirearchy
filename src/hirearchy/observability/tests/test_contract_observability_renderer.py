"""Contract of ``ObservabilityRenderer``: a pure function of the view it is given (``testing.PURE``), so it has one implementation; the suites of the views
it renders hold it to the exact text (``test_render``, ``test_second_golden``). Here, what any renderer must do with any view."""

from __future__ import annotations

from typing import Any

import pytest

from hirearchy.observability import ObservabilityRenderer
from hirearchy.observability._render import TextObservabilityRenderer

from ._support import expected


R: ObservabilityRenderer = TextObservabilityRenderer()


def test_rendering_does_not_change_the_view() -> None:
    import json

    view: dict[str, Any] = json.loads(expected("now_busy.json"))
    before = json.dumps(view)
    R.render_now(view, 10)
    assert json.dumps(view) == before


def test_the_same_view_is_the_same_text() -> None:
    import json

    view: dict[str, Any] = json.loads(expected("check_corrupt.json"))
    assert R.render_check(view) == R.render_check(json.loads(json.dumps(view)))


@pytest.mark.parametrize("cap", [None, 0, 3, 1000])
def test_a_cap_never_adds_more_than_the_hint(cap: int | None) -> None:
    import json

    lines = R.render_now(json.loads(expected("now_busy.json")), cap).splitlines()
    full = R.render_now(json.loads(expected("now_busy.json"))).splitlines()
    assert len(lines) == len(full) if cap is None or cap >= len(full) else len(lines) == cap + 1
