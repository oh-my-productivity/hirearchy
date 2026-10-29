#!/bin/zsh
# P2 quality snapshot: `hirearchy --root <S>/org quality --json` with the arm's CLI (snapshot_cli.sh). Usage: quality_snapshot.sh <label> <tag>
exec zsh ${0:A:h}/snapshot_cli.sh "$1" "$2" quality quality --json
