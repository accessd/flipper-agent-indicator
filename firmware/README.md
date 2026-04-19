# firmware/flipper_agent_indicator

Custom Flipper Zero `.fap` for the `flipper-agent-indicator` project.
Receives `NOTIFY` frames over BLE Serial from the host daemon, renders a
per-agent notification, and sends an `ACK` frame back when the user
presses OK.

## Requirements

- [ufbt](https://github.com/flipperdevices/flipperzero-ufbt)
- Unleashed Firmware SDK (DarkFlippers/unleashed-firmware) — official
  firmware does not expose the BLE Serial profile hooks this app uses.
- Tested against Unleashed release `1.3.x` or newer. Confirm once built on
  hardware.

Point ufbt at Unleashed before building:

```sh
ufbt update --index-url https://up.unleashedflip.com/directory.json
```

## Build & deploy

From the repo root:

```sh
cd firmware/flipper_agent_indicator
ufbt            # build .fap
ufbt launch     # flash to a connected Flipper and run
```

The resulting `.fap` lands in `firmware/flipper_agent_indicator/dist/`.

Before the first build, drop a 10x10 1-bit PNG at
`firmware/flipper_agent_indicator/assets/icon.png` — see
`assets/README.md`.

## Runtime behaviour

- On launch the app opens BLE Serial advertising, shows a "Waiting for
  agents..." idle screen, and blocks on its frame queue.
- Incoming `NOTIFY` frames flip the screen to a notification view and
  trigger the LED/vibra pattern for `(agent, state)`.
- `OK` (short press) dismisses: sends `ACK`, clears LED/vibra, returns to
  idle.
- `BACK` exits the app cleanly.
- `PING` frames get an auto `PONG` reply for liveness checks.

## Unleashed-specific API caveats

The BLE Serial profile API differs between official and Unleashed
firmware. This app currently calls into:

- `furi_hal_bt_start_advertising()` / `furi_hal_bt_stop_advertising()`
- `furi_hal_bt_serial_set_event_callback(buf_size, cb, ctx)`
- `furi_hal_bt_serial_tx(buf, len)`
- `SerialServiceEvent` / `SerialServiceEventTypeDataReceived`

Names and signatures in `ble_serial.c` track the Unleashed tree as of
early 2026. If Unleashed has renamed any of these, fix them in
`ble_serial.c` only — the rest of the app talks to this module through
`ble_serial.h`.

Official firmware does **not** ship a user-accessible Serial profile at
all; it is BLE HID-only. If you need official-firmware support, plan a
`FuriHalBtProfileSerial` bring-up via the newer `bt` record APIs instead.

## Protocol

See `protocol.h`. Frames are single-write, MTU-safe (<100 bytes). Host
(daemon) and firmware share the exact same wire format; the host-side
codec lives in `daemon/flipper_indicator/protocol.py`.
