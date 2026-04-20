#!/usr/bin/env bash
# Codex notify fan-out: tmux-agent-indicator + agent-indicator + flipper-agent-indicator.
# Point `notify` in ~/.codex/config.toml at this file.
set -uo pipefail

"bash" "/Users/accessd/.tmux/plugins/tmux-agent-indicator/adapters/codex-notify.sh" "$@" 2>/dev/null || true
"bash" "/Users/accessd/projects/github/accessd/agent-indicator/adapters/codex-notify.sh" "$@" 2>/dev/null || true
exec "/Users/accessd/projects/github/accessd/flipper-agent-indicator/hooks/codex-notify.sh" "$@"
