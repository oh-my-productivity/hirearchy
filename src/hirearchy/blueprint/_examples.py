"""``TemplateBlueprintExamples``: the ready-to-edit blueprint templates, served by the root tool ``blueprint_example(kind, service=False)``."""

from __future__ import annotations

from pathlib import Path

from ..kernel import OrgError
from ._example_texts import (
    EXTENSION,
    SCHEMA,
    SERVICE_BODIES,
    SERVICE_BUDGETS,
    SERVICE_HEAD,
    SERVICE_SCHEMA,
    SERVICE_TAIL,
    TEMPLATES,
)
from .api import EXAMPLE_KINDS, BlueprintExamples


EXTENSION_KIND = "extension"


def _without_block(text: str, header: str) -> str:
    """``text`` minus the YAML block that starts at the line ``header`` (its more deeply indented lines go too)."""
    out, skipping = [], False
    indent = len(header) - len(header.lstrip())
    for line in text.split("\n"):
        if line.rstrip() == header.rstrip():
            skipping = True
            continue
        if skipping and (not line.strip() or len(line) - len(line.lstrip()) > indent):
            continue
        skipping = False
        out.append(line)
    return "\n".join(out)


def _service_template(kind: str) -> str:
    """The template of ``kind`` as a standing service: no needs.deliverable (the service has its own), ``services:``
    with one commented service, and ``task`` reduced to an optional commented first request."""
    head = TEMPLATES[kind].split("\ntask:\n")[0]
    head = _without_block(head, "  deliverable:").replace("{schema}", "{service_schema}", 1)
    body = SERVICE_HEAD + SERVICE_BODIES[kind] + SERVICE_TAIL.format(budget=SERVICE_BUDGETS[kind], base="{base}")
    return head.rstrip("\n") + "\n" + body


class TemplateBlueprintExamples(BlueprintExamples):
    def example(self, kind: str = "research", base: Path | str = ".", service: bool = False) -> str:
        """The template text for ``kind`` with absolute paths under ``base``; ``service=True``: as a standing service."""
        key = (kind or "research").strip().lower()
        if key == EXTENSION_KIND:  # beside the four full kinds, which EXAMPLE_KINDS keeps (PC-17): a change to the organization, not a team
            return EXTENSION
        if key not in TEMPLATES:
            raise OrgError(f"unknown kind '{kind}': use one of {', '.join(EXAMPLE_KINDS)} "
                           "(research = web sources, documents = write from the user's local files, code = repo workspace with tests, analysis = data files analysed with a checked script); "
                           "kind extension is the template of a change to the existing organization")
        base_text = str(base).rstrip("/") or "/"
        if service:
            return _service_template(key).format(service_schema=SERVICE_SCHEMA, base=base_text)
        return TEMPLATES[key].format(schema=SCHEMA, base=base_text)
