"""Shared test machinery: fixtures, builders, the stand-in agents and the places in the repository that tests refer to.

``tests/`` is on ``sys.path`` (``pythonpath`` in pyproject.toml), so ``import testkit`` works in ``tests/`` and in the colocated
``src/orgmcp/**/tests/``. The constants below are absolute paths: a test that used to build them from its own ``__file__`` (which breaks
the moment the test moves) uses these instead.
"""

from pathlib import Path

TESTKIT = Path(__file__).resolve().parent
TESTS = TESTKIT.parent  # the directory of tests/test_*.py, tests/e2e, tests/meta, ...
REPO = TESTS.parent  # the repository root (examples/, skills/, README.md, pyproject.toml)

FAKE_AGENT = TESTKIT / "fake_agent.py"  # stand-in for kiro-cli: a script that works as one agent (a subprocess, not imported)
FAKE_TEAM_AGENT = TESTKIT / "fake_team_agent.py"  # the same for a whole team
EXPECTED_DASH = TESTKIT / "expected_dash"  # the expected text of `orgmcp dash --once` (tests/test_dashboard_characterization)
