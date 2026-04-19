#pragma once

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define FAI_TAG_NOTIFY 0x01
#define FAI_TAG_PING   0x02
#define FAI_TAG_ACK    0x81
#define FAI_TAG_PONG   0x82

#define FAI_MAX_TEXT_BYTES 64

typedef enum {
    FaiAgentClaude = 0,
    FaiAgentCodex = 1,
    FaiAgentOpencode = 2,
    FaiAgentGeneric = 0xFF,
} FaiAgentId;

typedef enum {
    FaiStateOff = 0,
    FaiStateRunning = 1,
    FaiStateNeedsInput = 2,
    FaiStateDone = 3,
} FaiState;

typedef enum {
    FaiFrameNotify,
    FaiFrameAck,
    FaiFramePing,
    FaiFramePong,
} FaiFrameKind;

typedef struct {
    FaiFrameKind kind;
    uint8_t agent;          // NOTIFY, ACK
    uint8_t state;          // NOTIFY
    uint8_t text_len;       // NOTIFY (<= FAI_MAX_TEXT_BYTES)
    char text[FAI_MAX_TEXT_BYTES + 1]; // NOTIFY, null-terminated
} FaiFrame;

// Encode a frame into `out`. Returns bytes written, or -1 on failure
// (unknown kind, buffer too small, text_len out of range).
int fai_protocol_encode(const FaiFrame* f, uint8_t* out, size_t out_cap);

// Decode a buffer into `out`. Returns 0 on success, -1 on parse error.
int fai_protocol_decode(const uint8_t* buf, size_t len, FaiFrame* out);

#ifdef __cplusplus
}
#endif
