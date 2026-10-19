"""The free input of a contract (inputs, deliverable) in its fixed form."""

from __future__ import annotations

from pathlib import Path

from ..kernel import JsonObject, OrgError
from .api import DELIVERABLE_KEYS, INPUT_RE, ContractNormalizer


class TextContractNormalizer(ContractNormalizer):
    """Inputs are ``{name, description, required}`` (or ``'name*:description'``); a deliverable is ``{description, format?, max_words?, path?}``."""

    def parse_input_spec(self, spec: str) -> JsonObject:
        raise NotImplementedError

    def inputs(self, value: object) -> list[JsonObject]:
        raise NotImplementedError

    def deliverable(self, value: object) -> JsonObject:
        raise NotImplementedError
