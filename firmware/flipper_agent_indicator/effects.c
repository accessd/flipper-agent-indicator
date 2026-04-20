#include "effects.h"

#include <notification/notification.h>
#include <notification/notification_messages.h>

static NotificationApp* g_notifications = NULL;

void effects_init(void) {
    if(g_notifications) return;
    g_notifications = furi_record_open(RECORD_NOTIFICATION);
}

void effects_deinit(void) {
    if(!g_notifications) return;
    notification_message(g_notifications, &sequence_reset_rgb);
    notification_message(g_notifications, &sequence_reset_vibro);
    furi_record_close(RECORD_NOTIFICATION);
    g_notifications = NULL;
}

// Per-agent LED colour for "needs input" attention (blink at 100ms).
static const NotificationSequence* agent_blink(uint8_t agent) {
    switch(agent) {
    case FaiAgentClaude:
        return &sequence_blink_blue_100;
    case FaiAgentCodex:
        return &sequence_blink_green_100;
    case FaiAgentOpencode:
        return &sequence_blink_magenta_100;
    default:
        return &sequence_blink_white_100;
    }
}

// Per-agent solid colour for "done".
static const NotificationSequence* agent_solid_done(uint8_t agent) {
    switch(agent) {
    case FaiAgentClaude:
        return &sequence_set_only_blue_255;
    case FaiAgentCodex:
        return &sequence_set_only_green_255;
    case FaiAgentOpencode:
        // No preset for solid magenta; reuse success sequence which flashes green.
        return &sequence_success;
    default:
        return &sequence_success;
    }
}

void effects_apply(const FaiFrame* notify) {
    if(!g_notifications || !notify) return;

    switch(notify->state) {
    case FaiStateNeedsInput:
        notification_message(g_notifications, &sequence_display_backlight_on);
        notification_message(g_notifications, agent_blink(notify->agent));
        notification_message(g_notifications, &sequence_double_vibro);
        break;
    case FaiStateDone:
        notification_message(g_notifications, &sequence_display_backlight_on);
        notification_message(g_notifications, agent_solid_done(notify->agent));
        notification_message(g_notifications, &sequence_single_vibro);
        break;
    case FaiStateRunning:
        // Silent — running state is common; we do not want to spam the user.
        break;
    case FaiStateOff:
    default:
        notification_message(g_notifications, &sequence_reset_rgb);
        break;
    }
}

void effects_clear(void) {
    if(!g_notifications) return;
    notification_message(g_notifications, &sequence_reset_rgb);
    notification_message(g_notifications, &sequence_reset_vibro);
}
