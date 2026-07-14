#!/usr/bin/env python3
"""Generate DroidLens PNG and ICO icon assets from vector design."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "branding" / "icons"
SIZES = (16, 32, 48, 64, 128, 256, 512)

EMERALD = (52, 168, 83, 255)
BLUE = (30, 136, 229, 255)
SLATE = (38, 50, 56, 255)
SLATE_LIGHT = (47, 59, 66, 255)
WHITE = (236, 239, 241, 255)
GRAY = (120, 144, 156, 255)
GRAY_LIGHT = (176, 190, 197, 255)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 512.0
    radius = int(108 * s)

    # Rounded background
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=SLATE)

    # UI nodes
    node_r = max(2, int(10 * s))
    line_w = max(1, int(6 * s))
    nodes = [(118, 372), (178, 332), (238, 352)]
    scaled = [(int(x * s), int(y * s)) for x, y in nodes]
    for i in range(len(scaled) - 1):
        d.line([scaled[i], scaled[i + 1]], fill=GRAY, width=line_w)
    for x, y in scaled:
        d.ellipse([x - node_r, y - node_r, x + node_r, y + node_r], fill=GRAY_LIGHT)

    # Android antennae
    for ax in (156, 338):
        x1, y1 = int(ax * s), int(118 * s)
        x2, y2 = int((ax + 18) * s), int((118 + 44) * s)
        d.rounded_rectangle([x1, y1, x2, y2], radius=max(1, int(9 * s)), fill=EMERALD)

    # Android head (approximate with ellipse + top cap)
    head_box = [int(132 * s), int(156 * s), int(380 * s), int(396 * s)]
    d.ellipse(head_box, fill=EMERALD)
    face_box = [int(164 * s), int(220 * s), int(348 * s), int(364 * s)]
    d.ellipse(face_box, fill=SLATE)

    eye_r = max(2, int(16 * s))
    for ex in (220, 292):
        cx, cy = int(ex * s), int(276 * s)
        d.ellipse([cx - eye_r, cy - eye_r, cx + eye_r, cy + eye_r], fill=WHITE)

    # Magnifying glass
    lens_cx, lens_cy = int(332 * s), int(332 * s)
    lens_r = int(78 * s)
    ring = max(2, int(22 * s))
    d.ellipse(
        [lens_cx - lens_r, lens_cy - lens_r, lens_cx + lens_r, lens_cy + lens_r],
        outline=BLUE,
        width=ring,
    )
    inner_r = int(52 * s)
    d.ellipse(
        [lens_cx - inner_r, lens_cy - inner_r, lens_cx + inner_r, lens_cy + inner_r],
        fill=(255, 255, 255, 30),
    )

    # Crosshair
    ch = max(1, int(5 * s))
    for x1, y1, x2, y2 in [
        (332, 296, 332, 318),
        (332, 346, 332, 368),
        (296, 332, 318, 332),
        (346, 332, 368, 332),
    ]:
        d.line([int(x1 * s), int(y1 * s), int(x2 * s), int(y2 * s)], fill=WHITE, width=ch)
    cr = max(2, int(14 * s))
    d.ellipse(
        [lens_cx - cr, lens_cy - cr, lens_cx + cr, lens_cy + cr],
        outline=WHITE,
        width=max(1, int(4 * s)),
    )

    # Handle
    hx1, hy1 = int(388 * s), int(388 * s)
    hx2, hy2 = int(438 * s), int(438 * s)
    d.line([hx1, hy1, hx2, hy2], fill=BLUE, width=max(2, int(22 * s)))

    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    images = {}
    for size in SIZES:
        im = draw_icon(size)
        path = OUT / f"icon-{size}.png"
        im.save(path, "PNG")
        images[size] = im
        print(f"Wrote {path}")

    # Master icon for electron-builder
    master = images[512]
    master_path = ROOT / "assets" / "branding" / "icon.png"
    master.save(master_path, "PNG")
    print(f"Wrote {master_path}")

    # Multi-size ICO for Windows
    ico_path = ROOT / "assets" / "branding" / "icon.ico"
    images[256].save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Wrote {ico_path}")

    # Favicon for web
    favicon = ROOT / "frontend" / "public" / "favicon.png"
    favicon.parent.mkdir(parents=True, exist_ok=True)
    images[32].save(favicon, "PNG")
    images[32].save(favicon.with_suffix(".ico"), format="ICO")
    print(f"Wrote {favicon}")


if __name__ == "__main__":
    main()
