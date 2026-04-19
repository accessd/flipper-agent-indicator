"""Bridge to tmux-agent-indicator.

On ACK from Flipper the daemon calls ``agent-state.sh --agent <name> --state
off`` to clear the tmux pane decoration. Fire-and-forget; failures are swallowed
because the tmux plugin may not be installed or the user may not be in a tmux
session.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import structlog

from .protocol import AgentId


_AGENT_NAME: dict[AgentId, str] = {
    AgentId.CLAUDE: "claude",
    AgentId.CODEX: "codex",
    AgentId.OPENCODE: "opencode",
    AgentId.GENERIC: "generic",
}


class TmuxBridge:
    def __init__(self, script_path: Path, enabled: bool = True) -> None:
        self._script = script_path
        self._enabled = enabled
        self._log = structlog.get_logger("bridge")

    def clear(self, agent: AgentId) -> None:
        if not self._enabled:
            return
        name = _AGENT_NAME.get(agent, "generic")
        cmd = [str(self._script), "--agent", name, "--state", "off"]
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
            self._log.debug("tmux.clear", agent=name)
        except (FileNotFoundError, OSError) as exc:
            self._log.debug("tmux.clear_failed", agent=name, error=str(exc))
