import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from flipper_indicator.protocol import AgentId, Notify, State
from flipper_indicator.socket_server import ParseError, SocketServer, parse_line


@pytest.fixture
def short_sock_path():
    # AF_UNIX paths on macOS are capped near 104 chars; pytest tmp_path is longer.
    d = tempfile.mkdtemp(prefix="fi-", dir="/tmp")
    path = Path(d) / "t.sock"
    yield path
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    os.rmdir(d)


def test_parse_line_ok() -> None:
    n = parse_line("agent=claude state=needs-input text=Hello there\n")
    assert n == Notify(AgentId.CLAUDE, State.NEEDS_INPUT, "Hello there")


def test_parse_line_no_text() -> None:
    n = parse_line("agent=codex state=done")
    assert n.text == ""
    assert n.agent == AgentId.CODEX
    assert n.state == State.DONE


def test_parse_line_text_may_contain_spaces() -> None:
    n = parse_line("agent=claude state=running text=Bash: rm -rf /tmp/x")
    assert n.text == "Bash: rm -rf /tmp/x"


def test_parse_line_unknown_agent_raises() -> None:
    with pytest.raises(ParseError):
        parse_line("agent=wat state=off")


def test_parse_line_missing_state_raises() -> None:
    with pytest.raises(ParseError):
        parse_line("agent=claude")


async def test_server_enqueues_notify(short_sock_path: Path) -> None:
    sock_path = short_sock_path
    q: asyncio.Queue[Notify] = asyncio.Queue()
    server = SocketServer(sock_path, q)
    await server.start()
    try:
        reader, writer = await asyncio.open_unix_connection(str(sock_path))
        writer.write(b"agent=opencode state=running text=thinking\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        notify = await asyncio.wait_for(q.get(), timeout=1.0)
        assert notify == Notify(AgentId.OPENCODE, State.RUNNING, "thinking")
    finally:
        await server.stop()


async def test_server_ignores_garbage(short_sock_path: Path) -> None:
    sock_path = short_sock_path
    q: asyncio.Queue[Notify] = asyncio.Queue()
    server = SocketServer(sock_path, q)
    await server.start()
    try:
        reader, writer = await asyncio.open_unix_connection(str(sock_path))
        writer.write(b"not-a-valid-line\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(q.get(), timeout=0.2)
    finally:
        await server.stop()
