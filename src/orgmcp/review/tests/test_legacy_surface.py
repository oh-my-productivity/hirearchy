"""The names ``orgmcp.review`` kept exporting when the module became a package (``LEGACY_EXPORTS``, until step E3).

Characterization: these tests passed on the module ``review.py`` and must keep passing on the package."""

from __future__ import annotations

import importlib

from orgmcp.review import api

review = importlib.import_module("orgmcp.review")  # as a module object: the tests read its attributes by name


def test_the_old_names_are_still_exported() -> None:
    for name in ("LEDGER", "Note", "Review", "read_ledger", "total_runs", "review_if_due", "review"):
        assert hasattr(review, name), name
    assert review.LEDGER == "reviews"


def test_the_data_types_are_the_ones_of_the_api() -> None:
    assert review.Note is api.Note and review.Review is api.Review


def test_the_scheduler_and_the_cli_reach_the_functions_through_the_package() -> None:
    assert callable(review.review) and callable(review.review_if_due)
