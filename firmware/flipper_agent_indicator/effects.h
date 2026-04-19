#pragma once

#include "protocol.h"

#ifdef __cplusplus
extern "C" {
#endif

// Call once at app startup, before any effects_apply/clear.
void effects_init(void);

// Release resources acquired by effects_init.
void effects_deinit(void);

// Apply per-(agent, state) LED color and vibra sequence.
void effects_apply(const FaiFrame* notify);

// Turn LED off, stop vibra.
void effects_clear(void);

#ifdef __cplusplus
}
#endif
