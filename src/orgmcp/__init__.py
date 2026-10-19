"""orgmcp: a file-based organization of agents, run over MCP."""

# Importing the package has always loaded the application (the command line imported ``orgmcp.core``, which builds the ``Org`` facade): it installs what the
# legacy modules read from the process - ``Message.load`` on the kernel's ``Message``, the defaults of ``orgmcp.telemetry``, the parts of ``orgmcp.blueprint`` -
# and a fresh interpreter that imports only ``orgmcp.kernel`` or ``orgmcp.telemetry`` relies on it (pinned by ``app/tests/test_message_parser.py`` and
# ``test_wire_telemetry.py``). The command line no longer imports it (``orgmcp.cli.main`` asks the composition root when it runs), so it is loaded here.
from . import core as _core  # noqa: F401
from .cli import main

__all__ = ["main"]
