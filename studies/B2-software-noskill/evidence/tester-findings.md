# csv2md independent test findings

Verdict: PASS (no required changes). Repo HEAD e6e1e5b.
Script: `lead/tester/work/run_tests.sh` (rerun: `sh lead/tester/work/run_tests.sh` from the repo root).
Full raw output: `lead/tester/work/raw_output.txt`. All commands run with `UV_CACHE_DIR=/tmp/orgmcp-b2-1792261142/repo/.uv-cache`, cwd = repo.
Every `uv run` prints a harmless `warning: VIRTUAL_ENV=... does not match the project environment` line on stderr (caused by the caller's environment, not the project); omitted below.

git status --porcelain: empty before and empty after (verified at start and end of the script). `lead/` and caches are ignored. I wrote only under lead/tester/work/.

## (1) Test suite
`uv run pytest 2>&1 | tail -5` -> `22 passed in 0.06s`, exit 0. PASS

## (2) Valid GFM table
`uv run csv2md sample.csv` (exit 0):
```
| name | role | notes |
| :--- | :--- | :--- |
| Smith, Jane | Engineer | Likes a\|b pipes |
| Bob | Designer | Says "hi" |
| Alice | Manager |  |
```
Header row, separator row, 3 columns in every row (the `Alice` row is padded). PASS

## (3) --align
- `csv2md sample.csv` and `--align left` -> `| :--- | :--- | :--- |` (default is left). PASS
- `--align center` -> `| :---: | :---: | :---: |`. PASS
- `--align right` -> `| ---: | ---: | ---: |`. PASS
- `csv2md --align middle sample.csv` -> exit 2, stderr: `csv2md: error: argument --align: invalid choice: 'middle' (choose from 'left', 'center', 'right')`. PASS
- `csv2md --align sample.csv` (missing value) -> exit 2, same style of invalid-choice error. PASS

## (4) Input sources (identical output to (2) in each case)
- file path: `csv2md sample.csv` exit 0. PASS
- stdin, no path: `cat sample.csv | csv2md` and `csv2md < sample.csv` exit 0. PASS
- stdin, `-`: `cat sample.csv | csv2md -` exit 0; `cat sample.csv | csv2md - --align right` gives right alignment. PASS
- `python -m csv2md sample.csv` also works.

## (5) Error paths (message on stderr, non-zero exit, stdout empty)
- `csv2md nonexistent.csv` -> `csv2md: error: file not found: nonexistent.csv`, exit 1. PASS
- `csv2md .` (directory) -> `csv2md: error: cannot read .: Is a directory`, exit 1. PASS
- `printf "" | csv2md` -> `csv2md: error: input is empty (no CSV rows found)`, exit 1. PASS
- whitespace-only `printf "   \n\t\n  \n" | csv2md` -> same message, exit 1. PASS
- only newlines `printf "\n\n"` -> same, exit 1. PASS
- invalid UTF-8 (`\xff\xfe`) -> `csv2md: error: input is not valid UTF-8 text`, exit 1. PASS
- extra positional (`csv2md a b`) -> argparse usage error, exit 2. PASS

## (6) Escaping, quoting, ragged rows
- `printf "a|b,c\n1|2,x||y\n" | csv2md` -> `| a\|b | c |` / `| 1\|2 | x\|\|y |`. PASS
- quoted commas `"x, y","a,b,c"` / `"1,2",3` -> `| x, y | a,b,c |` / `| 1,2 | 3 |`. PASS
- ragged: `a,b,c / 1 / 1,2,3,4,5` -> header extended to 5 columns, every row has 5 columns, separator has 5 cells. PASS
- ragged: `a,b,c,d / 1` -> `| 1 |  |  |  |` (4 columns each). PASS
- shorter row in sample.csv covered in (2). PASS

## (7) Edge cases
- unicode `zażółć`, `日本語 🎉` -> preserved verbatim. PASS
- quoted newline (LF) `"line1\nline2"` -> `line1<br>line2`, stays on one line. PASS
- CRLF stdin (including CRLF inside a quoted cell) -> clean rows, `<br>`; no `\r` leaks. PASS
- CRLF file (checked with `od -c`): output has only `\n`, no `\r`. Quoted CRLF in file -> `l1<br>l2`. PASS
- header-only CSV `a,b,c` -> header + separator, no body rows, exit 0. PASS
- blank lines between records are skipped. PASS
- row of empty cells `,` mid-table -> kept as an empty row; no trailing newline at EOF handled. PASS
- all-empty input `,,` -> treated as empty input (error, exit 1). Reasonable, not a defect.
- single column with `--align center` -> `| a |` / `| :---: |` / `| 1 |`. PASS
- `pyproject.toml`: runtime `dependencies = []`; pytest only in `[dependency-groups] dev`; console script `csv2md`. PASS

## Non-blocking observations (no change required)
- A UTF-8 BOM at the start of a file or stdin stays in the first header cell (`\ufeffa`). Opening the file with `utf-8-sig` would fix it, but this is outside the stated scope.

## REQUIRED CHANGES
None.
