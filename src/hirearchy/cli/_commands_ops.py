"""The commands that maintain or run the organization: ``upgrade-rules install-skill review run mcp kiro-profile``."""

from __future__ import annotations

import argparse
import json

from ..kernel import OrgError, Provider
from ..kiro import McpServerLocator, ProfileProvisioner
from ..review import HealthReviewer
from ..skill import SkillInstaller
from ..snapshots import OrgSnapshotter
from ..upgrade import RulesUpgrader
from ._ports import Arguments, Command, McpRunner, OrgSession, Output, SchedulerRunner


class UpgradeRulesCommand(Command):
    def __init__(self, session: OrgSession, upgrader: Provider[RulesUpgrader], out: Output) -> None:
        self._session = session
        self._upgrader = upgrader
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("upgrade-rules", help="rewrite the rules in ORG.md to the current template (keeps settings and mission)")
        s.add_argument("--dry-run", action="store_true", help="print what would change; write nothing")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=not args.dry_run)
        self._out.say(self._upgrader().upgrade_rules(dry_run=args.dry_run).text())


class InstallSkillCommand(Command):
    """Needs no organization: it copies a file into a skills directory."""

    def __init__(self, installer: SkillInstaller, out: Output) -> None:
        self._installer = installer
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("install-skill", help="copy the hirearchy assistant skill into a kiro skills directory (default ~/.kiro/skills)")
        s.add_argument("--dest", metavar="DIR", help="skills directory to install into; the file goes to DIR/hirearchy/SKILL.md (default: ~/.kiro/skills)")
        s.add_argument("--force", action="store_true", help="overwrite a different existing SKILL.md")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._out.say(self._installer.install_skill(args.dest, force=args.force))


class ReviewCommand(Command):
    def __init__(self, session: OrgSession, reviewer: Provider[HealthReviewer], snapshots: Provider[OrgSnapshotter], out: Output) -> None:
        self._session = session
        self._reviewer = reviewer
        self._snapshots = snapshots
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("review", help="run a health review now: tell managers (and you) about flagged agents")
        s.add_argument("--dry-run", action="store_true", help="print what would be sent; write nothing")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=not args.dry_run)
        result = self._reviewer().review(dry_run=args.dry_run)
        if result.notes and not args.dry_run:
            self._snapshots().commit("root: health review")
        self._out.say(result.render(args.dry_run))


class RunCommand(Command):
    def __init__(self, session: OrgSession, scheduler: SchedulerRunner) -> None:
        self._session = session
        self._scheduler = scheduler

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("run", help="run the scheduler")
        s.add_argument("--once", action="store_true", help="one pass, wait for those runs, exit")
        s.add_argument("--until-idle", action="store_true", help="exit when nothing is left to do")
        s.add_argument("--until-done", action="store_true",
                       help="exit when root has no open task and nothing is running or runnable (logs why, shown by status/progress)")
        s.add_argument("--max-runs", type=int, help="stop starting runs after this many (safety cap)")
        s.add_argument("--kiro", default="kiro-cli", help="kiro-cli binary")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        root = self._session.open(args, mutating=True)
        if args.until_done and args.once:
            raise OrgError("--until-done and --once are different modes: use one of them")
        self._scheduler.run(root, args.kiro, args.once, args.until_idle, args.until_done, args.max_runs)


class McpCommand(Command):
    def __init__(self, server: McpRunner) -> None:
        self._server = server

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("mcp", help="run the MCP server on stdio (identity from $ORG_AGENT, default root)")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._server.run()


class KiroProfileCommand(Command):
    def __init__(self, session: OrgSession, profiles: Provider[ProfileProvisioner], locator: Provider[McpServerLocator], out: Output) -> None:
        self._session = session
        self._profiles = profiles
        self._locator = locator
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        s = sub.add_parser("kiro-profile", help="write this organization's internal kiro profile (the scheduler does this itself)")
        s.add_argument("--tools")
        s.set_defaults(fn=self.run)

    def run(self, args: Arguments) -> None:
        self._session.open(args, mutating=True)  # the profile belongs to this organization
        name = self._profiles().ensure_profile([t for t in (args.tools or "").split(",") if t])
        self._out.say(f"wrote ~/.kiro/agents/{name}.json (mcp server: {json.dumps(self._locator().command())})")
