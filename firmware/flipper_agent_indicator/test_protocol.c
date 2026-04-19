// Host-side unit tests for the C protocol codec.
// Build: cc -Wall -Wextra -std=c11 protocol.c test_protocol.c -o test_protocol && ./test_protocol
// Not compiled into the .fap — runs on the dev machine to verify parity with Python.

#include "protocol.h"

#include <stdio.h>
#include <string.h>

static int failures = 0;
static int total = 0;

#define CHECK(cond, msg)                                                                \
    do {                                                                                \
        total++;                                                                        \
        if(!(cond)) {                                                                   \
            failures++;                                                                 \
            fprintf(stderr, "FAIL %s:%d: %s\n", __func__, __LINE__, msg);               \
        }                                                                               \
    } while(0)

static void test_notify_roundtrip(void) {
    FaiFrame in = {
        .kind = FaiFrameNotify,
        .agent = FaiAgentClaude,
        .state = FaiStateNeedsInput,
        .text_len = 19,
    };
    memcpy(in.text, "Bash: rm -rf build/", 19);

    uint8_t buf[128];
    int n = fai_protocol_encode(&in, buf, sizeof(buf));
    CHECK(n == 23, "encoded length");
    CHECK(buf[0] == FAI_TAG_NOTIFY, "tag");
    CHECK(buf[1] == FaiAgentClaude, "agent");
    CHECK(buf[2] == FaiStateNeedsInput, "state");
    CHECK(buf[3] == 19, "text_len");

    FaiFrame out;
    int rc = fai_protocol_decode(buf, n, &out);
    CHECK(rc == 0, "decode rc");
    CHECK(out.kind == FaiFrameNotify, "kind");
    CHECK(out.agent == FaiAgentClaude, "agent back");
    CHECK(out.state == FaiStateNeedsInput, "state back");
    CHECK(out.text_len == 19, "text_len back");
    CHECK(strcmp(out.text, "Bash: rm -rf build/") == 0, "text back");
}

static void test_notify_empty_text(void) {
    FaiFrame in = {.kind = FaiFrameNotify, .agent = FaiAgentCodex, .state = FaiStateDone, .text_len = 0};
    uint8_t buf[8];
    int n = fai_protocol_encode(&in, buf, sizeof(buf));
    CHECK(n == 4, "len");
    FaiFrame out;
    CHECK(fai_protocol_decode(buf, n, &out) == 0, "decode ok");
    CHECK(out.text_len == 0, "empty text_len");
    CHECK(out.text[0] == '\0', "empty text null");
}

static void test_ack_roundtrip(void) {
    FaiFrame in = {.kind = FaiFrameAck, .agent = FaiAgentGeneric};
    uint8_t buf[4];
    int n = fai_protocol_encode(&in, buf, sizeof(buf));
    CHECK(n == 2, "ack len");
    CHECK(buf[0] == FAI_TAG_ACK, "ack tag");
    CHECK(buf[1] == 0xFF, "ack agent");
    FaiFrame out;
    CHECK(fai_protocol_decode(buf, n, &out) == 0, "decode ack");
    CHECK(out.kind == FaiFrameAck, "ack kind");
    CHECK(out.agent == 0xFF, "ack agent back");
}

static void test_ping_pong(void) {
    FaiFrame ping = {.kind = FaiFramePing};
    FaiFrame pong = {.kind = FaiFramePong};
    uint8_t buf[2];
    CHECK(fai_protocol_encode(&ping, buf, sizeof(buf)) == 1, "ping len");
    CHECK(buf[0] == FAI_TAG_PING, "ping tag");
    CHECK(fai_protocol_encode(&pong, buf, sizeof(buf)) == 1, "pong len");
    CHECK(buf[0] == FAI_TAG_PONG, "pong tag");

    FaiFrame out;
    const uint8_t ping_bytes[] = {FAI_TAG_PING};
    const uint8_t pong_bytes[] = {FAI_TAG_PONG};
    CHECK(fai_protocol_decode(ping_bytes, 1, &out) == 0 && out.kind == FaiFramePing, "decode ping");
    CHECK(fai_protocol_decode(pong_bytes, 1, &out) == 0 && out.kind == FaiFramePong, "decode pong");
}

static void test_decode_rejects_bad_input(void) {
    FaiFrame out;
    CHECK(fai_protocol_decode(NULL, 0, &out) == -1, "null buf");
    CHECK(fai_protocol_decode((const uint8_t*)"", 0, &out) == -1, "empty");
    const uint8_t unknown[] = {0x55};
    CHECK(fai_protocol_decode(unknown, 1, &out) == -1, "unknown tag");
    const uint8_t short_notify[] = {FAI_TAG_NOTIFY, 0, 0};
    CHECK(fai_protocol_decode(short_notify, 3, &out) == -1, "short NOTIFY header");
    const uint8_t short_text[] = {FAI_TAG_NOTIFY, 0, 0, 10, 'a'};
    CHECK(fai_protocol_decode(short_text, 5, &out) == -1, "short NOTIFY text");
    const uint8_t short_ack[] = {FAI_TAG_ACK};
    CHECK(fai_protocol_decode(short_ack, 1, &out) == -1, "short ACK");
    const uint8_t oversized_text[] = {FAI_TAG_NOTIFY, 0, 0, FAI_MAX_TEXT_BYTES + 1};
    CHECK(fai_protocol_decode(oversized_text, 4, &out) == -1, "text_len > max");
}

static void test_encode_rejects_small_buffer(void) {
    FaiFrame f = {.kind = FaiFrameNotify, .agent = 0, .state = 0, .text_len = 10};
    memset(f.text, 'x', 10);
    uint8_t buf[5];
    CHECK(fai_protocol_encode(&f, buf, sizeof(buf)) == -1, "buffer too small");
}

int main(void) {
    test_notify_roundtrip();
    test_notify_empty_text();
    test_ack_roundtrip();
    test_ping_pong();
    test_decode_rejects_bad_input();
    test_encode_rejects_small_buffer();

    printf("%s: %d/%d passed\n", failures == 0 ? "PASS" : "FAIL", total - failures, total);
    return failures == 0 ? 0 : 1;
}
