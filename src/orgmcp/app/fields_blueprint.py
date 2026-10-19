"""Runtime fields of ``blueprint`` (ARCHITECTURE.md 3.32): none yet - the ports of the second half (``C-blueprint-2``) come with the rest.

``wire_blueprint`` provides ``RoleLibrary``, ``BlueprintLoader`` and ``BlueprintValidator`` to a builder already (``Builder.get``); they become fields
when step C-blueprint-2 fills this part and sets ``STEP`` (``test_runtime_fields`` takes all of 3.32 as one step).

Importing this part installs the parts of the legacy functions of ``blueprint`` (``wire_blueprint.install_legacy_parts``): ``runtime.py`` imports every
part when the application package is loaded, and a legacy function (``blueprint.validate(bp)``, with no ``Org`` at hand) needs them from then on.
This goes with the legacy functions (E3)."""

from __future__ import annotations

from dataclasses import dataclass

from . import wire_blueprint

STEP: str | None = None  # set to the step's name when the step fills this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)

wire_blueprint.install_legacy_parts()


@dataclass(frozen=True)
class Fields:
    """No field yet: the step that gives the package its runtime ports adds them here."""
