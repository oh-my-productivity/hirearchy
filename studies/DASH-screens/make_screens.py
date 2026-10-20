"""Regenerate the dashboard screenshots of a populated demo organization (headless; nothing touches a real org).

    cd <repo> && uv run python studies/DASH-screens/make_screens.py

Writes one SVG per screen into this directory (and a PNG next to it when ``rsvg-convert`` is on PATH), plus
``once.txt`` (the output of ``orgmcp dash --once``). The demo org is built under ``$TMPDIR`` by ``tests/testkit/dash_fixtures.py``
with a frozen clock, so the pictures are the same every time.
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tests"))

from testkit.dash_fixtures import DEMO_NOW, demo_org  # noqa: E402
from testkit.dashboard_world import dash_app  # noqa: E402
from testkit.dashdata_world import dd  # noqa: E402
from testkit.scheduler import scheduler_is  # noqa: E402

from orgmcp.app import wiring  # noqa: E402
from orgmcp.dashboard._app import DashApp  # noqa: E402
from orgmcp.daemon import SchedulerState  # noqa: E402

SIZE = (150, 42)


def save(app: DashApp, name: str) -> None:
    app.save_screenshot(f"{name}.svg", path=str(HERE))
    svg = HERE / f"{name}.svg"
    # rsvg collapses leading spaces of a text run unless told to keep them
    svg.write_text(svg.read_text(encoding="utf-8").replace("<svg ", '<svg xml:space="preserve" ', 1), encoding="utf-8")
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", str(svg), "-o", str(HERE / f"{name}.png")], check=True)
    print("wrote", svg.name)


async def main() -> None:
    with contextlib.ExitStack() as stack:  # the process overrides stay in force while the screens are taken; the demo has no real scheduler
        scheduler_is(lambda overrides: stack.enter_context(wiring.overriding(overrides)), SchedulerState("running", 7000, "2026-10-18 10:00:00Z"))
        await screens()


async def screens() -> None:
    ns = demo_org(Path(tempfile.mkdtemp(prefix="dash-demo-")))
    once = dd.render_once(dd.DashData(ns.org.root, now=lambda: DEMO_NOW)).replace(str(ns.org.root), "/path/to/acme")
    (HERE / "once.txt").write_text(once + "\n", encoding="utf-8")
    app = dash_app(ns.org.root, interval=3600, now=lambda: DEMO_NOW)
    async with app.run_test(size=SIZE) as pilot:
        async def step(*keys: str, name: str, wait: float = 0.0) -> None:
            await pilot.press(*keys)
            await app.settle(pilot)
            if wait:
                await asyncio.sleep(wait)
                await app.settle(pilot)
            save(app, name)

        await app.settle(pilot)
        save(app, "1-org-root")
        await step("down", "down", name="1-org-ceo-overview")
        await step("]", name="1-org-ceo-activity")
        await step("]", name="1-org-ceo-messages")
        await step("]", name="1-org-ceo-runlog")
        await step("]", name="1-org-ceo-memory")
        await step("]", name="1-org-ceo-charter")
        await step("2", name="2-workflows")
        await step("enter", name="2-workflows-trace", wait=0.5)
        await step("escape", "3", name="3-services")
        await step("enter", name="3-services-detail")
        await step("escape", "4", name="4-events")
        await step("e", name="4-events-errors")
        await step("e", "5", name="5-health")
        await step("question_mark", name="help")


if __name__ == "__main__":
    asyncio.run(main())
