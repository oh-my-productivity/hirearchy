"""``run_environment``: the one place that shapes the environment kiro-cli sees (docs/design/kiro-runtime-v3.md 5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kiro._env import SCRUBBED_PREFIX, SCRUBBED_VARIABLES, run_environment

HOME = Path("/state/kiro-home/org-1")


@pytest.mark.parametrize("name", sorted(SCRUBBED_VARIABLES))
def test_each_scrubbed_variable_is_removed(name: str) -> None:
    assert name not in run_environment({name: "x", "PATH": "/usr/bin"}, HOME)


def test_the_scrubbed_names_are_the_ones_of_the_design() -> None:
    assert set(SCRUBBED_VARIABLES) == {
        "ASBX_KIRO_MANDATORY_MCPS", "KIRO_CHAT_LOG_FILE", "KIRO_DUMP_CONFIGURATION", "KIRO_DUMP_CONFIGURATION_DIR",
        "KIRO_DUMP_REQUESTS", "KIRO_DUMP_REQUESTS_DIR",
    }
    assert SCRUBBED_PREFIX == "KIRO_FEATURE_"


def test_a_feature_variable_is_removed() -> None:
    assert "KIRO_FEATURE_X" not in run_environment({"KIRO_FEATURE_X": "1", "KIRO_FEATURES": "kept"}, HOME)
    assert run_environment({"KIRO_FEATURES": "kept"}, HOME)["KIRO_FEATURES"] == "kept"


def test_an_inherited_kiro_home_is_replaced() -> None:
    assert run_environment({"KIRO_HOME": "/elsewhere"}, HOME)["KIRO_HOME"] == str(HOME)
    assert run_environment({}, HOME)["KIRO_HOME"] == str(HOME)


def test_the_credential_the_log_level_the_path_and_the_session_variables_are_kept() -> None:
    kept = {"KIRO_API_KEY": "k", "KIRO_LOG_LEVEL": "debug", "PATH": "/usr/bin", "KIRO_SESSION_ID": "s", "KIRO_ENABLED_FEATURES": "a,b"}
    result = run_environment(kept, HOME)
    assert {name: result[name] for name in kept} == kept


def test_the_input_is_not_mutated_and_a_new_dict_is_returned() -> None:
    variables = {"KIRO_DUMP_REQUESTS": "1", "KIRO_HOME": "/x", "PATH": "/usr/bin"}
    before = dict(variables)
    result = run_environment(variables, HOME)
    assert variables == before and result is not variables
    result["NEW"] = "1"
    assert "NEW" not in variables
