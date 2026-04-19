from pathlib import Path
from unittest.mock import patch

from flipper_indicator.bridge import TmuxBridge
from flipper_indicator.protocol import AgentId


def test_clear_spawns_agent_state_script() -> None:
    import subprocess

    bridge = TmuxBridge(Path("/opt/agent-state.sh"))
    with patch("flipper_indicator.bridge.subprocess.Popen") as popen:
        bridge.clear(AgentId.CLAUDE)
    popen.assert_called_once()
    args, kwargs = popen.call_args
    assert args[0] == ["/opt/agent-state.sh", "--agent", "claude", "--state", "off"]
    assert kwargs["stdout"] == subprocess.DEVNULL
    assert kwargs["stderr"] == subprocess.DEVNULL
    assert kwargs["close_fds"] is True


def test_clear_maps_agents_to_names() -> None:
    bridge = TmuxBridge(Path("/x/s.sh"))
    mapping = {
        AgentId.CLAUDE: "claude",
        AgentId.CODEX: "codex",
        AgentId.OPENCODE: "opencode",
        AgentId.GENERIC: "generic",
    }
    for agent, name in mapping.items():
        with patch("flipper_indicator.bridge.subprocess.Popen") as popen:
            bridge.clear(agent)
        assert popen.call_args.args[0][2] == name


def test_clear_disabled_does_nothing() -> None:
    bridge = TmuxBridge(Path("/x/s.sh"), enabled=False)
    with patch("flipper_indicator.bridge.subprocess.Popen") as popen:
        bridge.clear(AgentId.CLAUDE)
    popen.assert_not_called()


def test_clear_swallows_missing_script() -> None:
    bridge = TmuxBridge(Path("/x/s.sh"))
    with patch("flipper_indicator.bridge.subprocess.Popen", side_effect=FileNotFoundError()):
        # must not raise
        bridge.clear(AgentId.CODEX)
