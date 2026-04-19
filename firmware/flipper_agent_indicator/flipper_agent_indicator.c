#include "ble_serial.h"
#include "effects.h"
#include "protocol.h"
#include "render.h"

#include <furi/furi.h>
#include <gui/gui.h>
#include <input/input.h>

#define TAG            "fai.app"
#define FAI_QUEUE_LEN  8

typedef enum {
    FaiUiIdle,
    FaiUiNotification,
} FaiUiMode;

typedef struct {
    FuriMutex* mutex;
    FaiUiMode mode;
    FaiFrame current; // valid iff mode == FaiUiNotification
} FaiUiState;

typedef struct {
    FuriMessageQueue* frame_queue; // FaiFrame
    FuriMessageQueue* input_queue; // InputEvent
    Gui* gui;
    ViewPort* view_port;
    FaiUiState ui;
    bool running;
} FaiApp;

// ---- GUI callbacks -------------------------------------------------------

static void fai_draw_cb(Canvas* canvas, void* ctx) {
    FaiApp* app = ctx;
    furi_mutex_acquire(app->ui.mutex, FuriWaitForever);
    if(app->ui.mode == FaiUiNotification) {
        render_notification(canvas, &app->ui.current);
    } else {
        render_idle(canvas);
    }
    furi_mutex_release(app->ui.mutex);
}

static void fai_input_cb(InputEvent* event, void* ctx) {
    FaiApp* app = ctx;
    furi_message_queue_put(app->input_queue, event, 0);
}

// ---- helpers -------------------------------------------------------------

static void fai_send_ack(uint8_t agent) {
    FaiFrame ack = {.kind = FaiFrameAck, .agent = agent};
    uint8_t buf[4];
    const int n = fai_protocol_encode(&ack, buf, sizeof(buf));
    if(n > 0) {
        ble_serial_send(buf, (size_t)n);
    }
}

static void fai_send_pong(void) {
    FaiFrame pong = {.kind = FaiFramePong};
    uint8_t buf[2];
    const int n = fai_protocol_encode(&pong, buf, sizeof(buf));
    if(n > 0) {
        ble_serial_send(buf, (size_t)n);
    }
}

static void fai_handle_frame(FaiApp* app, const FaiFrame* frame) {
    switch(frame->kind) {
    case FaiFrameNotify:
        furi_mutex_acquire(app->ui.mutex, FuriWaitForever);
        app->ui.mode = FaiUiNotification;
        app->ui.current = *frame;
        furi_mutex_release(app->ui.mutex);
        effects_apply(frame);
        view_port_update(app->view_port);
        break;
    case FaiFramePing:
        fai_send_pong();
        break;
    case FaiFrameAck:
    case FaiFramePong:
        // Unexpected from host; ignore.
        break;
    }
}

static void fai_handle_input(FaiApp* app, const InputEvent* event) {
    if(event->type != InputTypeShort) return;

    if(event->key == InputKeyBack) {
        app->running = false;
        return;
    }

    if(event->key == InputKeyOk) {
        furi_mutex_acquire(app->ui.mutex, FuriWaitForever);
        const bool has_notify = app->ui.mode == FaiUiNotification;
        const uint8_t agent = app->ui.current.agent;
        if(has_notify) {
            app->ui.mode = FaiUiIdle;
            memset(&app->ui.current, 0, sizeof(app->ui.current));
        }
        furi_mutex_release(app->ui.mutex);

        if(has_notify) {
            fai_send_ack(agent);
            effects_clear();
            view_port_update(app->view_port);
        }
    }
}

// ---- entry point ---------------------------------------------------------

int32_t flipper_agent_indicator_app(void* p) {
    UNUSED(p);

    FaiApp app = {0};
    app.ui.mutex = furi_mutex_alloc(FuriMutexTypeNormal);
    app.ui.mode = FaiUiIdle;
    app.running = true;

    app.frame_queue = furi_message_queue_alloc(FAI_QUEUE_LEN, sizeof(FaiFrame));
    app.input_queue = furi_message_queue_alloc(FAI_QUEUE_LEN, sizeof(InputEvent));

    app.view_port = view_port_alloc();
    view_port_draw_callback_set(app.view_port, fai_draw_cb, &app);
    view_port_input_callback_set(app.view_port, fai_input_cb, &app);

    app.gui = furi_record_open(RECORD_GUI);
    gui_add_view_port(app.gui, app.view_port, GuiLayerFullscreen);

    effects_init();
    ble_serial_init(app.frame_queue);

    FURI_LOG_I(TAG, "started");

    while(app.running) {
        FaiFrame frame;
        if(furi_message_queue_get(app.frame_queue, &frame, 50) == FuriStatusOk) {
            fai_handle_frame(&app, &frame);
        }

        InputEvent input;
        if(furi_message_queue_get(app.input_queue, &input, 0) == FuriStatusOk) {
            fai_handle_input(&app, &input);
        }
    }

    FURI_LOG_I(TAG, "stopping");

    ble_serial_deinit();
    effects_deinit();

    gui_remove_view_port(app.gui, app.view_port);
    view_port_free(app.view_port);
    furi_record_close(RECORD_GUI);

    furi_message_queue_free(app.frame_queue);
    furi_message_queue_free(app.input_queue);
    furi_mutex_free(app.ui.mutex);

    return 0;
}
