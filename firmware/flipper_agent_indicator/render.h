#pragma once

#include "protocol.h"

#include <gui/canvas.h>

#ifdef __cplusplus
extern "C" {
#endif

void render_idle(Canvas* canvas);
void render_notification(Canvas* canvas, const FaiFrame* notify);

// Return a short human-readable name for an agent id. Never NULL.
const char* render_agent_name(uint8_t agent);

// Return a short label for a state. Never NULL.
const char* render_state_name(uint8_t state);

#ifdef __cplusplus
}
#endif
