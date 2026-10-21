"""What the class-interface check (rule R6, ``class_interfaces.py``) does not look at, and why.

Three different things, kept apart on purpose:

* ``tests/golden/interface_allowlist.txt`` is the DEBT list: classes with behaviour that still have no Protocol base.
  It only shrinks (a refactor step removes entries; nobody adds one) and the end state is an empty file.
* ``EXEMPT_ALLOWLIST`` below is the PERMANENT exemption list: a class that legitimately has behaviour and no Protocol. It is
  empty at the start; an entry needs a one-line reason and a review. ``module.Qualname -> reason``.
* The structural exemptions (Protocols, exceptions, Textual subclasses, pure data) are rules, not lists: see
  ``class_interfaces.exemption``.
"""

from __future__ import annotations

EXEMPT_ALLOWLIST: dict[str, str] = {}

# Modules the walk skips. ``hirearchy.app`` is the composition root and the Org facade (ARCHITECTURE.md R6: "Exempt: ... and the app
# package"): it constructs concrete classes by definition. Colocated tests (``tests`` packages) and ``__main__`` are always skipped.
EXEMPT_PACKAGES: tuple[str, ...] = ("hirearchy.app",)
