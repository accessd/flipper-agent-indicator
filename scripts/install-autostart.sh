#!/usr/bin/env bash
# Install background autostart for flipper-indicator on macOS.
#
# Builds a minimal .app bundle (for the NSBluetoothAlwaysUsageDescription TCC
# key), registers it with launchd, and starts it. On first launch macOS will
# show the Bluetooth permission dialog; grant it once.
set -euo pipefail

APP_ID="dev.accessd.flipper-indicator"
APP_NAME="FlipperIndicator"
APP_DIR="${HOME}/Applications/${APP_NAME}.app"
LAUNCH_AGENT="${HOME}/Library/LaunchAgents/${APP_ID}.plist"
DAEMON_BIN="${HOME}/projects/github/accessd/flipper-agent-indicator/daemon/.venv/bin/flipper-indicator"
LOG_DIR="${HOME}/Library/Logs"

if [[ ! -x "${DAEMON_BIN}" ]]; then
    echo "error: ${DAEMON_BIN} not found or not executable" >&2
    echo "run daemon/.venv setup first" >&2
    exit 1
fi

mkdir -p "${APP_DIR}/Contents/MacOS" "${APP_DIR}/Contents/Resources"

cat > "${APP_DIR}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>${APP_ID}</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>Flipper Indicator</string>
    <key>CFBundleExecutable</key>
    <string>run</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>CFBundleVersion</key>
    <string>0.1.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>LSBackgroundOnly</key>
    <true/>
    <key>NSBluetoothAlwaysUsageDescription</key>
    <string>Flipper Indicator forwards AI agent notifications to a Flipper Zero over Bluetooth.</string>
    <key>NSBluetoothPeripheralUsageDescription</key>
    <string>Flipper Indicator forwards AI agent notifications to a Flipper Zero over Bluetooth.</string>
</dict>
</plist>
PLIST

cat > "${APP_DIR}/Contents/MacOS/run" <<WRAP
#!/bin/sh
exec "${DAEMON_BIN}" serve
WRAP
chmod +x "${APP_DIR}/Contents/MacOS/run"

# Clear any cached TCC attribution so macOS re-evaluates the new bundle.
codesign -f -s - "${APP_DIR}" >/dev/null 2>&1 || true

cat > "${LAUNCH_AGENT}" <<LAUNCHD
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${APP_ID}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${APP_DIR}/Contents/MacOS/run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/flipper-indicator.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/flipper-indicator.log</string>
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
LAUNCHD

launchctl unload "${LAUNCH_AGENT}" 2>/dev/null || true
launchctl load "${LAUNCH_AGENT}"

echo "installed: ${APP_DIR}"
echo "launchd:   ${LAUNCH_AGENT}"
echo "log:       ${LOG_DIR}/flipper-indicator.log"
echo
echo "On first Bluetooth access, macOS will show a permission dialog."
echo "If dialog is missed, open System Settings -> Privacy & Security -> Bluetooth,"
echo "and enable '${APP_NAME}' manually."
