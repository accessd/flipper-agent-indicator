"""UDS server that accepts single-line notify events from the CLI.

Wire format: ``agent=<name> state=<name> [text=<utf8, spaces ok until newline>]\n``

No response. Client closes immediately. Keeps the CLI hot path under the <50ms
budget by avoiding any BLE work on the request side.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import structlog

from .protocol import AgentId, Notify, State


_log = structlog.get_logger("uds")

_AGENT_BY_NAME = {
    "claude": AgentId.CLAUDE,
    "codex": AgentId.CODEX,
    "opencode": AgentId.OPENCODE,
    "generic": AgentId.GENERIC,
}

_STATE_BY_NAME = {
    "off": State.OFF,
    "running": State.RUNNING,
    "needs-input": State.NEEDS_INPUT,
    "done": State.DONE,
}


class ParseError(ValueError):
    pass


def parse_line(line: str) -> Notify:
    agent: AgentId | None = None
    state: State | None = None
    text = ""
    # text=... consumes the rest of the line; everything else is key=value.
    remaining = line.strip()
    while remaining:
        if remaining.startswith("text="):
            text = remaining[len("text="):]
            break
        sep = remaining.find(" ")
        token = remaining if sep == -1 else remaining[:sep]
        remaining = "" if sep == -1 else remaining[sep + 1:].lstrip()
        if "=" not in token:
            raise ParseError(f"expected key=value, got {token!r}")
        key, value = token.split("=", 1)
        if key == "agent":
            if value not in _AGENT_BY_NAME:
                raise ParseError(f"unknown agent: {value}")
            agent = _AGENT_BY_NAME[value]
        elif key == "state":
            if value not in _STATE_BY_NAME:
                raise ParseError(f"unknown state: {value}")
            state = _STATE_BY_NAME[value]
        else:
            raise ParseError(f"unknown key: {key}")
    if agent is None or state is None:
        raise ParseError("agent and state are required")
    return Notify(agent=agent, state=state, text=text)


class SocketServer:
    def __init__(self, path: Path, outgoing: asyncio.Queue[Notify]) -> None:
        self._path = path
        self._outgoing = outgoing
        self._server: asyncio.base_events.Server | None = None

    async def start(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists():
            self._path.unlink()
        self._server = await asyncio.start_unix_server(self._handle, path=str(self._path))
        os.chmod(self._path, 0o600)
        _log.info("uds.listening", path=str(self._path))

    async def serve_forever(self) -> None:
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=1.0)
        except asyncio.TimeoutError:
            writer.close()
            return
        try:
            line = raw.decode("utf-8", errors="replace")
            notify = parse_line(line)
        except ParseError as exc:
            _log.warning("uds.parse_error", error=str(exc))
            writer.close()
            return
        self._outgoing.put_nowait(notify)
        _log.debug("uds.enqueued", agent=notify.agent.name, state=notify.state.name)
        writer.close()
