#!/usr/bin/env python3
"""C1 profile writer (stdlib only): writes SB/kiro-home/agents/c1-<epoch>.json, every value written out. Never prints a value of the environment.
Variants: V0 (default), denv (--denv-names A,B: command /usr/bin/env -u A -u B uv ...), v1 (no uv), v2 (@hirearchy tools, two allow rules),
v4 (--stub-bin DIR on the server's PATH only; the PATH key in the profile env). --choice a|b as Setup 0 defines.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess

WT = "/Volumes/workspace/hirearchy"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sb", required=True)
    ap.add_argument("--epoch", required=True)
    ap.add_argument("--variant", default="v0", choices=["v0", "denv", "v1", "v2", "v4"])
    ap.add_argument("--denv-names", default="")
    ap.add_argument("--choice", default="default", choices=["default", "a", "b"])
    ap.add_argument("--stub-bin", default="")
    a = ap.parse_args()
    name = f"c1-{a.epoch}"
    cache = subprocess.run(["uv", "cache", "dir"], capture_output=True, text=True, check=True).stdout.strip()
    env = {"ORG_ROOT": f"{a.sb}/org", "HIREARCHY_STATE_DIR": f"{a.sb}/kiro-state", "HOME": f"{a.sb}/home", "UV_CACHE_DIR": cache}
    if a.choice == "b":
        del env["HOME"]
    if a.choice == "a":
        env["KIRO_API_KEY"] = os.environ["KIRO_API_KEY"]  # by name, from the environment at write time; never printed
    uv = ["uv", "--directory", WT, "run", "hirearchy", "mcp"]
    server = {"command": "uv", "args": uv[1:], "env": env}
    if a.variant == "denv":
        names = [n for n in a.denv_names.split(",") if n]
        server = {"command": "/usr/bin/env", "args": [x for n in names for x in ("-u", n)] + uv, "env": env}
    if a.variant == "v1":
        server = {"command": f"{WT}/.venv/bin/hirearchy", "args": ["mcp"], "env": env}
    if a.variant == "v4":
        env["PATH"] = a.stub_bin + ":" + os.environ["PATH"]
    prof = {"name": name, "description": "internal: hirearchy 0a.4 C1 reproduction; deleted after the attempt",
            "mcpServers": {"hirearchy": server}, "tools": ["*"], "permissions": {"rules": [{"capability": "all", "effect": "allow"}]},
            "resources": [f"skill://{WT}/skills/hirearchy/SKILL.md", "skill://.kiro/skills/*/SKILL.md"], "hooks": [],
            "includeMcpJson": False, "model": "claude-sonnet-5.5"}
    if a.choice == "b":
        prof["resources"] = ["skill://.kiro/skills/*/SKILL.md"]
    if a.variant == "v2":
        prof["tools"] = ["@hirearchy"]
        prof["permissions"] = {"rules": [{"capability": "tool", "effect": "allow", "tool": "hirearchy/progress"},
                                          {"capability": "tool", "effect": "allow", "tool": "hirearchy/start"}]}
    path = f"{a.sb}/kiro-home/agents/{name}.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(prof, fh, indent=2)
    shown = json.loads(json.dumps(prof))
    shown["mcpServers"]["hirearchy"]["env"].pop("KIRO_API_KEY", None)
    print(json.dumps(shown, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
