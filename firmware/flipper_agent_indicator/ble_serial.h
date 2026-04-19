#pragma once

#include <furi/furi.h>

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Initialize BLE Serial profile and register an RX callback that decodes
// incoming frames and pushes successfully parsed FaiFrame values onto
// `out_queue`. The queue must hold elements of size sizeof(FaiFrame).
void ble_serial_init(FuriMessageQueue* out_queue);

// Send `len` bytes over the BLE Serial TX characteristic. Safe to call from
// the app thread. Returns true on success.
bool ble_serial_send(const uint8_t* buf, size_t len);

// Tear down the BLE Serial profile and release resources. Safe to call
// after a successful init only.
void ble_serial_deinit(void);

#ifdef __cplusplus
}
#endif
