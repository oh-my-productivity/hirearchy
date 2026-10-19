"""The free input of a contract (inputs, deliverable) in its fixed form."""

from __future__ import annotations

from pathlib import Path

from ..kernel import JsonObject, OrgError
from .api import DELIVERABLE_KEYS, INPUT_RE, ContractNormalizer


class TextContractNormalizer(ContractNormalizer):
    """Inputs are ``{name, description, required}`` (or ``'name*:description'``); a deliverable is ``{description, format?, max_words?, path?}``."""

    def parse_input_spec(self, spec: str) -> JsonObject:
        name, _, desc = spec.partition(":")
        name = name.strip()
        required = name.endswith("*")
        return {"name": name.rstrip("*").strip(), "description": desc.strip(), "required": required}

    def inputs(self, value: object) -> list[JsonObject]:
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            raise OrgError("inputs must be a list of {name, description, required} (or may be empty)")
        out: list[JsonObject] = []
        seen: set[str] = set()
        for raw in value:
            item = self.parse_input_spec(raw) if isinstance(raw, str) else raw
            if not isinstance(item, dict):
                raise OrgError(f"each input must be {{name, description, required}} (got {raw!r})")
            extra = set(item) - {"name", "description", "required"}
            if extra:
                raise OrgError(f"unknown key(s) in input {item.get('name')!r}: {', '.join(sorted(extra))}. Use name, description, required")
            name = str(item.get("name") or "")
            if not INPUT_RE.fullmatch(name):
                raise OrgError(f"input name must be lowercase letters, digits and underscores, starting with a letter (max 32): {name!r}")
            if name in seen:
                raise OrgError(f"input name used twice: {name}")
            seen.add(name)
            required = item.get("required", True)
            if not isinstance(required, bool):
                raise OrgError(f"input {name}: required must be true or false")
            out.append({"name": name, "description": str(item.get("description") or "").strip(), "required": required})
        return out

    def deliverable(self, value: object) -> JsonObject:
        if not isinstance(value, dict):
            raise OrgError("deliverable must be {description, format?, max_words?, path?}")
        extra = set(value) - set(DELIVERABLE_KEYS)
        if extra:
            raise OrgError(f"unknown key(s) in deliverable: {', '.join(sorted(extra))}. Use {', '.join(DELIVERABLE_KEYS)}")
        desc = str(value.get("description") or "").strip()
        if not desc:
            raise OrgError("deliverable needs a description: what the owner hands back (e.g. one markdown file)")
        out: JsonObject = {"description": desc}
        if value.get("format"):
            out["format"] = str(value["format"]).strip()
        if value.get("max_words") not in (None, ""):
            mw = value["max_words"]
            if isinstance(mw, bool) or not isinstance(mw, int) or mw < 1:
                raise OrgError("deliverable.max_words must be a whole number of at least 1")
            out["max_words"] = mw
        if value.get("path"):
            path = str(value["path"]).strip()
            if not Path(path).expanduser().is_absolute():
                raise OrgError(f"deliverable.path must be an absolute path (got {path!r})")
            out["path"] = path
        return out
