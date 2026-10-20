"""What a rewrite of a charter does to its frontmatter: the keys the new text leaves out are kept, and the writer is told."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..kernel import JsonObject, flow_text


def _short(value: object, limit: int = 80) -> str:
    text = flow_text(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def charter_change_note(addr: str, old: JsonObject, written: JsonObject, merged: JsonObject) -> str:
    """What a charter rewrite did to the frontmatter: keys kept from the old one, keys changed (old -> new), added."""
    kept = [k for k in old if k not in written]
    changed = [f"{k}: {_short(old[k])} -> {_short(written[k])}" for k in old if k in written and old[k] != written[k]]
    added = [f"{k}: {_short(written[k])}" for k in written if k not in old]
    parts = [f"charter frontmatter of `{addr}`:"]
    parts.append(f"kept from the old frontmatter (not in your text): {', '.join(kept)}." if kept else "nothing kept from the old frontmatter (your text set every key).")
    if changed:
        parts.append("changed (old -> new): " + "; ".join(changed) + ".")
    if added:
        parts.append("added: " + "; ".join(added) + ".")
    if not changed and not added:
        parts.append("no key changed.")
    parts.append("A key you leave out is kept; to remove one, set it explicitly (e.g. `tools: []`).")
    return " ".join(parts)


@runtime_checkable
class CharterMerge(Protocol):
    def merge(self, addr: str, old: JsonObject, written: JsonObject) -> tuple[JsonObject, str]:
        """``(frontmatter to write, note for the writer)``: every key of ``old`` that ``written`` does not set is kept; a key
        ``written`` sets, even to an empty value, wins. The merged keys are the written ones first, then the kept ones in their old order."""
        ...


class CharterMerger(CharterMerge):
    def merge(self, addr: str, old: JsonObject, written: JsonObject) -> tuple[JsonObject, str]:
        merged = {**written, **{k: v for k, v in old.items() if k not in written}}
        return merged, charter_change_note(addr, old, written, merged)
