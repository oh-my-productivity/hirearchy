import os

import pytest

# The shared fixtures (org, isolated_kiro, fresh_telemetry, real_kiro) live in tests/testkit/fixtures.py; they are registered here, at
# the repository root, so they reach tests/ AND the colocated tests in src/orgmcp/**/tests/ (pytest resolves conftest.py by ancestry).
pytest_plugins = ["testkit.fixtures"]


def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true", default=False,
                     help="also run tests marked 'integration' (they use the real kiro-cli / a real LLM)")


def pytest_collection_modifyitems(config, items):
    """Tests marked ``integration`` call a real LLM through kiro-cli: skipped unless asked for
    (``pytest --run-integration`` or ``ORGMCP_RUN_INTEGRATION=1``)."""
    if config.getoption("--run-integration") or os.environ.get("ORGMCP_RUN_INTEGRATION"):
        return
    skip = pytest.mark.skip(reason="real-LLM integration test: pass --run-integration (or ORGMCP_RUN_INTEGRATION=1) to run it")
    for item in items:
        if "integration" not in item.keywords and item.path.parent.name == "integration":
            item.add_marker(pytest.mark.integration)  # whatever lives in tests/integration/ is one: a forgotten mark cannot leak
        if "integration" in item.keywords:
            item.add_marker(skip)
