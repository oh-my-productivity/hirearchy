"""The scripted stream of design 18.4 (no test lives here): six memos, Lena's rejections of memos 1, 2, 4 and 5, the answers that add C9-C12 and the two
items A (``P2``, ``WHY R1; C9``) and B (``P3``, ``WHY R2; C10``). Every record is placed at a tick the test chooses, so 18.4.1's moments can take
root's calls in every order. The rejections are numbered in the order of their notes: R1 memo 1, R2 memo 2, R3 memo 4, R4 memo 5."""

from __future__ import annotations

from collections.abc import Sequence

from hirearchy.kernel import Message
from hirearchy.services import ItemWatch, PlaybookItem

from ._watch_kit import Watching, contract, playbook, rule, step

V1 = ["s1", "s2", "sections", "s4", "s5", "owners", "s7", "s8"]  # C1-C8: C3 is the sections rule, C6 the owner rule
SUMMARY, INITIALS, FULL_NAMES, NOTE = "summary line first", "owners as initials only", "full names again", "initials with a note"  # C9, C10, C11, C12


class Stream:
    """One stream under the watch: ``w`` holds its mail, contract versions and playbook versions."""

    def __init__(self) -> None:
        self.w = Watching()
        self.acceptance = list(V1)
        self.items: list[PlaybookItem] = [step("P1", "Read the request.")]
        self.w.contracts.append(contract(1, V1, 0))
        self.w.versions.append(playbook(1, 0, self.items, op="first", admitted="first"))
        self.version = 1

    def answer(
        self, name: str, tick: int, remove: Sequence[str], add: Sequence[str], about: str, ids: Sequence[str], *, contract_version: bool = True,
    ) -> None:
        """The user's answer to the rejection of case ``name``: the contract version that answers it (unless ``contract_version`` is false: a link
        alone, ``feedback(confirms=...)``) and the link note ``define_service`` writes after it, naming ``ids``."""
        note = self.w.notes[name]
        if contract_version:
            self.acceptance = [t for t in self.acceptance if t not in remove] + [t for t in add if t not in self.acceptance]
            self.w.contracts.append(contract(len(self.w.contracts) + 1, self.acceptance, tick, answers=note.id, about=about))
        self.w.bag.link(note, tick, *ids, us=1)

    def item(self, tick: int, new: PlaybookItem, op: str = "add", admitted: str = "c", *, us: int = 0) -> None:
        """The owner's change of the playbook at ``tick``: ``new`` is added, or (``op`` edit or restore) replaces the item of its id."""
        known = any(i.id == new.id for i in self.items)
        self.items = [new if i.id == new.id else i for i in self.items] if known else [*self.items, new]
        self.version += 1
        self.w.versions.append(playbook(self.version, tick, self.items, op=op, item=new.id, admitted=admitted, us=us))

    def retire(self, tick: int, item_id: str) -> None:
        self.items = [i for i in self.items if i.id != item_id]
        self.version += 1
        self.w.versions.append(playbook(self.version, tick, self.items, op="retire", item=item_id, admitted="exempt"))

    def memo1(self) -> None:
        """Memo 1: rejected, answered (C9 added), the injection and a human rework accepted; A is live from the rework run."""
        self.w.case("m1", 100, 101, verdict=(102, "reject"))
        self.answer("m1", 103, [], [SUMMARY], "C3", ["C9"])
        first = self.w.tasks["m1"]
        self.w.case("m1i", 104, 105, revises=first, asked_by="relayed")  # the injection: a relayed rework with a wrong lesson
        self.w.case("m1h", 106, 107, verdict=(108, "accept"), revises=first, asked_by="human")
        self.item(110, rule("P2", "always", "start with the summary line", why=("R1", "C9")))

    def memo2(self, live: tuple[int, int] = (130, 0)) -> None:
        """Memo 2: rejected, answered (C10 added), a human rework accepted; B is live from ``live`` (ticks, microseconds)."""
        self.w.case("m2", 120, 121, verdict=(122, "reject"))
        self.answer("m2", 123, [], [INITIALS], "C6", ["C10"])
        self.w.case("m2h", 124, 125, verdict=(126, "accept"), revises=self.w.tasks["m2"], asked_by="human")
        self.item(live[0], rule("P3", "always", "write owners as initials only", why=("R2", "C10")), us=live[1])

    def memo4(self, ask: int = 150, done: int = 151, reject: int = 152) -> Message:
        """Memo 4 (delivered after memo 3): rejected. The answer (C10 removed, C11 added) is the caller's."""
        return self.w.case("m4", ask, done, verdict=(reject, "reject"))

    def memo5(self, ask: int = 170, done: int = 171, reject: int = 172) -> Message:
        return self.w.case("m5", ask, done, verdict=(reject, "reject"))

    def states(self) -> tuple[ItemWatch, ItemWatch]:
        found = self.w.states()
        return found["P2"], found["P3"]
