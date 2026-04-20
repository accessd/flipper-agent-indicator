"""Main daemon loop.

- UDS server receives Notify events from the CLI.
- Latest-wins forwarding: if multiple events queue up before BLE drains, only
  the last one matters (see non-goals in PLAN.md).
- BLE client ships frames and surfaces RX bytes back.
- On ACK, we clear the matching state in tmux-agent-indicator via TmuxBridge.
"""

from __future__ import annotations

import asyncio
import signal
from pathlib import Path

import structlog

from . import protocol
from .ble import FlipperClient
from .bridge import TmuxBridge
from .config import Config
from .patterns import PatternTable
from .protocol import Ack, Notify
from .socket_server import SocketServer


_log = structlog.get_logger("daemon")


async def run(config: Config) -> None:
    if not config.flipper_mac:
        raise RuntimeError(
            "flipper_mac not configured. Run `flipper-indicator pair` first."
        )

    notify_queue: asyncio.Queue[Notify] = asyncio.Queue()
    outgoing_bytes: asyncio.Queue[bytes] = asyncio.Queue(maxsize=1)
    incoming_bytes: asyncio.Queue[bytes] = asyncio.Queue()

    patterns = PatternTable(overrides=config.patterns)
    bridge = TmuxBridge(config.resolved_tmux_bridge_script, enabled=config.tmux_bridge_enabled)

    server = SocketServer(config.resolved_socket_path, notify_queue)
    await server.start()

    ble = FlipperClient(config.flipper_mac, outgoing_bytes, incoming_bytes)

    stop_event = asyncio.Event()
    _install_signal_handlers(stop_event)

    tasks = [
        asyncio.create_task(server.serve_forever(), name="uds"),
        asyncio.create_task(ble.run_forever(), name="ble"),
        asyncio.create_task(_forward_notifies(notify_queue, outgoing_bytes, patterns), name="forward"),
        asyncio.create_task(_handle_incoming(incoming_bytes, bridge), name="incoming"),
    ]
    try:
        stop_task = asyncio.create_task(stop_event.wait(), name="stop")
        done, _pending = await asyncio.wait(
            [*tasks, stop_task], return_when=asyncio.FIRST_COMPLETED
        )
        _log.info("daemon.stopping")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        # Surface any non-cancellation failure from the first-completed task.
        for t in done:
            if t is stop_task:
                continue
            exc = t.exception()
            if exc is not None:
                raise exc
    finally:
        await server.stop()


def _install_signal_handlers(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            # Windows; not a supported platform but don't crash at import.
            pass


async def _forward_notifies(
    incoming: asyncio.Queue[Notify],
    outgoing: asyncio.Queue[bytes],
    patterns: PatternTable,
) -> None:
    while True:
        notify = await incoming.get()
        pattern = patterns.get(notify.agent, notify.state)
        _log.info(
            "notify.forward",
            agent=notify.agent.name,
            state=notify.state.name,
            label=pattern.label,
            text=notify.text,
        )
        frame = protocol.encode(notify)
        # latest-wins: drop any pending frame before enqueueing the new one.
        while not outgoing.empty():
            try:
                outgoing.get_nowait()
            except asyncio.QueueEmpty:
                break
        await outgoing.put(frame)


async def _handle_incoming(incoming: asyncio.Queue[bytes], bridge: TmuxBridge) -> None:
    while True:
        raw = await incoming.get()
        # Flipper's Serial Service periodically notifies a 4-byte big-endian
        # "free RX buffer size" flow-control message on the data characteristic.
        # Drop it silently rather than spamming unknown-tag warnings.
        if len(raw) == 4 and raw[0] == 0:
            _log.debug("rx.flow_ctrl", free=int.from_bytes(raw, "big"))
            continue
        try:
            frame = protocol.decode(raw)
        except ValueError as exc:
            _log.warning("rx.decode_failed", error=str(exc), bytes=raw.hex())
            continue
        if isinstance(frame, Ack):
            _log.info("rx.ack", agent=frame.agent.name)
            bridge.clear(frame.agent)
        else:
            _log.debug("rx.frame", type=type(frame).__name__)
