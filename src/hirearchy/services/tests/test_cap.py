"""``playbook_word_cap``: the longest playbook an organization accepts."""

from __future__ import annotations

import pytest

from hirearchy.services._cap import DEFAULT_PLAYBOOK_WORDS, playbook_word_cap


def test_the_cap_is_the_setting() -> None:
    assert playbook_word_cap({"playbook_max_words": 250}) == 250
    assert playbook_word_cap({"playbook_max_words": "250"}) == 250


@pytest.mark.parametrize("value", [0, -3, "0", "abc", None, [5], {"a": 1}])
def test_a_setting_that_is_not_a_positive_number_means_one_thousand(value: object) -> None:
    assert playbook_word_cap({"playbook_max_words": value}) == DEFAULT_PLAYBOOK_WORDS == 1000


def test_the_cap_is_public_so_that_reflection_reads_the_setting_the_same_way() -> None:
    import hirearchy.services as services

    assert services.playbook_word_cap is playbook_word_cap and "playbook_word_cap" in services.__all__
