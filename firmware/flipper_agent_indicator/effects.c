#include "effects.h"

#include <notification/notification.h>
#include <notification/notification_messages.h>

static NotificationApp* g_notifications = NULL;

// ---- LED color presets per agent ----------------------------------------
// Claude=blue, Codex=green, OpenCode=magenta, Generic=white.

static const NotificationMessage msg_led_blue_dim = {
    .type = NotificationMessageTypeLedBlue,
    .data.led.value = 0x40,
};
static const NotificationMessage msg_led_blue_bright = {
    .type = NotificationMessageTypeLedBlue,
    .data.led.value = 0xFF,
};
static const NotificationMessage msg_led_green_dim = {
    .type = NotificationMessageTypeLedGreen,
    .data.led.value = 0x40,
};
static const NotificationMessage msg_led_green_bright = {
    .type = NotificationMessageTypeLedGreen,
    .data.led.value = 0xFF,
};
static const NotificationMessage msg_led_magenta_dim = {
    .type = NotificationMessageTypeLedRed,
    .data.led.value = 0x40,
};
static const NotificationMessage msg_led_magenta_bright = {
    .type = NotificationMessageTypeLedRed,
    .data.led.value = 0xFF,
};
static const NotificationMessage msg_led_white_dim = {
    .type = NotificationMessageTypeLedRed,
    .data.led.value = 0x40,
};
static const NotificationMessage msg_led_white_bright = {
    .type = NotificationMessageTypeLedRed,
    .data.led.value = 0xFF,
};

// Magenta = red + blue. White = red + green + blue. Represented as two-
// message sequences so a single state change paints both channels.
static const NotificationSequence seq_claude_running[] = {
    {&msg_led_blue_dim, &message_do_not_reset, NULL},
};
static const NotificationSequence seq_claude_done[] = {
    {&msg_led_blue_bright, &message_vibro_on, &message_delay_500,
     &message_vibro_off, &message_do_not_reset, NULL},
};
static const NotificationSequence seq_claude_needs[] = {
    {&msg_led_blue_bright, &message_vibro_on, &message_delay_100,
     &message_vibro_off, &message_delay_100, &message_vibro_on,
     &message_delay_100, &message_vibro_off, &message_delay_100,
     &message_vibro_on, &message_delay_100, &message_vibro_off,
     &message_do_not_reset, NULL},
};

static const NotificationSequence seq_codex_running[] = {
    {&msg_led_green_dim, &message_do_not_reset, NULL},
};
static const NotificationSequence seq_codex_done[] = {
    {&msg_led_green_bright, &message_vibro_on, &message_delay_500,
     &message_vibro_off, &message_do_not_reset, NULL},
};
static const NotificationSequence seq_codex_needs[] = {
    {&msg_led_green_bright, &message_vibro_on, &message_delay_100,
     &message_vibro_off, &message_delay_100, &message_vibro_on,
     &message_delay_100, &message_vibro_off, &message_delay_100,
     &message_vibro_on, &message_delay_100, &message_vibro_off,
     &message_do_not_reset, NULL},
};

static const NotificationSequence seq_opencode_running[] = {
    {&msg_led_magenta_dim, &msg_led_blue_dim, &message_do_not_reset, NULL},
};
static const NotificationSequence seq_opencode_done[] = {
    {&msg_led_magenta_bright, &msg_led_blue_bright, &message_vibro_on,
     &message_delay_500, &message_vibro_off, &message_do_not_reset, NULL},
};
static const NotificationSequence seq_opencode_needs[] = {
    {&msg_led_magenta_bright, &msg_led_blue_bright, &message_vibro_on,
     &message_delay_100, &message_vibro_off, &message_delay_100,
     &message_vibro_on, &message_delay_100, &message_vibro_off,
     &message_delay_100, &message_vibro_on, &message_delay_100,
     &message_vibro_off, &message_do_not_reset, NULL},
};

static const NotificationSequence seq_generic_running[] = {
    {&msg_led_white_dim, &msg_led_green_dim, &msg_led_blue_dim,
     &message_do_not_reset, NULL},
};
static const NotificationSequence seq_generic_done[] = {
    {&msg_led_white_bright, &msg_led_green_bright, &msg_led_blue_bright,
     &message_vibro_on, &message_delay_500, &message_vibro_off,
     &message_do_not_reset, NULL},
};
static const NotificationSequence seq_generic_needs[] = {
    {&msg_led_white_bright, &msg_led_green_bright, &msg_led_blue_bright,
     &message_vibro_on, &message_delay_100, &message_vibro_off,
     &message_delay_100, &message_vibro_on, &message_delay_100,
     &message_vibro_off, &message_delay_100, &message_vibro_on,
     &message_delay_100, &message_vibro_off, &message_do_not_reset, NULL},
};

static const NotificationSequence seq_off[] = {
    {&message_red_0, &message_green_0, &message_blue_0, &message_vibro_off, NULL},
};

void effects_init(void) {
    if(g_notifications) return;
    g_notifications = furi_record_open(RECORD_NOTIFICATION);
}

void effects_deinit(void) {
    if(!g_notifications) return;
    notification_message(g_notifications, seq_off);
    furi_record_close(RECORD_NOTIFICATION);
    g_notifications = NULL;
}

void effects_apply(const FaiFrame* notify) {
    if(!g_notifications || !notify) return;

    const NotificationSequence* seq = NULL;

    switch(notify->agent) {
    case FaiAgentClaude:
        seq = (notify->state == FaiStateDone)         ? seq_claude_done :
              (notify->state == FaiStateNeedsInput)   ? seq_claude_needs :
              (notify->state == FaiStateRunning)      ? seq_claude_running :
                                                        seq_off;
        break;
    case FaiAgentCodex:
        seq = (notify->state == FaiStateDone)         ? seq_codex_done :
              (notify->state == FaiStateNeedsInput)   ? seq_codex_needs :
              (notify->state == FaiStateRunning)      ? seq_codex_running :
                                                        seq_off;
        break;
    case FaiAgentOpencode:
        seq = (notify->state == FaiStateDone)         ? seq_opencode_done :
              (notify->state == FaiStateNeedsInput)   ? seq_opencode_needs :
              (notify->state == FaiStateRunning)      ? seq_opencode_running :
                                                        seq_off;
        break;
    default:
        seq = (notify->state == FaiStateDone)         ? seq_generic_done :
              (notify->state == FaiStateNeedsInput)   ? seq_generic_needs :
              (notify->state == FaiStateRunning)      ? seq_generic_running :
                                                        seq_off;
        break;
    }

    notification_message(g_notifications, seq);
}

void effects_clear(void) {
    if(!g_notifications) return;
    notification_message(g_notifications, seq_off);
}
