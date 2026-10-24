#!/bin/sh
printf "%s\n" "$*" >> "${KIRO_STUB_LOG:-/dev/null}"
case "$1" in
  --version) echo "kiro-cli 2.33.0" ;;
  whoami) echo "stub user" ;;
  chat)
    if [ "$2" = "--help" ]; then
      printf '%s\n' "Usage: kiro-cli chat [OPTIONS] [INPUT]" "      --v3" "      --require-mcp-startup" "      --output-format <FORMAT>"
    else
      cat > /dev/null
      printf '%s\n' '{"type":"runStarted","data":{"engine":"v3"}}'
      sleep 60
      printf '%s\n' '{"type":"runFinished","data":{"status":"success","stopReason":"end_turn"}}'
    fi
    ;;
esac
exit 0
