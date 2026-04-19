#include "ble_serial.h"

#include "protocol.h"

#include <furi/furi.h>
#include <bt/bt_service/bt.h>
#include <services/serial_service.h>
#include <profiles/serial_profile.h>

#include <string.h>

#define TAG "fai.ble"

// Worst-case NOTIFY frame = 4 header + FAI_MAX_TEXT_BYTES text.
// Double it to tolerate a second frame arriving mid-parse.
#define FAI_RX_BUF_CAP ((4 + FAI_MAX_TEXT_BYTES) * 2)

typedef struct {
    Bt* bt;
    FuriHalBleProfileBase* profile;
    FuriMessageQueue* out_queue;
    uint8_t rx_buf[FAI_RX_BUF_CAP];
    size_t rx_len;
    bool initialized;
} FaiBleSerial;

static FaiBleSerial g_ble = {0};

static void fai_ble_try_parse(void) {
    while(g_ble.rx_len > 0) {
        FaiFrame frame;
        if(fai_protocol_decode(g_ble.rx_buf, g_ble.rx_len, &frame) != 0) {
            if(g_ble.rx_len >= FAI_RX_BUF_CAP) {
                FURI_LOG_W(TAG, "rx buffer full, dropping");
                g_ble.rx_len = 0;
            }
            return;
        }

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

static uint16_t fai_ble_rx_callback(SerialServiceEvent event, void* context) {
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
    return (uint16_t)take;
}

void ble_serial_init(FuriMessageQueue* out_queue) {
    furi_check(out_queue);
    if(g_ble.initialized) return;

    g_ble.out_queue = out_queue;
    g_ble.rx_len = 0;

    g_ble.bt = furi_record_open(RECORD_BT);
    // Switching profiles restarts the BT core — profile pointer is required
    // for all subsequent tx/callback calls.
    g_ble.profile = bt_profile_start(g_ble.bt, ble_profile_serial, NULL);
    if(!g_ble.profile) {
        FURI_LOG_E(TAG, "bt_profile_start failed");
        furi_record_close(RECORD_BT);
        g_ble.bt = NULL;
        g_ble.out_queue = NULL;
        return;
    }

    ble_profile_serial_set_event_callback(
        g_ble.profile, FAI_RX_BUF_CAP, fai_ble_rx_callback, NULL);

    g_ble.initialized = true;
}

bool ble_serial_send(const uint8_t* buf, size_t len) {
    if(!g_ble.initialized || !buf || len == 0) return false;
    return ble_profile_serial_tx(g_ble.profile, (uint8_t*)buf, (uint16_t)len);
}

void ble_serial_deinit(void) {
    if(!g_ble.initialized) return;
    bt_profile_restore_default(g_ble.bt);
    furi_record_close(RECORD_BT);
    g_ble.bt = NULL;
    g_ble.profile = NULL;
    g_ble.out_queue = NULL;
    g_ble.rx_len = 0;
    g_ble.initialized = false;
}
