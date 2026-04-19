#include "protocol.h"

#include <string.h>

int fai_protocol_encode(const FaiFrame* f, uint8_t* out, size_t out_cap) {
    if(!f || !out) return -1;

    switch(f->kind) {
    case FaiFrameNotify: {
        if(f->text_len > FAI_MAX_TEXT_BYTES) return -1;
        const size_t needed = 4 + f->text_len;
        if(out_cap < needed) return -1;
        out[0] = FAI_TAG_NOTIFY;
        out[1] = f->agent;
        out[2] = f->state;
        out[3] = f->text_len;
        if(f->text_len) memcpy(&out[4], f->text, f->text_len);
        return (int)needed;
    }
    case FaiFrameAck:
        if(out_cap < 2) return -1;
        out[0] = FAI_TAG_ACK;
        out[1] = f->agent;
        return 2;
    case FaiFramePing:
        if(out_cap < 1) return -1;
        out[0] = FAI_TAG_PING;
        return 1;
    case FaiFramePong:
        if(out_cap < 1) return -1;
        out[0] = FAI_TAG_PONG;
        return 1;
    }
    return -1;
}

int fai_protocol_decode(const uint8_t* buf, size_t len, FaiFrame* out) {
    if(!buf || !out || len == 0) return -1;

    memset(out, 0, sizeof(*out));

    switch(buf[0]) {
    case FAI_TAG_NOTIFY: {
        if(len < 4) return -1;
        const uint8_t text_len = buf[3];
        if(text_len > FAI_MAX_TEXT_BYTES) return -1;
        if(len < (size_t)(4 + text_len)) return -1;
        out->kind = FaiFrameNotify;
        out->agent = buf[1];
        out->state = buf[2];
        out->text_len = text_len;
        if(text_len) memcpy(out->text, &buf[4], text_len);
        out->text[text_len] = '\0';
        return 0;
    }
    case FAI_TAG_ACK:
        if(len < 2) return -1;
        out->kind = FaiFrameAck;
        out->agent = buf[1];
        return 0;
    case FAI_TAG_PING:
        out->kind = FaiFramePing;
        return 0;
    case FAI_TAG_PONG:
        out->kind = FaiFramePong;
        return 0;
    }
    return -1;
}
