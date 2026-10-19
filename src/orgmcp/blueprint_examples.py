"""Ready-to-edit blueprint templates, served by the root tool ``blueprint_example(kind, service=False)``.

The texts moved into the package ``orgmcp.blueprint`` (``BlueprintExamples``); this module keeps the old names ``KINDS`` and ``example`` until step E3.
``orgmcp.app`` installs the implementation when it is loaded (``_install``): a legacy module may not import the private modules of a feature.
"""

from __future__ import annotations

from pathlib import Path

from .blueprint import EXAMPLE_KINDS, BlueprintExamples

KINDS = EXAMPLE_KINDS

_installed: BlueprintExamples | None = None


def _install(examples: BlueprintExamples) -> None:
    """Called by ``orgmcp.app`` when it is loaded."""
    global _installed
    _installed = examples


def example(kind: str = "research", base: Path | str = ".", service: bool = False) -> str:
    """The template text for ``kind`` with absolute paths under ``base``; ``service=True``: as a standing service."""
    if _installed is None:
        raise RuntimeError("orgmcp.app is not loaded: the templates of the blueprints are not installed")
    return _installed.example(kind, base, service)
