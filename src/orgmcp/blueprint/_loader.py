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

_BULLET = re.compile(r"^\s*(?:[-*+]|\d{1,2}[.)])\s+")
PATH_NAME_MAX = 1024  # text longer than this is never taken for a file name


def _bullets(text: str) -> list[str]:
    """The lines of a bullet or numbered text, without their markers and without the empty ones."""
    lines = [_BULLET.sub("", ln).strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]


def parse(text: str) -> object:
    try:
        return cast(object, yaml.safe_load(text))
    except yaml.YAMLError as exc:
        raise BlueprintError(f"blueprint is not valid YAML/JSON: {exc}") from exc


def normalize(bp: object) -> JsonObject:
    """The blueprint with the lenient forms made strict: acceptance given as a bullet or numbered text becomes a list (the task's, and each service's)."""
    if not isinstance(bp, dict):
        raise BlueprintError("a blueprint is a mapping with mission, needs, agents and task")
    task = bp.get("task")
    if isinstance(task, dict):
        acc = task.get("acceptance")
        if isinstance(acc, str):
            task = {**task, "acceptance": _bullets(acc)}
            bp = {**bp, "task": task}
    svcs = bp.get("services")
    if isinstance(svcs, list):
        fixed = []
        for sv in svcs:
            if isinstance(sv, dict) and isinstance(sv.get("acceptance"), str):
                sv = {**sv, "acceptance": _bullets(sv["acceptance"])}
            fixed.append(sv)
        bp = {**bp, "services": fixed}
    return bp


class YamlBlueprintLoader(BlueprintLoader):
    def __init__(self, files: TextFiles) -> None:
        self._files = files

    def load(self, source: object) -> JsonObject:
        if isinstance(source, dict):
            bp: object = source
        else:
            text = None
            if isinstance(source, Path):
                text = self._files.read(source.expanduser())
            elif isinstance(source, str) and "\n" not in source and len(source) < PATH_NAME_MAX:
                p = Path(source).expanduser()
                if self._files.is_file(p):
                    text = self._files.read(p)
            if text is None:
                text = str(source)
            bp = parse(text)
        return normalize(bp)

    def load_text(self, text: str) -> JsonObject:
        return normalize(parse(text))
