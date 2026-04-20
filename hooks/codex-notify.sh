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

TEXT=""
if command -v tmux >/dev/null 2>&1 && [ -n "${TMUX-}" ]; then
    TEXT="$(tmux display-message -p '#S:#W' 2>/dev/null || true)"
fi

if [ -n "$TEXT" ]; then
    flipper-indicator notify --agent codex --state "$STATE" --text "$TEXT" >/dev/null 2>&1 || true
else
    flipper-indicator notify --agent codex --state "$STATE" >/dev/null 2>&1 || true
fi
