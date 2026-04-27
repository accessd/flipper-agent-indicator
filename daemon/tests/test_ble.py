import asyncio

import pytest

from flipper_indicator.ble import FlipperClient


class FakeClient:
    def __init__(self, *, connected: bool = True) -> None:
        self._connected = connected
        self.writes: list[tuple[str, bytes, bool]] = []
        self.wrote = asyncio.Event()

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> bool:
        self._connected = False
        return True

    async def start_notify(self, char: str, cb) -> None:
        return None

    async def write_gatt_char(self, char: str, data: bytes, response: bool = False) -> None:
        self.writes.append((char, data, response))
        self.wrote.set()


async def test_pending_frame_survives_link_drop_before_write() -> None:
    outgoing: asyncio.Queue[bytes] = asyncio.Queue(maxsize=1)
    incoming: asyncio.Queue[bytes] = asyncio.Queue()
    client = FlipperClient("fake-mac", outgoing, incoming, write_uuid="write-char")
    frame = b"notify-frame"
    await outgoing.put(frame)

    with pytest.raises(RuntimeError, match="link dropped"):
        await client._pump_outgoing(FakeClient(connected=False))

    reconnected = FakeClient(connected=True)
    await pump_until_write(client, reconnected)

    assert reconnected.writes == [("write-char", frame, True)]


async def test_newer_frame_supersedes_pending_frame_after_link_drop() -> None:
    outgoing: asyncio.Queue[bytes] = asyncio.Queue(maxsize=1)
    incoming: asyncio.Queue[bytes] = asyncio.Queue()
    client = FlipperClient("fake-mac", outgoing, incoming, write_uuid="write-char")
    await outgoing.put(b"old-frame")

    with pytest.raises(RuntimeError, match="link dropped"):
        await client._pump_outgoing(FakeClient(connected=False))

    await outgoing.put(b"new-frame")
    reconnected = FakeClient(connected=True)
    await pump_until_write(client, reconnected)

    assert reconnected.writes == [("write-char", b"new-frame", True)]


async def pump_until_write(client: FlipperClient, reconnected: FakeClient) -> None:
    pump = asyncio.create_task(client._pump_outgoing(reconnected))
    try:
        await asyncio.wait_for(reconnected.wrote.wait(), timeout=1.0)
    finally:
        pump.cancel()
        await asyncio.gather(pump, return_exceptions=True)
