# X1: can kiro confine built-in file tools by path? (kiro-cli 2.29.1, claude-haiku-4.5, `--no-interactive`)

Method: temporary project-local profiles in a scratch dir (`<scratch>/ws/.kiro/agents/*.json`, cwd = `<scratch>/ws`), 6 real
runs, outcomes judged by the files on disk (not by what the model said). Scratch dir deleted afterwards. Directories:
`ws/` (allowed), `ro/` (read-only input, holds `secret.txt`), `other/` (outside, holds `secret.txt`).
Docs consulted: kiro.dev built-in tools and custom-agent pages (rendered client-side, only search snippets were
readable). The snippets mention CLI 3.0 has a new capability-based permission model and one GitHub issue (kirodotdev/Kiro
#7799) reports `toolsSettings` as not enforced: not true for `read`/`write` on 2.29.1 as shown here. CLI 3.x was not tested.

Tool names used in `toolsSettings`: `read`, `write` (canonical names; the `fs_read`/`fs_write` aliases were not tried).

## Runs

| # | profile | what | result on disk |
|---|---|---|---|
| 1 | `tools:[read,write]`, `allowedTools:[]`, `write.allowedPaths:[ws/**]`, `read.allowedPaths:[ws/**, ro/**]` | (1) write ws/in.txt (2) write other/out.txt (3) read ro/secret.txt (4) write ro/x.txt (5) read other/secret.txt (6) write `ws/../other/dots.txt` (7) write relative `rel.txt` | 1 OK, 3 OK, 7 OK (landed in cwd = ws). 2, 4, 5, 6 refused; nothing created outside ws. Message: `[denied] tool permission approval is not supported in non-interactive mode. Use --trust-all-tools to auto-approve.` |
| 2 | same, but `allowedTools:["read","write"]` | same 7 steps | **everything succeeded**: outside write, ro write, outside read, `..` write. A tool in `allowedTools` ignores `allowedPaths`. (The old scheduler profile had `allowedTools = tools`, i.e. no confinement at all.) |
| 3 | `tools:[read,write,shell]`, `allowedTools:["shell"]`, same toolsSettings | file-write tool to other/; shell `echo > other/shell.txt`; shell `cat other/secret.txt`; shell `echo > ro/shell.txt` | file tool refused; **all three shell commands ran** and created files outside ws and in ro. `shell` cannot be confined by path. |
| 4 | `allowedTools:["read","write"]`, `toolsSettings.write.deniedPaths:[other/**, ro/**]`, `read.deniedPaths:[other/**]` | write other, write ro, read other, write ws | first three refused: `Tool use was rejected because the arguments supplied are forbidden: <path>/**`; ws write OK. `deniedPaths` is a hard deny even for a trusted tool. Paths are matched after symlink resolution (`/tmp/x` pattern matched `/private/tmp/x`). |
| 5 | run-1 profile | list ro/, list ws/, read ws/sub/deep.txt, write `ws/newdir/a/b.txt`, list other/ | listing `ro` (pattern `ro/**`) refused; listing ws OK (cwd); nested read OK; new nested dirs + file OK; listing other refused. A directory listing needs the bare directory in `allowedPaths` as well as `dir/**`. |
| 6 | `write.allowedPaths:[]`, `read.allowedPaths:[ro, ro/**]`, `allowedTools:[]` | list ro, read ro file, list ws (cwd), read ws/sub/deep.txt, write relative `cwdfile.txt`, write `ws/abs.txt` | reads of ro and of the **cwd** OK (cwd is readable regardless of `allowedPaths`); both writes refused: empty `allowedPaths` = write nowhere, cwd is not writable by default. |

## Consequences used by the product

- Confine `read`/`write` by keeping them OUT of `allowedTools` and listing paths in `toolsSettings`; a call outside is refused
  in headless runs (no approval possible).
- `deniedPaths` on the org directory also removes the implicit "cwd is readable" for agents whose cwd is their org dir.
- `shell` stays unconfinable; say so in the plan and the prompt.
- Not tested: symlinks inside the allowed directory that point out (kiro's behaviour), the aliases `fs_read`/`fs_write`,
  CLI 3.x, and the exact generated profile (with `@orgmcp` in `allowedTools` and both `allowedPaths` and `deniedPaths`) as one
  end-to-end run: its parts were each exercised above, the 6-call budget was used up.
