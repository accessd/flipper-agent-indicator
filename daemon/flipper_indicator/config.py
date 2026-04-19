"""Config loader for the daemon.

Reads TOML from ``~/.config/flipper-agent-indicator/config.toml`` when present.
All fields have sensible defaults so the daemon can boot and log a clear error
when the MAC is missing, rather than crashing during import.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "flipper-agent-indicator" / "config.toml"
DEFAULT_TMUX_BRIDGE_SCRIPT = "~/.tmux/plugins/tmux-agent-indicator/scripts/agent-state.sh"
DEFAULT_LOG_PATH = "~/.local/state/flipper-agent-indicator/daemon.log"


def default_socket_path() -> str:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return str(Path(runtime_dir) / "flipper-indicator.sock")
    return f"/tmp/flipper-indicator-{os.getuid()}.sock"


@dataclass
class Config:
    flipper_mac: str | None = None
    tmux_bridge_enabled: bool = True
    tmux_bridge_script: str = DEFAULT_TMUX_BRIDGE_SCRIPT
    log_path: str = DEFAULT_LOG_PATH
    socket_path: str = field(default_factory=default_socket_path)
    # Free-form per-(agent,state) overrides; validated by patterns.PatternTable.
    patterns: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def resolved_tmux_bridge_script(self) -> Path:
        return Path(self.tmux_bridge_script).expanduser()

    @property
    def resolved_log_path(self) -> Path:
        return Path(self.log_path).expanduser()

    @property
    def resolved_socket_path(self) -> Path:
        return Path(self.socket_path).expanduser()


def load(path: Path | str | None = None) -> Config:
    cfg_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        return Config()
    with cfg_path.open("rb") as fh:
        raw = tomllib.load(fh)
    return _from_dict(raw)


def _from_dict(raw: dict[str, Any]) -> Config:
    kwargs: dict[str, Any] = {}
    if "flipper_mac" in raw:
        kwargs["flipper_mac"] = raw["flipper_mac"]
    if "tmux_bridge_enabled" in raw:
        kwargs["tmux_bridge_enabled"] = bool(raw["tmux_bridge_enabled"])
    if "tmux_bridge_script" in raw:
        kwargs["tmux_bridge_script"] = str(raw["tmux_bridge_script"])
    if "log_path" in raw:
        kwargs["log_path"] = str(raw["log_path"])
    if "socket_path" in raw:
        kwargs["socket_path"] = str(raw["socket_path"])
    if "patterns" in raw and isinstance(raw["patterns"], dict):
        kwargs["patterns"] = raw["patterns"]
    return Config(**kwargs)


def save_mac(mac: str, path: Path | str | None = None) -> Path:
    """Write or update ``flipper_mac`` in the config file."""
    cfg_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, Any] = {}
    if cfg_path.exists():
        with cfg_path.open("rb") as fh:
            existing = tomllib.load(fh)
    existing["flipper_mac"] = mac

    lines = [f'{key} = {_format_toml_value(value)}' for key, value in existing.items()
             if not isinstance(value, dict)]
    table_blocks: list[str] = []
    for key, value in existing.items():
        if isinstance(value, dict):
            table_blocks.append(_render_table(key, value))

    content = "\n".join(lines)
    if table_blocks:
        content += "\n\n" + "\n\n".join(table_blocks)
    if not content.endswith("\n"):
        content += "\n"
    cfg_path.write_text(content)
    return cfg_path


def _format_toml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return '"' + str(v).replace('\\', '\\\\').replace('"', '\\"') + '"'


def _render_table(name: str, table: dict[str, Any]) -> str:
    lines = [f"[{name}]"]
    for k, v in table.items():
        if isinstance(v, dict):
            lines.append(_render_table(f"{name}.{k}", v))
        else:
            lines.append(f"{k} = {_format_toml_value(v)}")
    return "\n".join(lines)
