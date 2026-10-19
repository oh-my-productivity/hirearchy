"""``YamlBlueprintLoader``: a blueprint from a path, a dict or YAML/JSON text, normalized.

PyYAML is used here (and in the kernel) and nowhere else; what it returns is ``object`` from this module on."""
from __future__ import annotations
import re
from pathlib import Path
from typing import cast
import yaml
from ..kernel import JsonObject
from ._protocols import TextFiles
from .api import BlueprintError, BlueprintLoader
_BULLET = re.compile('^\\s*(?:[-*+]|\\d{1,2}[.)])\\s+')
PATH_NAME_MAX = 1024

def _bullets(text: str) -> list[str]:
    """The lines of a bullet or numbered text, without their markers and without the empty ones."""
    raise NotImplementedError('red: C-blueprint-1')

def parse(text: str) -> object:
    raise NotImplementedError('red: C-blueprint-1')

def normalize(bp: object) -> JsonObject:
    """The blueprint with the lenient forms made strict: acceptance given as a bullet or numbered text becomes a list (the task's, and each service's)."""
    raise NotImplementedError('red: C-blueprint-1')

class YamlBlueprintLoader(BlueprintLoader):

    def __init__(self, files: TextFiles) -> None:
        self._files = files

    def load(self, source: object) -> JsonObject:
        raise NotImplementedError('red: C-blueprint-1')

    def load_text(self, text: str) -> JsonObject:
        raise NotImplementedError('red: C-blueprint-1')
