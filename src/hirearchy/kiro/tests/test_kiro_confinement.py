"""``KiroConfinementPolicy``: the golden file that the contract suite checks it against is complete."""

from __future__ import annotations

from typing import cast

from hirearchy.kiro import ConfinementPolicy
from hirearchy.kiro._confinement import KiroConfinementPolicy

from ._support import golden


def test_it_is_a_confinement_policy() -> None:
    assert isinstance(KiroConfinementPolicy(), ConfinementPolicy)


def test_the_golden_file_covers_every_combination() -> None:
    cases = cast(list[dict[str, object]], golden("confinement.json"))
    assert len(cases) == 16 * 4 * 3  # tool sets of {read, write, shell, web_search} x workspace {none, inside, the org itself, outside} x inputs {0, 1, 2}
    assert len({(tuple(cast(list[str], c["tools"])), c["workspace"], tuple(cast(list[str], c["inputs"]))) for c in cases}) == len(cases)
