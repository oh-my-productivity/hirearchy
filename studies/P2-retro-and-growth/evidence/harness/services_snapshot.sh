#!/bin/zsh
# P2 services snapshot: root's `hirearchy --root <S>/org services` with the arm's CLI (snapshot_cli.sh). Usage: services_snapshot.sh <label> <tag>
exec zsh ${0:A:h}/snapshot_cli.sh "$1" "$2" services services
