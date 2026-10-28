# P1 scoring (step 12, `score-and-report`, workflow `wf_9e81d83f470f71a8`)

Everything the scoring step wrote is under this folder, except `../aggregate.md` (protocol 12.4's place for the aggregate). No frozen file was
edited: `protocol.md` = `protocol.md5` (`70237b0f...`), `protocol-amendment-1.md` = its `.md5`, and every line of `harness/MD5SUMS` matched
before and after scoring (MD5SUMS md5 `d21508978d71e6d805f1760b25acb1b6`). The product freeze diff was empty. No stream was re-run.

| Step | What | Output |
|---|---|---|
| 1 | The frozen `extract_mechanical.py <stream> <sandbox> --out scoring/<label>/frozen --p1` (it runs `rederive_watch.py` and `guarantees.py`). Every extract, `watch/` and `guarantees/` file is byte-identical to the stream step's. | `<label>/frozen/` |
| 2 | `score_p1.py`: the manager's three scoring rulings over the frozen code (see its docstring): the memo input's name (`manager-decision-memo-input-name.md` + addendum; I2 `meeting_file`, F2 a path value), the lena-lines line form (`manager-decision-stage-1-gate.md` item 2; F1, I1), and `since` at whole seconds (`manager-decision-stage-1-gate.md` item 1; I1, I2, I3). Then the frozen `guarantees.g1/g2` with those readers. Fail-closed checks: every requested memo is in the memo-to-case map (6 of 6 in every stream); the parser reads every Lena turn (26/26, 24/24, 29/29, 25/25, 24/24, 25/25). | `<label>/measures/memo-input.txt`, `requests-by-turn.rederived.txt`, `lena-lines.normalised.*` (F1, I1), `<label>/watch-ruled/` (`since-cleared.txt` lists every cleared line with both values), `<label>/guarantees/`, `I2/measures/assistant_facts-substituted/` |
| 3 | The frozen `score_memos.py <stream> --memos 6 --owner-forms ...` (byte-identical to the stream step's output). For F2 also on a renamed view (`f2_renamed_view.py`: `<date>-memo.md` -> `memo-<date>.md`, nothing else), an arm-F reported reading only. | `<label>/measures/score_memos.*`, `F2/measures-renamed/` |
| 4 | `complete_ledger.py`: the stream step's D14 ledger plus the case facts from the final `progress` (protocol 6.3), then the frozen `rederive_watch.py --spend ... --stream <label>` (completeness: 0 missing cases in every stream). The approval's ceilings were not derived by hand, so `--quality` was not passed (a declared limit, STUDY.md). | `<label>/measures/spend-ledger.json`, `spend-rederived.json`, `spend-mismatches.txt` |
| 5 | `write_judged.py`: the judged keys of `harness/p1-judged-template.json` and `validity.json`, from the raw files (STUDY.md gives the readings). | `<label>/measures/judged.json`, `validity.json` |
| 6 | The frozen `aggregate.py scoring --out aggregate.md --streams F1,I1,I2,F2,F3,I3`. | `../aggregate.md` |

The scorer's scripts and their md5s: `SCORER-MD5SUMS.txt`.
