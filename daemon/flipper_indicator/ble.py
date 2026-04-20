"""Async BLE client for Flipper Zero BLE Serial."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Awaitable, Callable, Optional, Protocol

import structlog
from bleak import BleakClient, BleakScanner

# Flipper Serial Service (FlipperDevices BLE profile).
FLIPPER_SERIAL_SERVICE_UUID = "8fe5b3d5-2e7f-4a98-2a48-7acc60fe0000"
FLIPPER_WRITE_UUID = "19ed82ae-ed21-4c9d-4145-228e62fe0000"   # host -> flipper (RX on fw side)
FLIPPER_NOTIFY_UUID = "19ed82ae-ed21-4c9d-4145-228e63fe0000"  # flipper -> host (TX on fw side)

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
        write_uuid: str = FLIPPER_WRITE_UUID,
        notify_uuid: str = FLIPPER_NOTIFY_UUID,
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
            try:
                await client.write_gatt_char(self._write_uuid, frame, response=True)
                self._log.info("ble.tx", bytes=len(frame))
            except Exception as exc:
                self._log.error("ble.tx_failed", error=str(exc))
                raise


async def scan_devices(timeout: float = 8.0) -> list[tuple[str, str, list[str]]]:
    """Return a list of ``(name, address, service_uuids)`` tuples."""
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    out: list[tuple[str, str, list[str]]] = []
    for address, (device, adv) in found.items():
        name = device.name or adv.local_name or "<unknown>"
        uuids = list(adv.service_uuids or [])
        out.append((name, address, uuids))
    return out


async def iter_queue(q: asyncio.Queue[bytes]) -> AsyncIterator[bytes]:
    while True:
        yield await q.get()
