"""(a) The message files parse, ids are unique, sender and recipient copies match."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from ...agents import AgentDirectory
from ...kernel import RUNTIME, JsonObject, OrgLayout, norm
from ...mail import MessageFile
from .._ports import IntegrityCheck
from ._base import COPY_GRACE, verdict


class MessagesIntact(IntegrityCheck):
    """Every file parses and is named after its id; a sender's copy is in the ``sent/`` of the sender and a received one in a box of its recipient; an id
    is in ``sent/`` once and among the received copies once; and each sent copy has a received one (and the other way round) once the delivery that writes
    both had its ``COPY_GRACE``."""

    def __init__(self, layout: OrgLayout, agents: AgentDirectory) -> None:
        self._layout, self._agents = layout, agents

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        problems: list[str] = []
        rel = self._layout.rel
        sent: dict[str, list[MessageFile]] = defaultdict(list)
        recv: dict[str, list[MessageFile]] = defaultdict(list)
        for f in files:
            if f.error:
                problems.append(f"{rel(f.path)}: {f.error}")
                continue
            if f.path.stem != f.id:
                problems.append(f"{rel(f.path)}: file name differs from its id {f.id}")
            (sent if f.box == "sent" else recv)[f.id].append(f)
            meta = f.meta or {}
            if f.box == "sent" and norm(str(meta.get("from"))) != f.owner:
                problems.append(f"{rel(f.path)}: in the sent/ of {f.owner} but from {meta.get('from')}")
            if f.box != "sent" and norm(str(meta.get("to"))) != f.owner:
                problems.append(f"{rel(f.path)}: in the {f.box}/ of {f.owner} but addressed to {meta.get('to')}")
        for mid, fs in sent.items():
            if len(fs) > 1:
                problems.append(f"id {mid} appears {len(fs)} times in sent/ ({', '.join(f.owner for f in fs)})")
        for mid, fs in recv.items():
            if len(fs) > 1:
                problems.append(f"id {mid} appears {len(fs)} times among received copies ({', '.join(f'{f.owner}/{f.box}' for f in fs)})")
        for mid, fs in sent.items():
            f = fs[0]
            to = norm(str((f.meta or {}).get("to")))
            if mid not in recv and self._agents.exists(to) and now - f.mtime > COPY_GRACE:
                problems.append(f"{mid}: sent by {f.owner} to {to} but {to} has no copy (recover() or a run start re-delivers it)")
        for mid, fs in recv.items():
            f = fs[0]
            sender = norm(str((f.meta or {}).get("from")))
            if mid not in sent and sender != RUNTIME and self._agents.exists(sender) and now - f.mtime > COPY_GRACE:
                problems.append(f"{mid}: in {f.owner}/{f.box} from {sender} but {sender} has no sent copy")
        n = len(sent) + len({k for k in recv if k not in sent})
        return verdict("a", "messages intact: files parse, ids unique, sender and recipient copies match", problems, f"{n} message(s) checked")

