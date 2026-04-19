import asyncio
import os
import tempfile
import threading
from pathlib import Path

import pytest
from click.testing import CliRunner

from flipper_indicator.cli import main
from flipper_indicator.protocol import AgentId, Notify, State
from flipper_indicator.socket_server import SocketServer


@pytest.fixture
def short_sock_path():
    d = tempfile.mkdtemp(prefix="fi-", dir="/tmp")
    path = Path(d) / "t.sock"
    yield path
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    os.rmdir(d)


class _LiveSocket:
    """Runs a SocketServer in a background thread with its own loop."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.queue: asyncio.Queue[Notify] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._server: SocketServer | None = None
        self._started = threading.Event()

    def __enter__(self) -> "_LiveSocket":
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        assert self._started.wait(timeout=2.0), "server didn't come up"
        return self

    def __exit__(self, *exc) -> None:
        assert self._loop is not None and self._server is not None
        fut = asyncio.run_coroutine_threadsafe(self._server.stop(), self._loop)
        fut.result(timeout=2.0)
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self.queue = asyncio.Queue()
        self._server = SocketServer(self.path, self.queue)
        loop.run_until_complete(self._server.start())
        self._started.set()
        loop.run_forever()

    def pop(self, timeout: float = 1.0) -> Notify:
        assert self._loop is not None and self.queue is not None
        fut = asyncio.run_coroutine_threadsafe(
            asyncio.wait_for(self.queue.get(), timeout=timeout), self._loop
        )
        return fut.result(timeout=timeout + 0.5)


def _force_cfg(monkeypatch, sock_path: Path) -> None:
    from flipper_indicator import config as config_mod

    def fake_load(path=None):
        return config_mod.Config(socket_path=str(sock_path))

    monkeypatch.setattr(config_mod, "load", fake_load)


def test_notify_sends_line_to_daemon(short_sock_path: Path, monkeypatch) -> None:
    sock = short_sock_path
    _force_cfg(monkeypatch, sock)
    with _LiveSocket(sock) as live:
        runner = CliRunner()
        result = runner.invoke(main, ["notify", "--agent", "claude", "--state", "done"])
        assert result.exit_code == 0
        notify = live.pop()
        assert notify == Notify(AgentId.CLAUDE, State.DONE, "")


def test_notify_passes_text(short_sock_path: Path, monkeypatch) -> None:
    sock = short_sock_path
    _force_cfg(monkeypatch, sock)
    with _LiveSocket(sock) as live:
        runner = CliRunner()
        result = runner.invoke(
            main, ["notify", "--agent", "codex", "--state", "needs-input", "--text", "approve? y/n"]
        )
        assert result.exit_code == 0
        notify = live.pop()
        assert notify.text == "approve? y/n"


def test_notify_silent_when_daemon_down(tmp_path: Path, monkeypatch) -> None:
    sock = tmp_path / "missing.sock"
    _force_cfg(monkeypatch, sock)
    runner = CliRunner()
    result = runner.invoke(main, ["notify", "--agent", "opencode", "--state", "running"])
    assert result.exit_code == 0
    assert result.output == ""


def test_status_reports_down_when_no_socket(tmp_path: Path, monkeypatch) -> None:
    sock = tmp_path / "no.sock"
    _force_cfg(monkeypatch, sock)
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 1
    assert "down" in result.output


def test_status_reports_up(short_sock_path: Path, monkeypatch) -> None:
    sock = short_sock_path
    _force_cfg(monkeypatch, sock)
    with _LiveSocket(sock):
        runner = CliRunner()
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "up" in result.output
