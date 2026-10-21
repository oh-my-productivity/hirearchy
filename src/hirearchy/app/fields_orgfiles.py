"""Runtime fields of ``orgfiles`` (ARCHITECTURE.md 3.17): one field per port that ``wire_orgfiles.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..orgfiles import OrgFileReader, OrgFileStore, OrgFileWriter

STEP: str | None = "B-orgfiles"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    org_file_store: OrgFileStore
    org_file_reader: OrgFileReader
    org_file_writer: OrgFileWriter
