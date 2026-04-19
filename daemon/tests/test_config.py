from pathlib import Path

from flipper_indicator import config as config_mod
from flipper_indicator.config import Config, load, save_mac


def test_load_missing_returns_defaults(tmp_path: Path) -> None:
    cfg = load(tmp_path / "nope.toml")
    assert cfg.flipper_mac is None
    assert cfg.tmux_bridge_enabled is True
    assert cfg.patterns == {}


def test_load_full_toml(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        'flipper_mac = "AA:BB:CC:DD:EE:FF"\n'
        "tmux_bridge_enabled = false\n"
        'tmux_bridge_script = "/tmp/agent-state.sh"\n'
        'log_path = "/tmp/fi.log"\n'
        'socket_path = "/tmp/fi.sock"\n'
        "\n[patterns.claude.running]\n"
        'label = "thinking"\n'
    )
    cfg = load(path)
    assert cfg.flipper_mac == "AA:BB:CC:DD:EE:FF"
    assert cfg.tmux_bridge_enabled is False
    assert cfg.tmux_bridge_script == "/tmp/agent-state.sh"
    assert cfg.log_path == "/tmp/fi.log"
    assert cfg.socket_path == "/tmp/fi.sock"
    assert cfg.patterns["claude"]["running"]["label"] == "thinking"


def test_default_socket_path_uses_xdg_runtime(monkeypatch) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/tmp/runtime-uid")
    assert config_mod.default_socket_path() == "/tmp/runtime-uid/flipper-indicator.sock"


def test_default_socket_path_falls_back(monkeypatch) -> None:
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    path = config_mod.default_socket_path()
    assert path.startswith("/tmp/flipper-indicator-")
    assert path.endswith(".sock")


def test_resolved_paths_expand_user() -> None:
    cfg = Config(tmux_bridge_script="~/foo.sh", log_path="~/bar.log", socket_path="~/baz.sock")
    assert not str(cfg.resolved_tmux_bridge_script).startswith("~")
    assert not str(cfg.resolved_log_path).startswith("~")
    assert not str(cfg.resolved_socket_path).startswith("~")


def test_save_mac_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "config.toml"
    save_mac("11:22:33:44:55:66", target)
    assert target.exists()
    cfg = load(target)
    assert cfg.flipper_mac == "11:22:33:44:55:66"


def test_save_mac_preserves_other_fields(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text('tmux_bridge_enabled = false\nflipper_mac = "00:00:00:00:00:00"\n')
    save_mac("AA:BB:CC:DD:EE:FF", target)
    cfg = load(target)
    assert cfg.flipper_mac == "AA:BB:CC:DD:EE:FF"
    assert cfg.tmux_bridge_enabled is False
