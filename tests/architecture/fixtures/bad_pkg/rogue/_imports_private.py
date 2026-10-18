"""Violation: imports a private module of another package (and a package that rogue may not depend on)."""

from bad_pkg.mail import _mailbox  # noqa: F401
from bad_pkg.settings import api  # noqa: F401
