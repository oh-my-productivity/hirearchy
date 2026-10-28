"""Contract of ``OrgLimits``: the file-backed ORG.md and its in-memory fake change ``max_depth`` and nothing else (design 5.5 step 3, G2)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import OrgError
from hirearchy.settings import DEFAULT_CONFIG, OrgLimits
from hirearchy.settings.testing import IMPLEMENTATIONS, LimitsHarness

TEXT = (
    "---\n"
    "# the limits of this organization\n"
    "max_hops: 40   # longest chain\n"
    "max_depth: 3\n"
    "default_model: 'claude-sonnet-5.5'\n"
    "extra_allowed_models:\n"
    "  - claude-opus-5.5\n"
    "events: false\n"
    "---\n"
    "# Mission é ✓\n\n  two trailing spaces  \n\n1. Rule one.\n2. Rule two.\n"
)


@pytest.fixture(params=IMPLEMENTATIONS[OrgLimits], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> LimitsHarness:
    made = cast(Callable[[Path], LimitsHarness], request.param)(tmp_path)
    assert isinstance(made.limits, OrgLimits)
    return made


def test_set_max_depth_returns_the_old_value_and_writes_the_new(h: LimitsHarness) -> None:
    h.put(TEXT)
    assert h.limits.set_max_depth(6) == 3
    assert h.config()["max_depth"] == 6
    assert h.limits.set_max_depth(3) == 6  # the undo of a change writes the old value back
    assert h.config()["max_depth"] == 3


def test_a_missing_max_depth_reads_as_the_default_and_is_written(h: LimitsHarness) -> None:
    h.put("---\nevents: false\n---\nrules\n")
    assert h.limits.set_max_depth(5) == DEFAULT_CONFIG["max_depth"]
    assert h.config()["max_depth"] == 5 and h.config()["events"] is False


def test_an_org_md_without_a_frontmatter_block_gets_one(h: LimitsHarness) -> None:
    h.put("# Mission\n\nStudy octopuses.\n")
    assert h.limits.set_max_depth(5) == DEFAULT_CONFIG["max_depth"]
    assert h.stored() == "---\nmax_depth: 5\n---\n# Mission\n\nStudy octopuses.\n"


def test_set_max_depth_keeps_every_other_key_and_the_body_byte_for_byte(h: LimitsHarness) -> None:
    h.put(TEXT)
    h.limits.set_max_depth(7)
    assert h.stored() == TEXT.replace("max_depth: 3\n", "max_depth: 7\n")  # the comments, quotes and the list are as they were
    h.put("---\nmax_hops: 40\n---\n# Body\n\n  keep   this  \n")
    h.limits.set_max_depth(2)
    assert h.stored() == "---\nmax_hops: 40\nmax_depth: 2\n---\n# Body\n\n  keep   this  \n"


@pytest.mark.parametrize("value", [0, -1, -40])
def test_a_value_below_1_is_refused_and_nothing_is_written(h: LimitsHarness, value: int) -> None:
    h.put(TEXT)
    with pytest.raises(OrgError):
        h.limits.set_max_depth(value)
    assert h.stored() == TEXT


@pytest.mark.parametrize("broken", ["---\nmax_depth: [3\n---\nbody\n", "---\nmax_depth: 3\nno end of the block\n", "---\n- a\n- b\n---\nbody\n"])
def test_an_unparseable_org_md_is_refused_and_nothing_is_written(h: LimitsHarness, broken: str) -> None:
    h.put(broken)
    with pytest.raises(OrgError):
        h.limits.set_max_depth(4)
    assert h.stored() == broken


def test_a_missing_org_md_is_refused(h: LimitsHarness) -> None:
    with pytest.raises(OrgError):
        h.limits.set_max_depth(4)
    assert h.stored() is None
