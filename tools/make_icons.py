#!/usr/bin/env python3
"""Generate Mikan Focus PWA icons (pure stdlib — no PIL).

Draws a pixel-supersampled mikan (mandarin orange) with a leaf.
Outputs: icon-192.png, icon-512.png, icon-maskable-512.png
"""
import math
import pathlib
import struct
import zlib

HERE = pathlib.Path(__file__).resolve().parent.parent


def png_chunk(tag: bytes, data: bytes) -> bytes:
    c = struct.pack(">I", len(data)) + tag + data
    c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return c


def write_png(path: pathlib.Path, w: int, h: int, pixels):
    raw = bytearray()
    for row in pixels:
        raw += b"\x00"
        for px in row:
            raw += struct.pack("BBBB", *px)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    out = (b"\x89PNG\r\n\x1a\n"
           + png_chunk(b"IHDR", ihdr)
           + png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + png_chunk(b"IEND", b""))
    path.write_bytes(out)


def rot(px, py, ang):
    c, s = math.cos(ang), math.sin(ang)
    return px * c - py * s, px * s + py * c


def in_ellipse(px, py, cx, cy, rx, ry, ang=0.0):
    x, y = px - cx, py - cy
    if ang:
        x, y = rot(x, y, -ang)
    return (x / rx) ** 2 + (y / ry) ** 2 <= 1.0


# colors (r,g,b)
ORANGE = (245, 166, 35)
ORANGE_HI = (255, 196, 77)
ORANGE_DK = (232, 137, 12)
ORANGE_EDGE = (201, 112, 6)
LEAF = (106, 158, 63)
LEAF_DK = (90, 142, 51)
STEM = (138, 90, 42)
GLOSS = (255, 255, 255)


def sample(px, py, scale):
    """Return RGBA at normalized coords (-1..1) for a mikan scaled by `scale`."""
    # fruit circle
    r = 0.60 * scale
    cx, cy = 0.0, 0.07 * scale
    dx, dy = px - cx, py - cy
    d = math.hypot(dx, dy)

    if d <= r:
        # shading: light from top-left
        t = (dx * -0.55 + dy * -0.75) / (r * 1.4)  # -1..1-ish
        if t > 0.45:
            col = ORANGE_HI
        elif t > -0.15:
            col = ORANGE
        else:
            col = ORANGE_DK
        # edge ring
        if d > r - 0.045 * scale:
            col = ORANGE_EDGE
        # gloss highlight
        if in_ellipse(px, py, -0.22 * scale, -0.18 * scale, 0.16 * scale, 0.10 * scale, -0.5):
            col = tuple(min(255, int(c * 0.35 + 255 * 0.65)) for c in col)
        return (*col, 255)

    # leaf (rotated ellipse)
    if in_ellipse(px, py, 0.22 * scale, -0.62 * scale, 0.30 * scale, 0.13 * scale, -0.6):
        # leaf vein: darker along centerline
        x, y = rot(px - 0.22 * scale, py + 0.62 * scale, 0.6)
        if abs(y) < 0.022 * scale:
            return (*LEAF_DK, 255)
        return (*LEAF, 255)

    # stem
    if abs(px - 0.0) < 0.055 * scale and -0.62 * scale <= py <= -0.42 * scale:
        return (*STEM, 255)

    return (0, 0, 0, 0)


def render(size: int, scale: float = 1.0, ss: int = 3):
    px_per = 2.0 / size
    rows = []
    for j in range(size):
        row = []
        for i in range(size):
            acc = [0.0, 0.0, 0.0, 0.0]
            for sj in range(ss):
                for si in range(ss):
                    x = -1.0 + (i + (si + 0.5) / ss) * px_per
                    y = -1.0 + (j + (sj + 0.5) / ss) * px_per
                    r, g, b, a = sample(x, y, scale)
                    acc[0] += r * a
                    acc[1] += g * a
                    acc[2] += b * a
                    acc[3] += a
            n = ss * ss
            a = acc[3] / n
            if a <= 0:
                row.append((0, 0, 0, 0))
            else:
                row.append((int(acc[0] / acc[3]), int(acc[1] / acc[3]), int(acc[2] / acc[3]), int(round(a))))
        rows.append(row)
    return rows


def main():
    for size in (192, 512):
        rows = render(size, scale=1.0)
        write_png(HERE / f"icon-{size}.png", size, size, rows)
        print(f"wrote icon-{size}.png")
    # maskable: shrink fruit into the safe zone (~80% => scale 0.72)
    rows = render(512, scale=0.72, ss=3)
    write_png(HERE / "icon-maskable-512.png", 512, 512, rows)
    print("wrote icon-maskable-512.png")


if __name__ == "__main__":
    main()
