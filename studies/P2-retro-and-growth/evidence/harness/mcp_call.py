#!/usr/bin/env python3
"""P2 self-check only: one MCP tool call on a THROWAWAY org under /tmp/hirearchy-p2/, as root or as an agent, through the arm's own MCP server
(`uv --directory <REPO_A> run hirearchy mcp`, E7's injection script's form). Used by dryrun.sh for the product's reply texts that only the
MCP path gives (root's `feedback` question for a rejection, protocol 4.2 / F7 of the review; a parent's `write` of a report's charter, the
`by {parent}` label of design 4.5). Never used on a stream's org. Run inside the arm's product env:
    uv --directory <REPO_A> run python mcp_call.py --repo <REPO_A> --org <dir> [--agent <addr>] --tool <name> --args '<json>' [--out f]
    uv --directory <REPO_A> run python mcp_call.py --repo <REPO_A> --org <dir> --schema <tool>
KIRO_HOME is removed from the server's environment; ORG_AGENT is set only with --agent."""
import argparse
import asyncio
import json
import os
from pathlib import Path


async def call(repo: str, org: str, tool: str, args: dict | None, agent: str | None, schema: bool) -> str:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    env = {k: v for k, v in os.environ.items() if k not in ("ORG_AGENT", "ORG_REQUIRE_AGENT", "KIRO_HOME")}
    env["ORG_ROOT"] = org
    if agent:
        env["ORG_AGENT"] = agent
    p = StdioServerParameters(command="uv", args=["--directory", repo, "run", "hirearchy", "mcp"], env=env)
    async with stdio_client(p) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        if schema:
            t = next((t for t in (await s.list_tools()).tools if t.name == tool), None)
            return json.dumps(t.inputSchema if t else None, indent=1)
        res = await s.call_tool(tool, args or {})
        return "\n".join(getattr(c, "text", "") for c in res.content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--org", required=True)
    ap.add_argument("--agent")
    ap.add_argument("--tool")
    ap.add_argument("--args", default="{}")
    ap.add_argument("--schema")
    ap.add_argument("--out")
    a = ap.parse_args()
    real = str(Path(a.org).resolve())
    if not real.startswith("/private/tmp/hirearchy-p2/") or "/Users/aminalizadeh/organization" in real:
        raise SystemExit("refused: mcp_call.py runs only on a throwaway org under /tmp/hirearchy-p2/")
    text = asyncio.run(call(a.repo, a.org, a.schema or a.tool, None if a.schema else json.loads(a.args), a.agent, bool(a.schema)))
    if a.out:
        Path(a.out).write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
