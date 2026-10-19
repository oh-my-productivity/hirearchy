"""What an amendment of a contract changes, and how it is told to the owner."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import JsonObject, OrgError
from ._lines import criteria_lines
from ._protocols import ContractAmendment
from .api import Contract


def _described(deliverable: JsonObject) -> str:
    extra = [f"{k}: {deliverable[k]}" for k in ("format", "max_words", "path") if deliverable.get(k)]
    return f'"{deliverable.get("description", "")}"' + (f" ({'; '.join(extra)})" if extra else "")


def _inputs_listing(items: Sequence[JsonObject]) -> list[str]:
    return [f"{i['name']}{'*' if i['required'] else ''}: {i['description']}" for i in items]


class ContractAmender(ContractAmendment):
    """Criteria are added and removed by their exact text; the owner is told line by line what changed."""

    def numbered(self, items: Sequence[str], indent: str = "") -> str:
        return "\n".join(f"{indent}{i}. {x}" for i, x in enumerate(items, 1))

    def amended_criteria(self, name: str, current: Sequence[str], add: object, remove: object) -> list[str]:
        if add is None and remove is None:
            return list(current)
        add_n, remove_n = criteria_lines(add, "add_acceptance", required=False), criteria_lines(remove, "remove_acceptance", required=False)
        listing = f"Current criteria of `{name}`:\n{self.numbered(current)}"
        unknown = [x for x in remove_n if x not in current]
        if unknown:
            raise OrgError(
                "remove_acceptance must be the exact text of existing criteria; not found: "
                + "; ".join(f'"{x}"' for x in unknown) + f".\n{listing}"
            )
        dup = [x for x in add_n if x in current]
        if dup:
            raise OrgError(
                "add_acceptance: already a criterion: " + "; ".join(f'"{x}"' for x in dup)
                + f". Add only new criteria (to reword one, remove it and add the new text in two calls).\n{listing}"
            )
        twice = sorted({x for x in add_n if add_n.count(x) > 1})
        if twice:
            raise OrgError("add_acceptance lists the same criterion twice: " + "; ".join(f'"{x}"' for x in twice))
        result = [x for x in current if x not in remove_n] + add_n
        if not result:
            raise OrgError(f"that would leave `{name}` without acceptance criteria: a service needs at least one.\n{listing}")
        return result

    def changes(self, old: Contract, new: Contract) -> list[str]:
        out: list[str] = []

        def listing(label: str, before: list[str], after: list[str]) -> None:
            out.extend(f"- {label} removed: {x}" for x in before if x not in after)
            out.extend(f"+ {label} added: {x}" for x in after if x not in before)

        listing("acceptance", old.acceptance, new.acceptance)
        listing("input", _inputs_listing(old.inputs), _inputs_listing(new.inputs))
        if old.budget != new.budget:
            out.append(f"budget per request: {old.budget} -> {new.budget} runs")
        if old.locked != new.locked:
            out.append(f"locked: {str(old.locked).lower()} -> {str(new.locked).lower()}"
                       + (" (you may no longer revise the playbook)" if new.locked else ""))
        if old.description != new.description:
            out.append(f'description: "{old.description}" -> "{new.description}"')
        if old.deliverable != new.deliverable:
            out.append(f"deliverable: {_described(old.deliverable)} -> {_described(new.deliverable)}")
        if old.notes != new.notes:
            out.append(f'notes: "{old.notes}" -> "{new.notes}"')
        if not out and old.acceptance != new.acceptance:
            out.append("acceptance: order changed")
        return out

    def diff(self, old: Contract, new: Contract, changes: Sequence[str], where: str) -> str:
        head = (f"{old.defined_by or 'your parent'} changed the contract of service `{old.name}` (v{old.version} -> v{new.version}). "
                "Read it, and follow the new criteria from the next request on:")
        return "\n".join([head, *changes, f"Contract: {where}"])
