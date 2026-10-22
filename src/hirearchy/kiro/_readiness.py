"""``KiroReadiness``: can kiro-cli run this organization's agents (docs/design/kiro-runtime-v3.md 9, amendment A1)."""

from __future__ import annotations

from collections.abc import Callable

from ..access import AccessScopes
from ..agents import AgentDirectory
from ..kernel import Environment, OrgLayout
from ._env import run_environment
from ._placement import placement_problem, readable_places
from ._state import planted_problem
from .api import READINESS_TIMEOUT, CliResult, KiroCli, KiroHomeAudit, KiroPlaces, KiroStateDirs, RuntimeReadiness

REQUIRED_FLAGS = ("--v3", "--require-mcp-startup", "--output-format")  # of ``chat --help``
MAX_MESSAGE = 1000  # the design says 500; the whoami text alone holds the home twice, and a cut would hide what to do
MAX_QUOTED = 200  # of what a command printed


class KiroReadiness(RuntimeReadiness):
    def __init__(
        self, layout: OrgLayout, agents: AgentDirectory, scopes: AccessScopes, places: KiroPlaces, dirs: KiroStateDirs,
        audit: KiroHomeAudit, cli: KiroCli, environment: Environment,
    ) -> None:
        self._layout = layout
        self._agents = agents
        self._scopes = scopes
        self._places = places
        self._dirs = dirs
        self._audit = audit
        self._cli = cli
        self._environment = environment

    # ------------------------------------------------------------------------------------------------------ the methods

    def state_problem(self) -> str | None:
        return self._line(self._state)

    def check(self, kiro_bin: str) -> str | None:
        return self._line(lambda: self._state() or self._kiro(kiro_bin))

    # ---------------------------------------------------------------------------------------------------------- steps

    def _line(self, check: Callable[[], str | None]) -> str | None:
        """The problem of ``check`` as one line, never an exception (an unreadable or unwritable state is a problem)."""
        try:
            problem = check()
        except OSError as error:
            problem = f"cannot prepare the kiro home {self._places.home()}: {str(error)[:MAX_QUOTED]}"
        except Exception as error:  # fail closed: whatever cannot be checked is not ready
            problem = f"kiro-cli cannot be checked: {type(error).__name__}: {error}"
        return None if problem is None else self._one_line(problem)

    def _one_line(self, text: str) -> str:
        key = self._environment.get("KIRO_API_KEY")
        if key:
            text = text.replace(key, "***")
        return " ".join(text.split())[:MAX_MESSAGE]

    def _state(self) -> str | None:
        problem = self._places.problem()  # step 1
        if problem is not None:
            return problem
        root = self._layout.root
        for addr in [*self._agents.agents(), "root"]:  # step 2, before anything is created (root last: its readable folders are the agents')
            problem = placement_problem(self._places.roots(), readable_places(root, self._scopes, addr))
            if problem is not None:
                return problem
        home = self._places.home()  # step 3
        self._dirs.private_dir(home)
        return planted_problem(home, self._audit.planted(home))

    def _kiro(self, kiro_bin: str) -> str | None:
        env = run_environment(self._environment.variables(), self._places.home())
        version = self._call([kiro_bin, "--version"], env)  # step 4
        if isinstance(version, str):
            return version
        shown = (version.output.strip().splitlines() or [kiro_bin])[0].strip() or kiro_bin
        help_ = self._call([kiro_bin, "chat", "--help"], env)  # step 5
        if isinstance(help_, str):
            return help_
        missing = [flag for flag in REQUIRED_FLAGS if flag not in help_.output]
        if missing:
            return (
                f'{shown} does not offer {", ".join(missing)} in "chat --help": hirearchy runs agents on kiro-cli\'s V3 engine '
                "(verified with kiro-cli 2.33.0); upgrade kiro-cli"
            )
        if self._environment.get("KIRO_API_KEY"):  # step 6
            return None
        who = [kiro_bin, "whoami"]
        answer = self._run(who, env)
        if answer is None:
            return self._not_usable(who, None)
        if answer.code == 0:
            return None
        home = self._places.home()
        return (
            f"kiro-cli is not signed in for this organization's kiro home ({home}): set KIRO_API_KEY in the scheduler's environment "
            f'(verified), or make "KIRO_HOME={home} kiro-cli whoami" succeed (a sign-in inside a separate KIRO_HOME is not verified); '
            "hirearchy never falls back to ~/.kiro"
        )

    def _run(self, argv: list[str], env: dict[str, str]) -> CliResult | None:
        return self._cli.run(argv, env, READINESS_TIMEOUT)

    def _call(self, argv: list[str], env: dict[str, str]) -> CliResult | str:
        """The answer of a call that must succeed, else the problem text."""
        answer = self._run(argv, env)
        if answer is None or answer.code != 0:
            return self._not_usable(argv, answer)
        return answer

    @staticmethod
    def _not_usable(argv: list[str], answer: CliResult | None) -> str:
        shown = " ".join(argv)
        if answer is None:
            what = (
                f"did not answer within {READINESS_TIMEOUT:g} s or could not be started "
                "(a first start after an update can be slow: try again)"
            )
        else:
            first = next((line.strip() for line in answer.output.splitlines() if line.strip()), "")
            what = f"exited {answer.code}: {first[:MAX_QUOTED]}"
        return f'kiro-cli is not usable: "{shown}" {what}'
