# csv2md

A small Python 3.11 CLI that converts a CSV file (or stdin) to a Markdown (GFM) table.
Standard library only at runtime.

## Install

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11.

```sh
git clone <this repo> && cd csv2md
uv sync            # creates .venv, installs csv2md and pytest (dev)
```

## Usage

```sh
uv run csv2md [--align left|center|right] [PATH]
```

- `PATH`: CSV file to read. Omit it or use `-` to read from stdin.
- The first CSV row is the header.
- `--align` sets the column alignment (default `left`): `:---`, `:---:` or `---:`.
- A `|` inside a cell is written as `\|`.
- Rows shorter than the widest row are padded with empty cells; if a row is longer
  than the header, the header is extended with empty cells so no data is lost.
- Newlines inside quoted cells are written as `<br>` so each record stays on one line.
- Errors (missing file, empty input) go to stderr with a non-zero exit status.

### Examples

```sh
uv run csv2md sample.csv                    # from a file
cat sample.csv | uv run csv2md              # from stdin
cat sample.csv | uv run csv2md - --align right
uv run csv2md --align center sample.csv
```

Output of `uv run csv2md sample.csv`:

```
| name | role | notes |
| :--- | :--- | :--- |
| Smith, Jane | Engineer | Likes a\|b pipes |
| Bob | Designer | Says "hi" |
| Alice | Manager |  |
```

## Tests

```sh
uv run pytest
```
