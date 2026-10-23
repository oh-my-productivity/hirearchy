"""What an amendment of a contract changes, and how it is told to the owner."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence

from ..kernel import JsonObject, OrgError, clip_line
from ._lines import criteria_lines
from ._protocols import ContractAmendment
from .api import Contract, Criterion, confirmed_amendments


QUOTED_LINES = 3  # playbook lines quoted in the note about a removed criterion
QUOTED_CLIP = 160  # characters of one quoted line


def _described(deliverable: JsonObject) -> str:
    extra = [f"{k}: {deliverable[k]}" for k in ("format", "max_words", "path") if deliverable.get(k)]
    return f'"{deliverable.get("description", "")}"' + (f" ({'; '.join(extra)})" if extra else "")


def _inputs_listing(items: Sequence[JsonObject]) -> list[str]:
    return [f"{i['name']}{'*' if i['required'] else ''}: {i['description']}" for i in items]


class ContractAmender(ContractAmendment):
    """Criteria are added and removed by their exact text; the owner is told line by line what changed."""

    def listed(self, criteria: Sequence[Criterion], indent: str = "") -> str:
        return "\n".join(f"{indent}{c.id}: {c.text}" for c in criteria)

    def amended_criteria(self, name: str, current: Sequence[Criterion], add: object, remove: object) -> list[str]:
        texts = [c.text for c in current]
        if add is None and remove is None:
            return texts
        add_n, remove_n = criteria_lines(add, "add_acceptance", required=False), criteria_lines(remove, "remove_acceptance", required=False)
        listing = f"Current criteria of `{name}`:\n{self.listed(current)}"
        unknown = [x for x in remove_n if x not in texts]
        if unknown:
            raise OrgError(
                "remove_acceptance must be the exact text of existing criteria; not found: "
                + "; ".join(f'"{x}"' for x in unknown) + f".\n{listing}"
            )
        dup = [x for x in add_n if x in texts]
        if dup:
            raise OrgError(
                "add_acceptance: already a criterion: " + "; ".join(f'"{x}"' for x in dup)
                + f". Add only new criteria (to reword one, remove it and add the new text in two calls).\n{listing}"
            )
        twice = sorted({x for x in add_n if add_n.count(x) > 1})
        if twice:
            raise OrgError("add_acceptance lists the same criterion twice: " + "; ".join(f'"{x}"' for x in twice))
        result = [x for x in texts if x not in remove_n] + add_n
        if not result:
            raise OrgError(f"that would leave `{name}` without acceptance criteria: a service needs at least one.\n{listing}")
        return result

    def changes(self, old: Contract, new: Contract, ids: Mapping[str, str]) -> list[str]:
        out: list[str] = []

        def listing(label: str, before: list[str], after: list[str], tag: Mapping[str, str] | None = None) -> None:
            def shown(x: str) -> str:
                return f"{tag[x]}: {x}" if tag and x in tag else x

            out.extend(f"- {label} removed: {shown(x)}" for x in before if x not in after)
            out.extend(f"+ {label} added: {shown(x)}" for x in after if x not in before)

        listing("acceptance", old.acceptance, new.acceptance, ids)
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

    def diff(
        self, old: Contract, new: Contract, changes: Sequence[str], where: str, criteria: Sequence[Criterion], confirmed: Collection[str],
        quoting: Mapping[str, Sequence[str]] | None = None, playbook_version: int = 0,
    ) -> str:
        head = (f"{old.defined_by or 'your parent'} changed the contract of service `{old.name}` (v{old.version} -> v{new.version}). "
                "Read it, and follow the new criteria from the next request on:")
        shown = (f"{c.id}: {c.text}" + self._mark(c, confirmed) for c in criteria)
        removed = [self._removed(x, lines, playbook_version) for x, lines in (quoting or {}).items() if lines]
        rule_c = []
        if not new.locked and any(c.amended for c in criteria):  # on a locked contract revise_playbook refuses before the gate (DR-13)
            ids = ", ".join(c.id for c in confirmed_amendments(criteria, confirmed)) or "none yet"
            rule_c = [
                "Rule (c): a playbook revision that cites a criterion added by an amendment the client confirmed may add that criterion's "
                f'own words, one line each ("- C<k>: <its text>"); confirmed now: {ids}. A criterion marked (not confirmed) counts once the '
                "client's yes is recorded (it reaches you as a criterion link); one marked (user-initiated) never does."
            ]
        return "\n".join([head, *changes, "Acceptance criteria now:", *shown, *removed, *rule_c, f"Contract: {where}"])

    @staticmethod
    def _mark(criterion: Criterion, confirmed: Collection[str]) -> str:
        """An amendment the client has not confirmed is marked; one the user asked for on their own never counts."""
        if not criterion.amended:
            return ""
        if criterion.user:
            return " (user-initiated)"
        return "" if criterion.id in confirmed else " (not confirmed)"

    @staticmethod
    def _removed(criterion: str, lines: Sequence[str], version: int) -> str:
        """Advisory: the playbook still quotes a criterion the amendment removed (at most ``QUOTED_LINES`` of its lines are shown)."""
        shown = ", ".join(f'"{clip_line(x, QUOTED_CLIP)}"' for x in lines[:QUOTED_LINES])
        more = f" and {len(lines) - QUOTED_LINES} more" if len(lines) > QUOTED_LINES else ""
        return (
            f"Removed: {criterion}. Playbook v{version} still quotes it in {len(lines)} line(s): {shown}{more}. Where it differs from the "
            "contract, follow the contract; the playbook changes only by a revision the evidence admits (step 3)."
        )
