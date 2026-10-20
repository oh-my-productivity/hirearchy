"""orgmcp.app: the composition root and the ``Org`` facade (ARCHITECTURE.md section 6)."""

from .facade import Org
from .runtime import OrgRuntime
from .wiring import open_runtime, process_resources

__all__ = ["Org", "OrgRuntime", "open_runtime", "process_resources"]
