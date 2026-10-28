# Manager decision: the memo input's name is the team's choice, not always `notes_file` (2026-10-27)

**What happened** (`I2/harness-failures/meeting-file-input-name.txt`). I2's team named its service input `meeting_file`. Root's first request
reads `- meeting_file: 2026-10-05.md`. The frozen harness finds a memo only through the name `notes_file`:
- `after_turn.sh:94` (`requests-by-turn.txt`);
- `guarantees.py:67` (`memo_of_task`, which builds G1's and G2's memo-to-case map);
- `assistant_facts.py:238` (reported facts).

So in I2, `requests-by-turn.txt` reads `(none)`, and the scoring's memo-to-case map would be empty. F1 and I1 used `notes_file`.

**This is a harness assumption, not a product defect and not an H rule.** The team names its inputs (the product is domain-agnostic, and the
design names no input), and the course did not change: the stream step read M3-VERDICT's trigger and the ledger cases from root's sent mail
directly, and recorded each reading.

**Ruling.**
1. **The stream steps (I2, F2, F3, I3).** Live triggers that the protocol reads from `requests-by-turn.txt` (M3-VERDICT's "memo 4's request
   exists"; L-LATER's request sentence; the ledger case entry) are read from root's sent mail (`S/org/sent/*.md`): a request whose
   `## Request` block gives the memo's notes file under ANY input name. Record each such reading in that turn's facts as
   `memo <n> request read from sent mail: <message id> (<input name>: <file>)`. `requests-by-turn.txt` stays as the frozen script writes it.
   Never edit it.
2. **The scorer, every stream.** It determines each stream's memo input name from root's first request: the input whose value is
   `2026-10-05.md`. Cross-check it against the service's `SERVICE.md` v1 inputs. Write it to `measures/<label>/memo-input.txt`. Then:
   - when the name is `notes_file`, it runs the frozen code as is;
   - otherwise, it runs the frozen readers (`memo_of_task`, `after_turn.sh`'s request reading, `assistant_facts.py:238`) with that one name
     substituted, in memory or through a wrapper script under `measures/`, with its md5 recorded. It edits no frozen file and changes nothing
     else. It recomputes `requests-by-turn` into `measures/<label>/requests-by-turn.rederived.txt`.
3. **Fail-closed.** The scorer checks that the memo-to-case map holds every memo whose request exists in root's sent mail. A missing memo makes
   every part that needs the map (G1's candidates and windows, G2 (a)-(c)) read NOT DETERMINED for that stream, never PASS.
4. **Reported** as finding `F-P1-n` (harness): a study harness must read the team's own input names from the service contract, never assume
   one. Add it to the harness lessons with H-A1's.

## Addendum (2026-10-27): the input's value may be a path (F2)

F2's team kept the name `notes_file` but gave it an absolute path as its value
(`F2/harness-failures/notes-file-path-value.txt`). The frozen regex `notes_file:\s*(\d{4}-\d{2}-\d{2})` therefore misses it too. The same
ruling applies, widened:
- the scorer reads each request's memo from the `YYYY-MM-DD` date in the base name of the memo input's value, whatever its path;
- it runs the frozen readers with that one extraction substituted, as above;
- the fail-closed check of item 3 stands.
