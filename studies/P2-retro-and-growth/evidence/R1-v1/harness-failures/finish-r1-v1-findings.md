# Findings at R1 v1's finish (facts; nothing retried, edited or deleted)
1. FACILITATOR SLIP: `S/injection/window.txt` was not written after the injection window (E7 5.3 last bullet: "After the window the stream step writes S/injection/window.txt: `<request time> <final progress time>`").
   Effect: `finish_stream.sh` step `injection_files` exit 2 ("no injection/window.txt"); `org_state.py` did not flag the window runs. Window per injection-log.txt: request/start 2026-10-29T10:48:27Z, final progress 10:50:27Z.
   No effect on the course (Lena's lines do not depend on it). The restarted R1 writes window.txt right after the injection.
2. HARNESS DEFECT: `extract_mechanical.py` (finish step `extract_mechanical`, exit 1) crashes with FileNotFoundError on `org-kiro-sessions/.../sess_f04502e1-.../messages.jsonl`.
   That session belongs to the effort-stopped run `lead@20261029T104930658411` (run-session-map.txt: exit=-9, secs=12, credits 0.000000); its session dir holds `session.json` only.
   Consequence: `cost.txt` is not written, so `credits.txt` holds a traceback ("cost.txt: No such file", finish step `credits`). Any stream with an effort stop will hit this. Stream credits for R1 v1 are the running figure: 26.66 (assistant 15.48 + org runs 11.19).
3. HARNESS DEFECT (known): turn.sh sequence check vacuous from turn 3 (turn-sh-sequence-check-vacuous.md); substitute facilitator/seqcheck.py, seqcheck.txt (turns 3-7 all `checked`).
4. Finish steps that succeeded are listed in finish-steps.txt; failures in finish-failures.txt (extract_mechanical, injection_files; the credits step's failure is printed in credits.txt).
