"""What each agent was granted: model, workspace, inputs, tools (access).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from pathlib import Path

from ..kernel import inside as _inside, OrgError, ROOT
from ._facade_settings import config_default_model


class AccessMixin:
    """What each agent was granted: model, workspace, inputs, tools (access)."""

    @property
    def default_model(self) -> str:
        """The org-wide model: the config's ``default_model``, else DEFAULT_MODEL (also for ``null`` or a missing key)."""
        return config_default_model(self.config)

    def model_for(self, addr: str) -> str:
        """The model a run of ``addr`` uses: its charter's ``model``, else the org config's ``default_model``, else DEFAULT_MODEL."""
        meta, _ = self.charter(addr)
        return str(meta.get("model") or "").strip() or self.default_model

    def _check_authority(self, actor: str, tools: list[str], workspace: str | None, inputs: list[str] | None = None) -> None:
        """Authority only narrows down the tree: a parent cannot grant what it does not have."""
        meta, _ = self.charter(actor)
        extra = set(tools) - set(meta.get("tools") or [])
        if extra:
            raise OrgError(f"you cannot grant tools you do not have yourself: {', '.join(sorted(extra))}")
        if workspace:
            mine = meta.get("workspace")
            if not mine:
                raise OrgError("you have no workspace, so you cannot assign one")
            ws, base = Path(workspace).expanduser().resolve(), Path(mine).expanduser().resolve()
            if ws != base and base not in ws.parents:
                raise OrgError(f"a report's workspace must be inside yours ({mine})")
        if inputs:
            bases = [b for b in (self.workspace_of(actor), *self.inputs_of(actor)) if b is not None]
            if not bases:
                raise OrgError("you have no workspace or inputs, so you cannot assign inputs")
            for raw in inputs:
                if not any(_inside(Path(raw).expanduser().resolve(), b) for b in bases):
                    raise OrgError(
                        f"a report's inputs must be inside your inputs or workspace ({', '.join(map(str, bases))}): {raw}"
                    )

    def workspace_of(self, addr: str) -> Path | None:
        """The agent's workspace (read-write for its built-in tools) as a resolved path, if its charter has one."""
        a = self.norm(addr)
        if a == ROOT or not self.exists(a):
            return None
        raw = self.charter(a)[0].get("workspace")
        return Path(str(raw)).expanduser().resolve() if raw else None

    def inputs_of(self, addr: str) -> list[Path]:
        """The agent's read-only inputs (charter ``inputs``) as resolved paths."""
        a = self.norm(addr)
        if a == ROOT or not self.exists(a):
            return []
        raw = self.charter(a)[0].get("inputs")
        items = [raw] if isinstance(raw, str) else (raw if isinstance(raw, list) else [])
        return [Path(str(x)).expanduser().resolve() for x in items if str(x).strip()]

    @staticmethod
    def unconfined_read(meta: dict) -> bool:
        """Legacy charter: no workspace and no ``inputs`` key. Its built-in ``read`` is not confined (as before)."""
        return not meta.get("workspace") and "inputs" not in meta

    def _check_inputs(self, inputs) -> list[str]:
        """Inputs are absolute paths outside the organization directory (kiro reads them; the org owns its own)."""
        items = [inputs] if isinstance(inputs, str) else list(inputs or [])
        out = []
        for raw in items:
            text = str(raw).strip()
            if not text:
                continue
            p = Path(text).expanduser()
            if not p.is_absolute():
                raise OrgError(f"an input must be an absolute path (got `{text}`)")
            p = p.resolve()
            if _inside(p, self.root) or _inside(self.root, p):
                raise OrgError(f"an input must not overlap the organization directory ({self.root}): {text}")
            out.append(text)
        return out

    def readable_roots(self, addr: str) -> list[Path]:
        """Directories outside the org that ``read`` shows to ``addr`` by absolute path: its workspace and inputs, and
        the workspace of every agent in its subtree (so a manager can verify what its team made)."""
        a = self.norm(addr)
        roots = [*self.inputs_of(a)]
        roots += [w for s in self.subtree(a) if (w := self.workspace_of(s)) is not None]
        return roots

    def tool_names(self, addr: str) -> dict[str, str]:
        """The names under which ``addr`` has orgmcp's ``read`` and ``write`` tools.

        kiro exposes MCP tools by their plain names, so a built-in ``read``/``write`` of the same name SHADOWS the orgmcp
        tool (the agent sees only kiro's; studies/F-read-experiment, F2-tool-names). An agent whose charter holds the
        built-in gets orgmcp's tool as ``org_read`` / ``org_write`` instead; everyone else (and root) keeps the plain names.
        """
        tools = set((self.charter(addr)[0].get("tools") or []) if addr != ROOT else [])
        return {t: (f"org_{t}" if t in tools else t) for t in ("read", "write")}
