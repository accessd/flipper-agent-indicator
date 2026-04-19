#!/usr/bin/env bash
# Convenience wrapper around `flipper-indicator pair`.
set -euo pipefail
exec flipper-indicator pair "$@"
