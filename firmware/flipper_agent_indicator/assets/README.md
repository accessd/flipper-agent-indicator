# Assets

## `icon.png` (required before first build)

ufbt expects a **10x10** 1-bit PNG at `assets/icon.png`. The build system
(`fbt_assets.py`) converts it to an `Icon` resource at compile time.

Constraints:

- Dimensions: exactly 10x10 pixels.
- Color depth: 1-bit (black/white). Transparent pixels are treated as white.
- Format: PNG.
- Filename: `icon.png` (referenced from `../application.fam` as
  `fap_icon="assets/icon.png"`).

Design tips:

- Flipper screen is monochrome, so contrast only. No anti-aliasing.
- Keep 1-2px padding from the edges to avoid visual clipping in the
  launcher grid.

Generate with any pixel editor (Aseprite, Pixelorama, GIMP at 1-bit
indexed mode). The file is not checked in yet because we refuse to commit
placeholder binaries — add a real icon before the first ufbt build or the
manifest will fail to resolve.
