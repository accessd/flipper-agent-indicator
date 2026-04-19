#!/usr/bin/env bash
# Installs the flipper-agent-indicator Python daemon.
# Registering hooks and pairing with Flipper are manual follow-up steps.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

require_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "error: python3 not found. Install Python >= 3.11." >&2
        exit 1
    fi
    local ver
    ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    local major="${ver%%.*}"
    local minor="${ver#*.}"
    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 11 ]; }; then
        echo "error: Python $ver detected; need >= 3.11 (tomllib, TaskGroup)." >&2
        exit 1
    fi
}

install_daemon() {
    if command -v pipx >/dev/null 2>&1; then
        echo "Installing via pipx..."
        pipx install --force "$REPO_ROOT/daemon"
    else
        echo "pipx not found; falling back to pip --user."
        python3 -m pip install --user --upgrade "$REPO_ROOT/daemon"
    fi
}

post_install_hint() {
    cat <<EOF

Installed. Next steps:

  1. Pair with your Flipper:
       flipper-indicator pair

  2. Start the daemon (foreground for now):
       flipper-indicator serve

  3. Register hooks in your agent's config:
       Claude:   copy $REPO_ROOT/hooks/claude-hooks.json into your Claude hooks file.
       Codex:    point Codex's notify to $REPO_ROOT/hooks/codex-notify.sh.
       OpenCode: copy $REPO_ROOT/hooks/opencode-flipper-indicator.js into
                 ~/.config/opencode/plugins/.

  4. Optional: register a launchd plist to auto-start the daemon
     (see README.md -> Autostart on macOS).

EOF
}

main() {
    require_python
    install_daemon
    post_install_hint
}

main "$@"
