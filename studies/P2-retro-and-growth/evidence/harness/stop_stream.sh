#!/bin/zsh
# P2 stop path (protocol 3.6). Usage: stop_stream.sh <label> "<reason>"
# Writes <label>/stopped.txt (the reason, the last turn, UTC), runs finish_stream.sh --end <credits|stopped> (end.txt, protocol 3.7; it
# restores the global skill in arm C), then skill_move.sh restore <label> again (idempotent). Prints the restore's state last; the step then
# sends its warning.
LABEL="$1"; REASON="$2"
H0=${0:A:h}
source $H0/arm.sh "$LABEL" || exit 2
D=$EV/$LABEL
LAST=$(grep -c '^turn ' $D/turn-times.txt 2>/dev/null)
echo "stopped $(date -u +%FT%TZ) after turn ${LAST:-0}: $REASON" >> $D/stopped.txt
END=stopped; [[ "$REASON" == credits* ]] && END=credits
zsh $H0/finish_stream.sh $LABEL --end $END; frc=$?
[[ $ARM == C ]] && zsh $H0/skill_move.sh restore $LABEL
zsh $H0/skill_move.sh status
echo "stop_stream $LABEL: finish exit $frc; reason: $REASON"
