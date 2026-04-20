#!/usr/bin/env python3
"""Generate Flipper FAP assets: 10x10 icon + 32x32 mascots for each state.

Run from repo root:
    .venv/bin/python scripts/generate-art.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path("firmware/flipper_agent_indicator/assets")


def new_img(size: tuple[int, int]) -> Image.Image:
    return Image.new("1", size, color=1)


def put(img: Image.Image, xy: tuple[int, int]) -> None:
    x, y = xy
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), 0)


def rect(img: Image.Image, x0: int, y0: int, x1: int, y1: int, fill: bool = True) -> None:
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if fill or x in (x0, x1) or y in (y0, y1):
                put(img, (x, y))


def rounded_head(img: Image.Image, x0: int, y0: int, x1: int, y1: int) -> None:
    # filled rectangle with corner pixels removed (gives a pill-ish rounded look)
    rect(img, x0, y0, x1, y1)
    for cx, cy in [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]:
        img.putpixel((cx, cy), 1)


def antennae(img: Image.Image, head_top_y: int) -> None:
    # two antennae sticking straight up from the head, ending in a small "bulb"
    for x in (11, 20):
        for dy in range(4):
            put(img, (x, head_top_y - dy))
        # bulb
        rect(img, x - 1, head_top_y - 6, x + 1, head_top_y - 5)


def eyes_open(img: Image.Image, cy: int) -> None:
    for cx in (11, 20):
        rect(img, cx - 1, cy - 1, cx + 1, cy + 1)


def eyes_happy(img: Image.Image, cy: int) -> None:
    # ^ ^ upward arcs
    for cx in (11, 20):
        put(img, (cx - 2, cy + 1))
        put(img, (cx - 1, cy))
        put(img, (cx, cy - 1))
        put(img, (cx + 1, cy))
        put(img, (cx + 2, cy + 1))


def mouth_line(img: Image.Image, y: int) -> None:
    for x in range(13, 19):
        put(img, (x, y))


def mouth_smile(img: Image.Image, y: int) -> None:
    put(img, (12, y))
    put(img, (13, y + 1))
    for x in range(14, 18):
        put(img, (x, y + 2))
    put(img, (18, y + 1))
    put(img, (19, y))


def mouth_o(img: Image.Image, y: int) -> None:
    # small circle "!"-style surprise
    cx, cy = 15, y
    for dx, dy in [(-1, -1), (0, -1), (1, -1), (-2, 0), (2, 0), (-1, 1), (0, 1), (1, 1)]:
        put(img, (cx + dx, cy + dy))


def body(img: Image.Image) -> None:
    rect(img, 10, 22, 21, 25)  # torso
    rect(img, 12, 26, 13, 30)  # left leg
    rect(img, 18, 26, 19, 30)  # right leg


def left_arm_down(img: Image.Image) -> None:
    rect(img, 7, 22, 9, 27)


def right_arm_down(img: Image.Image) -> None:
    rect(img, 22, 22, 24, 27)


def right_arm_waving(img: Image.Image) -> None:
    # diagonal arm up-right, then a small hand
    for i in range(6):
        put(img, (22 + i, 22 - i))
    rect(img, 27, 15, 29, 17)


def right_arm_thumbs_up(img: Image.Image) -> None:
    # vertical arm + fist + thumb
    rect(img, 22, 18, 24, 25)  # forearm going up
    rect(img, 21, 13, 24, 17)  # fist
    # thumb
    put(img, (25, 15))
    put(img, (25, 14))
    put(img, (24, 13))


def exclamation(img: Image.Image) -> None:
    rect(img, 1, 10, 2, 17)  # bar
    rect(img, 1, 19, 2, 20)  # dot


def check(img: Image.Image) -> None:
    # a bold ✓ glyph in the top-left corner
    put(img, (1, 15))
    put(img, (2, 16))
    put(img, (3, 17))
    put(img, (4, 16))
    put(img, (5, 15))
    put(img, (6, 14))
    put(img, (7, 13))


def mascot_idle() -> Image.Image:
    img = new_img((32, 32))
    antennae(img, head_top_y=5)
    rounded_head(img, 5, 6, 26, 21)
    # face cavity: clear a centered area so we can draw features on white
    for y in range(8, 20):
        for x in range(7, 25):
            img.putpixel((x, y), 1)
    eyes_open(img, cy=12)
    mouth_line(img, y=17)
    body(img)
    left_arm_down(img)
    right_arm_down(img)
    return img


def mascot_needs_input() -> Image.Image:
    img = new_img((32, 32))
    antennae(img, head_top_y=5)
    rounded_head(img, 5, 6, 26, 21)
    for y in range(8, 20):
        for x in range(7, 25):
            img.putpixel((x, y), 1)
    eyes_open(img, cy=12)
    mouth_o(img, y=17)
    body(img)
    left_arm_down(img)
    right_arm_waving(img)
    exclamation(img)
    return img


def mascot_done() -> Image.Image:
    img = new_img((32, 32))
    antennae(img, head_top_y=5)
    rounded_head(img, 5, 6, 26, 21)
    for y in range(8, 20):
        for x in range(7, 25):
            img.putpixel((x, y), 1)
    eyes_happy(img, cy=12)
    mouth_smile(img, y=16)
    body(img)
    left_arm_down(img)
    right_arm_thumbs_up(img)
    check(img)
    return img


def icon_10x10() -> Image.Image:
    img = new_img((10, 10))
    d = ImageDraw.Draw(img)
    # antennae
    for x in (3, 6):
        d.point((x, 0), fill=0)
        d.point((x, 1), fill=0)
    # head border
    d.rectangle([1, 2, 8, 8], outline=0)
    # eyes
    d.point((3, 4), fill=0)
    d.point((6, 4), fill=0)
    # mouth
    d.line([(3, 7), (6, 7)], fill=0)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    icon_10x10().save(OUT / "icon.png", optimize=True)
    mascot_idle().save(OUT / "mascot_idle.png", optimize=True)
    mascot_needs_input().save(OUT / "mascot_needs_input.png", optimize=True)
    mascot_done().save(OUT / "mascot_done.png", optimize=True)
    print(f"wrote: {OUT}/icon.png, mascot_idle.png, mascot_needs_input.png, mascot_done.png")


if __name__ == "__main__":
    main()
