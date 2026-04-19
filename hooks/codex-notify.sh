#!/usr/bin/env bash
# flipper-agent-indicator adapter for Codex notify events.
# Parallel to tmux-agent-indicator/adapters/codex-notify.sh.

set -euo pipefail

EVENT="${1:-agent-turn-complete}"

case "$EVENT" in
    start|session-start|turn-start|working)
        STATE="running"
        ;;
    permission*|approve*|needs-input|input-required|ask-user)
        STATE="needs-input"
        ;;
    agent-turn-complete|complete|done|stop|error|fail*)
        STATE="done"
        ;;
    *)
        STATE="done"
        ;;
esac

flipper-indicator notify --agent codex --state "$STATE" >/dev/null 2>&1 || true
