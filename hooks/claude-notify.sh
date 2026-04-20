#!/usr/bin/env bash
# Claude hook wrapper: attaches the current tmux session:window as context.
# Usage: claude-notify.sh <state>   (state = off|running|needs-input|done)
set -eu

STATE="${1:?state required}"
TEXT=""
if command -v tmux >/dev/null 2>&1 && [ -n "${TMUX-}" ]; then
    TEXT="$(tmux display-message -p '#S:#W' 2>/dev/null || true)"
fi

if [ -n "$TEXT" ]; then
    flipper-indicator notify --agent claude --state "$STATE" --text "$TEXT" >/dev/null 2>&1 || true
else
    flipper-indicator notify --agent claude --state "$STATE" >/dev/null 2>&1 || true
fi
