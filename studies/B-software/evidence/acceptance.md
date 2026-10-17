1. pyproject.toml, src/csv2md/{__init__,__main__,cli,converter}.py, README.md exist in the workspace and `pip install` of the project into a throwaway venv yields a working `csv2md` command.
2. A unittest suite in tests/ covers: basic table, quoted fields with commas, pipe escaping, embedded newlines, ragged rows, --no-header, --align, --pad, custom delimiter, stdin, -o, BOM, empty-input error, unicode.
3. The suite passes when run with `PYTHONPATH=src python3 -m unittest discover -s tests -v`; the report quotes the pass count from an actual run log.
4. An independent reviewer agent (not the author) approved the work (APPROVED), and README matches actual behavior.
5. Report names the final project path and lists known limitations honestly.
