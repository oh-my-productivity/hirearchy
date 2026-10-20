"""Contract of ``TokenSource``: the real one (``secrets``) and the counting one produce tokens of the same shape."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import TokenSource
from orgmcp.kernel.testing import IMPLEMENTATIONS

HEX = re.compile(r"[0-9a-f]*")


@pytest.fixture(params=IMPLEMENTATIONS[TokenSource], ids=lambda factory: factory.__name__)
def tokens(request: pytest.FixtureRequest, tmp_path: Path) -> TokenSource:
    made = cast(Callable[[Path], TokenSource], request.param)(tmp_path)
    assert isinstance(made, TokenSource)
    return made


@pytest.mark.parametrize("nbytes", [1, 2, 4, 16])
def test_a_token_is_two_lowercase_hex_digits_per_byte(tokens: TokenSource, nbytes: int) -> None:
    token = tokens.token_hex(nbytes)
    assert len(token) == 2 * nbytes and HEX.fullmatch(token) is not None


def test_tokens_are_not_repeated(tokens: TokenSource) -> None:
    made = [tokens.token_hex(4) for _ in range(300)]
    assert len(set(made)) == len(made)
