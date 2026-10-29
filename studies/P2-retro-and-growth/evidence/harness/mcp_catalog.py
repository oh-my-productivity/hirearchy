#!/usr/bin/env python3
"""P2 tool catalog of one product (protocol 8.3): an MCP stdio `list_tools` of the profile's server command, bound as root to a throwaway
org. Run inside the arm's product env: `uv --directory <REPO_A> run python mcp_catalog.py --repo <REPO_A> --org <dir> --out <file>`.
Writes {tool name: md5 of its description and input schema (sorted JSON)} plus the names. Makes no tool call. KIRO_HOME, ORG_AGENT and
ORG_REQUIRE_AGENT are removed from the server's environment (E7's injection script's form)."""
import argparse
import asyncio
import hashlib
import json
import os


async def catalog(repo: str, org: str, call: str | None = None) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    env = {k: v for k, v in os.environ.items() if k not in ("ORG_AGENT", "ORG_REQUIRE_AGENT", "KIRO_HOME")}
    env["ORG_ROOT"] = org
    p = StdioServerParameters(command="uv", args=["--directory", repo, "run", "hirearchy", "mcp"], env=env)
    async with stdio_client(p) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        tools = (await s.list_tools()).tools
        if call:  # the self-check's dry run only: one read-only tool call as root (an event of the MCP path before the changes)
            await s.call_tool(call, {})
    return {t.name: hashlib.md5(json.dumps({"description": t.description, "input_schema": t.inputSchema}, sort_keys=True).encode()).hexdigest()
            for t in tools}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--org", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--call", help="self-check only: one read-only tool to call (whoami)")
    a = ap.parse_args()
    if a.call and a.call not in ("whoami", "services", "status"):
        raise SystemExit("--call takes a read-only tool: whoami, services or status")
    c = asyncio.run(catalog(a.repo, a.org, a.call))
    open(a.out, "w").write(json.dumps({"repo": a.repo, "tools": c, "names": sorted(c)}, indent=1, sort_keys=True) + "\n")
    print(f"catalog of {a.repo}: {len(c)} tools: {' '.join(sorted(c))}")


if __name__ == "__main__":
    main()
