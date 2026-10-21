#!/usr/bin/env python3
"""Generate the PWA icons without any image library (pure stdlib).

A rounded indigo square with a white chevron; the maskable variant is
full-bleed with the glyph shrunk into the 80% safe zone. Outputs PNGs
(192, 512, maskable 512, apple-touch 180) into icons/.
"""
import math
import pathlib
import struct
import zlib

ACCENT = (79, 70, 229)   # #4f46e5
WHITE = (255, 255, 255)
OUT = pathlib.Path(__file__).resolve().parent.parent / "icons"


def dist_to_segment(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    denom = vx * vx + vy * vy
    t = 0.0 if denom == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / denom))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def render(size, maskable=False):
    rows = bytearray()
    r = 0 if maskable else size * 0.19
    half = size / 2
    # chevron: left-top -> right-middle -> left-bottom
    pts = [(size * 0.30, size * 0.32), (size * 0.58, size * 0.50), (size * 0.30, size * 0.68)]
    if maskable:  # shrink into the maskable safe zone (>= 80%)
        pts = [(half + (x - half) * 0.62, half + (y - half) * 0.62) for x, y in pts]
    (ax, ay), (bx, by), (cx, cy) = pts
    th = size * (0.055 if maskable else 0.065)
    for y in range(size):
        rows.append(0)  # PNG filter type 0
        for x in range(size):
            inside = True
            if not maskable:
                in_band_x = r <= x <= size - r
                in_band_y = r <= y <= size - r
                inside = in_band_x or in_band_y
                if not inside:
                    corner_x = r if x < half else size - r
                    corner_y = r if y < half else size - r
                    inside = math.hypot(x - corner_x, y - corner_y) <= r
            if inside:
                d = min(dist_to_segment(x, y, ax, ay, bx, by),
                        dist_to_segment(x, y, bx, by, cx, cy))
                color, alpha = (WHITE if d <= th else ACCENT), 255
            else:
                color, alpha = (0, 0, 0), 0
            rows += bytes(color) + bytes([alpha])
    return rows


def png(size, raw):
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def main():
    OUT.mkdir(exist_ok=True)
    for name, size, maskable in [
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("icon-maskable-512.png", 512, True),
        ("apple-touch-icon.png", 180, False),
    ]:
        (OUT / name).write_bytes(png(size, render(size, maskable)))
        print(f"wrote icons/{name}")


if __name__ == "__main__":
    main()
