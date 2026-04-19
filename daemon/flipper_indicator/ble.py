"""Async BLE client for Flipper Zero BLE Serial.

The Flipper exposes a Nordic UART Service (NUS)-compatible BLE Serial profile.
Write frames to the TX characteristic; subscribe to notifications on the RX
characteristic. UUIDs below are the common Nordic UART UUIDs that Flipper
firmware uses; the firmware agent should confirm these against the running
build.

TODO: verify NUS_RX_UUID / NUS_TX_UUID match the custom `.fap` built by the
firmware agent. If they diverge, the daemon config should grow a
``rx_char_uuid`` / ``tx_char_uuid`` override.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Awaitable, Callable, Optional, Protocol

import structlog
from bleak import BleakClient, BleakScanner

# Nordic UART Service UUIDs. These match what Flipper BLE Serial typically
# exposes; if the `.fap` uses a different UUID, the scanner fallback below
# selects the first characteristic with write+notify properties on the device.
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_WRITE_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # host -> flipper
NUS_NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # flipper -> host

BACKOFF_INITIAL = 1.0
BACKOFF_MAX = 30.0


class BleakLike(Protocol):
    async def connect(self) -> bool: ...
    async def disconnect(self) -> bool: ...
    async def start_notify(self, char: str, cb: Callable[..., None]) -> None: ...
    async def write_gatt_char(self, char: str, data: bytes, response: bool = False) -> None: ...
    @property
    def is_connected(self) -> bool: ...


ScannerFn = Callable[[str, float], Awaitable[Optional[object]]]
ClientFactory = Callable[[object], BleakLike]


async def _default_scanner(mac: str, timeout: float) -> Optional[object]:
    return await BleakScanner.find_device_by_address(mac, timeout=timeout)


def _default_client_factory(device: object) -> BleakLike:
    return BleakClient(device)  # type: ignore[return-value, arg-type]


class FlipperClient:
    """Keeps a BLE Serial session with Flipper; publishes RX frames to a queue."""

    def __init__(
        self,
        mac: str,
        outgoing: asyncio.Queue[bytes],
        incoming: asyncio.Queue[bytes],
        *,
        scanner: ScannerFn = _default_scanner,
        client_factory: ClientFactory = _default_client_factory,
        write_uuid: str = NUS_WRITE_UUID,
        notify_uuid: str = NUS_NOTIFY_UUID,
    ) -> None:
        self._mac = mac
        self._outgoing = outgoing
        self._incoming = incoming
        self._scanner = scanner
        self._client_factory = client_factory
        self._write_uuid = write_uuid
        self._notify_uuid = notify_uuid
        self._log = structlog.get_logger("ble")

    async def run_forever(self) -> None:
        backoff = BACKOFF_INITIAL
        while True:
            try:
                await self._session()
                backoff = BACKOFF_INITIAL
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._log.warning("ble.session_ended", error=str(exc), retry_in=backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)

    async def _session(self) -> None:
        self._log.info("ble.scan", mac=self._mac)
        device = await self._scanner(self._mac, 10.0)
        if device is None:
            raise RuntimeError(f"device {self._mac} not found")

        client = self._client_factory(device)
        self._log.info("ble.connecting", mac=self._mac)
        await client.connect()
        self._log.info("ble.connected", mac=self._mac)
        try:
            def on_notify(_sender: object, data: bytearray) -> None:
                self._incoming.put_nowait(bytes(data))

            await client.start_notify(self._notify_uuid, on_notify)
            await self._pump_outgoing(client)
        finally:
            try:
                await client.disconnect()
            except Exception:  # macOS CoreBluetooth can raise on teardown
                pass
            self._log.info("ble.disconnected", mac=self._mac)

    async def _pump_outgoing(self, client: BleakLike) -> None:
        while True:
            frame = await self._outgoing.get()
            if not client.is_connected:
                raise RuntimeError("link dropped")
            await client.write_gatt_char(self._write_uuid, frame, response=False)
            self._log.debug("ble.tx", bytes=len(frame))


async def scan_devices(timeout: float = 8.0) -> list[tuple[str, str]]:
    """Return a list of ``(name, address)`` tuples for nearby BLE devices."""
    devices = await BleakScanner.discover(timeout=timeout)
    return [(d.name or "<unknown>", d.address) for d in devices]


async def iter_queue(q: asyncio.Queue[bytes]) -> AsyncIterator[bytes]:
    while True:
        yield await q.get()
