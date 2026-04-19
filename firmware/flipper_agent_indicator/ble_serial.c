#include "ble_serial.h"

#include "protocol.h"

#include <furi/furi.h>
#include <furi_hal_bt.h>
#include <furi_hal_bt_serial.h>

#include <string.h>

#define TAG "fai.ble"

// Worst-case NOTIFY frame = 4 header + FAI_MAX_TEXT_BYTES text.
// Double it to tolerate a second frame arriving mid-parse.
#define FAI_RX_BUF_CAP ((4 + FAI_MAX_TEXT_BYTES) * 2)

typedef struct {
    FuriMessageQueue* out_queue;
    uint8_t rx_buf[FAI_RX_BUF_CAP];
    size_t rx_len;
    bool initialized;
} FaiBleSerial;

static FaiBleSerial g_ble = {0};

// Attempt to parse as many complete frames as the buffer contains.
// Drops the buffer on any parse failure so that desync cannot wedge us.
static void fai_ble_try_parse(void) {
    while(g_ble.rx_len > 0) {
        FaiFrame frame;
        const int rc = fai_protocol_decode(g_ble.rx_buf, g_ble.rx_len, &frame);
        if(rc != 0) {
            // Cannot tell if it's partial or garbage without a length prefix.
            // If the buffer is full, drop it; otherwise wait for more bytes.
            if(g_ble.rx_len >= FAI_RX_BUF_CAP) {
                FURI_LOG_W(TAG, "rx buffer full, dropping");
                g_ble.rx_len = 0;
            }
            return;
        }

        // Compute consumed length from the frame kind.
        size_t consumed = 0;
        switch(frame.kind) {
        case FaiFrameNotify:
            consumed = 4 + frame.text_len;
            break;
        case FaiFrameAck:
            consumed = 2;
            break;
        case FaiFramePing:
        case FaiFramePong:
            consumed = 1;
            break;
        }
        if(consumed == 0 || consumed > g_ble.rx_len) {
            g_ble.rx_len = 0;
            return;
        }

        if(g_ble.out_queue) {
            furi_message_queue_put(g_ble.out_queue, &frame, 0);
        }

        const size_t remaining = g_ble.rx_len - consumed;
        if(remaining > 0) {
            memmove(g_ble.rx_buf, g_ble.rx_buf + consumed, remaining);
        }
        g_ble.rx_len = remaining;
    }
}

// BLE Serial RX callback. Signature follows Unleashed's
// `SerialServiceEventCallback` convention: event + size + context.
// Unleashed exposes the received bytes through a helper fetch call;
// this wrapper copies them into our ring buffer and kicks the parser.
static uint16_t fai_ble_rx_callback(
    SerialServiceEvent event,
    void* context) {
    UNUSED(context);
    if(event.event != SerialServiceEventTypeDataReceived) {
        return 0;
    }

    const size_t space = FAI_RX_BUF_CAP - g_ble.rx_len;
    if(space == 0) {
        FURI_LOG_W(TAG, "rx overflow, flushing");
        g_ble.rx_len = 0;
        return 0;
    }

    const size_t take = event.data.size < space ? event.data.size : space;
    memcpy(g_ble.rx_buf + g_ble.rx_len, event.data.buffer, take);
    g_ble.rx_len += take;

    fai_ble_try_parse();
    return take;
}

void ble_serial_init(FuriMessageQueue* out_queue) {
    furi_check(out_queue);
    if(g_ble.initialized) return;

    g_ble.out_queue = out_queue;
    g_ble.rx_len = 0;

    // Switch BT stack to the Serial profile exposed by Unleashed.
    furi_hal_bt_start_advertising();
    furi_hal_bt_serial_set_event_callback(
        FAI_RX_BUF_CAP, fai_ble_rx_callback, NULL);

    g_ble.initialized = true;
}

bool ble_serial_send(const uint8_t* buf, size_t len) {
    if(!g_ble.initialized || !buf || len == 0) return false;
    return furi_hal_bt_serial_tx((uint8_t*)buf, len);
}

void ble_serial_deinit(void) {
    if(!g_ble.initialized) return;
    furi_hal_bt_serial_set_event_callback(0, NULL, NULL);
    furi_hal_bt_stop_advertising();
    g_ble.out_queue = NULL;
    g_ble.rx_len = 0;
    g_ble.initialized = false;
}
