# Freeze gap found by the preflight (2026-10-29)
Step 2 (freeze) recorded the standing rules' md5 only as line 2 of protocol.md5 (and in freeze.txt), and did not write the separate
`standing-rules-streams.md5` that protocol 0 names and that harness/arm.sh md5gate_ok() reads. Result: md5gate_ok printed
"standing-rules-streams.md5 missing (not frozen)" and would have made setup_stream.sh / next_stream.sh / turn.sh refuse every stream.
Action by the preflight (no frozen file touched; protocol.md, standing-rules-streams.md and every harness file are unchanged): wrote
standing-rules-streams.md5 = the line already recorded in protocol.md5 line 2 and freeze.txt (909fbb79c838b69a2d620089545c3ae6),
verified equal to `md5 -q standing-rules-streams.md`. md5 of the new file: cd96e18199cbeab648785e4c372ad79e.
