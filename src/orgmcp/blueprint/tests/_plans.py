"""The blueprints of the plan suites and what the legacy second half of ``main`` made of them (no test lives here).

``golden/second_half.json`` was captured from the flat ``blueprint.py`` before it moved: for every kind of example blueprint, as a plain task and as
a service (``<kind>[-service]``), as the template is (``raw``: its placeholders are still there, so it has errors) and as the assistant fills it
(``filled``): the details of the plan, the block for the user, the errors, the charter of every agent, the default playbook of every service, the
text of ``propose_org`` (a few) and the plan id of the filled blueprint at a fixed base. The directory the blueprints were made in is written
``<BASE>``; ``blueprint_at`` makes the same blueprints in another one."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

GOLDEN = Path(__file__).resolve().parent / "golden" / "second_half.json"
FIXED_BASE = "/golden/base"
LABELS = [f"{kind}{'-service' if service else ''}" for kind in ("research", "documents", "code", "analysis") for service in (False, True)]
KEYS = [f"{label}/{variant}" for label in LABELS for variant in ("raw", "filled")]
PROPOSED = ["research/filled", "research-service/filled", "code/filled", "research-service/raw", "analysis/raw"]


def golden() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return result


def fill(text: str) -> str:
    """What the assistant does with a template: every placeholder gets the user's (here: a fixed) value."""
    for placeholder, value in (("<folder-with-your-files>", "docs"), ("<folder-with-your-data>", "data"), ("<project-folder>", "proj"),
                               ("<name>", "briefs"), ("<service-name>", "my-service"), ("<input-name>", "topic"), ("<PLACEHOLDER>", "x")):
        text = text.replace(placeholder, value)
    return re.sub(r"<[A-Z][^<>\n]*>", "Sample text", text)


def base_dir(tmp: Path) -> Path:
    """The directory the blueprints are made in: it holds what the templates point at."""
    base = tmp.resolve() / "base"
    for name in ("docs", "data", "proj", "deliverables"):
        (base / name).mkdir(parents=True, exist_ok=True)
    return base


def template_at(label: str, variant: str, base: Path) -> str:
    """The text of the example ``label`` in ``base``, as it is (``raw``) or filled in (``filled``)."""
    text: str = golden()["examples"][label].replace(FIXED_BASE, str(base))
    return fill(text) if variant == "filled" else text


def scrub(text: str, base: Path) -> str:
    """The text with the directory of the blueprints written ``<BASE>`` and the plan id written ``<ID>``."""
    text = text.replace(str(base), "<BASE>")
    return re.sub(r'plan_id(: |=")[0-9a-f]{12}', lambda m: f"plan_id{m.group(1)}<ID>", text)
