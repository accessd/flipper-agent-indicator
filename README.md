# flipper-agent-indicator

Physical notification surface for AI coding agents. Companion to
[`tmux-agent-indicator`](https://github.com/accessd/tmux-agent-indicator).

When Claude / Codex / OpenCode changes state (`running`, `needs-input`, `done`,
`off`), the same hooks that drive the tmux pane also drive a custom `.fap`
running on a Flipper Zero over BLE Serial. The Flipper shows the agent label,
blinks its LED, and vibrates. Press OK on the device to dismiss — the daemon
clears both the Flipper screen and the tmux pane decoration.

## How it fits together

```
agent hook
    |
    v
flipper-indicator notify  --(UDS line)-->  flipper-indicator serve
                                                     |
                                                     | BLE Serial (bleak)
                                                     v
                                           Flipper Zero custom .fap
                                                     |
                                         OK-press = ACK frame
                                                     |
                                                     v
                             tmux-agent-indicator/scripts/agent-state.sh --state off
```

- Hook scripts are fire-and-forget over a Unix domain socket, so they cost <50ms
  and never block the agent.
- The daemon is the only process that holds the BLE connection. It reconnects
  with exponential backoff.
- The tmux plugin is independent and authoritative for terminal UX. This
  project is additive — both fire in parallel.

## Requirements

- macOS (Darwin) with Bluetooth.
- Python >= 3.11 (uses `tomllib` and `asyncio.TaskGroup`).
- `pipx` recommended (falls back to `pip --user`).
- A Flipper Zero running the companion `.fap` built by the firmware agent from
  this repo's `firmware/` directory. Unleashed Firmware.
- Optional: [`tmux-agent-indicator`](https://github.com/accessd/tmux-agent-indicator)
  installed if you want tmux pane decorations alongside the Flipper.

## Install

```sh
./install.sh
```

This installs the daemon and CLI as `flipper-indicator`. Then:

```sh
flipper-indicator pair    # scan, pick your Flipper, save its MAC
flipper-indicator serve   # run the daemon in the foreground
```

Config lives at `~/.config/flipper-agent-indicator/config.toml`.

## Hook registration

### Claude

Drop `hooks/claude-hooks.json` into your Claude settings hooks file (or merge
its entries if you already have one). The commands call
`flipper-indicator notify --agent claude --state <state>`.

### Codex

Point Codex's notify command at `hooks/codex-notify.sh`.

### OpenCode

Copy `hooks/opencode-flipper-indicator.js` into `~/.config/opencode/plugins/`
(or `.opencode/plugins/` for project-local).

All three can coexist with the tmux-agent-indicator hooks — the tmux scripts
and `flipper-indicator notify` are independent.

## Autostart on macOS (launchd)

Create `~/Library/LaunchAgents/dev.flipper-agent-indicator.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>dev.flipper-agent-indicator</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/YOUR_USER/.local/bin/flipper-indicator</string>
    <string>serve</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/flipper-indicator.log</string>
  <key>StandardErrorPath</key><string>/tmp/flipper-indicator.err</string>
</dict>
</plist>
```

Load with:

```sh
launchctl load ~/Library/LaunchAgents/dev.flipper-agent-indicator.plist
```

Note: the first BLE connect will trigger macOS's Bluetooth permission dialog
for the Python interpreter. Grant it under **System Settings -> Privacy &
Security -> Bluetooth**, then restart the daemon.

## Config file reference

```toml
flipper_mac = "AA:BB:CC:DD:EE:FF"
tmux_bridge_enabled = true
tmux_bridge_script = "~/.tmux/plugins/tmux-agent-indicator/scripts/agent-state.sh"
log_path = "~/.local/state/flipper-agent-indicator/daemon.log"
socket_path = "/tmp/flipper-indicator-501.sock"   # default picks XDG_RUNTIME_DIR

# Optional overrides. Firmware owns the actual LED/vibra playback; the host
# sends (agent, state) and the firmware picks its own pattern. Overrides here
# are informational unless the firmware exposes a matching option.
[patterns.claude.running]
label = "Claude: thinking"
led_rgb = [40, 100, 255]
vibra_sequence = [60, 120]
```

## Troubleshooting

**Hook runs but nothing happens.**
Check `flipper-indicator status`. If it reports `down`, start the daemon:
`flipper-indicator serve`. The CLI is intentionally silent on failure so it
never breaks your agent session.

**Daemon logs `device not found`.**
Wake the Flipper, make sure it's advertising, and that its BLE is on. The
daemon retries with exponential backoff up to 30s between attempts.

**Bluetooth permission dialog never shows up.**
macOS scopes BLE permissions to the binary path. If you re-install Python or
switch interpreters, grant access again to the new path.

**I want to disable the tmux bridge.**
Set `tmux_bridge_enabled = false` in `config.toml`. ACK frames will still be
logged, but `agent-state.sh` won't be invoked.

**CLI is slow from hooks.**
Run `time flipper-indicator notify --agent claude --state done`. It should be
<50ms. If it's slower, check that the daemon is running and the UDS path is
correct — a missing socket still exits fast, but DNS or TOML load overhead
dominates otherwise. Consider setting `socket_path` to a fixed absolute path.

**Multiple notifications queue up.**
By design: single-event overwrite (latest wins). If this ever feels lossy,
file an issue.
