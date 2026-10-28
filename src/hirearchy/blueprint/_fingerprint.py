"""``OrgFingerprint``: the parts of the organization an extension depends on, so that its plan id goes stale when one of them changes (design 5.4)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from ..kernel import ROOT, norm
from ._extension_org import Reads, as_int
from ._protocols import Fingerprinting
from ._view import s
from .api import BlueprintError

UNREADABLE = "refused: the organization cannot be read ({error}), so no plan can be made against it. Try again; if it persists, tell the user."
AGENT_KEYS = ("can_hire", "max_children", "tools", "workspace", "inputs", "model", "kind")
NAMING = {
    "add_agents": "parent", "add_services": "owner", "budgets": "owner", "retire_services": "owner", "add_charter_lines": "agent",
    "remove_charter_lines": "agent", "limits": "agent", "retire": "agent",
}


def _entries(bp: Mapping[str, object], section: str) -> list[Mapping[str, object]]:
    extend = bp.get("extend")
    found = extend.get(section) if isinstance(extend, Mapping) else None
    return [e for e in found if isinstance(e, Mapping)] if isinstance(found, list) else []


class OrgFingerprint(Fingerprinting):
    def __init__(self, reads: Reads) -> None:
        self._reads = reads

    def fingerprint(self, bp: Mapping[str, object]) -> str:
        try:
            return json.dumps(self._parts(bp), sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)
        except Exception as error:  # noqa: BLE001 - a charter or a contract that does not parse (YAML) is as unreadable as a file that cannot be opened
            raise BlueprintError(UNREADABLE.format(error=error)) from error

    def _parts(self, bp: Mapping[str, object]) -> dict[str, object]:
        reads = self._reads
        named: dict[str, None] = {}
        for section, key in NAMING.items():
            for entry in _entries(bp, section):
                if s(entry.get(key)):
                    named[norm(s(entry.get(key)))] = None
        new = [norm(f"{s(e.get('parent'))}/{s(e.get('name'))}" if norm(s(e.get("parent"))) != ROOT else s(e.get("name"))) for e in _entries(bp, "add_agents")]
        retired = {norm(s(e.get("agent"))) for e in _entries(bp, "retire")}
        owners = {norm(s(e.get("parent"))).split("/")[0] for e in _entries(bp, "add_agents") if norm(s(e.get("parent"))) != ROOT}  # the teams an added agent joins
        agents: dict[str, object] = {}
        for addr in sorted(a for a in {*named, *owners} if a != ROOT):
            if not reads.agents.exists(addr):
                agents[addr] = None
                continue
            meta, body = reads.charters.charter(addr)
            agents[addr] = {
                **{k: meta.get(k) for k in AGENT_KEYS},
                "body": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                "reports": sorted(reads.agents.subtree(addr)[1:] if addr in retired else reads.agents.children(addr)),
            }
        services: dict[str, object] = {}
        pairs = {(norm(s(e.get("owner"))), s(e.get("service")) or s(e.get("name"))) for sec in ("add_services", "budgets", "retire_services") for e in _entries(bp, sec)}
        pairs |= {(o, n) for o in owners if reads.agents.exists(o) for n in reads.services.service_names(o)}
        for owner, name in sorted(pairs):
            contract = reads.services.read_contract(owner, name) if reads.agents.exists(owner) else None
            services[f"{owner}/{name}"] = None if contract is None else {
                "version": contract.version, "budget": contract.budget, "playbook": reads.services.read_playbook(owner, name).version,
            }
        return {
            "agents": agents, "free": {a: not reads.agents.exists(a) for a in sorted(new)}, "services": services,
            "max_depth": as_int(reads.org.config().get("max_depth"), 4),
        }
