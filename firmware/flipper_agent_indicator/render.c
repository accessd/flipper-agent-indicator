#include "render.h"

#include <gui/canvas.h>

#include <string.h>

#define FAI_TEXT_LINE_CHARS 21 // ~128px at Secondary font, 6px glyph
#define FAI_TEXT_MAX_LINES  3

const char* render_agent_name(uint8_t agent) {
    switch(agent) {
    case FaiAgentClaude:
        return "Claude";
    case FaiAgentCodex:
        return "Codex";
    case FaiAgentOpencode:
        return "OpenCode";
    default:
        return "Agent";
    }
}

const char* render_state_name(uint8_t state) {
    switch(state) {
    case FaiStateOff:
        return "off";
    case FaiStateRunning:
        return "running";
    case FaiStateNeedsInput:
        return "needs-input";
    case FaiStateDone:
        return "done";
    default:
        return "?";
    }
}

void render_idle(Canvas* canvas) {
    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 4, 14, "Agent Indicator");
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 4, 32, "Waiting for agents...");
    canvas_draw_str(canvas, 4, 48, "BLE Serial ready");
    canvas_draw_str(canvas, 4, 62, "Back: exit");
}

// Copy up to `line_cap-1` chars from [src, src+span) into `dst` and NUL-term.
static void fai_copy_span(char* dst, size_t line_cap, const char* src, size_t span) {
    if(line_cap == 0) return;
    const size_t take = span < (line_cap - 1) ? span : (line_cap - 1);
    memcpy(dst, src, take);
    dst[take] = '\0';
}

// Greedy wrap: fills up to FAI_TEXT_MAX_LINES lines of FAI_TEXT_LINE_CHARS
// chars, preferring to break on spaces. Truncates hard past the last line.
static int fai_wrap(const char* text, char lines[FAI_TEXT_MAX_LINES][FAI_TEXT_LINE_CHARS + 1]) {
    const size_t len = strlen(text);
    size_t pos = 0;
    int used = 0;

    while(pos < len && used < FAI_TEXT_MAX_LINES) {
        const size_t remaining = len - pos;
        if(remaining <= FAI_TEXT_LINE_CHARS) {
            fai_copy_span(lines[used], sizeof(lines[used]), text + pos, remaining);
            used++;
            break;
        }

        // Look for last space within the window.
        size_t split = FAI_TEXT_LINE_CHARS;
        for(size_t i = FAI_TEXT_LINE_CHARS; i > 0; i--) {
            if(text[pos + i - 1] == ' ') {
                split = i - 1;
                break;
            }
        }
        if(split == 0) split = FAI_TEXT_LINE_CHARS; // no space — hard break

        fai_copy_span(lines[used], sizeof(lines[used]), text + pos, split);
        used++;
        pos += split;
        while(pos < len && text[pos] == ' ') pos++;
    }

    return used;
}

void render_notification(Canvas* canvas, const FaiFrame* notify) {
    canvas_clear(canvas);

    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 4, 12, render_agent_name(notify->agent));

    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 4, 26, render_state_name(notify->state));

    if(notify->text_len > 0) {
        char lines[FAI_TEXT_MAX_LINES][FAI_TEXT_LINE_CHARS + 1];
        memset(lines, 0, sizeof(lines));
        const int used = fai_wrap(notify->text, lines);
        int y = 40;
        for(int i = 0; i < used; i++) {
            canvas_draw_str(canvas, 4, y, lines[i]);
            y += 10;
        }
    }

    // Footer hint.
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 4, 62, "OK: dismiss");
}
