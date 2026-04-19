"""Click entrypoint.

Four subcommands:
  * ``notify`` — hot path invoked from agent hooks. Fire-and-forget UDS write.
  * ``serve`` — run the long-lived daemon in the foreground.
  * ``pair`` — scan BLE, pick a device, save its MAC to the config.
  * ``status`` — probe the UDS socket to check whether the daemon is up.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import sys
from pathlib import Path

import click
import structlog

from . import config as config_mod
from . import ble as ble_mod
from . import daemon as daemon_mod


@click.group()
@click.version_option()
def main() -> None:
    pass


@main.command()
@click.option("--agent", required=True, type=click.Choice(["claude", "codex", "opencode", "generic"]))
@click.option("--state", required=True, type=click.Choice(["off", "running", "needs-input", "done"]))
@click.option("--text", default="", help="Optional short label (<=64 bytes UTF-8).")
def notify(agent: str, state: str, text: str) -> None:
    """Push a single state change to the daemon and exit."""
    cfg = config_mod.load()
    line = f"agent={agent} state={state}"
    if text:
        line += f" text={text}"
    line += "\n"
    _send_line_silent(cfg.resolved_socket_path, line.encode("utf-8"))
    # Always exit 0: missed notifications must not block the agent.
    sys.exit(0)


@main.command()
@click.option("--log-level", default="INFO", show_default=True)
def serve(log_level: str) -> None:
    """Run the daemon in the foreground."""
    _configure_logging(log_level)
    cfg = config_mod.load()
    try:
        asyncio.run(daemon_mod.run(cfg))
    except KeyboardInterrupt:
        pass


@main.command()
@click.option("--timeout", default=8.0, show_default=True, help="BLE scan seconds.")
def pair(timeout: float) -> None:
    """Scan BLE, let the user pick a device, save its MAC."""
    _configure_logging("WARNING")
    click.echo(f"Scanning for BLE devices ({timeout:.0f}s)...")
    devices = asyncio.run(ble_mod.scan_devices(timeout=timeout))
    if not devices:
        click.echo("No devices found. Make sure Bluetooth is on and Flipper BLE is enabled.")
        sys.exit(1)

    for i, (name, address) in enumerate(devices, 1):
        click.echo(f"  [{i}] {name}  {address}")
    raw = click.prompt("Pick a device", type=str)
    try:
        idx = int(raw) - 1
        name, address = devices[idx]
    except (ValueError, IndexError):
        click.echo("Invalid selection.", err=True)
        sys.exit(1)

    path = config_mod.save_mac(address)
    click.echo(f"Saved {address} ({name}) to {path}")


@main.command()
def status() -> None:
    """Report whether the daemon's UDS socket is responsive."""
    cfg = config_mod.load()
    sock_path = cfg.resolved_socket_path
    if not Path(sock_path).exists():
        click.echo(f"down (no socket at {sock_path})")
        sys.exit(1)
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(str(sock_path))
        s.close()
    except OSError as exc:
        click.echo(f"down ({exc})")
        sys.exit(1)
    click.echo(f"up ({sock_path})")


def _send_line_silent(sock_path: Path, payload: bytes) -> None:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.2)
        s.connect(str(sock_path))
        s.sendall(payload)
        s.close()
    except OSError:
        # Daemon down, permission denied, socket missing — all intentionally silent.
        pass


def _configure_logging(level: str) -> None:
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=numeric, format="%(message)s", stream=sys.stderr)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(numeric),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
    )


if __name__ == "__main__":
    main()
