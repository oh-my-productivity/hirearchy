"""The organization tree with one state line per agent (overview).

The bodies call the ports of ``self.runtime`` (step C-overview; ARCHITECTURE.md 5.3 and 6.4). ``_agent_line`` and ``_indent`` are the prompts' (they stay
in ``PromptsMixin`` until C-prompts): the tree does not use them."""

from __future__ import annotations

from .runtime import OrgRuntime


class OverviewMixin:
    """The organization tree with one state line per agent (overview)."""

    runtime: OrgRuntime

    def tree(self) -> str:
        return self.runtime.org_tree.tree()
