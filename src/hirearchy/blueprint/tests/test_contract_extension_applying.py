"""Contract of ``ExtensionApplying``: an approved extension is applied against the organization as it is now, or refused as stale or invalid."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.blueprint import BlueprintError, ExtensionApplying
from hirearchy.blueprint.testing import IMPLEMENTATIONS, ExtensionApplyHarness

from ._support import implementations, make


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ExtensionApplying]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> ExtensionApplyHarness:
    made = make(request, tmp_path, ExtensionApplyHarness)
    assert isinstance(made.applier, ExtensionApplying)
    return made


def test_an_extension_with_its_plan_id_is_applied_and_the_reply_names_the_change(h: ExtensionApplyHarness) -> None:
    reply = h.applier.apply(h.extension, plan_id=h.plan_id)
    assert reply.startswith(f"applied the change {h.plan_id} to ")


def test_without_a_plan_id_the_comparison_is_skipped(h: ExtensionApplyHarness) -> None:
    assert h.applier.apply(h.extension, plan_id=None).startswith("applied the change ")


def test_a_plan_id_that_is_not_the_extensions_is_refused_as_stale(h: ExtensionApplyHarness) -> None:
    with pytest.raises(BlueprintError, match="^not applied: plan_id does not match this change against the organization as it is now"):
        h.applier.apply(h.extension, plan_id="000000000000")


def test_a_blueprint_that_is_not_an_extension_is_refused(h: ExtensionApplyHarness) -> None:
    with pytest.raises(BlueprintError):
        h.applier.apply({"mission": "m", "agents": []}, plan_id=None)
